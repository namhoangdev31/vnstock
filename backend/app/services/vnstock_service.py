"""Dịch vụ VnstockService — Cổng kết nối dữ liệu tài chính toàn diện vnstock v4.

Cung cấp giao diện nhất quán và hoàn chỉnh cho toàn bộ hệ sinh thái dữ liệu vnstock:
- Bộ chuyển đổi API hiện đại (Quote, Listing, Company, Finance, Retail, Market, Reference, Fundamental)
- Cơ chế tự động thử lại đa nguồn dữ liệu (VCI → KBS → MSN → DNSE)
- Bộ điều tiết tần suất gọi API (Rate Limiting chống khóa IP, tuân thủ AGENTS §7.2)
- Toàn diện 5 phân hệ: Tham chiếu, Hồ sơ doanh nghiệp, Bảng giá & Giao dịch, Báo cáo & Chỉ số TC, Hàng hóa & Ngoại tệ
- Chuyển đổi và chuẩn hóa dữ liệu linh hoạt (pandas DataFrame / dict / list)
"""

import logging
from datetime import date
from typing import Any

import pandas as pd
from vnstock import (
    Company,
    Finance,
    Fundamental,
    Listing,
    Market,
    Quote,
    Reference,
    Retail,
)

from app.core.config import settings
from app.services.rate_limit import RateLimiter

logger = logging.getLogger(__name__)


class VnstockServiceError(Exception):
    """Ngoại lệ phát sinh khi tất cả các nguồn dữ liệu vnstock đều thất bại."""


