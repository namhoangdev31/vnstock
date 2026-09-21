"""DataSyncManager — orchestrates data synchronization from vnstock → PostgreSQL.

3 sync modes:
1. Historical Backfill  — one-time full data import
2. Incremental Daily    — daily update after market close
3. Intraday Collector   — realtime bar collection during trading session
"""

from __future__ import annotations

import gc
import logging
import time
import uuid
from collections.abc import Callable
from datetime import date, datetime
from typing import Any

import pandas as pd
from sqlalchemy import and_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlmodel import Session, col, select

from app.models import VN_TZ
from app.models.models_stock import (
    BondSpecification,
    CompanyOfficer,
    CompanyProfile,
    CompanyShareholder,
    CorporateEvent,
    CoveredWarrant,
    DataSyncLog,
    DerivativeContract,
    FinancialRatio,
    FinancialReport,
    IndexConstituent,
    StockOHLCVDaily,
    StockOHLCVIntraday,
    StockSymbol,
)
from app.services.sync_constants import (
    BOND_SPECIFICATION_UPDATE_FIELDS,
    BOND_TYPE_CONFIG,
    COMPANY_OFFICER_UPDATE_FIELDS,
    COMPANY_PROFILE_UPDATE_FIELDS,
    COMPANY_SHAREHOLDER_UPDATE_FIELDS,
    CORPORATE_EVENT_UPDATE_FIELDS,
    COVERED_WARRANT_UPDATE_FIELDS,
    CW_STOCK_SYMBOL_UPDATE_FIELDS,
    DAILY_OHLCV_UPDATE_FIELDS,
    DERIV_STOCK_SYMBOL_UPDATE_FIELDS,
    DERIVATIVE_CONTRACT_UPDATE_FIELDS,
    FINANCIAL_RATIO_UPDATE_FIELDS,
    FINANCIAL_REPORT_UPDATE_FIELDS,
    INDEX_CONSTITUENT_UPDATE_FIELDS,
    INTRADAY_OHLCV_UPDATE_FIELDS,
    META_FINANCIAL_KEYS,
    STANDARD_INDEXES,
    STOCK_SYMBOL_UPDATE_FIELDS,
    get_third_thursday,
)
from app.services.vnstock_service import VnstockService, VnstockServiceError

