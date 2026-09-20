"""DataSyncManager — orchestrates data synchronization from vnstock → PostgreSQL.

3 sync modes:
1. Historical Backfill  — one-time full data import
2. Incremental Daily    — daily update after market close
3. Intraday Collector   — realtime bar collection during trading session
"""

from __future__ import annotations

import gc
import logging
import uuid
from collections.abc import Callable
from datetime import UTC, date, datetime
from typing import Any

import pandas as pd
from sqlalchemy import and_
from sqlmodel import Session, col, select

from app.models.models_stock import (
    BondSpecification,
    CompanyProfile,
    CoveredWarrant,
    DataSyncLog,
    DerivativeContract,
    FinancialReport,
    StockOHLCVDaily,
    StockOHLCVIntraday,
    StockSymbol,
)
from app.services.vnstock_service import VnstockService, VnstockServiceError

logger = logging.getLogger(__name__)

# Bảng tra cứu & thiết lập cấu hình định danh
STANDARD_INDEXES: frozenset[str] = frozenset(
    {"VNINDEX", "VN30", "HNX", "HNX30", "UPCOM"}
)

BOND_TYPE_CONFIG: dict[str, tuple[str, str]] = {
    "corporate": ("Trái phiếu DN", "corporate_bond"),
    "government": ("Trái phiếu Chính phủ", "government_bond"),
}

META_FINANCIAL_KEYS: frozenset[str] = frozenset(
    {"year", "yearReport", "quarter", "lengthReport", "ticker", "symbol"}
)

STOCK_SYMBOL_UPDATE_FIELDS: list[str] = [
    "organ_name",
    "exchange",
    "industry",
    "icb_code",
    "icb_name",
    "asset_type",
    "lot_size",
    "is_active",
    "updated_at",
]

CW_STOCK_SYMBOL_UPDATE_FIELDS: list[str] = [
    "organ_name",
    "exchange",
    "industry",
    "asset_type",
    "lot_size",
    "is_active",
    "updated_at",
]

COVERED_WARRANT_UPDATE_FIELDS: list[str] = [
    "underlying_symbol",
    "issuer_name",
    "warrant_type",
    "exercise_price",
    "conversion_ratio",
    "exercise_ratio",
    "issue_date",
    "maturity_date",
    "last_trading_date",
    "settlement_type",
    "is_active",
    "updated_at",
]

BOND_SPECIFICATION_UPDATE_FIELDS: list[str] = [
    "bond_type",
    "issuer_symbol",
    "issuer_name",
    "par_value",
    "coupon_rate",
    "coupon_type",
    "tenor_years",
    "issue_date",
    "maturity_date",
    "is_active",
    "updated_at",
]


def get_third_thursday(year: int, month: int) -> date:
    """Tính ngày Thứ Năm lần thứ 3 trong tháng (ngày đáo hạn hợp đồng phái sinh VN30)."""
    first_day = date(year, month, 1)
    days_to_thursday = (3 - first_day.weekday()) % 7
    first_thursday = first_day.day + days_to_thursday
    return date(year, month, first_thursday + 14)


