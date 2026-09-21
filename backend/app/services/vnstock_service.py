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
from sqlmodel import Session
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
from app.services.rate_limit import CircuitBreakerOpenError, RateLimiter

logger = logging.getLogger(__name__)


class VnstockServiceError(Exception):
    """Ngoại lệ phát sinh khi tất cả các nguồn dữ liệu vnstock đều thất bại."""


class VnstockService:
    """Đóng gói toàn diện thư viện vnstock với cơ chế đa nguồn và quản lý lỗi chuẩn hóa."""

    VALID_SOURCES_QUOTE = ["vci", "kbs", "msn"]
    VALID_SOURCES_LISTING = ["kbs", "vci", "msn"]
    VALID_SOURCES_COMPANY = ["kbs", "vci"]
    VALID_SOURCES_FINANCE = ["kbs", "vci"]

    def __init__(
        self,
        source: str | None = None,
        fallback_source: str | None = None,
        tertiary_source: str | None = None,
        limiter: RateLimiter | None = None,
        db_session: Session | None = None,
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
        self.db_session = db_session
        self.last_successful_source: str | None = None
        self._current_source: str = self.source

    @property
    def sources(self) -> list[str]:
        """Danh sách các nguồn dữ liệu có thứ tự, khử trùng lặp.

        Ưu tiên các nguồn theo Rule 7.1 (VCI -> KBS -> MSN).
        Nếu nguồn cấu hình là TCBS (không còn được Quote hỗ trợ ở v4.0.6),
        hệ thống sẽ tự động điều phối fallback sang VCI và KBS.
        """
        configured = [self.source, self.fallback_source, self.tertiary_source]
        normalized: list[str] = []
        for s in configured:
            if s and s not in normalized:
                normalized.append(s)

        # Bổ sung các nguồn chuẩn nếu chưa có trong cấu hình
        for default_src in ["vci", "kbs", "msn"]:
            if default_src not in normalized:
                normalized.append(default_src)

        return normalized

    def _get_valid_sources(self, allowed_sources: list[str]) -> list[str]:
        """Lọc danh sách nguồn hợp lệ cho từng bộ chuyển đổi cụ thể."""
        return [s for s in self.sources if s in allowed_sources]

    def _throttle(self, provider: str | None = None) -> None:
        """Kích hoạt độ trễ tối thiểu và kiểm tra circuit breaker theo từng provider."""
        src = (
            provider
            or getattr(self, "_current_source", None)
            or getattr(self, "source", "vci")
        )
        self._current_source = src

        # Kiểm tra circuit breaker trước khi request
        if hasattr(self._limiter, "is_available"):
            try:
                if not self._limiter.is_available(src, session=self.db_session):
                    raise CircuitBreakerOpenError(src)
            except CircuitBreakerOpenError:
                raise
            except Exception:
                pass

        if hasattr(self._limiter, "wait"):
            try:
                self._limiter.wait(provider=src, session=self.db_session)
            except TypeError:
                self._limiter.wait()

    def record_success(self, provider: str | None = None) -> None:
        """Ghi nhận thành công nguồn dữ liệu và cập nhật last_successful_source."""
        src = (
            provider
            or getattr(self, "_current_source", None)
            or getattr(self, "source", "vci")
        )
        self.last_successful_source = src
        if hasattr(self._limiter, "record_success"):
            try:
                self._limiter.record_success(provider=src, session=self.db_session)
            except Exception:
                pass

    def record_failure(self, provider: str | None = None) -> None:
        """Ghi nhận thất bại nguồn dữ liệu và cập nhật circuit breaker."""
        src = (
            provider
            or getattr(self, "_current_source", None)
            or getattr(self, "source", "vci")
        )
        if hasattr(self._limiter, "record_failure"):
            try:
                self._limiter.record_failure(provider=src, session=self.db_session)
            except Exception:
                pass

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
                self._throttle(src)
                lst = Listing(source=src, show_log=False)
                # Ưu tiên symbols_by_exchange để có sẵn thông tin cột sàn niêm yết (exchange)
                if hasattr(lst, "symbols_by_exchange"):
                    df = lst.symbols_by_exchange()
                    if df is not None and not df.empty:
                        self.record_success(src)
                        logger.info(
                            "Đã tải %d mã cổ phiếu (kèm cột sàn) qua nguồn %s",
                            len(df),
                            src,
                        )
                        return df

                df = lst.all_symbols()
                if df is not None and not df.empty:
                    self.record_success(src)
                    logger.info("Đã tải %d mã cổ phiếu qua nguồn %s", len(df), src)
                    return df
            except CircuitBreakerOpenError:
                logger.warning("Circuit breaker is OPEN for %s, skipping provider", src)
                continue
            except Exception:
                self.record_failure(src)
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
                self._throttle(src)
                lst = Listing(source=src, show_log=False)
                df = lst.symbols_by_exchange()
                if df is not None and not df.empty:
                    self.record_success(src)
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
            except CircuitBreakerOpenError:
                logger.warning("Circuit breaker is OPEN for %s, skipping provider", src)
                continue
            except Exception:
                self.record_failure(src)
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
                self._throttle(src)
                lst = Listing(source=src, show_log=False)
                # Thử symbols_by_industries trước, sau đó thử industries_icb
                if hasattr(lst, "symbols_by_industries"):
                    df = lst.symbols_by_industries()
                else:
                    df = lst.industries_icb()

                if df is not None and not df.empty:
                    self.record_success(src)
                    logger.info(
                        "Đã tải danh mục phân ngành (%d dòng) qua %s", len(df), src
                    )
                    return df
            except CircuitBreakerOpenError:
                logger.warning("Circuit breaker is OPEN for %s, skipping provider", src)
                continue
            except Exception:
                self.record_failure(src)
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
                self._throttle(src)
                lst = Listing(source=src, show_log=False)
                result = lst.symbols_by_group(group=group.upper())
                symbols = self._series_to_symbols(result)
                if symbols:
                    self.record_success(src)
                    logger.info(
                        "Đã tải %d mã cho nhóm chỉ số %s qua nguồn %s",
                        len(symbols),
                        group,
                        src,
                    )
                    return symbols
            except CircuitBreakerOpenError:
                logger.warning("Circuit breaker is OPEN for %s, skipping provider", src)
                continue
            except Exception:
                self.record_failure(src)
                logger.warning(
                    "Lỗi tải nhóm chỉ số %s qua nguồn %s, thử tiếp...",
                    group,
                    src,
                    exc_info=True,
                )
                continue

        raise VnstockServiceError(f"Không thể tải danh sách mã cho nhóm chỉ số {group}")

    @staticmethod
    def _resolve_sub_obj(
        ref_obj: Any, attr_name: str, *args: Any, **kwargs: Any
    ) -> Any:
        """Truy xuất an toàn sub-object của Reference/Market, hỗ trợ cả callable lẫn property/attribute."""
        if not hasattr(ref_obj, attr_name):
            return None
        sub = getattr(ref_obj, attr_name)
        from unittest.mock import NonCallableMock

        if isinstance(sub, NonCallableMock):
            if getattr(sub, "_mock_children", None):
                return sub
            if callable(sub):
                return sub(*args, **kwargs)
            return sub

        if callable(sub):
            try:
                return sub(*args, **kwargs)
            except TypeError:
                return sub
        return sub

    # -------------------------------------------------------------------------
    # Nhóm Reference UI: Cổ phiếu (Reference.equity)
    # -------------------------------------------------------------------------

    def fetch_reference_equity_list(self) -> pd.DataFrame:
        """Liệt kê toàn bộ mã cổ phiếu niêm yết qua Reference.equity().list()."""
        try:
            self._throttle()
            ref = Reference()
            sub = self._resolve_sub_obj(ref, "equity")
            res = sub.list() if sub is not None else None
            if isinstance(res, pd.DataFrame) and not res.empty:
                return res
            elif res is not None and not isinstance(res, pd.DataFrame):
                return pd.DataFrame(res)
        except Exception:
            logger.warning(
                "Lỗi tải danh sách cổ phiếu qua Reference.equity.list", exc_info=True
            )

        return pd.DataFrame()

    def fetch_reference_equity_by_industry(self) -> pd.DataFrame:
        """Liệt kê cổ phiếu theo ngành (chuẩn ICB) qua Reference.equity().list_by_industry()."""
        try:
            self._throttle()
            ref = Reference()
            sub = self._resolve_sub_obj(ref, "equity")
            res = sub.list_by_industry() if sub is not None else None
            if isinstance(res, pd.DataFrame) and not res.empty:
                return res
            elif res is not None and not isinstance(res, pd.DataFrame):
                return pd.DataFrame(res)
        except Exception:
            logger.warning(
                "Lỗi tải phân ngành cổ phiếu qua Reference.equity.list_by_industry",
                exc_info=True,
            )

        return pd.DataFrame()

    def fetch_reference_equity_by_exchange(self) -> pd.DataFrame:
        """Liệt kê cổ phiếu theo sàn (HOSE, HNX, UPCOM) qua Reference.equity().list_by_exchange()."""
        try:
            self._throttle()
            ref = Reference()
            sub = self._resolve_sub_obj(ref, "equity")
            res = sub.list_by_exchange() if sub is not None else None
            if isinstance(res, pd.DataFrame) and not res.empty:
                return res
            elif res is not None and not isinstance(res, pd.DataFrame):
                return pd.DataFrame(res)
        except Exception:
            logger.warning(
                "Lỗi tải cổ phiếu theo sàn qua Reference.equity.list_by_exchange",
                exc_info=True,
            )

        return pd.DataFrame()

    def fetch_reference_equity_by_group(self, group: str = "VN30") -> pd.DataFrame:
        """Liệt kê cổ phiếu theo nhóm chỉ số/sàn (ví dụ: 'VN30') qua Reference.equity().list_by_group()."""
        try:
            self._throttle()
            ref = Reference()
            sub = self._resolve_sub_obj(ref, "equity")
            res = sub.list_by_group(group=group.upper()) if sub is not None else None
            if isinstance(res, pd.DataFrame) and not res.empty:
                return res
            elif res is not None and not isinstance(res, pd.DataFrame):
                return pd.DataFrame(res)
        except Exception:
            logger.warning(
                "Lỗi tải cổ phiếu nhóm %s qua Reference.equity.list_by_group",
                group,
                exc_info=True,
            )

        return pd.DataFrame()

    # -------------------------------------------------------------------------
    # Nhóm Reference UI: Chỉ số (Reference.index)
    # -------------------------------------------------------------------------

    def fetch_reference_index_list(self) -> pd.DataFrame:
        """Danh sách tất cả các chỉ số thị trường (VNINDEX, VN30,...) qua Reference.index().list()."""
        try:
            self._throttle()
            ref = Reference()
            sub = self._resolve_sub_obj(ref, "index")
            res = sub.list() if sub is not None else None
            if isinstance(res, pd.DataFrame) and not res.empty:
                return res
            elif res is not None and not isinstance(res, pd.DataFrame):
                return pd.DataFrame(res)
        except Exception:
            logger.warning(
                "Lỗi tải danh sách chỉ số qua Reference.index.list", exc_info=True
            )

        return pd.DataFrame()

    def fetch_index_list(self) -> pd.DataFrame:
        """Lấy danh sách toàn bộ các chỉ số thị trường chứng khoán Việt Nam (VNINDEX, VN30, HNX,...).

        Trả về:
            pd.DataFrame thông tin và mã các chỉ số.
        """
        return self.fetch_reference_index_list()

    def fetch_reference_index_groups(self) -> pd.DataFrame:
        """Danh sách các nhóm chỉ số hỗ trợ qua Reference.index().groups()."""
        try:
            self._throttle()
            ref = Reference()
            sub = self._resolve_sub_obj(ref, "index")
            res = sub.groups() if sub is not None else None
            if isinstance(res, pd.DataFrame) and not res.empty:
                return res
            elif res is not None and not isinstance(res, pd.DataFrame):
                return pd.DataFrame(res)
        except Exception:
            logger.warning(
                "Lỗi tải nhóm chỉ số qua Reference.index.groups", exc_info=True
            )

        return pd.DataFrame()

    def fetch_reference_index_members(self, symbol: str = "VN30") -> pd.DataFrame:
        """Danh sách các mã thành phần trong rổ chỉ số qua Reference.index().members()."""
        try:
            self._throttle()
            ref = Reference()
            sub = self._resolve_sub_obj(ref, "index")
            res = sub.members(symbol=symbol.upper()) if sub is not None else None
            if isinstance(res, pd.DataFrame) and not res.empty:
                return res
            elif isinstance(res, (list, tuple, pd.Series)):
                return pd.DataFrame({"symbol": list(res)})
        except Exception:
            logger.warning(
                "Lỗi tải thành phần chỉ số %s qua Reference.index.members",
                symbol,
                exc_info=True,
            )

        return pd.DataFrame()

    # -------------------------------------------------------------------------
    # Nhóm Reference UI: Các nhóm tài sản khác (ETF, Futures, Warrant, Bond, Fund)
    # -------------------------------------------------------------------------

    def fetch_reference_etf_list(self) -> pd.DataFrame:
        """Danh sách các chứng chỉ quỹ ETF qua Reference.etf().list()."""
        try:
            self._throttle()
            ref = Reference()
            sub = self._resolve_sub_obj(ref, "etf")
            res = sub.list() if sub is not None else None
            if isinstance(res, pd.DataFrame) and not res.empty:
                return res
            elif isinstance(res, (list, tuple, pd.Series)):
                return pd.DataFrame({"symbol": list(res)})
        except Exception:
            logger.warning("Lỗi tải danh mục ETF qua Reference.etf.list", exc_info=True)

        return pd.DataFrame()

    def fetch_reference_futures_list(self) -> pd.DataFrame:
        """Danh sách hợp đồng tương lai phái sinh qua Reference.futures().list()."""
        try:
            self._throttle()
            ref = Reference()
            sub = self._resolve_sub_obj(ref, "futures")
            res = sub.list() if sub is not None else None
            if isinstance(res, pd.DataFrame) and not res.empty:
                return res
            elif isinstance(res, (list, tuple, pd.Series)):
                return pd.DataFrame({"symbol": list(res)})
        except Exception:
            logger.warning(
                "Lỗi tải danh mục phái sinh qua Reference.futures.list", exc_info=True
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
                self._throttle(src)
                lst = Listing(source=src, show_log=False)
                if hasattr(lst, "all_future_indices"):
                    df = lst.all_future_indices()
                    if df is not None and not df.empty:
                        self.record_success(src)
                        logger.info("Đã tải %d hợp đồng phái sinh qua %s", len(df), src)
                        return df
            except CircuitBreakerOpenError:
                logger.warning("Circuit breaker is OPEN for %s, skipping provider", src)
                continue
            except Exception:
                self.record_failure(src)
                continue

        # Thử qua Reference layer
        return self.fetch_reference_futures_list()

    def fetch_reference_warrant_list(self) -> pd.DataFrame:
        """Danh sách chứng quyền có bảo đảm qua Reference.warrant().list()."""
        try:
            self._throttle()
            ref = Reference()
            sub = self._resolve_sub_obj(ref, "warrant")
            res = sub.list() if sub is not None else None
            if isinstance(res, pd.DataFrame) and not res.empty:
                self.record_success()
                return res
            elif isinstance(res, (list, tuple, pd.Series)):
                self.record_success()
                return pd.DataFrame({"symbol": list(res)})
        except Exception:
            self.record_failure()
            logger.warning(
                "Lỗi tải danh mục chứng quyền qua Reference.warrant.list", exc_info=True
            )

        return pd.DataFrame()

    def fetch_covered_warrants_list(self) -> pd.DataFrame | pd.Series:
        """Lấy danh sách các chứng quyền có bảo đảm (Covered Warrants - CW) đang niêm yết trên HOSE.

        Trả về:
            pd.DataFrame hoặc pd.Series chứa danh sách mã chứng quyền.
        """
        valid_sources = self._get_valid_sources(self.VALID_SOURCES_LISTING)
        for src in valid_sources:
            try:
                self._throttle(src)
                lst = Listing(source=src, show_log=False)
                if hasattr(lst, "all_covered_warrant"):
                    res = lst.all_covered_warrant()
                    if res is not None and not res.empty:
                        self.record_success(src)
                        logger.info("Đã tải %d chứng quyền qua %s", len(res), src)
                        return res
            except CircuitBreakerOpenError:
                logger.warning("Circuit breaker is OPEN for %s, skipping provider", src)
                continue
            except Exception:
                self.record_failure(src)
                continue

        # Thử qua Reference layer
        return self.fetch_reference_warrant_list()

    def fetch_reference_fund_list(self) -> pd.DataFrame:
        """Danh sách các quỹ mở FMarket qua Reference.fund().list()."""
        try:
            self._throttle()
            ref = Reference()
            sub = self._resolve_sub_obj(ref, "fund")
            res = sub.list() if sub is not None else None
            if isinstance(res, pd.DataFrame) and not res.empty:
                logger.info("Đã tải danh mục quỹ (%d quỹ) qua Reference.fund", len(res))
                return res
            elif res is not None and not isinstance(res, pd.DataFrame):
                return pd.DataFrame(res)
        except Exception:
            logger.warning(
                "Lỗi tải danh mục quỹ qua Reference.fund.list", exc_info=True
            )

        return pd.DataFrame()

    def fetch_funds_list(self) -> pd.DataFrame:
        """Lấy danh sách các chứng chỉ quỹ mở FMarket và chứng chỉ quỹ ETF."""
        return self.fetch_reference_fund_list()

    def fetch_reference_bond_list(self, bond_type: str = "all") -> pd.DataFrame:
        """Danh sách trái phiếu doanh nghiệp & chính phủ qua Reference.bond().list()."""
        try:
            self._throttle()
            ref = Reference()
            sub = self._resolve_sub_obj(ref, "bond")
            res = sub.list(bond_type=bond_type) if sub is not None else None
            if isinstance(res, pd.DataFrame) and not res.empty:
                logger.info("Đã tải %d mã trái phiếu qua Reference.bond", len(res))
                return res
            elif res is not None and not isinstance(res, pd.DataFrame):
                return pd.DataFrame(res)
        except Exception:
            logger.warning(
                "Lỗi tải danh mục trái phiếu qua Reference.bond.list", exc_info=True
            )

        return pd.DataFrame()

    def fetch_bonds_list(self, bond_type: str = "all") -> pd.DataFrame:
        """Lấy danh sách trái phiếu doanh nghiệp và trái phiếu chính phủ niêm yết trên HNX.

        Tham số:
            bond_type: 'all' (toàn bộ), 'corporate' (doanh nghiệp), 'government' (chính phủ).

        Trả về:
            pd.DataFrame chứa mã trái phiếu và phân loại (symbol, type).
        """
        res = self.fetch_reference_bond_list(bond_type=bond_type)
        if not res.empty:
            return res

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

    # -------------------------------------------------------------------------
    # Nhóm Reference UI: Tìm kiếm (Reference.search)
    # -------------------------------------------------------------------------

    def search_reference_symbol(self, query: str, limit: int = 10) -> pd.DataFrame:
        """Tìm kiếm mã chứng khoán theo từ khóa qua Reference.search.symbol()."""
        try:
            self._throttle()
            ref = Reference()
            sub = self._resolve_sub_obj(ref, "search")
            res = sub.symbol(query=query, limit=limit) if sub is not None else None
            if isinstance(res, pd.DataFrame) and not res.empty:
                logger.info("Tìm kiếm mã '%s' trả về %d kết quả", query, len(res))
                return res
            elif res is not None and not isinstance(res, pd.DataFrame):
                return pd.DataFrame(res)
        except Exception:
            logger.warning(
                "Lỗi tìm kiếm mã chứng khoán cho từ khóa '%s'", query, exc_info=True
            )

        return pd.DataFrame()

    def search_symbols(self, query: str, limit: int = 10) -> pd.DataFrame:
        """Tìm kiếm mã chứng khoán hoặc thông tin liên quan theo từ khóa."""
        return self.search_reference_symbol(query=query, limit=limit)

    def search_reference_info(self, query: str, limit: int = 10) -> pd.DataFrame:
        """Tìm kiếm thông tin chi tiết tài sản qua Reference.search.info()."""
        try:
            self._throttle()
            ref = Reference()
            sub = self._resolve_sub_obj(ref, "search")
            res = sub.info(query=query, limit=limit) if sub is not None else None
            if isinstance(res, pd.DataFrame) and not res.empty:
                logger.info(
                    "Tìm kiếm thông tin tài sản '%s' trả về %d kết quả", query, len(res)
                )
                return res
            elif res is not None and not isinstance(res, pd.DataFrame):
                return pd.DataFrame(res)
        except Exception:
            logger.warning(
                "Lỗi tìm kiếm thông tin tài sản cho từ khóa '%s'", query, exc_info=True
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
                self._throttle(src)
                c = Company(symbol=symbol, source=src, show_log=False)
                df = c.overview()
                if df is not None and not df.empty:
                    self.record_success(src)
                    return df.iloc[0].to_dict()
            except CircuitBreakerOpenError:
                logger.warning("Circuit breaker is OPEN for %s, skipping provider", src)
                continue
            except Exception:
                self.record_failure(src)
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
                self._throttle(src)
                c = Company(symbol=symbol, source=src, show_log=False)
                df = c.shareholders()
                if df is not None and not df.empty:
                    self.record_success(src)
                    logger.info(
                        "Đã tải %d cổ đông lớn của %s qua %s", len(df), symbol, src
                    )
                    return df
            except CircuitBreakerOpenError:
                continue
            except Exception:
                self.record_failure(src)
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
                self._throttle(src)
                c = Company(symbol=symbol, source=src, show_log=False)
                df = c.officers()
                if df is not None and not df.empty:
                    self.record_success(src)
                    logger.info(
                        "Đã tải %d lãnh đạo của %s qua %s", len(df), symbol, src
                    )
                    return df
            except CircuitBreakerOpenError:
                continue
            except Exception:
                self.record_failure(src)
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
                self._throttle(src)
                c = Company(symbol=symbol, source=src, show_log=False)
                df = c.subsidiaries()
                if df is not None and not df.empty:
                    self.record_success(src)
                    logger.info(
                        "Đã tải %d công ty con của %s qua %s", len(df), symbol, src
                    )
                    return df
            except CircuitBreakerOpenError:
                continue
            except Exception:
                self.record_failure(src)
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
                self._throttle(src)
                c = Company(symbol=symbol, source=src, show_log=False)
                df = c.insider_trading()
                if df is not None and not df.empty:
                    self.record_success(src)
                    logger.info(
                        "Đã tải %d giao dịch nội bộ của %s qua %s", len(df), symbol, src
                    )
                    return df
            except CircuitBreakerOpenError:
                continue
            except Exception:
                self.record_failure(src)
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
                self._throttle(src)
                c = Company(symbol=symbol, source=src, show_log=False)
                df = c.capital_history()
                if df is not None and not df.empty:
                    self.record_success(src)
                    logger.info(
                        "Đã tải lịch sử vốn (%d sự kiện) của %s qua %s",
                        len(df),
                        symbol,
                        src,
                    )
                    return df
            except CircuitBreakerOpenError:
                continue
            except Exception:
                self.record_failure(src)
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
                self._throttle(src)
                c = Company(symbol=symbol, source=src, show_log=False)
                df = c.news()
                if df is not None and not df.empty:
                    self.record_success(src)
                    logger.info("Đã tải %d tin tức cho %s qua %s", len(df), symbol, src)
                    return df
            except CircuitBreakerOpenError:
                continue
            except Exception:
                self.record_failure(src)
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
                self._throttle(src)
                c = Company(symbol=symbol, source=src, show_log=False)
                df = c.events()
                if df is not None and not df.empty:
                    self.record_success(src)
                    logger.info("Đã tải %d sự kiện cho %s qua %s", len(df), symbol, src)
                    return df
            except CircuitBreakerOpenError:
                continue
            except Exception:
                self.record_failure(src)
                continue

        return pd.DataFrame()

    # -------------------------------------------------------------------------
    # Nhóm Reference UI: Hồ sơ doanh nghiệp (Reference.company)
    # -------------------------------------------------------------------------

    def fetch_reference_company_info(self, symbol: str) -> pd.DataFrame:
        """Lấy tổng quan về doanh nghiệp (ngành, vốn hóa...) qua Reference.company().info()."""
        try:
            self._throttle()
            ref = Reference()
            sub = self._resolve_sub_obj(ref, "company", symbol)
            res = sub.info() if sub is not None else None
            if isinstance(res, pd.DataFrame) and not res.empty:
                return res
            elif res is not None and not isinstance(res, pd.DataFrame):
                return pd.DataFrame(res)
        except Exception:
            logger.warning(
                "Lỗi tải thông tin doanh nghiệp %s qua Reference.company.info",
                symbol,
                exc_info=True,
            )

        return pd.DataFrame()

    def fetch_reference_company_shareholders(self, symbol: str) -> pd.DataFrame:
        """Lấy danh sách cổ đông lớn qua Reference.company().shareholders()."""
        try:
            self._throttle()
            ref = Reference()
            sub = self._resolve_sub_obj(ref, "company", symbol)
            res = sub.shareholders() if sub is not None else None
            if isinstance(res, pd.DataFrame) and not res.empty:
                return res
            elif res is not None and not isinstance(res, pd.DataFrame):
                return pd.DataFrame(res)
        except Exception:
            logger.warning(
                "Lỗi tải cổ đông %s qua Reference.company.shareholders",
                symbol,
                exc_info=True,
            )

        return pd.DataFrame()

    def fetch_reference_company_officers(self, symbol: str) -> pd.DataFrame:
        """Lấy danh sách ban lãnh đạo công ty qua Reference.company().officers()."""
        try:
            self._throttle()
            ref = Reference()
            sub = self._resolve_sub_obj(ref, "company", symbol)
            res = sub.officers() if sub is not None else None
            if isinstance(res, pd.DataFrame) and not res.empty:
                return res
            elif res is not None and not isinstance(res, pd.DataFrame):
                return pd.DataFrame(res)
        except Exception:
            logger.warning(
                "Lỗi tải ban lãnh đạo %s qua Reference.company.officers",
                symbol,
                exc_info=True,
            )

        return pd.DataFrame()

    def fetch_reference_company_subsidiaries(self, symbol: str) -> pd.DataFrame:
        """Lấy danh sách công ty con, công ty liên kết qua Reference.company().subsidiaries()."""
        try:
            self._throttle()
            ref = Reference()
            sub = self._resolve_sub_obj(ref, "company", symbol)
            res = sub.subsidiaries() if sub is not None else None
            if isinstance(res, pd.DataFrame) and not res.empty:
                return res
            elif res is not None and not isinstance(res, pd.DataFrame):
                return pd.DataFrame(res)
        except Exception:
            logger.warning(
                "Lỗi tải công ty con %s qua Reference.company.subsidiaries",
                symbol,
                exc_info=True,
            )

        return pd.DataFrame()

    def fetch_reference_company_ownership(self, symbol: str) -> pd.DataFrame:
        """Lấy cơ cấu sở hữu doanh nghiệp qua Reference.company().ownership()."""
        try:
            self._throttle()
            ref = Reference()
            sub = self._resolve_sub_obj(ref, "company", symbol)
            res = sub.ownership() if sub is not None else None
            if isinstance(res, pd.DataFrame) and not res.empty:
                return res
            elif res is not None and not isinstance(res, pd.DataFrame):
                return pd.DataFrame(res)
        except Exception:
            logger.warning(
                "Lỗi tải cơ cấu sở hữu %s qua Reference.company.ownership",
                symbol,
                exc_info=True,
            )

        return pd.DataFrame()

    def fetch_reference_company_insider_trading(self, symbol: str) -> pd.DataFrame:
        """Lấy lịch sử giao dịch nội bộ qua Reference.company().insider_trading()."""
        try:
            self._throttle()
            ref = Reference()
            sub = self._resolve_sub_obj(ref, "company", symbol)
            res = sub.insider_trading() if sub is not None else None
            if isinstance(res, pd.DataFrame) and not res.empty:
                return res
            elif res is not None and not isinstance(res, pd.DataFrame):
                return pd.DataFrame(res)
        except Exception:
            logger.warning(
                "Lỗi tải giao dịch nội bộ %s qua Reference.company.insider_trading",
                symbol,
                exc_info=True,
            )

        return pd.DataFrame()

    def fetch_reference_company_capital_history(self, symbol: str) -> pd.DataFrame:
        """Lấy lịch sử thay đổi vốn điều lệ qua Reference.company().capital_history()."""
        try:
            self._throttle()
            ref = Reference()
            sub = self._resolve_sub_obj(ref, "company", symbol)
            res = sub.capital_history() if sub is not None else None
            if isinstance(res, pd.DataFrame) and not res.empty:
                return res
            elif res is not None and not isinstance(res, pd.DataFrame):
                return pd.DataFrame(res)
        except Exception:
            logger.warning(
                "Lỗi tải lịch sử tăng vốn %s qua Reference.company.capital_history",
                symbol,
                exc_info=True,
            )

        return pd.DataFrame()

    def fetch_reference_company_news(self, symbol: str) -> pd.DataFrame:
        """Lấy tin tức liên quan đến doanh nghiệp qua Reference.company().news()."""
        try:
            self._throttle()
            ref = Reference()
            sub = self._resolve_sub_obj(ref, "company", symbol)
            res = sub.news() if sub is not None else None
            if isinstance(res, pd.DataFrame) and not res.empty:
                return res
            elif res is not None and not isinstance(res, pd.DataFrame):
                return pd.DataFrame(res)
        except Exception:
            logger.warning(
                "Lỗi tải tin tức %s qua Reference.company.news", symbol, exc_info=True
            )

        return pd.DataFrame()

    def fetch_reference_company_events(self, symbol: str) -> pd.DataFrame:
        """Lấy các sự kiện doanh nghiệp (cổ tức, ĐHCĐ...) qua Reference.company().events()."""
        try:
            self._throttle()
            ref = Reference()
            sub = self._resolve_sub_obj(ref, "company", symbol)
            res = sub.events() if sub is not None else None
            if isinstance(res, pd.DataFrame) and not res.empty:
                return res
            elif res is not None and not isinstance(res, pd.DataFrame):
                return pd.DataFrame(res)
        except Exception:
            logger.warning(
                "Lỗi tải sự kiện doanh nghiệp %s qua Reference.company.events",
                symbol,
                exc_info=True,
            )

        return pd.DataFrame()

    def fetch_reference_events_calendar(
        self,
        start: str | None = None,
        end: str | None = None,
        event_type: str | None = None,
        page: int = 0,
        limit: int = 20000,
        source: str = "kbs",
    ) -> pd.DataFrame:
        """Lịch sự kiện thị trường (cổ tức, ĐHCĐ, phát hành) qua Reference.events.calendar()."""
        try:
            self._throttle()
            ref = Reference()
            sub = self._resolve_sub_obj(ref, "events")
            if sub is not None and hasattr(sub, "calendar"):
                res = sub.calendar(
                    start=start,
                    end=end,
                    event_type=event_type,
                    page=page,
                    limit=limit,
                    source=source,
                )
                if isinstance(res, pd.DataFrame) and not res.empty:
                    return res
                elif res is not None and not isinstance(res, pd.DataFrame):
                    return pd.DataFrame(res)
        except Exception:
            logger.warning(
                "Lỗi tải lịch sự kiện thị trường qua Reference.events.calendar",
                exc_info=True,
            )

        return pd.DataFrame()

    def fetch_reference_industry_list(self, source: str | None = None) -> pd.DataFrame:
        """Danh mục phân loại ngành qua Reference.industry.list()."""
        try:
            self._throttle()
            ref = Reference()
            sub = self._resolve_sub_obj(ref, "industry")
            if sub is not None and hasattr(sub, "list"):
                res = sub.list(source=source) if source else sub.list()
                if isinstance(res, pd.DataFrame) and not res.empty:
                    return res
                elif res is not None and not isinstance(res, pd.DataFrame):
                    return pd.DataFrame(res)
        except Exception:
            logger.warning(
                "Lỗi tải danh mục ngành qua Reference.industry.list", exc_info=True
            )

        return pd.DataFrame()

    def fetch_reference_market_status(self) -> pd.DataFrame:
        """Trạng thái phiên giao dịch hiện tại qua Reference.market.status()."""
        try:
            self._throttle()
            ref = Reference()
            sub = self._resolve_sub_obj(ref, "market")
            if sub is not None and hasattr(sub, "status"):
                res = sub.status()
                if isinstance(res, pd.DataFrame) and not res.empty:
                    return res
                elif res is not None and not isinstance(res, pd.DataFrame):
                    return pd.DataFrame(res)
        except Exception:
            logger.warning(
                "Lỗi tải trạng thái thị trường qua Reference.market.status",
                exc_info=True,
            )

        return pd.DataFrame()

    @staticmethod
    def show_api(node: Any = None) -> None:
        """Hiển thị cấu trúc cây API của thư viện vnstock qua vnstock.show_api()."""
        try:
            from vnstock import show_api as vnstock_show_api

            vnstock_show_api(node)
        except Exception:
            logger.warning("Lỗi hiển thị API tree qua show_api", exc_info=True)

    @staticmethod
    def show_doc(obj: Any) -> None:
        """Hiển thị tài liệu hướng dẫn cho hàm/phương thức qua vnstock.show_doc()."""
        try:
            from vnstock import show_doc as vnstock_show_doc

            vnstock_show_doc(obj)
        except Exception:
            logger.warning("Lỗi hiển thị tài liệu qua show_doc", exc_info=True)

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
                self._throttle(src)
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
                    self.record_success(src)
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
            except CircuitBreakerOpenError:
                logger.warning("Circuit breaker is OPEN for %s, skipping provider", src)
                continue
            except Exception:
                self.record_failure(src)
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
                self._throttle(src)
                q = Quote(symbol=symbol, source=src, show_log=False)
                df = q.history(
                    interval=interval,
                    count_back=count_back,
                )
                if df is not None and not df.empty:
                    self.record_success(src)
                    logger.info(
                        "Đã tải %d nến intraday cho %s (%s) qua nguồn %s",
                        len(df),
                        symbol,
                        interval,
                        src,
                    )
                    return df
            except CircuitBreakerOpenError:
                logger.warning("Circuit breaker is OPEN for %s, skipping provider", src)
                continue
            except Exception:
                self.record_failure(src)
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
                self._throttle(src)
                q = Quote(symbol=symbol, source=src, show_log=False)
                df = q.intraday(symbol=symbol, page_size=page_size)
                if df is not None:
                    self.record_success(src)
                    logger.info(
                        "Đã tải %d tick khớp lệnh cho %s qua nguồn %s",
                        len(df),
                        symbol,
                        src,
                    )
                    return df
            except CircuitBreakerOpenError:
                logger.warning("Circuit breaker is OPEN for %s, skipping provider", src)
                continue
            except Exception:
                self.record_failure(src)
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

    @staticmethod
    def _format_date_param(d: date | str | None) -> str | None:
        """Chuẩn hóa tham số ngày thành chuỗi YYYY-MM-DD."""
        if d is None:
            return None
        if isinstance(d, date):
            return d.strftime("%Y-%m-%d")
        return str(d)

    def fetch_market_quote(self, symbols: str | list[str]) -> pd.DataFrame:
        """Lấy bảng giá realtime snapshot đầy đủ (giá khớp, 3 bước giá mua/bán, trần/sàn/TC, khối ngoại).

        Tham số:
            symbols: Mã cổ phiếu đơn lẻ hoặc danh sách các mã (ví dụ: 'VNM' hoặc ['VNM', 'FPT']).

        Trả về:
            pd.DataFrame bảng giá chi tiết 29-30 cột.
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
        start: date | str | None = None,
        end: date | str | None = None,
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
            s_str = self._format_date_param(start)
            e_str = self._format_date_param(end)
            if s_str:
                kwargs["start"] = s_str
            if e_str:
                kwargs["end"] = e_str
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
        parsed_start = start if isinstance(start, date) or start is None else None
        parsed_end = end if isinstance(end, date) or end is None else None
        return self.fetch_price_history(
            symbol=symbol,
            start=parsed_start,
            end=parsed_end,
            interval=interval,
            count=count,
        )

    # -------------------------------------------------------------------------
    # Nhóm A: Lớp equity (Cổ phiếu)
    # -------------------------------------------------------------------------

    def fetch_market_equity_ohlcv(
        self,
        symbol: str,
        start: date | str | None = None,
        end: date | str | None = None,
        interval: str = "1D",
        count: int = 100,
    ) -> pd.DataFrame:
        """Lấy dữ liệu nến OHLCV cổ phiếu qua lớp Market.equity.

        Tham số:
            symbol: Mã cổ phiếu (ví dụ: 'FPT', 'VCB').
            start: Ngày bắt đầu (YYYY-MM-DD).
            end: Ngày kết thúc (YYYY-MM-DD).
            interval: Khung thời gian ('1m', '5m', '15m', '30m', '1h', '1D', '1W').
            count: Số lượng nến cần lấy nếu không chỉ định start.
        """
        try:
            self._throttle()
            mkt = Market()
            kwargs: dict[str, Any] = {"interval": interval, "count": count}
            s_str = self._format_date_param(start)
            e_str = self._format_date_param(end)
            if s_str:
                kwargs["start"] = s_str
            if e_str:
                kwargs["end"] = e_str

            df = mkt.equity(symbol).ohlcv(**kwargs)
            if isinstance(df, pd.DataFrame) and not df.empty:
                return df
            elif df is not None and not isinstance(df, pd.DataFrame):
                return pd.DataFrame(df)
        except Exception:
            logger.warning(
                "Lỗi tải nến cổ phiếu %s qua Market.equity.ohlcv", symbol, exc_info=True
            )

        return pd.DataFrame()

    def fetch_market_equity_trades(self, symbol: str) -> pd.DataFrame:
        """Lấy dữ liệu khớp lệnh chi tiết trong ngày (Tick-by-tick) qua Market.equity.trades."""
        try:
            self._throttle()
            mkt = Market()
            df = mkt.equity(symbol).trades()
            if isinstance(df, pd.DataFrame) and not df.empty:
                return df
            elif df is not None and not isinstance(df, pd.DataFrame):
                return pd.DataFrame(df)
        except Exception:
            logger.warning(
                "Lỗi tải khớp lệnh cổ phiếu %s qua Market.equity.trades",
                symbol,
                exc_info=True,
            )

        return pd.DataFrame()

    def fetch_market_equity_quote(self, symbol: str) -> pd.DataFrame:
        """Lấy thông tin giá hiện tại (Bảng giá) của cổ phiếu qua Market.equity.quote."""
        try:
            self._throttle()
            mkt = Market()
            df = mkt.equity(symbol).quote()
            if isinstance(df, pd.DataFrame) and not df.empty:
                return df
            elif df is not None and not isinstance(df, pd.DataFrame):
                return pd.DataFrame(df)
        except Exception:
            logger.warning(
                "Lỗi tải bảng giá cổ phiếu %s qua Market.equity.quote",
                symbol,
                exc_info=True,
            )

        return pd.DataFrame()

    # -------------------------------------------------------------------------
    # Nhóm B: Lớp futures (Hợp đồng tương lai / Phái sinh)
    # -------------------------------------------------------------------------

    def fetch_market_futures_ohlcv(
        self,
        symbol: str = "VN30F1M",
        start: date | str | None = None,
        end: date | str | None = None,
        interval: str = "1D",
        count: int = 100,
    ) -> pd.DataFrame:
        """Lấy nến OHLCV hợp đồng phái sinh qua Market.futures.ohlcv."""
        try:
            self._throttle()
            mkt = Market()
            kwargs: dict[str, Any] = {"interval": interval, "count": count}
            s_str = self._format_date_param(start)
            e_str = self._format_date_param(end)
            if s_str:
                kwargs["start"] = s_str
            if e_str:
                kwargs["end"] = e_str

            df = mkt.futures(symbol).ohlcv(**kwargs)
            if isinstance(df, pd.DataFrame) and not df.empty:
                return df
            elif df is not None and not isinstance(df, pd.DataFrame):
                return pd.DataFrame(df)
        except Exception:
            logger.warning(
                "Lỗi tải nến phái sinh %s qua Market.futures.ohlcv",
                symbol,
                exc_info=True,
            )

        return pd.DataFrame()

    def fetch_market_futures_trades(self, symbol: str = "VN30F1M") -> pd.DataFrame:
        """Lấy dữ liệu khớp lệnh chi tiết phái sinh trong ngày qua Market.futures.trades."""
        try:
            self._throttle()
            mkt = Market()
            df = mkt.futures(symbol).trades()
            if isinstance(df, pd.DataFrame) and not df.empty:
                return df
            elif df is not None and not isinstance(df, pd.DataFrame):
                return pd.DataFrame(df)
        except Exception:
            logger.warning(
                "Lỗi tải khớp lệnh phái sinh %s qua Market.futures.trades",
                symbol,
                exc_info=True,
            )

        return pd.DataFrame()

    def fetch_market_futures_quote(self, symbol: str = "VN30F1M") -> pd.DataFrame:
        """Lấy bảng giá phái sinh, giá khớp, bước giá và khối lượng mở (OI) qua Market.futures.quote."""
        try:
            self._throttle()
            mkt = Market()
            df = mkt.futures(symbol).quote()
            if isinstance(df, pd.DataFrame) and not df.empty:
                logger.info("Đã tải bảng giá phái sinh cho %s", symbol)
                return df
            elif df is not None and not isinstance(df, pd.DataFrame):
                return pd.DataFrame(df)
        except Exception:
            logger.warning(
                "Lỗi tải bảng giá phái sinh %s qua Market.futures",
                symbol,
                exc_info=True,
            )

        return pd.DataFrame()

    def fetch_futures_quote(self, symbol: str = "VN30F1M") -> pd.DataFrame:
        """Alias tương thích ngược cho fetch_market_futures_quote."""
        return self.fetch_market_futures_quote(symbol=symbol)

    # -------------------------------------------------------------------------
    # Nhóm C: Lớp warrant (Chứng quyền có bảo đảm)
    # -------------------------------------------------------------------------

    def fetch_market_warrant_ohlcv(
        self,
        symbol: str,
        start: date | str | None = None,
        end: date | str | None = None,
        interval: str = "1D",
        count: int = 100,
    ) -> pd.DataFrame:
        """Lấy nến OHLCV chứng quyền qua Market.warrant.ohlcv."""
        try:
            self._throttle()
            mkt = Market()
            kwargs: dict[str, Any] = {"interval": interval, "count": count}
            s_str = self._format_date_param(start)
            e_str = self._format_date_param(end)
            if s_str:
                kwargs["start"] = s_str
            if e_str:
                kwargs["end"] = e_str

            df = mkt.warrant(symbol).ohlcv(**kwargs)
            if isinstance(df, pd.DataFrame) and not df.empty:
                return df
            elif df is not None and not isinstance(df, pd.DataFrame):
                return pd.DataFrame(df)
        except Exception:
            logger.warning(
                "Lỗi tải nến chứng quyền %s qua Market.warrant.ohlcv",
                symbol,
                exc_info=True,
            )

        return pd.DataFrame()

    def fetch_market_warrant_trades(self, symbol: str) -> pd.DataFrame:
        """Lấy dữ liệu khớp lệnh chi tiết chứng quyền trong ngày qua Market.warrant.trades."""
        try:
            self._throttle()
            mkt = Market()
            df = mkt.warrant(symbol).trades()
            if isinstance(df, pd.DataFrame) and not df.empty:
                return df
            elif df is not None and not isinstance(df, pd.DataFrame):
                return pd.DataFrame(df)
        except Exception:
            logger.warning(
                "Lỗi tải khớp lệnh chứng quyền %s qua Market.warrant.trades",
                symbol,
                exc_info=True,
            )

        return pd.DataFrame()

    def fetch_market_warrant_quote(self, symbol: str) -> pd.DataFrame:
        """Lấy bảng giá chứng quyền qua Market.warrant.quote."""
        try:
            self._throttle()
            mkt = Market()
            df = mkt.warrant(symbol).quote()
            if isinstance(df, pd.DataFrame) and not df.empty:
                return df
            elif df is not None and not isinstance(df, pd.DataFrame):
                return pd.DataFrame(df)
        except Exception:
            logger.warning(
                "Lỗi tải bảng giá chứng quyền %s qua Market.warrant.quote",
                symbol,
                exc_info=True,
            )

        return pd.DataFrame()

    # -------------------------------------------------------------------------
    # Nhóm D: Lớp etf (Chứng chỉ quỹ ETF)
    # -------------------------------------------------------------------------

    def fetch_market_etf_ohlcv(
        self,
        symbol: str,
        start: date | str | None = None,
        end: date | str | None = None,
        interval: str = "1D",
        count: int = 100,
    ) -> pd.DataFrame:
        """Lấy nến OHLCV chứng chỉ quỹ ETF qua Market.etf.ohlcv."""
        try:
            self._throttle()
            mkt = Market()
            kwargs: dict[str, Any] = {"interval": interval, "count": count}
            s_str = self._format_date_param(start)
            e_str = self._format_date_param(end)
            if s_str:
                kwargs["start"] = s_str
            if e_str:
                kwargs["end"] = e_str

            df = mkt.etf(symbol).ohlcv(**kwargs)
            if isinstance(df, pd.DataFrame) and not df.empty:
                return df
            elif df is not None and not isinstance(df, pd.DataFrame):
                return pd.DataFrame(df)
        except Exception:
            logger.warning(
                "Lỗi tải nến ETF %s qua Market.etf.ohlcv", symbol, exc_info=True
            )

        return pd.DataFrame()

    def fetch_market_etf_trades(self, symbol: str) -> pd.DataFrame:
        """Lấy dữ liệu khớp lệnh chi tiết chứng chỉ quỹ ETF qua Market.etf.trades."""
        try:
            self._throttle()
            mkt = Market()
            df = mkt.etf(symbol).trades()
            if isinstance(df, pd.DataFrame) and not df.empty:
                return df
            elif df is not None and not isinstance(df, pd.DataFrame):
                return pd.DataFrame(df)
        except Exception:
            logger.warning(
                "Lỗi tải khớp lệnh ETF %s qua Market.etf.trades", symbol, exc_info=True
            )

        return pd.DataFrame()

    def fetch_market_etf_quote(self, symbol: str) -> pd.DataFrame:
        """Lấy bảng giá chứng chỉ quỹ ETF qua Market.etf.quote."""
        try:
            self._throttle()
            mkt = Market()
            df = mkt.etf(symbol).quote()
            if isinstance(df, pd.DataFrame) and not df.empty:
                return df
            elif df is not None and not isinstance(df, pd.DataFrame):
                return pd.DataFrame(df)
        except Exception:
            logger.warning(
                "Lỗi tải bảng giá ETF %s qua Market.etf.quote", symbol, exc_info=True
            )

        return pd.DataFrame()

    # -------------------------------------------------------------------------
    # Nhóm E: Lớp fund (Quỹ mở FMarket)
    # -------------------------------------------------------------------------

    def fetch_market_fund_nav(self, symbol: str) -> pd.DataFrame:
        """Lấy giá trị tài sản ròng NAV của quỹ mở qua Market.fund.nav."""
        try:
            self._throttle()
            mkt = Market()
            df = mkt.fund(symbol).nav()
            if isinstance(df, pd.DataFrame) and not df.empty:
                return df
            elif df is not None and not isinstance(df, pd.DataFrame):
                return pd.DataFrame(df)
        except Exception:
            logger.warning(
                "Lỗi tải NAV quỹ mở %s qua Market.fund.nav", symbol, exc_info=True
            )

        return pd.DataFrame()

    def fetch_market_fund_history(self, symbol: str) -> pd.DataFrame:
        """Lấy lịch sử giá trị NAV của quỹ mở qua Market.fund.history."""
        try:
            self._throttle()
            mkt = Market()
            df = mkt.fund(symbol).history()
            if isinstance(df, pd.DataFrame) and not df.empty:
                return df
            elif df is not None and not isinstance(df, pd.DataFrame):
                return pd.DataFrame(df)
        except Exception:
            logger.warning(
                "Lỗi tải lịch sử NAV quỹ %s qua Market.fund.history",
                symbol,
                exc_info=True,
            )

        return pd.DataFrame()

    def fetch_market_fund_top_holding(self, symbol: str) -> pd.DataFrame:
        """Lấy danh mục top cổ phiếu nắm giữ của quỹ mở qua Market.fund.top_holding."""
        try:
            self._throttle()
            mkt = Market()
            df = mkt.fund(symbol).top_holding()
            if isinstance(df, pd.DataFrame) and not df.empty:
                return df
            elif df is not None and not isinstance(df, pd.DataFrame):
                return pd.DataFrame(df)
        except Exception:
            logger.warning(
                "Lỗi tải top holding quỹ %s qua Market.fund.top_holding",
                symbol,
                exc_info=True,
            )

        return pd.DataFrame()

    def fetch_market_fund_asset_holding(self, symbol: str) -> pd.DataFrame:
        """Lấy cơ cấu phân bổ tài sản của quỹ mở qua Market.fund.asset_holding."""
        try:
            self._throttle()
            mkt = Market()
            df = mkt.fund(symbol).asset_holding()
            if isinstance(df, pd.DataFrame) and not df.empty:
                return df
            elif df is not None and not isinstance(df, pd.DataFrame):
                return pd.DataFrame(df)
        except Exception:
            logger.warning(
                "Lỗi tải phân bổ tài sản quỹ %s qua Market.fund.asset_holding",
                symbol,
                exc_info=True,
            )

        return pd.DataFrame()

    def fetch_market_fund_industry_holding(self, symbol: str) -> pd.DataFrame:
        """Lấy cơ cấu phân bổ ngành của quỹ mở qua Market.fund.industry_holding."""
        try:
            self._throttle()
            mkt = Market()
            df = mkt.fund(symbol).industry_holding()
            if isinstance(df, pd.DataFrame) and not df.empty:
                return df
            elif df is not None and not isinstance(df, pd.DataFrame):
                return pd.DataFrame(df)
        except Exception:
            logger.warning(
                "Lỗi tải phân bổ ngành quỹ %s qua Market.fund.industry_holding",
                symbol,
                exc_info=True,
            )

        return pd.DataFrame()

    # -------------------------------------------------------------------------
    # Nhóm F: Tài sản Quốc tế & Vĩ mô (forex, crypto, commodity)
    # -------------------------------------------------------------------------

    def fetch_market_forex_ohlcv(
        self,
        symbol: str = "USDVND",
        start: date | str | None = None,
        end: date | str | None = None,
        interval: str = "1D",
        count: int = 100,
    ) -> pd.DataFrame:
        """Lấy nến tỷ giá ngoại tệ nến OHLCV qua Market.forex.ohlcv."""
        try:
            self._throttle()
            mkt = Market()
            kwargs: dict[str, Any] = {"interval": interval, "count": count}
            s_str = self._format_date_param(start)
            e_str = self._format_date_param(end)
            if s_str:
                kwargs["start"] = s_str
            if e_str:
                kwargs["end"] = e_str

            df = mkt.forex(symbol).ohlcv(**kwargs)
            if isinstance(df, pd.DataFrame) and not df.empty:
                return df
            elif df is not None and not isinstance(df, pd.DataFrame):
                return pd.DataFrame(df)
        except Exception:
            logger.warning(
                "Lỗi tải nến forex %s qua Market.forex.ohlcv", symbol, exc_info=True
            )

        return pd.DataFrame()

    def fetch_market_crypto_ohlcv(
        self,
        symbol: str = "BTC",
        start: date | str | None = None,
        end: date | str | None = None,
        interval: str = "1D",
        count: int = 100,
    ) -> pd.DataFrame:
        """Lấy nến giá tiền mã hóa nến OHLCV qua Market.crypto.ohlcv."""
        try:
            self._throttle()
            mkt = Market()
            kwargs: dict[str, Any] = {"interval": interval, "count": count}
            s_str = self._format_date_param(start)
            e_str = self._format_date_param(end)
            if s_str:
                kwargs["start"] = s_str
            if e_str:
                kwargs["end"] = e_str

            df = mkt.crypto(symbol).ohlcv(**kwargs)
            if isinstance(df, pd.DataFrame) and not df.empty:
                return df
            elif df is not None and not isinstance(df, pd.DataFrame):
                return pd.DataFrame(df)
        except Exception:
            logger.warning(
                "Lỗi tải nến crypto %s qua Market.crypto.ohlcv", symbol, exc_info=True
            )

        return pd.DataFrame()

    def fetch_market_commodity_ohlcv(
        self,
        symbol: str = "Gold",
        start: date | str | None = None,
        end: date | str | None = None,
        interval: str = "1D",
        count: int = 100,
    ) -> pd.DataFrame:
        """Lấy nến giá hàng hóa quốc tế nến OHLCV qua Market.commodity.ohlcv."""
        try:
            self._throttle()
            mkt = Market()
            kwargs: dict[str, Any] = {"interval": interval, "count": count}
            s_str = self._format_date_param(start)
            e_str = self._format_date_param(end)
            if s_str:
                kwargs["start"] = s_str
            if e_str:
                kwargs["end"] = e_str

            df = mkt.commodity(symbol).ohlcv(**kwargs)
            if isinstance(df, pd.DataFrame) and not df.empty:
                return df
            elif df is not None and not isinstance(df, pd.DataFrame):
                return pd.DataFrame(df)
        except Exception:
            logger.warning(
                "Lỗi tải nến hàng hóa %s qua Market.commodity.ohlcv",
                symbol,
                exc_info=True,
            )

        return pd.DataFrame()

    # -------------------------------------------------------------------------
    # Nhóm G: Lớp bond (Trái phiếu)
    # -------------------------------------------------------------------------

    def fetch_market_bond_ohlcv(
        self,
        symbol: str,
        start: date | str | None = None,
        end: date | str | None = None,
        interval: str = "1D",
        count: int = 100,
    ) -> pd.DataFrame:
        """Lấy nến giá giao dịch trái phiếu qua Market.bond.ohlcv."""
        try:
            self._throttle()
            mkt = Market()
            kwargs: dict[str, Any] = {"interval": interval, "count": count}
            s_str = self._format_date_param(start)
            e_str = self._format_date_param(end)
            if s_str:
                kwargs["start"] = s_str
            if e_str:
                kwargs["end"] = e_str

            df = mkt.bond(symbol).ohlcv(**kwargs)
            if isinstance(df, pd.DataFrame) and not df.empty:
                return df
            elif df is not None and not isinstance(df, pd.DataFrame):
                return pd.DataFrame(df)
        except Exception:
            logger.warning(
                "Lỗi tải nến trái phiếu %s qua Market.bond.ohlcv", symbol, exc_info=True
            )

        return pd.DataFrame()

    def fetch_market_bond_quote(self, symbol: str) -> pd.DataFrame:
        """Lấy bảng giá trái phiếu qua Market.bond.quote."""
        try:
            self._throttle()
            mkt = Market()
            df = mkt.bond(symbol).quote()
            if isinstance(df, pd.DataFrame) and not df.empty:
                return df
            elif df is not None and not isinstance(df, pd.DataFrame):
                return pd.DataFrame(df)
        except Exception:
            logger.warning(
                "Lỗi tải bảng giá trái phiếu %s qua Market.bond.quote",
                symbol,
                exc_info=True,
            )

        return pd.DataFrame()

    def fetch_market_bond_trades(self, symbol: str) -> pd.DataFrame:
        """Lấy dữ liệu khớp lệnh chi tiết trái phiếu trong ngày qua Market.bond.trades."""
        try:
            self._throttle()
            mkt = Market()
            df = mkt.bond(symbol).trades()
            if isinstance(df, pd.DataFrame) and not df.empty:
                return df
            elif df is not None and not isinstance(df, pd.DataFrame):
                return pd.DataFrame(df)
        except Exception:
            logger.warning(
                "Lỗi tải khớp lệnh trái phiếu %s qua Market.bond.trades",
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
            fnd = Fundamental()
            eq = self._resolve_sub_obj(fnd, "equity", symbol)
            if eq is not None:
                method_map_fnd = {
                    "income_statement": getattr(eq, "income_statement", None),
                    "balance_sheet": getattr(eq, "balance_sheet", None),
                    "cash_flow": getattr(eq, "cash_flow", None),
                }
                fetch_fn = method_map_fnd.get(report_type)
                if fetch_fn is not None:
                    df = fetch_fn(period=period_clean, orient=orient)
                    if isinstance(df, pd.DataFrame) and not df.empty:
                        self.record_success()
                        logger.info(
                            "Đã tải %d dòng BCTC %s cho %s (%s, %s) qua Fundamental",
                            len(df),
                            report_type,
                            symbol,
                            period_clean,
                            orient,
                        )
                        return df
                    elif df is not None and not isinstance(df, pd.DataFrame):
                        self.record_success()
                        return pd.DataFrame(df)
        except Exception:
            self.record_failure()
            logger.warning(
                "Lỗi tải BCTC %s cho %s qua Fundamental, thử fallback qua Finance...",
                report_type,
                symbol,
                exc_info=True,
            )

        # Fallback qua lớp Finance truyền thống
        for src in valid_sources:
            try:
                self._throttle(src)
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
                    self.record_success(src)
                    logger.info(
                        "Đã tải %d dòng BCTC %s cho %s (%s) qua Finance/%s",
                        len(df),
                        report_type,
                        symbol,
                        period_clean,
                        src,
                    )
                    return df
            except CircuitBreakerOpenError:
                logger.warning("Circuit breaker is OPEN for %s, skipping provider", src)
                continue
            except Exception:
                self.record_failure(src)
                continue

        raise VnstockServiceError(
            f"Không thể tải báo cáo tài chính {report_type} cho {symbol}"
        )

    def fetch_fundamental_income_statement(
        self,
        symbol: str,
        period: str = "year",
        orient: str = "report",
        **kwargs: Any,
    ) -> pd.DataFrame:
        """Lấy kết quả kinh doanh của doanh nghiệp qua Fundamental.equity.income_statement()."""
        return self.fetch_financials(
            symbol=symbol,
            report_type="income_statement",
            period=period,
            orient=orient,
        )

    def fetch_fundamental_balance_sheet(
        self,
        symbol: str,
        period: str = "year",
        orient: str = "report",
        **kwargs: Any,
    ) -> pd.DataFrame:
        """Lấy bảng cân đối kế toán của doanh nghiệp qua Fundamental.equity.balance_sheet()."""
        return self.fetch_financials(
            symbol=symbol,
            report_type="balance_sheet",
            period=period,
            orient=orient,
        )

    def fetch_fundamental_cash_flow(
        self,
        symbol: str,
        period: str = "year",
        orient: str = "report",
        **kwargs: Any,
    ) -> pd.DataFrame:
        """Lấy báo cáo lưu chuyển tiền tệ qua Fundamental.equity.cash_flow()."""
        return self.fetch_financials(
            symbol=symbol,
            report_type="cash_flow",
            period=period,
            orient=orient,
        )

    def fetch_fundamental_ratio(
        self,
        symbol: str,
        orient: str = "report",
        **kwargs: Any,
    ) -> pd.DataFrame:
        """Lấy hơn 50 chỉ số tài chính và định giá định lượng qua Fundamental.equity.ratio()."""
        return self.fetch_financial_ratios(symbol=symbol, orient=orient)

    def fetch_fundamental_ratios(
        self,
        symbol: str,
        orient: str = "report",
        **kwargs: Any,
    ) -> pd.DataFrame:
        """Lấy các chỉ số tài chính qua Fundamental.equity.ratios() (alias)."""
        return self.fetch_fundamental_ratio(symbol=symbol, orient=orient, **kwargs)

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
            fnd = Fundamental()
            eq = self._resolve_sub_obj(fnd, "equity", symbol)
            if eq is not None and hasattr(eq, "ratio"):
                df = eq.ratio(orient=orient)
                if isinstance(df, pd.DataFrame) and not df.empty:
                    self.record_success()
                    logger.info(
                        "Đã tải %d chỉ số tài chính cho %s qua Fundamental.equity.ratio",
                        len(df),
                        symbol,
                    )
                    return df
                elif df is not None and not isinstance(df, pd.DataFrame):
                    self.record_success()
                    return pd.DataFrame(df)
        except Exception:
            self.record_failure()
            logger.warning(
                "Lỗi tải chỉ số tài chính qua Fundamental cho %s, thử Finance...",
                symbol,
                exc_info=True,
            )

        # Fallback qua lớp Finance
        valid_sources = self._get_valid_sources(self.VALID_SOURCES_FINANCE)
        for src in valid_sources:
            try:
                self._throttle(src)
                f = Finance(symbol=symbol, source=src, show_log=False)
                df = f.ratio()
                if df is not None and not df.empty:
                    self.record_success(src)
                    logger.info(
                        "Đã tải chỉ số tài chính cho %s qua Finance/%s", symbol, src
                    )
                    return df
            except CircuitBreakerOpenError:
                logger.warning("Circuit breaker is OPEN for %s, skipping provider", src)
                continue
            except Exception:
                self.record_failure(src)
                continue

        raise VnstockServiceError(f"Không thể tải chỉ số tài chính cho mã {symbol}")

    # =========================================================================
    # PHÂN HỆ 5: HÀNG HÓA, VÀNG & NGOẠI TỆ BÁN LẺ (RETAIL DATA)
    # =========================================================================

    def fetch_retail_gold(
        self,
        source: str = "sjc",
        date: date | str | None = None,
    ) -> pd.DataFrame:
        """Tải dữ liệu giá vàng trong nước (SJC, Bảo Tín Minh Châu) qua Retail.gold().

        Tham số:
            source: Nguồn giá vàng ('sjc' hoặc 'btmc').
            date: Ngày tra cứu 'YYYY-MM-DD' hoặc datetime.date (None để lấy giá mới nhất).

        Trả về:
            pd.DataFrame bảng giá vàng (time, buy, sell, type).
        """
        actual_source = source
        actual_date = date
        if isinstance(date, str) and date.lower() in ("sjc", "btmc"):
            actual_source = date.lower()
            actual_date = None

        date_str = self._format_date_param(actual_date)

        try:
            self._throttle()
            retail = Retail()
            df = retail.gold(source=actual_source.lower(), date=date_str)
            if isinstance(df, pd.DataFrame) and not df.empty:
                logger.info(
                    "Đã tải %d dòng giá vàng (%s, ngày: %s)",
                    len(df),
                    actual_source,
                    date_str or "mới nhất",
                )
                return df
            elif df is not None and not isinstance(df, pd.DataFrame):
                return pd.DataFrame(df)
        except Exception:
            logger.warning("Lỗi tải giá vàng nguồn %s", actual_source, exc_info=True)

        return pd.DataFrame()

    def fetch_gold_prices(
        self,
        date_str: date | str | None = None,
        source: str = "sjc",
    ) -> pd.DataFrame:
        """Tải dữ liệu giá vàng trong nước (alias tương thích ngược cho fetch_retail_gold)."""
        return self.fetch_retail_gold(source=source, date=date_str)

    def fetch_retail_exchange_rate(
        self,
        date: date | str = "",
    ) -> pd.DataFrame:
        """Tải tỷ giá ngoại hối trực tiếp từ ngân hàng Vietcombank (VCB) qua Retail.exchange_rate().

        Tham số:
            date: Ngày tra cứu 'YYYY-MM-DD' hoặc datetime.date (để trống lấy tỷ giá hiện tại).

        Trả về:
            pd.DataFrame tỷ giá ngoại tệ (currency, buy_cash, buy_transfer, sell).
        """
        date_str = self._format_date_param(date) if date else ""

        try:
            self._throttle()
            retail = Retail()
            df = retail.exchange_rate(date=date_str or "")
            if isinstance(df, pd.DataFrame) and not df.empty:
                logger.info(
                    "Đã tải %d dòng tỷ giá ngoại tệ (ngày: %s)",
                    len(df),
                    date_str or "hiện tại",
                )
                return df
            elif df is not None and not isinstance(df, pd.DataFrame):
                return pd.DataFrame(df)
        except Exception:
            logger.warning("Lỗi tải tỷ giá ngoại tệ", exc_info=True)

        return pd.DataFrame()

    def fetch_exchange_rate(self, date_str: date | str = "") -> pd.DataFrame:
        """Tải tỷ giá ngoại tệ Vietcombank (alias tương thích ngược cho fetch_retail_exchange_rate)."""
        return self.fetch_retail_exchange_rate(date=date_str)


# Khởi tạo thể hiện Singleton dùng chung toàn bộ ứng dụng
vnstock_service = VnstockService()