logger = logging.getLogger(__name__)


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
        log.completed_at = datetime.now(VN_TZ)
        self.session.add(log)
        self.session.commit()
        return log

    def _run_sync_task(
        self,
        sync_type: str,
        task_func: Callable[[], int],
        symbol: str | None = None,
    ) -> DataSyncLog:
        """Quản lý vòng đời tác vụ đồng bộ: khởi tạo log -> thực thi -> bắt lỗi & rollback -> cập nhật log."""
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

    @staticmethod
    def _deduplicate_records(
        records: list[dict[str, Any]],
        conflict_keys: list[str],
    ) -> list[dict[str, Any]]:
        """Khử trùng lặp bản ghi theo conflict_keys, giữ bản ghi xuất hiện sau cùng."""
        if not records or not conflict_keys:
            return records
        dedup_map: dict[tuple[Any, ...], dict[str, Any]] = {}
        for rec in records:
            key = tuple(rec.get(k) for k in conflict_keys)
            dedup_map[key] = rec
        return list(dedup_map.values())

    @staticmethod
    def _standardize_record_keys(
        records: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Đồng nhất tập khóa (keys) cho toàn bộ danh sách records để tránh lỗi schema mismatch."""
        if not records:
            return records
        all_keys: set[str] = set().union(*(rec.keys() for rec in records))
        return [{k: rec.get(k, None) for k in all_keys} for rec in records]

    def _upsert_postgresql(
        self,
        model_cls: type[Any],
        records: list[dict[str, Any]],
        conflict_keys: list[str],
        update_fields: list[str],
        batch_size: int = 500,
    ) -> int:
        """Thực thi Bulk UPSERT chuyên biệt cho PostgreSQL với hỗ trợ ON CONFLICT an toàn."""
        if not records:
            return 0

        insert_stmt = pg_insert(model_cls)

        # Xây dựng mệnh đề ON CONFLICT theo chuẩn dialects/postgresql/dml.py:
        # - Khi update_fields có trường: gọi on_conflict_do_update với set_=update_dict
        # - Khi update_fields rỗng: gọi on_conflict_do_nothing (tránh ValueError do set_ rỗng)
        # Sử dụng getattr để gọi an toàn, giải quyết triệt để lỗi phân tích tĩnh sai của PyCharm
        # (PyCharm không suy luận được kiểu trả về qua decorator @_generative của SQLAlchemy nên báo giả PyNoneFunctionAssignment)
        if update_fields:
            excluded = insert_stmt.excluded
            update_dict = {f: getattr(excluded, f) for f in update_fields}
            do_update_fn: Any = insert_stmt.on_conflict_do_update
            upsert_stmt: Any = do_update_fn(
                index_elements=conflict_keys,
                set_=update_dict,
            )
        else:
            do_nothing_fn: Any = insert_stmt.on_conflict_do_nothing
            upsert_stmt: Any = do_nothing_fn(
                index_elements=conflict_keys,
            )

        num_cols = len(records[0]) if records else 1
        # Giới hạn an toàn tham số PostgreSQL (tối đa 32,767 tham số trên mỗi câu lệnh)
        safe_batch_size = max(1, 32767 // max(num_cols, 1))
        step = min(batch_size, safe_batch_size)

        for i in range(0, len(records), step):
            batch = records[i : i + step]
            stmt = upsert_stmt.values(batch)
            self.session.execute(stmt)

        self.session.flush()
        return len(records)

    def _upsert_sqlite(
        self,
        model_cls: type[Any],
        records: list[dict[str, Any]],
        conflict_keys: list[str],
        update_fields: list[str],
    ) -> int:
        """Thực thi Bulk UPSERT fallback cho SQLite ORM session."""
        for rec in records:
            conditions = [
                getattr(model_cls, k) == rec[k] for k in conflict_keys if k in rec
            ]
            existing = (
                self.session.exec(select(model_cls).where(and_(*conditions))).first()
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

    def _bulk_upsert(
        self,
        model_cls: type[Any],
        records: list[dict[str, Any]],
        conflict_keys: list[str],
        update_fields: list[str],
        batch_size: int = 500,
    ) -> int:
        """Thực hiện bulk upsert dữ liệu vào DB theo batch, tương thích PostgreSQL & SQLite.

        Quy trình xử lý an toàn:
        1. Khử trùng lặp nội bộ theo conflict_keys (ngăn chặn lỗi PostgreSQL CardinalityViolation).
        2. Đồng nhất tập keys giữa các bản ghi để câu lệnh multi-row VALUES luôn chuẩn xác.
        3. Phân nhánh thực thi: PostgreSQL tối ưu qua ON CONFLICT hoặc SQLite fallback.
        4. Bảo toàn khóa chính `id` (UUID), không ghi đè UUID cũ khi cập nhật.
        """
        if not records:
            return 0

        # 1. Khử trùng lặp nội bộ
        deduped = self._deduplicate_records(records, conflict_keys)
        # 2. Đồng nhất keys cho batch
        standardized = self._standardize_record_keys(deduped)

        # 3. Thực thi theo dialect
        if self.is_postgresql:
            return self._upsert_postgresql(
                model_cls,
                standardized,
                conflict_keys,
                update_fields,
                batch_size=batch_size,
            )
        return self._upsert_sqlite(
            model_cls, standardized, conflict_keys, update_fields
        )

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
                now_utc = datetime.now(VN_TZ)
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
    # Safe Extraction Helpers (Loại bỏ triệt để code smell row.get nested)
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_val(row: Any, *keys: str, default: Any = None) -> Any:
        """Trích xuất giá trị đầu tiên tồn tại và không rỗng từ danh sách keys trong row."""
        match row:
            case dict():
                getter = row.get
            case _:
                getter = getattr(row, "get", lambda k, d=None: getattr(row, k, d))

        for k in keys:
            v = getter(k, None)
            if v is not None and pd.notna(v):
                if isinstance(v, str) and not v.strip():
                    continue
                return v
        return default

    @classmethod
    def _extract_str(
        cls, row: Any, *keys: str, default: str | None = None
    ) -> str | None:
        """Trích xuất giá trị dạng chuỗi an toàn."""
        val = cls._extract_val(row, *keys)
        return str(val).strip() if val is not None else default

    @classmethod
    def _extract_float(
        cls, row: Any, *keys: str, default: float | None = None
    ) -> float | None:
        """Trích xuất giá trị số thực an toàn."""
        val = cls._extract_val(row, *keys)
        parsed = cls._parse_float(val)
        return parsed if parsed is not None else default

    @classmethod
    def _extract_int(cls, row: Any, *keys: str, default: int | None = 0) -> int | None:
        """Trích xuất giá trị số nguyên an toàn."""
        val = cls._extract_val(row, *keys)
        match val:
            case None:
                return default
            case int():
                return val
            case float():
                return int(val)
            case str() if val.strip().isdigit():
                return int(val.strip())
            case _:
                try:
                    return int(float(val))
                except (ValueError, TypeError):
                    return default

    @classmethod
    def _extract_date(cls, row: Any, *keys: str) -> date | None:
        """Trích xuất ngày (date) an toàn."""
        val = cls._extract_val(row, *keys)
        return cls._parse_date(val)

    @classmethod
    def _extract_datetime(cls, row: Any, *keys: str) -> datetime | None:
        """Trích xuất ngày giờ (datetime) an toàn."""
        val = cls._extract_val(row, *keys)
        return cls._parse_datetime(val)

    # ------------------------------------------------------------------
    # Data Normalization & Parsing Primitives
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
                    .values(index_group="VN30", updated_at=datetime.now(VN_TZ))
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
        """Đồng bộ các hợp đồng phái sinh chuẩn vào StockSymbol và DerivativeContract bằng Bulk UPSERT."""
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

        contract_defs: list[tuple[str, date, str]] = [
            ("VN30F1M", m1_exp, "Hợp đồng tương lai VN30 tháng hiện tại"),
            ("VN30F2M", m2_exp, "Hợp đồng tương lai VN30 tháng kế tiếp"),
        ]
        seen_codes: set[str] = {c[0] for c in contract_defs}

        try:
            deriv_raw = self.svc.fetch_derivatives_list()
            deriv_df = self._normalize_to_dataframe(deriv_raw, symbol_col="ticker")
            if not deriv_df.empty:
                col_name = self._resolve_symbol_column(deriv_df)
                if col_name:
                    for _, row in deriv_df.iterrows():
                        code = self._extract_str(row, col_name)
                        if not code or code in seen_codes:
                            continue
                        exp = self._extract_derivative_expiry(code, fallback=m1_exp)
                        contract_defs.append((code, exp, f"Hợp đồng tương lai {code}"))
                        seen_codes.add(code)
        except Exception as exc:
            logger.warning("Could not fetch extra derivatives list: %s", exc)

        now_utc = datetime.now(VN_TZ)
        sym_records = [
            {
                "id": uuid.uuid4(),
                "symbol": code,
                "organ_name": desc,
                "exchange": "DERIV",
                "industry": "Derivatives",
                "asset_type": "derivative",
                "lot_size": 1,
                "is_active": True,
                "updated_at": now_utc,
            }
            for code, _, desc in contract_defs
        ]

        deriv_records = [
            {
                "id": uuid.uuid4(),
                "symbol": code,
                "underlying_symbol": "VN30",
                "multiplier": 100_000.0,
                "expiration_date": exp_date,
                "is_active": True,
                "updated_at": now_utc,
            }
            for code, exp_date, _ in contract_defs
        ]

        self._bulk_upsert(
            StockSymbol,
            sym_records,
            ["symbol"],
            DERIV_STOCK_SYMBOL_UPDATE_FIELDS,
        )
        self._bulk_upsert(
            DerivativeContract,
            deriv_records,
            ["symbol"],
            DERIVATIVE_CONTRACT_UPDATE_FIELDS,
        )
        self.session.commit()
        return len(contract_defs)

    def _sync_covered_warrants(self) -> int:
        """Đồng bộ danh mục chứng quyền có bảo đảm (CW) vào StockSymbol và CoveredWarrant sử dụng Bulk UPSERT."""
        cw_data = self.svc.fetch_covered_warrants_list()
        df = self._normalize_to_dataframe(cw_data)
        if df.empty:
            return 0

        col_sym = self._resolve_symbol_column(df)
        if not col_sym:
            return 0

        now_utc = datetime.now(VN_TZ)
        today_d = date.today()

        sym_records: list[dict[str, Any]] = []
        cw_records: list[dict[str, Any]] = []
        underlying_codes: set[str] = set()

        for _, row in df.iterrows():
            code = self._extract_str(row, col_sym)
            if not code or len(code) < 6:
                continue

            raw_und = self._extract_str(
                row, "underlying_symbol", "underlying", "target_symbol"
            )
            raw_wtype = self._extract_str(row, "warrant_type", "type")
            underlying, warrant_type = self._extract_warrant_meta(
                code, raw_underlying=raw_und, raw_warrant_type=raw_wtype
            )
            if not underlying:
                continue

            underlying_codes.add(underlying)
            maturity_date = self._extract_date(
                row, "maturity_date", "maturityDate", "expiration_date"
            )
            is_active = not (maturity_date and maturity_date < today_d)

            sym_records.append(
                {
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
            )

            cw_records.append(
                {
                    "id": uuid.uuid4(),
                    "symbol": code,
                    "underlying_symbol": underlying,
                    "issuer_name": self._extract_str(row, "issuer_name", "issuer"),
                    "warrant_type": warrant_type,
                    "exercise_price": self._extract_float(
                        row, "exercise_price", "exercisePrice"
                    ),
                    "conversion_ratio": self._extract_str(
                        row, "conversion_ratio", "conversionRatio"
                    ),
                    "exercise_ratio": self._extract_float(
                        row, "exercise_ratio", "exerciseRatio", "ratio"
                    ),
                    "issue_date": self._extract_date(row, "issue_date", "issueDate"),
                    "maturity_date": maturity_date,
                    "last_trading_date": self._extract_date(
                        row, "last_trading_date", "lastTradingDate"
                    ),
                    "settlement_type": self._extract_str(
                        row, "settlement_type", "settlementType", default="cash"
                    ),
                    "is_active": is_active,
                    "updated_at": now_utc,
                }
            )

        if not cw_records:
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
            sym_records,
            ["symbol"],
            CW_STOCK_SYMBOL_UPDATE_FIELDS,
        )
        self._bulk_upsert(
            CoveredWarrant,
            cw_records,
            ["symbol"],
            COVERED_WARRANT_UPDATE_FIELDS,
        )

        self.session.commit()
        return len(cw_records)

    def _sync_bonds(self) -> int:
        """Đồng bộ danh mục trái phiếu doanh nghiệp & chính phủ vào StockSymbol và BondSpecification sử dụng Bulk UPSERT."""
        raw_bonds = self.svc.fetch_bonds_list(bond_type="all")
        df = self._normalize_to_dataframe(raw_bonds)
        if df.empty:
            return 0

        col_sym = self._resolve_symbol_column(df)
        if not col_sym:
            return 0

        now_utc = datetime.now(VN_TZ)
        today_d = date.today()

        # Bóc tách danh sách mã tổ chức phát hành tiềm năng
        candidate_issuers: set[str] = set()
        for _, row in df.iterrows():
            code = self._extract_str(row, col_sym)
            if not code:
                continue

            raw_b_type = self._extract_str(
                row, "type", "bond_type", default="corporate"
            ).lower()
            b_type = "government" if raw_b_type == "government" else "corporate"
            if b_type == "corporate":
                cand = self._extract_str(
                    row,
                    "issuer_symbol",
                    "issuerSymbol",
                    "company_code",
                    default=code[:3],
                )
                if cand:
                    candidate_issuers.add(cand)

        existing_issuers = self._find_or_create_symbols(
            candidate_issuers, auto_create=False
        )

        sym_records: list[dict[str, Any]] = []
        bond_records: list[dict[str, Any]] = []

        for _, row in df.iterrows():
            code = self._extract_str(row, col_sym)
            if not code:
                continue

            raw_b_type = self._extract_str(
                row, "type", "bond_type", default="corporate"
            ).lower()
            b_type = "government" if raw_b_type == "government" else "corporate"

            issuer_symbol = None
            if b_type == "corporate":
                cand = self._extract_str(
                    row,
                    "issuer_symbol",
                    "issuerSymbol",
                    "company_code",
                    default=code[:3],
                )
                if cand in existing_issuers:
                    issuer_symbol = cand

            maturity_date = self._extract_date(
                row, "maturity_date", "maturityDate", "expiration_date"
            )
            is_active = not (maturity_date and maturity_date < today_d)

            label_prefix, asset_label = BOND_TYPE_CONFIG.get(
                b_type, ("Trái phiếu", "corporate_bond")
            )

            sym_records.append(
                {
                    "id": uuid.uuid4(),
                    "symbol": code,
                    "organ_name": f"{label_prefix} {code}",
                    "exchange": "HNX",
                    "industry": "Bonds",
                    "asset_type": asset_label,
                    "lot_size": 1,
                    "is_active": is_active,
                    "updated_at": now_utc,
                }
            )

            bond_records.append(
                {
                    "id": uuid.uuid4(),
                    "symbol": code,
                    "bond_type": b_type,
                    "issuer_symbol": issuer_symbol,
                    "issuer_name": self._extract_str(row, "issuer_name", "issuer"),
                    "par_value": self._extract_float(
                        row, "par_value", "parValue", default=100_000.0
                    ),
                    "coupon_rate": self._extract_float(
                        row, "coupon_rate", "couponRate", "coupon"
                    ),
                    "coupon_type": self._extract_str(
                        row, "coupon_type", "couponType", default="fixed"
                    ),
                    "tenor_years": self._extract_float(
                        row, "tenor_years", "tenorYears", "term"
                    ),
                    "issue_date": self._extract_date(row, "issue_date", "issueDate"),
                    "maturity_date": maturity_date,
                    "is_active": is_active,
                    "updated_at": now_utc,
                }
            )

        if not bond_records:
            return 0

        self._bulk_upsert(
            StockSymbol,
            sym_records,
            ["symbol"],
            CW_STOCK_SYMBOL_UPDATE_FIELDS,
        )
        self._bulk_upsert(
            BondSpecification,
            bond_records,
            ["symbol"],
            BOND_SPECIFICATION_UPDATE_FIELDS,
        )

        self.session.commit()
        return len(bond_records)

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

            now_utc = datetime.now(VN_TZ)
            records: list[dict[str, Any]] = []
            for _, row in df.iterrows():
                symbol_str = self._extract_str(row, "ticker", "symbol")
                if not symbol_str:
                    continue

                symbol_str = symbol_str.upper()
                organ_name = self._extract_str(row, "organName", "organ_name")
                raw_exchange = (
                    self._extract_str(row, "exchange", "organCode", default="").upper()
                    or None
                )
                icb_code = self._extract_str(row, "icbCode", "icb_code")
                icb_name = self._extract_str(row, "icbName", "icb_name")
                industry = icb_name or self._extract_str(row, "industry")
                raw_type = self._extract_str(row, "type", "asset_type", default="stock")

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

        Sử dụng Bulk UPSERT giúp tự động cập nhật và chèn mới nhanh chóng, không bị trùng lặp.
        """
        target_end = end or date.today()

        def _task() -> int:
            df = self.svc.fetch_price_history(symbol, start, target_end, interval="1D")
            if df is None or df.empty:
                return 0

            self._ensure_symbol_exists(symbol)

            records: list[dict[str, Any]] = []
            for _, row in df.iterrows():
                trading_date = self._extract_date(row, "time", "date")
                if trading_date is None:
                    continue

                records.append(
                    {
                        "id": uuid.uuid4(),
                        "symbol": symbol,
                        "trading_date": trading_date,
                        "open": self._extract_float(row, "open", default=0.0),
                        "high": self._extract_float(row, "high", default=0.0),
                        "low": self._extract_float(row, "low", default=0.0),
                        "close": self._extract_float(row, "close", default=0.0),
                        "volume": self._extract_int(row, "volume", default=0),
                        "value": self._extract_float(row, "value"),
                        "source": self.svc.source,
                    }
                )

            count = self._bulk_upsert(
                StockOHLCVDaily,
                records,
                ["symbol", "trading_date"],
                DAILY_OHLCV_UPDATE_FIELDS,
            )
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
        """Collect intraday bars for a symbol bằng Bulk UPSERT, loại bỏ hoàn toàn N+1 queries."""

        def _task() -> int:
            df = self.svc.fetch_intraday(
                symbol, interval=interval, count_back=count_back
            )
            if df is None or df.empty:
                return 0

            self._ensure_symbol_exists(symbol)

            records: list[dict[str, Any]] = []
            for _, row in df.iterrows():
                ts = self._extract_datetime(row, "time", "date")
                if ts is None:
                    continue

                records.append(
                    {
                        "id": uuid.uuid4(),
                        "symbol": symbol,
                        "timestamp": ts,
                        "interval": interval,
                        "open": self._extract_float(row, "open", default=0.0),
                        "high": self._extract_float(row, "high", default=0.0),
                        "low": self._extract_float(row, "low", default=0.0),
                        "close": self._extract_float(row, "close", default=0.0),
                        "volume": self._extract_int(row, "volume", default=0),
                        "source": self.svc.source,
                    }
                )

            count = self._bulk_upsert(
                StockOHLCVIntraday,
                records,
                ["symbol", "timestamp", "interval"],
                INTRADAY_OHLCV_UPDATE_FIELDS,
            )
            self.session.commit()
            logger.info(
                "Collected %d intraday bars for %s (%s)", count, symbol, interval
            )
            return count

        return self._run_sync_task("intraday", _task, symbol=symbol)

    def sync_company_profile(self, symbol: str) -> DataSyncLog:
        """Sync company profile/overview data bằng Bulk UPSERT."""

        def _task() -> int:
            data = self.svc.fetch_company_overview(symbol)
            if not data:
                raise VnstockServiceError("Empty response")

            self._ensure_symbol_exists(symbol)

            profile_record = {
                "id": uuid.uuid4(),
                "symbol": symbol,
                "company_name": self._extract_str(data, "companyName", "company_name"),
                "short_name": self._extract_str(data, "shortName", "short_name"),
                "industry_name": self._extract_str(
                    data, "industryName", "industry_name"
                ),
                "established_date": self._extract_str(
                    data, "establishedYear", "established_date"
                ),
                "listed_date": self._extract_str(data, "listingDate", "listed_date"),
                "charter_capital": self._extract_float(
                    data, "charterCapital", "charter_capital"
                ),
                "outstanding_shares": self._extract_float(
                    data, "outstandingShare", "outstanding_shares"
                ),
                "market_cap": self._extract_float(data, "marketCap", "market_cap"),
                "website": self._extract_str(data, "website", default=""),
                "description": self._extract_str(
                    data, "companyProfile", "description", default=""
                ),
                "updated_at": datetime.now(VN_TZ),
            }

            self._bulk_upsert(
                CompanyProfile,
                [profile_record],
                ["symbol"],
                COMPANY_PROFILE_UPDATE_FIELDS,
            )
            self.session.commit()
            return 1

        return self._run_sync_task("profile", _task, symbol=symbol)

    def sync_financials(
        self,
        symbol: str,
        report_type: str = "income_statement",
        period: str = "quarterly",
    ) -> DataSyncLog:
        """Sync financial reports for a symbol bằng Bulk UPSERT, loại bỏ hoàn toàn N+1 queries."""

        def _task() -> int:
            df = self.svc.fetch_financials(
                symbol, report_type=report_type, period=period
            )
            if df is None or df.empty:
                return 0

            self._ensure_symbol_exists(symbol)

            now_utc = datetime.now(VN_TZ)
            records: list[dict[str, Any]] = []
            for _, row in df.iterrows():
                year = self._extract_int(row, "year", "yearReport", default=0)
                quarter = self._extract_int(
                    row, "quarter", "lengthReport", default=None
                )
                row_dict = row.to_dict() if hasattr(row, "to_dict") else dict(row)
                row_data = {
                    k: v for k, v in row_dict.items() if k not in META_FINANCIAL_KEYS
                }

                records.append(
                    {
                        "id": uuid.uuid4(),
                        "symbol": symbol,
                        "report_type": report_type,
                        "period": period,
                        "year": year,
                        "quarter": quarter,
                        "data": row_data,
                        "source": self.svc.source,
                        "updated_at": now_utc,
                    }
                )

            count = self._bulk_upsert(
                FinancialReport,
                records,
                ["symbol", "report_type", "period", "year", "quarter"],
                FINANCIAL_REPORT_UPDATE_FIELDS,
            )
            self.session.commit()
            logger.info("Synced %d financial records for %s", count, symbol)
            return count

        return self._run_sync_task("financials", _task, symbol=symbol)

    def sync_financial_ratios(
        self,
        symbol: str,
        period: str = "quarter",
    ) -> DataSyncLog:
        """Đồng bộ bộ chỉ số tài chính định lượng & định giá (P/E, P/B, ROE, ROA, EPS...) bằng Bulk UPSERT."""

        def _task() -> int:
            df = self.svc.fetch_financial_ratios(symbol)
            if df is None or df.empty:
                return 0

            self._ensure_symbol_exists(symbol)
            now_utc = datetime.now(VN_TZ)
            records: list[dict[str, Any]] = []

            # Phân loại 2 dạng cấu trúc trả về từ vnstock:
            # Dạng 1: Dạng ma trận ngang (columns chứa các kỳ YYYY-Qx hoặc YYYY, rows là các chỉ số)
            # Dạng 2: Dạng bảng dọc (mỗi row là một kỳ báo cáo)
            period_cols = [
                c
                for c in df.columns
                if any(char.isdigit() for char in str(c))
                and ("-" in str(c) or len(str(c)) == 4)
            ]

            if period_cols and ("item" in df.columns or "item_id" in df.columns):
                # Xử lý dạng 1: Ma trận xoay chiều (pivot)
                # Map các chỉ số chuẩn hóa
                metric_row_map: dict[str, dict[str, Any]] = {}
                for col_name in period_cols:
                    col_str = str(col_name).strip()
                    # Parse year và quarter từ tên cột (ví dụ '2024-Q3', '2024_Q2', '2024')
                    parts = col_str.replace("_", "-").split("-")
                    year = int(parts[0]) if parts[0].isdigit() else 0
                    quarter = None
                    if len(parts) > 1 and "Q" in parts[1].upper():
                        q_str = parts[1].upper().replace("Q", "")
                        quarter = int(q_str) if q_str.isdigit() else None

                    metric_row_map[col_str] = {
                        "id": uuid.uuid4(),
                        "symbol": symbol,
                        "period": period,
                        "year": year,
                        "quarter": quarter,
                        "source": self.svc.source,
                        "updated_at": now_utc,
                    }

                for _, row in df.iterrows():
                    item_name = str(row.get("item", "")).lower()
                    item_id = str(row.get("item_id", "")).lower()
                    target_field: str | None = None

                    if "p/e" in item_name or "p/e" in item_id or "pe" == item_id:
                        target_field = "pe"
                    elif "p/b" in item_name or "p/b" in item_id or "pb" == item_id:
                        target_field = "pb"
                    elif "p/s" in item_name or "ps" == item_id:
                        target_field = "ps"
                    elif "roe" in item_name or "roe" in item_id:
                        target_field = "roe"
                    elif "roa" in item_name or "roa" in item_id:
                        target_field = "roa"
                    elif "roic" in item_name or "roic" in item_id:
                        target_field = "roic"
                    elif (
                        "eps" in item_name
                        or "eps" in item_id
                        or "thu nhập trên mỗi cổ phần" in item_name
                    ):
                        target_field = "eps"
                    elif (
                        "bvps" in item_name
                        or "bvps" in item_id
                        or "giá trị sổ sách" in item_name
                    ):
                        target_field = "bvps"
                    elif "biên lợi nhuận gộp" in item_name or "gross_margin" in item_id:
                        target_field = "gross_margin"
                    elif "biên lợi nhuận ròng" in item_name or "net_margin" in item_id:
                        target_field = "net_margin"
                    elif (
                        "nợ/vốn" in item_name
                        or "debt_to_equity" in item_id
                        or "d/e" in item_name
                    ):
                        target_field = "debt_to_equity"
                    elif "thanh toán nhanh" in item_name or "quick_ratio" in item_id:
                        target_field = "quick_ratio"
                    elif (
                        "thanh toán hiện hành" in item_name
                        or "current_ratio" in item_id
                    ):
                        target_field = "current_ratio"
                    elif "cổ tức" in item_name or "dividend_yield" in item_id:
                        target_field = "dividend_yield"

                    if target_field:
                        for col_name in period_cols:
                            raw_val = row.get(col_name)
                            try:
                                val = float(raw_val) if pd.notna(raw_val) else None
                            except (ValueError, TypeError):
                                val = None
                            metric_row_map[str(col_name).strip()][target_field] = val

                records = [r for r in metric_row_map.values() if r["year"] > 0]
            else:
                # Xử lý dạng 2: Bảng chuẩn từng row là 1 kỳ
                for _, row in df.iterrows():
                    year = self._extract_int(row, "year", "yearReport", default=0)
                    quarter = self._extract_int(
                        row, "quarter", "lengthReport", default=None
                    )
                    if year == 0:
                        continue
                    records.append(
                        {
                            "id": uuid.uuid4(),
                            "symbol": symbol,
                            "period": period,
                            "year": year,
                            "quarter": quarter,
                            "pe": self._extract_float(
                                row, "pe", "priceToEarning", "p/e"
                            ),
                            "pb": self._extract_float(row, "pb", "priceToBook", "p/b"),
                            "ps": self._extract_float(row, "ps", "p/s"),
                            "roe": self._extract_float(row, "roe"),
                            "roa": self._extract_float(row, "roa"),
                            "roic": self._extract_float(row, "roic"),
                            "eps": self._extract_float(row, "eps"),
                            "bvps": self._extract_float(row, "bvps"),
                            "gross_margin": self._extract_float(
                                row, "gross_margin", "grossMargin"
                            ),
                            "net_margin": self._extract_float(
                                row, "net_margin", "netMargin"
                            ),
                            "debt_to_equity": self._extract_float(
                                row, "debt_to_equity", "debtToEquity"
                            ),
                            "quick_ratio": self._extract_float(
                                row, "quick_ratio", "quickRatio"
                            ),
                            "current_ratio": self._extract_float(
                                row, "current_ratio", "currentRatio"
                            ),
                            "dividend_yield": self._extract_float(
                                row, "dividend_yield", "dividendYield"
                            ),
                            "source": self.svc.source,
                            "updated_at": now_utc,
                        }
                    )

            if not records:
                return 0

            count = self._bulk_upsert(
                FinancialRatio,
                records,
                ["symbol", "period", "year", "quarter"],
                FINANCIAL_RATIO_UPDATE_FIELDS,
            )
            self.session.commit()
            logger.info("Synced %d financial ratio records for %s", count, symbol)
            return count

        return self._run_sync_task("ratios", _task, symbol=symbol)

    def sync_company_shareholders(self, symbol: str) -> DataSyncLog:
        """Đồng bộ danh sách cổ đông lớn / cổ đông nội bộ bằng Bulk UPSERT."""

        def _task() -> int:
            df = self.svc.fetch_company_shareholders(symbol)
            if df is None or df.empty:
                return 0

            self._ensure_symbol_exists(symbol)
            now_utc = datetime.now(VN_TZ)
            records: list[dict[str, Any]] = []

            for _, row in df.iterrows():
                name = self._extract_str(
                    row, "name", "shareHolderName", "shareholder_name", default=""
                )
                if not name:
                    continue
                share_count = (
                    self._extract_float(
                        row, "shares_owned", "shareCount", "share_count", default=0.0
                    )
                    or 0.0
                )
                ownership_pct = (
                    self._extract_float(
                        row,
                        "ownership_percentage",
                        "sharePercentage",
                        "ownership_pct",
                        default=0.0,
                    )
                    or 0.0
                )

                records.append(
                    {
                        "id": uuid.uuid4(),
                        "symbol": symbol,
                        "shareholder_name": name[:255],
                        "share_count": share_count,
                        "ownership_pct": ownership_pct,
                        "is_institutional": bool(row.get("is_institutional", False)),
                        "is_foreign": bool(row.get("is_foreign", False)),
                        "is_state": bool(row.get("is_state", False)),
                        "updated_at": now_utc,
                    }
                )

            if not records:
                return 0

            count = self._bulk_upsert(
                CompanyShareholder,
                records,
                ["symbol", "shareholder_name"],
                COMPANY_SHAREHOLDER_UPDATE_FIELDS,
            )
            self.session.commit()
            logger.info("Synced %d shareholders for %s", count, symbol)
            return count

        return self._run_sync_task("shareholders", _task, symbol=symbol)

    def sync_company_officers(self, symbol: str) -> DataSyncLog:
        """Đồng bộ ban điều hành & Hội đồng quản trị doanh nghiệp bằng Bulk UPSERT."""

        def _task() -> int:
            df = self.svc.fetch_company_officers(symbol)
            if df is None or df.empty:
                return 0

            self._ensure_symbol_exists(symbol)
            now_utc = datetime.now(VN_TZ)
            records: list[dict[str, Any]] = []

            for _, row in df.iterrows():
                name = self._extract_str(
                    row, "name", "officerName", "officer_name", default=""
                )
                position = self._extract_str(
                    row,
                    "position",
                    "officerPosition",
                    "position_en",
                    default="Lãnh đạo",
                )
                if not name:
                    continue

                records.append(
                    {
                        "id": uuid.uuid4(),
                        "symbol": symbol,
                        "officer_name": name[:255],
                        "position": position[:255],
                        "share_count": self._extract_float(
                            row, "shares_owned", "shareCount", "share_count"
                        ),
                        "ownership_pct": self._extract_float(
                            row, "ownership_percentage", "sharePercentage"
                        ),
                        "updated_at": now_utc,
                    }
                )

            if not records:
                return 0

            count = self._bulk_upsert(
                CompanyOfficer,
                records,
                ["symbol", "officer_name", "position"],
                COMPANY_OFFICER_UPDATE_FIELDS,
            )
            self.session.commit()
            logger.info("Synced %d officers for %s", count, symbol)
            return count

        return self._run_sync_task("officers", _task, symbol=symbol)

    def sync_corporate_events(self, symbol: str) -> DataSyncLog:
        """Đồng bộ sự kiện doanh nghiệp & lịch chi trả cổ tức bằng Bulk UPSERT."""

        def _task() -> int:
            df = self.svc.fetch_company_events(symbol)
            if df is None or df.empty:
                return 0

            self._ensure_symbol_exists(symbol)
            now_utc = datetime.now(VN_TZ)
            records: list[dict[str, Any]] = []

            for _, row in df.iterrows():
                event_title = self._extract_str(
                    row,
                    "event_title",
                    "eventTitle",
                    "content",
                    default="Sự kiện doanh nghiệp",
                )
                event_type = self._extract_str(
                    row, "event_type", "eventType", "type", default="dividend"
                )

                # Parse ngày giao dịch không hưởng quyền (ex_date)
                raw_ex_date = row.get("ex_date") or row.get("exDate") or row.get("date")
                ex_date: date | None = None
                if raw_ex_date and pd.notna(raw_ex_date):
                    try:
                        ex_date = date.fromisoformat(str(raw_ex_date)[:10])
                    except (ValueError, TypeError):
                        ex_date = None

                records.append(
                    {
                        "id": uuid.uuid4(),
                        "symbol": symbol,
                        "event_type": event_type[:30],
                        "event_title": event_title[:500],
                        "ex_date": ex_date,
                        "cash_rate": self._extract_float(
                            row, "cash_rate", "cashRate", "value"
                        ),
                        "stock_rate": self._extract_float(
                            row, "stock_rate", "stockRate", "ratio"
                        ),
                        "ratio_string": self._extract_str(
                            row, "ratio_string", "ratioString"
                        ),
                        "notes": self._extract_str(row, "notes", "note"),
                        "details": {},
                        "source": self.svc.source,
                        "created_at": now_utc,
                    }
                )

            if not records:
                return 0

            count = self._bulk_upsert(
                CorporateEvent,
                records,
                ["symbol", "event_type", "ex_date"],
                CORPORATE_EVENT_UPDATE_FIELDS,
            )
            self.session.commit()
            logger.info("Synced %d corporate events for %s", count, symbol)
            return count

        return self._run_sync_task("events", _task, symbol=symbol)

    def sync_index_constituents(self, group: str = "VN30") -> DataSyncLog:
        """Đồng bộ danh sách thành phần và tỷ trọng rổ chỉ số (VN30, VN100, VNFINLEAD)."""

        def _task() -> int:
            symbols = self.svc.fetch_group_symbols(group=group)
            if not symbols:
                return 0

            # Đảm bảo các mã tồn tại trong bảng stock_symbol
            self._find_or_create_symbols(symbols, exchange="HOSE", asset_type="stock")

            now_utc = datetime.now(VN_TZ)
            today_date = date.today()
            records: list[dict[str, Any]] = []
            default_weight = round(100.0 / len(symbols), 4)

            for sym in symbols:
                records.append(
                    {
                        "id": uuid.uuid4(),
                        "index_code": group.upper(),
                        "symbol": sym.strip().upper(),
                        "weight": default_weight,
                        "effective_date": today_date,
                        "updated_at": now_utc,
                    }
                )

            count = self._bulk_upsert(
                IndexConstituent,
                records,
                ["index_code", "symbol", "effective_date"],
                INDEX_CONSTITUENT_UPDATE_FIELDS,
            )
            self.session.commit()
            logger.info("Synced %d constituents for index group %s", count, group)
            return count

        return self._run_sync_task("constituents", _task, symbol=group.upper())

    def sync_company_full(self, symbol: str) -> dict[str, Any]:
        """Đồng bộ toàn diện thông tin doanh nghiệp (Hồ sơ + Cổ đông + Ban lãnh đạo + Sự kiện)."""
        sym_clean = symbol.strip().upper()
        results = {
            "profile": self.sync_company_profile(sym_clean),
            "shareholders": self.sync_company_shareholders(sym_clean),
            "officers": self.sync_company_officers(sym_clean),
            "events": self.sync_corporate_events(sym_clean),
        }
        return {
            k: {"status": v.status, "rows_synced": v.rows_synced}
            for k, v in results.items()
        }

    def sync_financials_full(
        self, symbol: str, period: str = "quarter"
    ) -> dict[str, Any]:
        """Đồng bộ toàn diện BCTC (KQKD + CĐKT + LCTT) và bộ chỉ số tài chính Ratios."""
        sym_clean = symbol.strip().upper()
        results = {
            "income_statement": self.sync_financials(
                sym_clean, report_type="income_statement", period=period
            ),
            "balance_sheet": self.sync_financials(
                sym_clean, report_type="balance_sheet", period=period
            ),
            "cash_flow": self.sync_financials(
                sym_clean, report_type="cash_flow", period=period
            ),
            "ratios": self.sync_financial_ratios(sym_clean, period=period),
        }
        return {
            k: {"status": v.status, "rows_synced": v.rows_synced}
            for k, v in results.items()
        }

    def sync_batch_symbols_data(
        self,
        symbols: list[str],
        sync_types: list[str],
        delay_sec: float = 0.3,
    ) -> dict[str, Any]:
        """Đồng bộ dữ liệu hàng loạt mã cổ phiếu có kiểm soát tần suất gọi (Rule 7.2 Anti-Ban)."""
        batch_summary: dict[str, dict[str, Any]] = {}
        for sym in symbols:
            sym_clean = sym.strip().upper()
            sym_result: dict[str, Any] = {}
            for st in sync_types:
                if st == "profile":
                    sym_result["profile"] = self.sync_company_profile(sym_clean).status
                elif st == "shareholders":
                    sym_result["shareholders"] = self.sync_company_shareholders(
                        sym_clean
                    ).status
                elif st == "officers":
                    sym_result["officers"] = self.sync_company_officers(
                        sym_clean
                    ).status
                elif st == "events":
                    sym_result["events"] = self.sync_corporate_events(sym_clean).status
                elif st == "financials":
                    sym_result["financials"] = self.sync_financials(sym_clean).status
                elif st == "ratios":
                    sym_result["ratios"] = self.sync_financial_ratios(sym_clean).status
                elif st == "daily":
                    sym_result["daily"] = self.sync_daily_incremental(sym_clean).status
                time.sleep(delay_sec)

            batch_summary[sym_clean] = sym_result
            time.sleep(delay_sec)

        return batch_summary


__all__ = [
    "BOND_SPECIFICATION_UPDATE_FIELDS",
    "BOND_TYPE_CONFIG",
    "COMPANY_OFFICER_UPDATE_FIELDS",
    "COMPANY_PROFILE_UPDATE_FIELDS",
    "COMPANY_SHAREHOLDER_UPDATE_FIELDS",
    "CORPORATE_EVENT_UPDATE_FIELDS",
    "COVERED_WARRANT_UPDATE_FIELDS",
    "CW_STOCK_SYMBOL_UPDATE_FIELDS",
    "DAILY_OHLCV_UPDATE_FIELDS",
    "DERIVATIVE_CONTRACT_UPDATE_FIELDS",
    "DERIV_STOCK_SYMBOL_UPDATE_FIELDS",
    "DataSyncManager",
    "FINANCIAL_RATIO_UPDATE_FIELDS",
    "FINANCIAL_REPORT_UPDATE_FIELDS",
    "INDEX_CONSTITUENT_UPDATE_FIELDS",
    "INTRADAY_OHLCV_UPDATE_FIELDS",
    "META_FINANCIAL_KEYS",
    "STANDARD_INDEXES",
    "STOCK_SYMBOL_UPDATE_FIELDS",
    "get_third_thursday",
]