class VnstockService:
    """Đóng gói toàn diện thư viện vnstock với cơ chế đa nguồn và quản lý lỗi chuẩn hóa."""

    # Danh sách các nguồn hợp lệ theo từng bộ chuyển đổi của vnstock v4.0.6
    VALID_SOURCES_QUOTE = ["vci", "kbs", "msn", "dnse"]
    VALID_SOURCES_LISTING = ["kbs", "vci", "msn"]
    VALID_SOURCES_COMPANY = ["kbs", "vci"]
    VALID_SOURCES_FINANCE = ["kbs", "vci"]

    def __init__(
        self,
        source: str | None = None,
        fallback_source: str | None = None,
        tertiary_source: str | None = None,
        limiter: RateLimiter | None = None,
    ) -> None:
        """Khởi tạo dịch vụ VnstockService với danh sách nguồn ưu tiên và bộ điều tiết tần suất."""
        self.source = (source or settings.VNSTOCK_SOURCE).lower()
        self.fallback_source = (
            fallback_source or settings.VNSTOCK_FALLBACK_SOURCE
        ).lower()
        self.tertiary_source = (
            tertiary_source or settings.VNSTOCK_TERTIARY_SOURCE
        ).lower()
        self._limiter = limiter or RateLimiter(
            min_delay=settings.VNSTOCK_REQUEST_MIN_DELAY
        )

    @property
    def sources(self) -> list[str]:
        """Danh sách các nguồn dữ liệu có thứ tự, khử trùng lặp.

        Ưu tiên các nguồn theo Rule 7.1 (VCI -> KBS -> MSN -> DNSE).
        Nếu nguồn cấu hình là TCBS (không còn được Quote hỗ trợ ở v4.0.6),
        hệ thống sẽ tự động điều phối fallback sang VCI và KBS.
        """
        configured = [self.source, self.fallback_source, self.tertiary_source]
        normalized: list[str] = []
        for s in configured:
            if s and s not in normalized:
                normalized.append(s)

        # Bổ sung các nguồn chuẩn nếu chưa có trong cấu hình
        for default_src in ["vci", "kbs", "msn", "dnse"]:
            if default_src not in normalized:
                normalized.append(default_src)

        return normalized

    def _get_valid_sources(self, allowed_sources: list[str]) -> list[str]:
        """Lọc danh sách nguồn hợp lệ cho từng bộ chuyển đổi cụ thể."""
        return [s for s in self.sources if s in allowed_sources]

    def _throttle(self) -> None:
        """Kích hoạt độ trễ tối thiểu giữa các lệnh gọi API bên ngoài để tránh nghẽn/khóa IP."""
        self._limiter.wait()

    # =========================================================================
    # PHÂN HỆ 1: THAM CHIẾU & DANH MỤC THỊ TRƯỜNG (REFERENCE DATA)
    # =========================================================================

    def fetch_all_symbols(self) -> pd.DataFrame:
        """Lấy danh sách tất cả các mã cổ phiếu đang niêm yết trên thị trường (HOSE, HNX, UPCOM).

        Trả về:
            pd.DataFrame chứa danh sách mã, tên tổ chức và thông tin sàn niêm yết.
        """
        valid_sources = self._get_valid_sources(self.VALID_SOURCES_LISTING)
        for src in valid_sources:
            try:
                self._throttle()
                lst = Listing(source=src, show_log=False)
                # Ưu tiên symbols_by_exchange để có sẵn thông tin cột sàn niêm yết (exchange)
                if hasattr(lst, "symbols_by_exchange"):
                    df = lst.symbols_by_exchange()
                    if df is not None and not df.empty:
                        logger.info(
                            "Đã tải %d mã cổ phiếu (kèm cột sàn) qua nguồn %s",
                            len(df),
                            src,
                        )
                        return df

                df = lst.all_symbols()
                if df is not None and not df.empty:
                    logger.info("Đã tải %d mã cổ phiếu qua nguồn %s", len(df), src)
                    return df
            except Exception:
                logger.warning(
                    "Lỗi tải danh sách mã qua nguồn %s, đang thử nguồn dự phòng...",
                    src,
                    exc_info=True,
                )
                continue

        raise VnstockServiceError(
            "Không thể tải danh sách mã cổ phiếu từ tất cả các nguồn"
        )

    def fetch_symbols_by_exchange(self, exchange: str | None = None) -> pd.DataFrame:
        """Lấy danh sách các mã cổ phiếu có thông tin sàn niêm yết (HOSE, HNX, UPCOM).

        Tham số:
            exchange: Tên sàn giao dịch ('HOSE', 'HNX', 'UPCOM') hoặc None để lấy toàn bộ các sàn.

        Trả về:
            pd.DataFrame chứa danh sách cổ phiếu kèm thông tin sàn niêm yết.
        """
        valid_sources = self._get_valid_sources(self.VALID_SOURCES_LISTING)
        for src in valid_sources:
            try:
                self._throttle()
                lst = Listing(source=src, show_log=False)
                df = lst.symbols_by_exchange()
                if df is not None and not df.empty:
                    if exchange and "exchange" in df.columns:
                        target_exs = (
                            {"HOSE", "HSX"}
                            if exchange.upper() in ("HOSE", "HSX")
                            else {exchange.upper()}
                        )
                        filtered = df[
                            df["exchange"].str.upper().isin(target_exs)
                        ].copy()
                        logger.info(
                            "Đã tải %d mã thuộc sàn %s qua nguồn %s",
                            len(filtered),
                            exchange,
                            src,
                        )
                        return filtered
                    logger.info(
                        "Đã tải toàn bộ %d mã kèm sàn qua nguồn %s", len(df), src
                    )
                    return df
            except Exception:
                logger.warning(
                    "Lỗi tải mã theo sàn %s qua nguồn %s, thử nguồn khác...",
                    exchange or "tất cả",
                    src,
                    exc_info=True,
                )
                continue

        raise VnstockServiceError(
            f"Không thể tải danh sách mã chứng khoán theo sàn ({exchange or 'tất cả'})"
        )

    def fetch_symbols_by_industry(self) -> pd.DataFrame:
        """Lấy danh sách mã chứng khoán phân loại theo ngành (chuẩn ICB/KBS).

        Trả về:
            pd.DataFrame danh mục mã kèm phân ngành chi tiết.
        """
        valid_sources = self._get_valid_sources(self.VALID_SOURCES_LISTING)
        for src in valid_sources:
            try:
                self._throttle()
                lst = Listing(source=src, show_log=False)
                # Thử symbols_by_industries trước, sau đó thử industries_icb
                if hasattr(lst, "symbols_by_industries"):
                    df = lst.symbols_by_industries()
                else:
                    df = lst.industries_icb()

                if df is not None and not df.empty:
                    logger.info(
                        "Đã tải danh mục phân ngành (%d dòng) qua %s", len(df), src
                    )
                    return df
            except Exception:
                logger.warning(
                    "Lỗi tải phân ngành qua %s, thử tiếp...", src, exc_info=True
                )
                continue

        raise VnstockServiceError(
            "Không thể tải danh mục phân ngành từ tất cả các nguồn"
        )

    def fetch_group_symbols(self, group: str = "VN30") -> list[str]:
        """Lấy danh sách các mã cổ phiếu thuộc rổ chỉ số (ví dụ: VN30, VN100, VNFINLEAD).

        Tham số:
            group: Tên nhóm chỉ số (mặc định: 'VN30').

        Trả về:
            list[str] danh sách các mã cổ phiếu thành viên.
        """
        valid_sources = self._get_valid_sources(self.VALID_SOURCES_LISTING)
        for src in valid_sources:
            try:
                self._throttle()
                lst = Listing(source=src, show_log=False)
                result = lst.symbols_by_group(group=group.upper())
                symbols = self._series_to_symbols(result)
                if symbols:
                    logger.info(
                        "Đã tải %d mã cho nhóm chỉ số %s qua nguồn %s",
                        len(symbols),
                        group,
                        src,
                    )
                    return symbols
            except Exception:
                logger.warning(
                    "Lỗi tải nhóm chỉ số %s qua nguồn %s, thử tiếp...",
                    group,
                    src,
                    exc_info=True,
                )
                continue

        raise VnstockServiceError(f"Không thể tải danh sách mã cho nhóm chỉ số {group}")

    def fetch_index_list(self) -> pd.DataFrame:
        """Lấy danh sách toàn bộ các chỉ số thị trường chứng khoán Việt Nam (VNINDEX, VN30, HNX,...).

        Trả về:
            pd.DataFrame thông tin và mã các chỉ số.
        """
        try:
            self._throttle()
            ref = Reference()
            df = ref.index.list()
            if df is not None and not df.empty:
                logger.info(
                    "Đã tải danh sách %d chỉ số thị trường qua Reference", len(df)
                )
                return df
        except Exception:
            logger.warning(
                "Lỗi tải danh sách chỉ số thị trường qua Reference", exc_info=True
            )

        return pd.DataFrame()

    def fetch_derivatives_list(self) -> pd.DataFrame:
        """Lấy danh sách các hợp đồng tương lai phái sinh đang giao dịch (VN30F1M, VN30F2M,...).

        Trả về:
            pd.DataFrame danh mục hợp đồng phái sinh.
        """
        valid_sources = self._get_valid_sources(self.VALID_SOURCES_LISTING)
        for src in valid_sources:
            try:
                self._throttle()
                lst = Listing(source=src, show_log=False)
                if hasattr(lst, "all_future_indices"):
                    df = lst.all_future_indices()
                    if df is not None and not df.empty:
                        logger.info("Đã tải %d hợp đồng phái sinh qua %s", len(df), src)
                        return df
            except Exception:
                continue

        # Thử qua Reference layer
        try:
            self._throttle()
            ref = Reference()
            df = ref.futures().list()
            if df is not None and not df.empty:
                return df
        except Exception:
            pass

        return pd.DataFrame()

    def fetch_funds_list(self) -> pd.DataFrame:
        """Lấy danh sách các chứng chỉ quỹ mở FMarket và chứng chỉ quỹ ETF.

        Trả về:
            pd.DataFrame danh mục quỹ mở và ETF.
        """
        try:
            self._throttle()
            ref = Reference()
            df = ref.fund.list()
            if df is not None and not df.empty:
                logger.info("Đã tải danh mục quỹ (%d quỹ) qua Reference.fund", len(df))
                return df
        except Exception:
            logger.warning("Lỗi tải danh mục quỹ qua Reference.fund", exc_info=True)

        return pd.DataFrame()

    def fetch_covered_warrants_list(self) -> pd.DataFrame | pd.Series:
        """Lấy danh sách các chứng quyền có bảo đảm (Covered Warrants - CW) đang niêm yết trên HOSE.

        Trả về:
            pd.DataFrame hoặc pd.Series chứa danh sách mã chứng quyền.
        """
        valid_sources = self._get_valid_sources(self.VALID_SOURCES_LISTING)
        for src in valid_sources:
            try:
                self._throttle()
                lst = Listing(source=src, show_log=False)
                if hasattr(lst, "all_covered_warrant"):
                    res = lst.all_covered_warrant()
                    if res is not None and not res.empty:
                        logger.info("Đã tải %d chứng quyền qua %s", len(res), src)
                        return res
            except Exception:
                continue

        # Thử qua Reference layer
        try:
            self._throttle()
            ref = Reference()
            res = ref.warrant().list()
            if res is not None and not res.empty:
                return res
        except Exception:
            pass

        return pd.DataFrame()

    def fetch_bonds_list(self, bond_type: str = "all") -> pd.DataFrame:
        """Lấy danh sách trái phiếu doanh nghiệp và trái phiếu chính phủ niêm yết trên HNX.

        Tham số:
            bond_type: 'all' (toàn bộ), 'corporate' (doanh nghiệp), 'government' (chính phủ).

        Trả về:
            pd.DataFrame chứa mã trái phiếu và phân loại (symbol, type).
        """
        try:
            self._throttle()
            ref = Reference()
            df = ref.bond.list(bond_type=bond_type)
            if df is not None and not df.empty:
                logger.info("Đã tải %d mã trái phiếu qua Reference.bond", len(df))
                return df
        except Exception:
            logger.warning(
                "Lỗi tải danh mục trái phiếu qua Reference.bond", exc_info=True
            )

        # Fallback thử qua VCI listing nếu Reference lỗi
        try:
            self._throttle()
            lst = Listing(source="vci", show_log=False)
            bonds_corp = (
                lst.all_bonds()
                if bond_type in ("all", "corporate")
                else pd.Series(dtype="object")
            )
            bonds_gov = (
                lst.all_government_bonds()
                if bond_type in ("all", "government")
                else pd.Series(dtype="object")
            )
            df_corp = (
                pd.DataFrame({"symbol": bonds_corp, "type": "corporate"})
                if not bonds_corp.empty
                else pd.DataFrame(columns=["symbol", "type"])
            )
            df_gov = (
                pd.DataFrame({"symbol": bonds_gov, "type": "government"})
                if not bonds_gov.empty
                else pd.DataFrame(columns=["symbol", "type"])
            )
            combined = pd.concat([df_corp, df_gov], ignore_index=True)
            if not combined.empty:
                return combined
        except Exception:
            pass

        return pd.DataFrame()

    def search_symbols(self, query: str, limit: int = 10) -> pd.DataFrame:
        """Tìm kiếm mã chứng khoán hoặc thông tin liên quan theo từ khóa.

        Tham số:
            query: Từ khóa tìm kiếm (mã, tên công ty).
            limit: Số lượng kết quả tối đa (mặc định: 10).

        Trả về:
            pd.DataFrame kết quả tìm kiếm.
        """
        try:
            self._throttle()
            ref = Reference()
            df = ref.search.symbol(query=query, limit=limit)
            if df is not None and not df.empty:
                logger.info("Tìm kiếm '%s' trả về %d kết quả", query, len(df))
                return df
        except Exception:
            logger.warning(
                "Lỗi tìm kiếm mã chứng khoán cho từ khóa '%s'", query, exc_info=True
            )

        return pd.DataFrame()

    @staticmethod
    def _series_to_symbols(result: object) -> list[str]:
        """Chuẩn hóa dữ liệu Series/list/DataFrame thành danh sách các mã chuỗi ký tự."""
        if result is None:
            return []
        if isinstance(result, pd.Series):
            return [str(s) for s in result.tolist() if str(s).strip()]
        if isinstance(result, pd.DataFrame):
            col = "symbol" if "symbol" in result.columns else result.columns[0]
            return [str(s) for s in result[col].tolist() if str(s).strip()]
        if isinstance(result, (list, tuple)):
            return [str(s) for s in result if str(s).strip()]
        return []

    # =========================================================================
    # PHÂN HỆ 2: HỒ SƠ & DỮ LIỆU DOANH NGHIỆP (COMPANY DATA)
    # =========================================================================

    def fetch_company_overview(self, symbol: str) -> dict[str, Any]:
        """Lấy thông tin tổng quan/hồ sơ cơ bản của doanh nghiệp.

        Tham số:
            symbol: Mã cổ phiếu (ví dụ: 'VNM', 'FPT').

        Trả về:
            dict chứa thông tin tóm tắt về doanh nghiệp.
        """
        valid_sources = self._get_valid_sources(self.VALID_SOURCES_COMPANY)
        for src in valid_sources:
            try:
                self._throttle()
                c = Company(symbol=symbol, source=src, show_log=False)
                df = c.overview()
                if df is not None and not df.empty:
                    return df.iloc[0].to_dict()
            except Exception:
                logger.warning(
                    "Lỗi tải hồ sơ doanh nghiệp %s qua nguồn %s, thử tiếp...",
                    symbol,
                    src,
                    exc_info=True,
                )
                continue

        raise VnstockServiceError(f"Không thể tải hồ sơ doanh nghiệp cho {symbol}")

    def fetch_company_shareholders(self, symbol: str) -> pd.DataFrame:
        """Lấy danh sách cổ đông lớn và tỷ lệ sở hữu của doanh nghiệp.

        Tham số:
            symbol: Mã cổ phiếu.

        Trả về:
            pd.DataFrame danh sách cổ đông lớn.
        """
        valid_sources = self._get_valid_sources(self.VALID_SOURCES_COMPANY)
        for src in valid_sources:
            try:
                self._throttle()
                c = Company(symbol=symbol, source=src, show_log=False)
                df = c.shareholders()
                if df is not None and not df.empty:
                    logger.info(
                        "Đã tải %d cổ đông lớn của %s qua %s", len(df), symbol, src
                    )
                    return df
            except Exception:
                continue

        return pd.DataFrame()

    def fetch_company_officers(self, symbol: str) -> pd.DataFrame:
        """Lấy danh sách ban lãnh đạo, HĐQT, ban kiểm soát và ban điều hành.

        Tham số:
            symbol: Mã cổ phiếu.

        Trả về:
            pd.DataFrame danh sách nhân sự ban lãnh đạo.
        """
        valid_sources = self._get_valid_sources(self.VALID_SOURCES_COMPANY)
        for src in valid_sources:
            try:
                self._throttle()
                c = Company(symbol=symbol, source=src, show_log=False)
                df = c.officers()
                if df is not None and not df.empty:
                    logger.info(
                        "Đã tải %d lãnh đạo của %s qua %s", len(df), symbol, src
                    )
                    return df
            except Exception:
                continue

        return pd.DataFrame()

    def fetch_company_subsidiaries(self, symbol: str) -> pd.DataFrame:
        """Lấy danh sách các công ty con và công ty liên kết của doanh nghiệp.

        Tham số:
            symbol: Mã cổ phiếu.

        Trả về:
            pd.DataFrame danh sách công ty con và tỷ lệ sở hữu.
        """
        valid_sources = self._get_valid_sources(self.VALID_SOURCES_COMPANY)
        for src in valid_sources:
            try:
                self._throttle()
                c = Company(symbol=symbol, source=src, show_log=False)
                df = c.subsidiaries()
                if df is not None and not df.empty:
                    logger.info(
                        "Đã tải %d công ty con của %s qua %s", len(df), symbol, src
                    )
                    return df
            except Exception:
                continue

        return pd.DataFrame()

    def fetch_company_insider_trading(self, symbol: str) -> pd.DataFrame:
        """Lấy nhật ký giao dịch cổ phiếu của người nội bộ và người có liên quan.

        Tham số:
            symbol: Mã cổ phiếu.

        Trả về:
            pd.DataFrame nhật ký giao dịch nội bộ.
        """
        valid_sources = self._get_valid_sources(self.VALID_SOURCES_COMPANY)
        for src in valid_sources:
            try:
                self._throttle()
                c = Company(symbol=symbol, source=src, show_log=False)
                df = c.insider_trading()
                if df is not None and not df.empty:
                    logger.info(
                        "Đã tải %d giao dịch nội bộ của %s qua %s", len(df), symbol, src
                    )
                    return df
            except Exception:
                continue

        return pd.DataFrame()

    def fetch_company_capital_history(self, symbol: str) -> pd.DataFrame:
        """Lấy lịch sử các đợt tăng vốn điều lệ của doanh nghiệp.

        Tham số:
            symbol: Mã cổ phiếu.

        Trả về:
            pd.DataFrame lịch sử tăng vốn.
        """
        valid_sources = self._get_valid_sources(self.VALID_SOURCES_COMPANY)
        for src in valid_sources:
            try:
                self._throttle()
                c = Company(symbol=symbol, source=src, show_log=False)
                df = c.capital_history()
                if df is not None and not df.empty:
                    logger.info(
                        "Đã tải lịch sử vốn (%d sự kiện) của %s qua %s",
                        len(df),
                        symbol,
                        src,
                    )
                    return df
            except Exception:
                continue

        return pd.DataFrame()

    def fetch_company_news(self, symbol: str) -> pd.DataFrame:
        """Lấy luồng tin tức mới nhất liên quan đến mã cổ phiếu.

        Tham số:
            symbol: Mã cổ phiếu.

        Trả về:
            pd.DataFrame danh sách bài viết tin tức.
        """
        valid_sources = self._get_valid_sources(self.VALID_SOURCES_COMPANY)
        for src in valid_sources:
            try:
                self._throttle()
                c = Company(symbol=symbol, source=src, show_log=False)
                df = c.news()
                if df is not None and not df.empty:
                    logger.info("Đã tải %d tin tức cho %s qua %s", len(df), symbol, src)
                    return df
            except Exception:
                continue

        return pd.DataFrame()

    def fetch_company_events(self, symbol: str) -> pd.DataFrame:
        """Lấy lịch các sự kiện doanh nghiệp: chia cổ tức (tiền/cổ phiếu), ngày GDKHQ, ĐHCĐ.

        Tham số:
            symbol: Mã cổ phiếu.

        Trả về:
            pd.DataFrame lịch sự kiện doanh nghiệp.
        """
        valid_sources = self._get_valid_sources(self.VALID_SOURCES_COMPANY)
        for src in valid_sources:
            try:
                self._throttle()
                c = Company(symbol=symbol, source=src, show_log=False)
                df = c.events()
                if df is not None and not df.empty:
                    logger.info("Đã tải %d sự kiện cho %s qua %s", len(df), symbol, src)
                    return df
            except Exception:
                continue

        return pd.DataFrame()

    # =========================================================================
    # PHÂN HỆ 3: DỮ LIỆU THỊ TRƯỜNG & GIAO DỊCH (MARKET DATA)
    # =========================================================================

    def fetch_price_history(
        self,
        symbol: str,
        start: date | None = None,
        end: date | None = None,
        interval: str = "1D",
        count: int | None = None,
    ) -> pd.DataFrame:
        """Tải dữ liệu nến lịch sử OHLCV của cổ phiếu hoặc phái sinh.

        Tham số:
            symbol: Mã chứng khoán (ví dụ: 'VNM', 'VN30F1M').
            start: Ngày bắt đầu (tùy chọn).
            end: Ngày kết thúc (tùy chọn).
            interval: Khung thời gian nến ('1m', '5m', '15m', '1H', '1D', '1W').
            count: Số lượng thanh nến gần nhất cần lấy (tùy chọn).

        Trả về:
            pd.DataFrame chứa các cột: time, open, high, low, close, volume.
        """
        valid_sources = self._get_valid_sources(self.VALID_SOURCES_QUOTE)
        start_str = start.strftime("%Y-%m-%d") if start else None
        end_str = end.strftime("%Y-%m-%d") if end else None

        for src in valid_sources:
            try:
                self._throttle()
                q = Quote(symbol=symbol, source=src, show_log=False)
                kwargs: dict[str, Any] = {"interval": interval}
                if start_str:
                    kwargs["start"] = start_str
                if end_str:
                    kwargs["end"] = end_str
                if count is not None:
                    kwargs["count_back"] = count

                df = q.history(**kwargs)
                if df is not None and not df.empty:
                    logger.info(
                        "Đã tải %d nến giá cho %s (%s-%s, %s) qua nguồn %s",
                        len(df),
                        symbol,
                        start_str or "N/A",
                        end_str or "N/A",
                        interval,
                        src,
                    )
                    return df
            except Exception:
                logger.warning(
                    "Lỗi tải nến giá cho %s qua nguồn %s, thử nguồn tiếp...",
                    symbol,
                    src,
                    exc_info=True,
                )
                continue

        raise VnstockServiceError(f"Không thể tải lịch sử giá cho mã {symbol}")

    def fetch_intraday(
        self,
        symbol: str,
        interval: str = "1m",
        count_back: int = 300,
    ) -> pd.DataFrame:
        """Tải dữ liệu nến intraday tần suất cao gần nhất.

        Tham số:
            symbol: Mã chứng khoán.
            interval: Khung thời gian ('1m', '5m', '15m').
            count_back: Số lượng thanh nến gần nhất cần lấy (mặc định: 300).

        Trả về:
            pd.DataFrame chứa nến giá intraday.
        """
        valid_sources = self._get_valid_sources(self.VALID_SOURCES_QUOTE)
        for src in valid_sources:
            try:
                self._throttle()
                q = Quote(symbol=symbol, source=src, show_log=False)
                df = q.history(
                    interval=interval,
                    count_back=count_back,
                )
                if df is not None and not df.empty:
                    logger.info(
                        "Đã tải %d nến intraday cho %s (%s) qua nguồn %s",
                        len(df),
                        symbol,
                        interval,
                        src,
                    )
                    return df
            except Exception:
                logger.warning(
                    "Lỗi tải nến intraday cho %s qua nguồn %s, thử nguồn tiếp...",
                    symbol,
                    src,
                    exc_info=True,
                )
                continue

        raise VnstockServiceError(f"Không thể tải dữ liệu nến intraday cho mã {symbol}")

    def fetch_tick_orderflow(
        self,
        symbol: str,
        page_size: int = 100,
    ) -> pd.DataFrame:
        """Tải luồng khớp lệnh từng tick (tick-by-tick) và phân loại lệnh chủ động mua/bán.

        Sử dụng Quote.intraday để lấy các trường: time, price, volume, match_type (Buy/Sell/ATO/ATC).

        Tham số:
            symbol: Mã chứng khoán.
            page_size: Số lượng tick gần nhất cần lấy (mặc định: 100).

        Trả về:
            pd.DataFrame chi tiết các lượt khớp lệnh.
        """
        valid_sources = self._get_valid_sources(self.VALID_SOURCES_QUOTE)
        for src in valid_sources:
            try:
                self._throttle()
                q = Quote(symbol=symbol, source=src, show_log=False)
                df = q.intraday(symbol=symbol, page_size=page_size)
                if df is not None:
                    logger.info(
                        "Đã tải %d tick khớp lệnh cho %s qua nguồn %s",
                        len(df),
                        symbol,
                        src,
                    )
                    return df
            except Exception:
                logger.warning(
                    "Lỗi tải tick orderflow cho %s qua nguồn %s, thử nguồn tiếp...",
                    symbol,
                    src,
                    exc_info=True,
                )
                continue

        raise VnstockServiceError(
            f"Không thể tải dữ liệu tick orderflow cho mã {symbol}"
        )

    def fetch_market_quote(self, symbols: str | list[str]) -> pd.DataFrame:
        """Lấy bảng giá realtime snapshot đầy đủ (giá khớp, 3 bước giá mua/bán, trần/sàn/TC, khối ngoại).

        Tham số:
            symbols: Mã cổ phiếu đơn lẻ hoặc danh sách các mã (ví dụ: 'VNM' hoặc ['VNM', 'FPT']).

        Trả về:
            pd.DataFrame bảng giá chi tiết 29 cột.
        """
        try:
            self._throttle()
            mkt = Market()
            df = mkt.quote(symbols)
            if df is not None and not df.empty:
                logger.info(
                    "Đã tải bảng giá snapshot cho %s (%d dòng)", symbols, len(df)
                )
                return df
        except Exception:
            logger.warning("Lỗi tải bảng giá snapshot qua Market.quote", exc_info=True)

        return pd.DataFrame()

    def fetch_index_ohlcv(
        self,
        symbol: str = "VNINDEX",
        start: date | None = None,
        end: date | None = None,
        interval: str = "1D",
        count: int | None = None,
    ) -> pd.DataFrame:
        """Tải nến lịch sử và nến intraday chuyên biệt cho các chỉ số thị trường (VNINDEX, VN30, HNX-INDEX).

        Tham số:
            symbol: Tên chỉ số ('VNINDEX', 'VN30', 'HNX-INDEX').
            start: Ngày bắt đầu.
            end: Ngày kết thúc.
            interval: Khung thời gian ('1m', '1D').
            count: Số lượng nến gần nhất.

        Trả về:
            pd.DataFrame nến điểm số chỉ số.
        """
        try:
            self._throttle()
            mkt = Market()
            kwargs: dict[str, Any] = {"interval": interval}
            if start:
                kwargs["start"] = start.strftime("%Y-%m-%d")
            if end:
                kwargs["end"] = end.strftime("%Y-%m-%d")
            if count is not None:
                kwargs["count"] = count

            df = mkt.index(symbol).ohlcv(**kwargs)
            if df is not None and not df.empty:
                logger.info(
                    "Đã tải %d nến chỉ số cho %s qua Market.index", len(df), symbol
                )
                return df
        except Exception:
            logger.warning(
                "Lỗi tải nến chỉ số %s qua Market.index, thử qua Quote...",
                symbol,
                exc_info=True,
            )

        # Fallback qua Quote thông thường
        return self.fetch_price_history(
            symbol=symbol, start=start, end=end, interval=interval, count=count
        )

    def fetch_futures_quote(self, symbol: str = "VN30F1M") -> pd.DataFrame:
        """Lấy bảng giá phái sinh, giá khớp, bước giá và khối lượng mở (Open Interest - OI).

        Tham số:
            symbol: Mã hợp đồng phái sinh (mặc định: 'VN30F1M').

        Trả về:
            pd.DataFrame bảng giá hợp đồng phái sinh.
        """
        try:
            self._throttle()
            mkt = Market()
            df = mkt.futures(symbol).quote()
            if df is not None and not df.empty:
                logger.info("Đã tải bảng giá phái sinh cho %s", symbol)
                return df
        except Exception:
            logger.warning(
                "Lỗi tải bảng giá phái sinh %s qua Market.futures",
                symbol,
                exc_info=True,
            )

        return pd.DataFrame()

    # =========================================================================
    # PHÂN HỆ 4: BÁO CÁO TÀI CHÍNH & ĐỊNH GIÁ CƠ BẢN (FUNDAMENTAL DATA)
    # =========================================================================

    def fetch_financials(
        self,
        symbol: str,
        report_type: str = "income_statement",
        period: str = "quarter",
        orient: str = "report",
    ) -> pd.DataFrame:
        """Tải báo cáo tài chính của doanh nghiệp (Kết quả KD, Cân đối kế toán, Lưu chuyển tiền tệ).

        Tham số:
            symbol: Mã cổ phiếu.
            report_type: Loại báo cáo ('income_statement', 'balance_sheet', 'cash_flow').
            period: Kỳ báo cáo ('quarter' hoặc 'year').
            orient: Định dạng cấu trúc ('report' cho mẫu kế toán, 'time_series' cho chuỗi thời gian).

        Trả về:
            pd.DataFrame chứa dữ liệu báo cáo tài chính.
        """
        period_clean = "quarter" if "quarter" in period else "year"
        valid_sources = self._get_valid_sources(self.VALID_SOURCES_FINANCE)

        # Thử qua lớp Fundamental hiện đại trước (hỗ trợ tham số orient)
        try:
            self._throttle()
            fnd = Fundamental().equity(symbol)
            method_map_fnd = {
                "income_statement": fnd.income_statement,
                "balance_sheet": fnd.balance_sheet,
                "cash_flow": fnd.cash_flow,
            }
            fetch_fn = method_map_fnd.get(report_type)
            if fetch_fn is not None:
                df = fetch_fn(period=period_clean, orient=orient)
                if df is not None and not df.empty:
                    logger.info(
                        "Đã tải %d dòng BCTC %s cho %s (%s, %s) qua Fundamental",
                        len(df),
                        report_type,
                        symbol,
                        period_clean,
                        orient,
                    )
                    return df
        except Exception:
            logger.warning(
                "Lỗi tải BCTC %s cho %s qua Fundamental, thử fallback qua Finance...",
                report_type,
                symbol,
                exc_info=True,
            )

        # Fallback qua lớp Finance truyền thống
        for src in valid_sources:
            try:
                self._throttle()
                f = Finance(
                    symbol=symbol,
                    source=src,
                    period=period_clean,
                    show_log=False,
                )
                method_map_fin = {
                    "income_statement": f.income_statement,
                    "balance_sheet": f.balance_sheet,
                    "cash_flow": f.cash_flow,
                }
                fetch_fn_legacy = method_map_fin.get(report_type)
                if fetch_fn_legacy is None:
                    raise ValueError(f"Loại báo cáo không hợp lệ: {report_type}")

                df = fetch_fn_legacy(period=period_clean)
                if df is not None and not df.empty:
                    logger.info(
                        "Đã tải %d dòng BCTC %s cho %s (%s) qua Finance/%s",
                        len(df),
                        report_type,
                        symbol,
                        period_clean,
                        src,
                    )
                    return df
            except Exception:
                continue

        raise VnstockServiceError(
            f"Không thể tải báo cáo tài chính {report_type} cho {symbol}"
        )

    def fetch_financial_ratios(
        self, symbol: str, orient: str = "report"
    ) -> pd.DataFrame:
        """Lấy bộ 58 chỉ số tài chính và định giá định lượng (P/E, P/B, EPS, ROE, ROA, đòn bẩy D/E,...).

        Tham số:
            symbol: Mã cổ phiếu.
            orient: Định dạng cấu trúc ('report' hoặc 'time_series').

        Trả về:
            pd.DataFrame chứa toàn bộ các chỉ số tài chính.
        """
        # Thử qua lớp Fundamental hiện đại
        try:
            self._throttle()
            fnd = Fundamental().equity(symbol)
            df = fnd.ratio(orient=orient)
            if df is not None and not df.empty:
                logger.info(
                    "Đã tải %d chỉ số tài chính cho %s qua Fundamental.equity.ratio",
                    len(df),
                    symbol,
                )
                return df
        except Exception:
            logger.warning(
                "Lỗi tải chỉ số tài chính qua Fundamental cho %s, thử Finance...",
                symbol,
                exc_info=True,
            )

        # Fallback qua lớp Finance
        valid_sources = self._get_valid_sources(self.VALID_SOURCES_FINANCE)
        for src in valid_sources:
            try:
                self._throttle()
                f = Finance(symbol=symbol, source=src, show_log=False)
                df = f.ratio()
                if df is not None and not df.empty:
                    logger.info(
                        "Đã tải chỉ số tài chính cho %s qua Finance/%s", symbol, src
                    )
                    return df
            except Exception:
                continue

        raise VnstockServiceError(f"Không thể tải chỉ số tài chính cho mã {symbol}")

    # =========================================================================
    # PHÂN HỆ 5: HÀNG HÓA, VÀNG & NGOẠI TỆ BÁN LẺ (RETAIL DATA)
    # =========================================================================

    def fetch_gold_prices(
        self,
        date_str: str | None = None,
        source: str = "sjc",
    ) -> pd.DataFrame:
        """Tải dữ liệu giá vàng trong nước (mua/bán) qua phân hệ Retail.

        Tham số:
            date_str: Ngày tra cứu định dạng 'YYYY-MM-DD' (tùy chọn).
            source: Nguồn giá vàng ('sjc' cho SJC hoặc 'btmc' cho Bảo Tín Minh Châu).

        Trả về:
            pd.DataFrame bảng giá vàng.
        """
        actual_source = source
        actual_date = date_str
        if isinstance(date_str, str) and date_str.lower() in ("sjc", "btmc"):
            actual_source = date_str.lower()
            actual_date = None

        try:
            self._throttle()
            retail = Retail()
            df = retail.gold(source=actual_source.lower(), date=actual_date)
            if df is not None and not df.empty:
                logger.info(
                    "Đã tải %d dòng giá vàng (%s, ngày: %s)",
                    len(df),
                    actual_source,
                    actual_date or "hôm nay",
                )
                return df
        except Exception:
            logger.warning("Lỗi tải giá vàng nguồn %s", actual_source, exc_info=True)

        return pd.DataFrame()

    def fetch_exchange_rate(self, date_str: str = "") -> pd.DataFrame:
        """Tải tỷ giá ngoại tệ Vietcombank (USD/VND, EUR/VND,...) theo ngày giao dịch.

        Tham số:
            date_str: Ngày tra cứu định dạng 'YYYY-MM-DD' (mặc định lấy ngày gần nhất).

        Trả về:
            pd.DataFrame chứa tỷ giá mua tiền mặt, mua chuyển khoản và giá bán ra.
        """
        try:
            self._throttle()
            retail = Retail()
            df = retail.exchange_rate(date=date_str)
            if df is not None and not df.empty:
                logger.info(
                    "Đã tải %d dòng tỷ giá ngoại tệ (ngày: %s)",
                    len(df),
                    date_str or "hôm nay",
                )
                return df
        except Exception:
            logger.warning("Lỗi tải tỷ giá ngoại tệ", exc_info=True)

        return pd.DataFrame()


# Khởi tạo thể hiện Singleton dùng chung toàn bộ ứng dụng
vnstock_service = VnstockService()