class DataSyncManager:
    """Manage data synchronization from vnstock API → PostgreSQL."""

    def __init__(
        self,
        session: Session,
        vnstock_svc: VnstockService | None = None,
    ) -> None:
        self.session = session
        self.svc = vnstock_svc or VnstockService()

    @property
    def is_postgresql(self) -> bool:
        """Kiểm tra xem kết nối cơ sở dữ liệu hiện tại có phải là PostgreSQL hay không."""
        bind = self.session.get_bind()
        return getattr(getattr(bind, "dialect", None), "name", "") == "postgresql"

    # ------------------------------------------------------------------
    # Common Reusable Handlers & Lifecycle Management
    # ------------------------------------------------------------------

    def _create_log(self, sync_type: str, symbol: str | None = None) -> DataSyncLog:
        """Create a sync log entry with status 'started'."""
        source_val = getattr(self.svc, "source", None)
        source_str = source_val[:10] if isinstance(source_val, str) else "VCI"
        log = DataSyncLog(
            sync_type=sync_type,
            symbol=symbol,
            source=source_str,
            status="started",
        )
        self.session.add(log)
        self.session.flush()
        return log

    def _finish_log(
        self,
        log: DataSyncLog,
        status: str,
        rows_synced: int = 0,
        error_message: str | None = None,
    ) -> DataSyncLog:
        """Update a sync log entry on completion."""
        log.status = status
        log.rows_synced = rows_synced
        log.error_message = error_message
        log.completed_at = datetime.now(UTC)
        self.session.add(log)
        self.session.commit()
        return log

    def _run_sync_task(
        self,
        sync_type: str,
        task_func: Callable[[], int],
        symbol: str | None = None,
    ) -> DataSyncLog:
        """Quản lý vòng đời của một tác vụ đồng bộ: khởi tạo log -> thực thi -> bắt lỗi & rollback -> cập nhật log."""
        log = self._create_log(sync_type, symbol=symbol)
        try:
            rows_synced = task_func()
            return self._finish_log(log, "success", rows_synced=rows_synced)
        except VnstockServiceError as exc:
            return self._finish_log(log, "failed", error_message=str(exc))
        except Exception as exc:
            self.session.rollback()
            logger.exception("Lỗi đồng bộ %s (symbol=%s)", sync_type, symbol)
            return self._finish_log(log, "failed", error_message=str(exc))

    def _bulk_upsert(
        self,
        model_cls: type[Any],
        records: list[dict[str, Any]],
        conflict_keys: list[str],
        update_fields: list[str],
        batch_size: int = 500,
    ) -> int:
        """Thực hiện bulk upsert dữ liệu vào DB theo batch, tương thích PostgreSQL & SQLite.

        Bảo toàn trường khóa chính `id` (UUID), không ghi đè UUID cũ khi cập nhật.
        """
        if not records:
            return 0

        if self.is_postgresql:
            from sqlalchemy.dialects.postgresql import insert as pg_insert

            for i in range(0, len(records), batch_size):
                batch = records[i : i + batch_size]
                stmt = pg_insert(model_cls).values(batch)
                stmt = stmt.on_conflict_do_update(
                    index_elements=conflict_keys,
                    set_={f: getattr(stmt.excluded, f) for f in update_fields},
                )
                self.session.execute(stmt)
        else:
            for rec in records:
                conditions = [
                    getattr(model_cls, k) == rec[k] for k in conflict_keys if k in rec
                ]
                existing = (
                    self.session.exec(
                        select(model_cls).where(and_(*conditions))
                    ).first()
                    if conditions
                    else None
                )
                if existing:
                    for f in update_fields:
                        if f in rec and rec[f] is not None:
                            setattr(existing, f, rec[f])
                    self.session.add(existing)
                else:
                    self.session.add(model_cls(**rec))
            self.session.flush()

        return len(records)

    def _find_or_create_symbols(
        self,
        symbols: set[str] | list[str],
        *,
        auto_create: bool = False,
        default_name_prefix: str = "Mã cơ sở",
        asset_type: str = "stock",
        exchange: str = "HOSE",
        lot_size: int = 100,
    ) -> set[str]:
        """Tìm kiếm danh sách mã chứng khoán đã tồn tại; tự động thêm mới nếu auto_create=True."""
        clean_symbols = {str(s).strip().upper() for s in symbols if str(s).strip()}
        if not clean_symbols:
            return set()

        existing = set(
            self.session.exec(
                select(StockSymbol.symbol).where(
                    col(StockSymbol.symbol).in_(list(clean_symbols))
                )
            ).all()
        )
        if auto_create:
            missing = clean_symbols - existing
            if missing:
                now_utc = datetime.now(UTC)
                for sym in missing:
                    self.session.add(
                        StockSymbol(
                            id=uuid.uuid4(),
                            symbol=sym,
                            organ_name=f"{default_name_prefix} {sym}",
                            exchange=exchange,
                            industry="Equities",
                            asset_type=asset_type,
                            lot_size=lot_size,
                            is_active=True,
                            updated_at=now_utc,
                        )
                    )
                self.session.flush()
                existing.update(missing)
        return existing

    def _ensure_symbol_exists(
        self,
        symbol: str,
        organ_name: str | None = None,
        asset_type: str = "stock",
        exchange: str | None = None,
        lot_size: int = 100,
    ) -> None:
        """Ensure a symbol exists in stock_symbol before adding related records."""
        clean_sym = symbol.strip().upper()
        prefix = organ_name or f"Mã {clean_sym}"
        self._find_or_create_symbols(
            {clean_sym},
            auto_create=True,
            default_name_prefix=prefix,
            asset_type=asset_type,
            exchange=exchange or "HOSE",
            lot_size=lot_size,
        )
        self.session.commit()

    # ------------------------------------------------------------------
    # Data Normalization & Extraction Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_to_dataframe(data: Any, symbol_col: str = "symbol") -> pd.DataFrame:
        """Chuẩn hóa dữ liệu đầu vào (DataFrame, Series, list) thành pd.DataFrame duy nhất."""
        match data:
            case pd.DataFrame() if not data.empty:
                return data
            case pd.Series() if not data.empty:
                return pd.DataFrame({symbol_col: data})
            case list() if data:
                return pd.DataFrame({symbol_col: data})
            case _:
                return pd.DataFrame()

    @staticmethod
    def _resolve_symbol_column(df: pd.DataFrame) -> str | None:
        """Xác định tên cột biểu diễn mã chứng khoán trong DataFrame."""
        if df.empty:
            return None
        for candidate in ("symbol", "ticker"):
            if candidate in df.columns:
                return candidate
        return df.columns[0] if len(df.columns) > 0 else None

    @staticmethod
    def _classify_symbol(
        symbol_str: str,
        raw_type: str = "stock",
        exchange: str | None = None,
    ) -> tuple[str, int, str | None]:
        """Phân loại nhóm tài sản (asset_type), quy mô lô (lot_size) và sàn giao dịch (exchange)."""
        match symbol_str:
            case s if "VN30F" in s:
                return "derivative", 1, exchange or "DERIV"
            case s if s.startswith(("E1VFVN30", "FUE")) or "ETF" in s:
                return "etf", 100, exchange
            case s if s in STANDARD_INDEXES:
                return "index", 1, exchange
            case _:
                return raw_type.lower(), 100, exchange

    @staticmethod
    def _extract_warrant_meta(
        code: str,
        raw_underlying: Any = None,
        raw_warrant_type: Any = None,
    ) -> tuple[str | None, str]:
        """Trích xuất mã tài sản cơ sở và loại chứng quyền (call/put) bằng pattern matching."""
        if raw_underlying and pd.notna(raw_underlying):
            underlying = str(raw_underlying).strip().upper()
        else:
            match code:
                case s if s.startswith(("C", "P")) and len(s) == 8:
                    underlying = s[1:4]
                case s if s.startswith(("C", "P")) and len(s) >= 6:
                    underlying = s[1:-4] if len(s) > 6 else s[1:4]
                case _:
                    underlying = None

        raw_w_str = str(raw_warrant_type or "").lower().strip()
        match raw_w_str:
            case "call" | "put":
                warrant_type = raw_w_str
            case _:
                match code:
                    case s if s.startswith("C"):
                        warrant_type = "call"
                    case s if s.startswith("P"):
                        warrant_type = "put"
                    case _:
                        warrant_type = "call"

        return underlying, warrant_type

    @staticmethod
    def _extract_derivative_expiry(code: str, fallback: date) -> date:
        """Trích xuất ngày đáo hạn phái sinh từ mã hợp đồng hoặc dùng ngày dự phòng."""
        match code:
            case s if len(s) == 9 and s.startswith("VN30F"):
                try:
                    yy = 2000 + int(s[5:7])
                    mm = int(s[7:9])
                    return get_third_thursday(yy, mm)
                except (ValueError, IndexError):
                    return fallback
            case _:
                return fallback

    @staticmethod
    def _parse_date(value: object) -> date | None:
        """Parse various date formats to date object using pattern matching."""
        match value:
            case datetime():
                return value.date()
            case date():
                return value
            case pd.Timestamp():
                return value.date()
            case str() if value.strip():
                try:
                    return datetime.strptime(value.strip()[:10], "%Y-%m-%d").date()
                except ValueError:
                    return None
            case _:
                return None

    @staticmethod
    def _parse_datetime(value: object) -> datetime | None:
        """Parse various datetime formats using pattern matching."""
        match value:
            case datetime():
                return value
            case pd.Timestamp():
                return value.to_pydatetime()
            case str() if value.strip():
                clean_val = value.strip()
                for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
                    try:
                        return datetime.strptime(clean_val, fmt)
                    except ValueError:
                        continue
                return None
            case _:
                return None

    @staticmethod
    def _parse_float(value: object) -> float | None:
        """Parse various numeric formats safely to float using pattern matching."""
        match value:
            case None:
                return None
            case float() | int():
                return float(value)
            case _ if pd.isna(value):
                return None
            case _:
                try:
                    return float(value)  # type: ignore
                except (ValueError, TypeError):
                    return None

    # ------------------------------------------------------------------
    # Sub-Sync Logics (VN30, Derivatives, CW, Bonds)
    # ------------------------------------------------------------------

    def _sync_vn30_group(self) -> int:
        """Cập nhật cờ index_group='VN30' cho các cổ phiếu thuộc rổ VN30."""
        try:
            vn30_symbols = self.svc.fetch_group_symbols("VN30")
            if not vn30_symbols:
                return 0
            tickers = [str(s).strip().upper() for s in vn30_symbols if str(s).strip()]
            if not tickers:
                return 0

            if self.is_postgresql:
                from sqlalchemy import update

                stmt = (
                    update(StockSymbol)
                    .where(col(StockSymbol.symbol).in_(tickers))
                    .values(index_group="VN30", updated_at=datetime.now(UTC))
                )
                self.session.execute(stmt)
                return len(tickers)

            count = 0
            for ticker in tickers:
                sym = self.session.get(StockSymbol, ticker)
                if sym:
                    sym.index_group = "VN30"
                    self.session.add(sym)
                    count += 1
            return count
        except Exception as exc:
            logger.warning("Could not fetch VN30 group during symbols sync: %s", exc)
            return 0

    def _sync_derivatives(self) -> int:
        """Đồng bộ các hợp đồng phái sinh chuẩn vào StockSymbol và DerivativeContract."""
        today = date.today()
        this_month_thursday = get_third_thursday(today.year, today.month)
        if today <= this_month_thursday:
            m1_year, m1_month = today.year, today.month
            m1_exp = this_month_thursday
        else:
            m1_month = today.month + 1 if today.month < 12 else 1
            m1_year = today.year if today.month < 12 else today.year + 1
            m1_exp = get_third_thursday(m1_year, m1_month)

        m2_month = m1_month + 1 if m1_month < 12 else 1
        m2_year = m1_year if m1_month < 12 else m1_year + 1
        m2_exp = get_third_thursday(m2_year, m2_month)

        contracts = [
            ("VN30F1M", m1_exp, "Hợp đồng tương lai VN30 tháng hiện tại"),
            ("VN30F2M", m2_exp, "Hợp đồng tương lai VN30 tháng kế tiếp"),
        ]

        count = 0
        now_utc = datetime.now(UTC)
        for symbol_code, exp_date, desc in contracts:
            sym = self.session.get(StockSymbol, symbol_code)
            if sym:
                sym.organ_name = desc
                sym.exchange = "DERIV"
                sym.asset_type = "derivative"
                sym.lot_size = 1
                sym.is_active = True
                sym.updated_at = now_utc
                self.session.add(sym)
            else:
                self.session.add(
                    StockSymbol(
                        id=uuid.uuid4(),
                        symbol=symbol_code,
                        organ_name=desc,
                        exchange="DERIV",
                        industry="Derivatives",
                        asset_type="derivative",
                        lot_size=1,
                        is_active=True,
                        updated_at=now_utc,
                    )
                )

            contract = self.session.get(DerivativeContract, symbol_code)
            if contract:
                contract.expiration_date = exp_date
                contract.underlying_symbol = "VN30"
                contract.multiplier = 100_000.0
                contract.is_active = True
                contract.updated_at = now_utc
                self.session.add(contract)
            else:
                self.session.add(
                    DerivativeContract(
                        id=uuid.uuid4(),
                        symbol=symbol_code,
                        underlying_symbol="VN30",
                        multiplier=100_000.0,
                        expiration_date=exp_date,
                        is_active=True,
                        updated_at=now_utc,
                    )
                )
            count += 1

        try:
            deriv_raw = self.svc.fetch_derivatives_list()
            deriv_df = self._normalize_to_dataframe(deriv_raw, symbol_col="ticker")
            if not deriv_df.empty:
                col_name = self._resolve_symbol_column(deriv_df)
                if col_name:
                    contract_codes = {c[0] for c in contracts}
                    for _, row in deriv_df.iterrows():
                        code = str(row.get(col_name, "")).strip().upper()
                        if not code or code in contract_codes:
                            continue

                        exp = self._extract_derivative_expiry(code, fallback=m1_exp)
                        sym = self.session.get(StockSymbol, code)
                        if not sym:
                            self.session.add(
                                StockSymbol(
                                    id=uuid.uuid4(),
                                    symbol=code,
                                    organ_name=f"Hợp đồng tương lai {code}",
                                    exchange="DERIV",
                                    industry="Derivatives",
                                    asset_type="derivative",
                                    lot_size=1,
                                    is_active=True,
                                    updated_at=now_utc,
                                )
                            )
                        contract = self.session.get(DerivativeContract, code)
                        if not contract:
                            self.session.add(
                                DerivativeContract(
                                    id=uuid.uuid4(),
                                    symbol=code,
                                    underlying_symbol="VN30",
                                    multiplier=100_000.0,
                                    expiration_date=exp,
                                    is_active=True,
                                    updated_at=now_utc,
                                )
                            )
                        count += 1
        except Exception as exc:
            logger.warning("Could not fetch extra derivatives list: %s", exc)

        return count

    def _sync_covered_warrants(self) -> int:
        """Đồng bộ danh mục chứng quyền có bảo đảm (CW) vào StockSymbol và CoveredWarrant sử dụng Bulk UPSERT."""
        cw_data = self.svc.fetch_covered_warrants_list()
        df = self._normalize_to_dataframe(cw_data)
        if df.empty:
            return 0

        col_sym = self._resolve_symbol_column(df)
        if not col_sym:
            return 0

        now_utc = datetime.now(UTC)
        today_d = date.today()

        sym_map: dict[str, dict[str, Any]] = {}
        cw_map: dict[str, dict[str, Any]] = {}
        underlying_codes: set[str] = set()

        for _, row in df.iterrows():
            code = str(row.get(col_sym, "")).strip().upper()
            if not code or len(code) < 6:
                continue

            raw_und = row.get(
                "underlying_symbol",
                row.get("underlying", row.get("target_symbol", None)),
            )
            raw_wtype = row.get("warrant_type", row.get("type", None))
            underlying, warrant_type = self._extract_warrant_meta(
                code, raw_underlying=raw_und, raw_warrant_type=raw_wtype
            )
            if not underlying:
                continue

            underlying_codes.add(underlying)

            issuer_name = (
                str(row.get("issuer_name", row.get("issuer", ""))).strip() or None
            )
            exercise_price = self._parse_float(
                row.get("exercise_price", row.get("exercisePrice"))
            )
            conversion_ratio = (
                str(
                    row.get(
                        "conversion_ratio",
                        row.get("conversionRatio", ""),
                    )
                ).strip()
                or None
            )
            exercise_ratio = self._parse_float(
                row.get(
                    "exercise_ratio",
                    row.get("exerciseRatio", row.get("ratio")),
                )
            )
            issue_date = self._parse_date(row.get("issue_date", row.get("issueDate")))
            maturity_date = self._parse_date(
                row.get(
                    "maturity_date",
                    row.get("maturityDate", row.get("expiration_date")),
                )
            )
            last_trading_date = self._parse_date(
                row.get("last_trading_date", row.get("lastTradingDate"))
            )
            settlement_type = (
                str(
                    row.get(
                        "settlement_type",
                        row.get("settlementType", "cash"),
                    )
                ).strip()
                or "cash"
            )

            is_active = not (maturity_date and maturity_date < today_d)

            sym_map[code] = {
                "id": uuid.uuid4(),
                "symbol": code,
                "organ_name": f"Chứng quyền {code} (Cơ sở {underlying})",
                "exchange": "HOSE",
                "industry": "Covered Warrants",
                "asset_type": "covered_warrant",
                "lot_size": 10,
                "is_active": is_active,
                "updated_at": now_utc,
            }

            cw_map[code] = {
                "id": uuid.uuid4(),
                "symbol": code,
                "underlying_symbol": underlying,
                "issuer_name": issuer_name,
                "warrant_type": warrant_type,
                "exercise_price": exercise_price,
                "conversion_ratio": conversion_ratio,
                "exercise_ratio": exercise_ratio,
                "issue_date": issue_date,
                "maturity_date": maturity_date,
                "last_trading_date": last_trading_date,
                "settlement_type": settlement_type,
                "is_active": is_active,
                "updated_at": now_utc,
            }

        if not cw_map:
            return 0

        # Đảm bảo tất cả mã cơ sở (underlying_symbol) đã tồn tại trong StockSymbol
        self._find_or_create_symbols(
            underlying_codes,
            auto_create=True,
            default_name_prefix="Cổ phiếu cơ sở",
        )

        # Bulk UPSERT cả 2 bảng StockSymbol và CoveredWarrant
        self._bulk_upsert(
            StockSymbol,
            list(sym_map.values()),
            ["symbol"],
            CW_STOCK_SYMBOL_UPDATE_FIELDS,
        )
        self._bulk_upsert(
            CoveredWarrant,
            list(cw_map.values()),
            ["symbol"],
            COVERED_WARRANT_UPDATE_FIELDS,
        )

        self.session.commit()
        return len(cw_map)

    def _sync_bonds(self) -> int:
        """Đồng bộ danh mục trái phiếu doanh nghiệp & chính phủ vào StockSymbol và BondSpecification sử dụng Bulk UPSERT."""
        raw_bonds = self.svc.fetch_bonds_list(bond_type="all")
        df = self._normalize_to_dataframe(raw_bonds)
        if df.empty:
            return 0

        col_sym = self._resolve_symbol_column(df)
        if not col_sym:
            return 0

        now_utc = datetime.now(UTC)
        today_d = date.today()

        sym_map: dict[str, dict[str, Any]] = {}
        bond_map: dict[str, dict[str, Any]] = {}
        candidate_issuers: set[str] = set()

        for _, row in df.iterrows():
            code = str(row.get(col_sym, "")).strip().upper()
            if not code:
                continue

            raw_b_type = str(row.get("type", row.get("bond_type", "corporate"))).lower()
            b_type = "government" if raw_b_type == "government" else "corporate"

            if b_type == "corporate":
                raw_issuer = row.get(
                    "issuer_symbol",
                    row.get("issuerSymbol", row.get("company_code")),
                )
                cand = (
                    str(raw_issuer).strip().upper()
                    if raw_issuer and pd.notna(raw_issuer)
                    else code[:3]
                )
                candidate_issuers.add(cand)

        # Tra cứu các mã doanh nghiệp phát hành đã tồn tại
        existing_issuers = self._find_or_create_symbols(
            candidate_issuers, auto_create=False
        )

        for _, row in df.iterrows():
            code = str(row.get(col_sym, "")).strip().upper()
            if not code:
                continue

            raw_b_type = str(row.get("type", row.get("bond_type", "corporate"))).lower()
            b_type = "government" if raw_b_type == "government" else "corporate"

            issuer_symbol = None
            if b_type == "corporate":
                raw_issuer = row.get(
                    "issuer_symbol",
                    row.get("issuerSymbol", row.get("company_code")),
                )
                cand = (
                    str(raw_issuer).strip().upper()
                    if raw_issuer and pd.notna(raw_issuer)
                    else code[:3]
                )
                if cand in existing_issuers:
                    issuer_symbol = cand

            issuer_name = (
                str(row.get("issuer_name", row.get("issuer", ""))).strip() or None
            )
            par_value = (
                self._parse_float(row.get("par_value", row.get("parValue")))
                or 100_000.0
            )
            coupon_rate = self._parse_float(
                row.get(
                    "coupon_rate",
                    row.get("couponRate", row.get("coupon")),
                )
            )
            coupon_type = (
                str(
                    row.get(
                        "coupon_type",
                        row.get("couponType", "fixed"),
                    )
                ).strip()
                or "fixed"
            )
            tenor_years = self._parse_float(
                row.get(
                    "tenor_years",
                    row.get("tenorYears", row.get("term")),
                )
            )
            issue_date = self._parse_date(row.get("issue_date", row.get("issueDate")))
            maturity_date = self._parse_date(
                row.get(
                    "maturity_date",
                    row.get("maturityDate", row.get("expiration_date")),
                )
            )

            is_active = not (maturity_date and maturity_date < today_d)

            label_prefix, asset_label = BOND_TYPE_CONFIG.get(
                b_type, ("Trái phiếu", "corporate_bond")
            )
            organ_label = f"{label_prefix} {code}"

            sym_map[code] = {
                "id": uuid.uuid4(),
                "symbol": code,
                "organ_name": organ_label,
                "exchange": "HNX",
                "industry": "Bonds",
                "asset_type": asset_label,
                "lot_size": 1,
                "is_active": is_active,
                "updated_at": now_utc,
            }

            bond_map[code] = {
                "id": uuid.uuid4(),
                "symbol": code,
                "bond_type": b_type,
                "issuer_symbol": issuer_symbol,
                "issuer_name": issuer_name,
                "par_value": par_value,
                "coupon_rate": coupon_rate,
                "coupon_type": coupon_type,
                "tenor_years": tenor_years,
                "issue_date": issue_date,
                "maturity_date": maturity_date,
                "is_active": is_active,
                "updated_at": now_utc,
            }

        if not bond_map:
            return 0

        # Bulk UPSERT cả 2 bảng StockSymbol và BondSpecification
        self._bulk_upsert(
            StockSymbol,
            list(sym_map.values()),
            ["symbol"],
            CW_STOCK_SYMBOL_UPDATE_FIELDS,
        )
        self._bulk_upsert(
            BondSpecification,
            list(bond_map.values()),
            ["symbol"],
            BOND_SPECIFICATION_UPDATE_FIELDS,
        )

        self.session.commit()
        return len(bond_map)

    # ------------------------------------------------------------------
    # Public Sync APIs
    # ------------------------------------------------------------------

    def sync_covered_warrants(self) -> DataSyncLog:
        """Đồng bộ riêng danh mục chứng quyền có bảo đảm (Covered Warrants)."""
        return self._run_sync_task("covered_warrants", self._sync_covered_warrants)

    def sync_bonds(self) -> DataSyncLog:
        """Đồng bộ riêng danh mục trái phiếu doanh nghiệp & chính phủ."""
        return self._run_sync_task("bonds", self._sync_bonds)

    def sync_symbols(self) -> DataSyncLog:
        """Sync all stock symbols to the database."""

        def _task() -> int:
            raw_symbols = self.svc.fetch_all_symbols()
            df = self._normalize_to_dataframe(raw_symbols)
            if df.empty:
                raise VnstockServiceError("Empty response")

            now_utc = datetime.now(UTC)
            records = []
            for _, row in df.iterrows():
                symbol_str = (
                    str(row.get("ticker", row.get("symbol", ""))).strip().upper()
                )
                if not symbol_str:
                    continue

                organ_name = (
                    str(row.get("organName", row.get("organ_name", ""))) or None
                )
                raw_exchange = (
                    str(row.get("exchange", row.get("organCode", ""))).upper() or None
                )
                icb_code = str(row.get("icbCode", row.get("icb_code", ""))) or None
                icb_name = str(row.get("icbName", row.get("icb_name", ""))) or None
                industry = icb_name or str(row.get("industry", "")) or None
                raw_type = str(row.get("type", row.get("asset_type", "stock")))

                asset_type, lot_size, exchange = self._classify_symbol(
                    symbol_str, raw_type=raw_type, exchange=raw_exchange
                )

                records.append(
                    {
                        "id": uuid.uuid4(),
                        "symbol": symbol_str,
                        "organ_name": organ_name,
                        "exchange": exchange,
                        "industry": industry,
                        "icb_code": icb_code,
                        "icb_name": icb_name,
                        "asset_type": asset_type,
                        "lot_size": lot_size,
                        "is_active": True,
                        "updated_at": now_utc,
                    }
                )

            self._bulk_upsert(
                StockSymbol,
                records,
                ["symbol"],
                STOCK_SYMBOL_UPDATE_FIELDS,
            )
            self.session.commit()
            count = len(records)

            del records
            gc.collect()

            # Sync VN30 group, Derivatives, Covered Warrants & Bonds
            self._sync_vn30_group()
            deriv_count = self._sync_derivatives()
            cw_count = self._sync_covered_warrants()
            bond_count = self._sync_bonds()
            count += deriv_count + cw_count + bond_count

            logger.info(
                "Synced %d symbols (including %d derivatives, %d warrants, %d bonds)",
                count,
                deriv_count,
                cw_count,
                bond_count,
            )
            return count

        return self._run_sync_task("symbols", _task)

    def backfill_daily(
        self,
        symbol: str,
        start: date,
        end: date | None = None,
    ) -> DataSyncLog:
        """Backfill historical daily OHLCV data for a symbol.

        Smart fill: checks existing data in DB and only fetches missing ranges.
        """
        target_end = end or date.today()

        def _task() -> int:
            existing = self.session.exec(
                select(col(StockOHLCVDaily.trading_date))
                .where(StockOHLCVDaily.symbol == symbol)
                .where(StockOHLCVDaily.trading_date >= start)
                .where(StockOHLCVDaily.trading_date <= target_end)
                .order_by(col(StockOHLCVDaily.trading_date))
            ).all()
            existing_dates = set(existing)

            df = self.svc.fetch_price_history(symbol, start, target_end, interval="1D")
            if df is None or df.empty:
                return 0

            self._ensure_symbol_exists(symbol)

            count = 0
            for _, row in df.iterrows():
                trading_date = self._parse_date(row.get("time", row.get("date", "")))
                if trading_date is None or trading_date in existing_dates:
                    continue

                ohlcv = StockOHLCVDaily(
                    symbol=symbol,
                    trading_date=trading_date,
                    open=float(row.get("open", 0)),
                    high=float(row.get("high", 0)),
                    low=float(row.get("low", 0)),
                    close=float(row.get("close", 0)),
                    volume=int(row.get("volume", 0)),
                    value=float(row["value"])
                    if "value" in row and pd.notna(row["value"])
                    else None,
                    source=self.svc.source,
                )
                self.session.add(ohlcv)
                count += 1

            self.session.commit()
            logger.info("Backfilled %d daily bars for %s", count, symbol)
            return count

        return self._run_sync_task("daily_ohlcv", _task, symbol=symbol)

    def sync_daily_incremental(
        self, symbols: list[str] | None = None
    ) -> list[DataSyncLog]:
        """Update daily OHLCV for all active symbols (or a specified list).

        Fetches only data after the last date in DB for each symbol.
        """
        if symbols is None:
            active = self.session.exec(
                select(StockSymbol.symbol).where(StockSymbol.is_active == True)  # noqa: E712
            ).all()
            symbols = list(active)

        logs: list[DataSyncLog] = []
        today = date.today()

        for symbol in symbols:
            last_date_result = self.session.exec(
                select(col(StockOHLCVDaily.trading_date))
                .where(StockOHLCVDaily.symbol == symbol)
                .order_by(col(StockOHLCVDaily.trading_date).desc())
                .limit(1)
            ).first()

            if last_date_result is None:
                from datetime import timedelta

                start = today - timedelta(days=30)
            else:
                from datetime import timedelta

                start = last_date_result + timedelta(days=1)

            if start > today:
                continue

            log = self.backfill_daily(symbol, start, today)
            logs.append(log)

        return logs

    def collect_intraday(
        self,
        symbol: str,
        interval: str = "1m",
        count_back: int = 300,
    ) -> DataSyncLog:
        """Collect intraday bars for a symbol."""

        def _task() -> int:
            df = self.svc.fetch_intraday(
                symbol, interval=interval, count_back=count_back
            )
            if df is None or df.empty:
                return 0

            self._ensure_symbol_exists(symbol)

            count = 0
            for _, row in df.iterrows():
                ts = self._parse_datetime(row.get("time", row.get("date", "")))
                if ts is None:
                    continue

                existing = self.session.exec(
                    select(StockOHLCVIntraday)
                    .where(StockOHLCVIntraday.symbol == symbol)
                    .where(StockOHLCVIntraday.timestamp == ts)
                    .where(StockOHLCVIntraday.interval == interval)
                ).first()

                if existing:
                    existing.open = float(row.get("open", 0))
                    existing.high = float(row.get("high", 0))
                    existing.low = float(row.get("low", 0))
                    existing.close = float(row.get("close", 0))
                    existing.volume = int(row.get("volume", 0))
                    self.session.add(existing)
                else:
                    bar = StockOHLCVIntraday(
                        symbol=symbol,
                        timestamp=ts,
                        interval=interval,
                        open=float(row.get("open", 0)),
                        high=float(row.get("high", 0)),
                        low=float(row.get("low", 0)),
                        close=float(row.get("close", 0)),
                        volume=int(row.get("volume", 0)),
                        source=self.svc.source,
                    )
                    self.session.add(bar)
                count += 1

            self.session.commit()
            logger.info(
                "Collected %d intraday bars for %s (%s)", count, symbol, interval
            )
            return count

        return self._run_sync_task("intraday", _task, symbol=symbol)

    def sync_company_profile(self, symbol: str) -> DataSyncLog:
        """Sync company profile/overview data."""

        def _task() -> int:
            data = self.svc.fetch_company_overview(symbol)
            if not data:
                raise VnstockServiceError("Empty response")

            self._ensure_symbol_exists(symbol)

            profile_data = {
                "company_name": str(
                    data.get("companyName", data.get("company_name", ""))
                ),
                "short_name": str(data.get("shortName", data.get("short_name", ""))),
                "industry_name": str(
                    data.get("industryName", data.get("industry_name", ""))
                ),
                "established_date": str(
                    data.get("establishedYear", data.get("established_date", ""))
                ),
                "listed_date": str(
                    data.get("listingDate", data.get("listed_date", ""))
                ),
                "charter_capital": data.get(
                    "charterCapital", data.get("charter_capital")
                ),
                "outstanding_shares": data.get(
                    "outstandingShare", data.get("outstanding_shares")
                ),
                "market_cap": data.get("marketCap", data.get("market_cap")),
                "website": str(data.get("website", "")),
                "description": str(
                    data.get("companyProfile", data.get("description", ""))
                ),
            }

            existing = self.session.get(CompanyProfile, symbol)
            if existing:
                for k, v in profile_data.items():
                    if v:
                        setattr(existing, k, v)
                existing.updated_at = datetime.now(UTC)
                self.session.add(existing)
            else:
                self.session.add(CompanyProfile(symbol=symbol, **profile_data))

            self.session.commit()
            return 1

        return self._run_sync_task("profile", _task, symbol=symbol)

    def sync_financials(
        self,
        symbol: str,
        report_type: str = "income_statement",
        period: str = "quarterly",
    ) -> DataSyncLog:
        """Sync financial reports for a symbol."""

        def _task() -> int:
            df = self.svc.fetch_financials(
                symbol, report_type=report_type, period=period
            )
            if df is None or df.empty:
                return 0

            self._ensure_symbol_exists(symbol)

            count = 0
            for _, row in df.iterrows():
                year = int(row.get("year", row.get("yearReport", 0)))
                quarter = row.get("quarter", row.get("lengthReport"))
                quarter_int = (
                    int(quarter) if quarter is not None and pd.notna(quarter) else None
                )

                existing = self.session.exec(
                    select(FinancialReport)
                    .where(FinancialReport.symbol == symbol)
                    .where(FinancialReport.report_type == report_type)
                    .where(FinancialReport.period == period)
                    .where(FinancialReport.year == year)
                    .where(FinancialReport.quarter == quarter_int)
                ).first()

                row_data = {
                    k: v
                    for k, v in row.to_dict().items()
                    if k not in META_FINANCIAL_KEYS
                }

                if existing:
                    existing.data = row_data
                    existing.updated_at = datetime.now(UTC)
                    self.session.add(existing)
                else:
                    report = FinancialReport(
                        symbol=symbol,
                        report_type=report_type,
                        period=period,
                        year=year,
                        quarter=quarter_int,
                        data=row_data,
                        source=self.svc.source,
                    )
                    self.session.add(report)
                count += 1

            self.session.commit()
            logger.info("Synced %d financial records for %s", count, symbol)
            return count

        return self._run_sync_task("financials", _task, symbol=symbol)
