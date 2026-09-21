"""DataSyncManager — orchestrates data synchronization from vnstock → PostgreSQL.

3 sync modes:
1. Historical Backfill  — one-time full data import
2. Incremental Daily    — daily update after market close
3. Intraday Collector   — realtime bar collection during trading session
"""

from __future__ import annotations

import gc
import logging
import math
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
from app.models.entities.asset_master import Instrument, InstrumentAlias
from app.models.models_quant import InstitutionalFlow
from app.models.models_stock import (
    BondSpecification,
    CapitalHistory,
    CompanyOfficer,
    CompanyProfile,
    CompanyShareholder,
    CompanySubsidiary,
    CorporateEvent,
    CoveredWarrant,
    DataSyncLog,
    DerivativeContract,
    FinancialRatio,
    FinancialReport,
    IndexConstituent,
    InsiderTrading,
    StockOHLCVDaily,
    StockOHLCVIntraday,
    StockSymbol,
)
from app.services.financial_revision_service import (
    acquire_financial_report_lock,
    record_financial_report_revision,
)
from app.services.screener_service import ScreenerService
from app.services.sync_constants import (
    BOND_SPECIFICATION_UPDATE_FIELDS,
    BOND_TYPE_CONFIG,
    CAPITAL_HISTORY_UPDATE_FIELDS,
    COMPANY_OFFICER_UPDATE_FIELDS,
    COMPANY_PROFILE_UPDATE_FIELDS,
    COMPANY_SHAREHOLDER_UPDATE_FIELDS,
    COMPANY_SUBSIDIARY_UPDATE_FIELDS,
    CORPORATE_EVENT_UPDATE_FIELDS,
    COVERED_WARRANT_UPDATE_FIELDS,
    CW_STOCK_SYMBOL_UPDATE_FIELDS,
    DAILY_OHLCV_UPDATE_FIELDS,
    DERIV_STOCK_SYMBOL_UPDATE_FIELDS,
    DERIVATIVE_CONTRACT_UPDATE_FIELDS,
    FINANCIAL_RATIO_UPDATE_FIELDS,
    FINANCIAL_REPORT_UPDATE_FIELDS,
    INDEX_CONSTITUENT_UPDATE_FIELDS,
    INSIDER_TRADING_UPDATE_FIELDS,
    INSTITUTIONAL_FLOW_UPDATE_FIELDS,
    INTRADAY_OHLCV_UPDATE_FIELDS,
    META_FINANCIAL_KEYS,
    STANDARD_INDEXES,
    STOCK_SYMBOL_UPDATE_FIELDS,
    get_third_thursday,
)
from app.services.vnstock_service import VnstockService, VnstockServiceError

logger = logging.getLogger(__name__)


def _extract_financial_summary_fields(
    data: dict[str, Any],
) -> dict[str, float | None]:
    """Trích xuất các chỉ tiêu tài chính cốt lõi vào các cột số học tường minh từ payload."""
    res: dict[str, float | None] = {
        "revenue": None,
        "gross_profit": None,
        "operating_profit": None,
        "net_profit_parent": None,
        "total_assets": None,
        "short_term_assets": None,
        "cash_and_equivalents": None,
        "total_liabilities": None,
        "short_term_debt": None,
        "long_term_debt": None,
        "owners_equity": None,
        "operating_cash_flow": None,
        "investing_cash_flow": None,
        "financing_cash_flow": None,
    }
    for k, v in data.items():
        if v is None:
            continue
        try:
            val = float(v)
        except (ValueError, TypeError):
            continue
        kl = str(k).lower()
        if "doanh thu thuần" in kl or "net_revenue" in kl or kl == "revenue":
            if res["revenue"] is None:
                res["revenue"] = val
        elif "lợi nhuận gộp" in kl or "gross_profit" in kl:
            if res["gross_profit"] is None:
                res["gross_profit"] = val
        elif (
            "lợi nhuận thuần từ hoạt động kinh doanh" in kl or "operating_profit" in kl
        ):
            if res["operating_profit"] is None:
                res["operating_profit"] = val
        elif (
            "lợi nhuận sau thuế của công ty mẹ" in kl
            or "cổ đông công ty mẹ" in kl
            or "net_profit_parent" in kl
            or "lnst cty mẹ" in kl
        ):
            if res["net_profit_parent"] is None:
                res["net_profit_parent"] = val
        elif ("lợi nhuận sau thuế" in kl or "net_profit" in kl) and res[
            "net_profit_parent"
        ] is None:
            res["net_profit_parent"] = val
        elif "tổng cộng tài sản" in kl or "tổng tài sản" in kl or "total_assets" in kl:
            if res["total_assets"] is None:
                res["total_assets"] = val
        elif "tài sản ngắn hạn" in kl or "short_term_assets" in kl:
            if res["short_term_assets"] is None:
                res["short_term_assets"] = val
        elif (
            "tiền và các khoản tương đương tiền" in kl
            or "tiền và tương đương tiền" in kl
            or kl == "cash"
        ):
            if res["cash_and_equivalents"] is None:
                res["cash_and_equivalents"] = val
        elif (
            "nợ phải trả" in kl or "tổng nợ phải trả" in kl or "total_liabilities" in kl
        ):
            if res["total_liabilities"] is None:
                res["total_liabilities"] = val
        elif (
            "vay và nợ thuê tài chính ngắn hạn" in kl
            or "vay ngắn hạn" in kl
            or "short_term_debt" in kl
        ):
            if res["short_term_debt"] is None:
                res["short_term_debt"] = val
        elif (
            "vay và nợ thuê tài chính dài hạn" in kl
            or "vay dài hạn" in kl
            or "long_term_debt" in kl
        ):
            if res["long_term_debt"] is None:
                res["long_term_debt"] = val
        elif "vốn chủ sở hữu" in kl or "owners_equity" in kl or kl == "equity":
            if res["owners_equity"] is None:
                res["owners_equity"] = val
        elif (
            "lưu chuyển tiền thuần từ hoạt động kinh doanh" in kl
            or "operating_cash_flow" in kl
            or "ocf" == kl
        ):
            if res["operating_cash_flow"] is None:
                res["operating_cash_flow"] = val
        elif (
            "lưu chuyển tiền thuần từ hoạt động đầu tư" in kl
            or "investing_cash_flow" in kl
        ):
            if res["investing_cash_flow"] is None:
                res["investing_cash_flow"] = val
        elif (
            "lưu chuyển tiền thuần từ hoạt động tài chính" in kl
            or "financing_cash_flow" in kl
        ):
            if res["financing_cash_flow"] is None:
                res["financing_cash_flow"] = val
    return res


def _extract_published_at(data: dict[str, Any]) -> datetime | None:
    """Trích xuất ngày công bố thực tế từ payload nếu có."""
    date_keys = [
        "publish_date",
        "published_date",
        "published_at",
        "public_date",
        "ngay_cong_bo",
        "ngay_cbtt",
        "issue_date",
        "audit_date",
        "release_date",
    ]
    for key in date_keys:
        val = data.get(key)
        if val:
            if isinstance(val, datetime):
                return (
                    val.astimezone(VN_TZ) if val.tzinfo else val.replace(tzinfo=VN_TZ)
                )
            if isinstance(val, date):
                return datetime.combine(val, datetime.min.time(), tzinfo=VN_TZ)
            if isinstance(val, str):
                s = val.strip()
                if not s:
                    continue
                try:
                    dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
                    return (
                        dt.astimezone(VN_TZ) if dt.tzinfo else dt.replace(tzinfo=VN_TZ)
                    )
                except (ValueError, TypeError):
                    try:
                        d = date.fromisoformat(s)
                        return datetime.combine(d, datetime.min.time(), tzinfo=VN_TZ)
                    except (ValueError, TypeError):
                        pass
    return None


class DataSyncManager:
    """Manage data synchronization from vnstock API → PostgreSQL."""

    def __init__(
        self,
        session: Session,
        vnstock_svc: VnstockService | None = None,
    ) -> None:
        self.session = session
        self.svc = vnstock_svc or VnstockService(db_session=session)
        if getattr(self.svc, "db_session", None) is None:
            self.svc.db_session = session

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
            self.session.exec(stmt)

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

    def _sync_asset_master(
        self,
        symbols_info: list[dict[str, Any]],
    ) -> None:
        """Đồng bộ kép (dual-write) danh mục mã vào Asset Master (Instrument & InstrumentAlias)."""
        if not symbols_info:
            return

        now_utc = datetime.now(VN_TZ)
        type_mapping = {
            "stock": "EQUITY",
            "equity": "EQUITY",
            "etf": "EQUITY",
            "derivative": "FUTURES",
            "futures": "FUTURES",
            "covered_warrant": "COVERED_WARRANT",
            "corporate_bond": "CORPORATE_BOND",
            "government_bond": "GOVERNMENT_BOND",
            "bond": "CORPORATE_BOND",
            "index": "INDEX",
        }

        # Deduplicate symbols_info by symbol
        items_by_sym: dict[str, dict[str, Any]] = {}
        for item in symbols_info:
            sym = str(item.get("symbol") or "").strip().upper()
            if sym:
                items_by_sym[sym] = item

        if not items_by_sym:
            return

        canonical_codes: list[str] = []
        for sym, item in items_by_sym.items():
            raw_type = str(item.get("asset_type") or "stock").lower()
            inst_type = type_mapping.get(raw_type, "EQUITY")
            prefix = "EQUITY" if inst_type == "EQUITY" else inst_type
            if raw_type == "derivative":
                prefix = "FUTURES"
            elif raw_type == "covered_warrant":
                prefix = "CW"
            elif "bond" in raw_type:
                prefix = "BOND"
            canonical_codes.append(f"{prefix}:{sym}")

        # Batch query existing instruments
        existing_instruments: dict[str, Instrument] = {}
        batch_size = 500
        for i in range(0, len(canonical_codes), batch_size):
            chunk = canonical_codes[i : i + batch_size]
            for inst in self.session.exec(
                select(Instrument).where(col(Instrument.canonical_code).in_(chunk))
            ).all():
                existing_instruments[inst.canonical_code] = inst

        all_instruments_by_sym: dict[str, Instrument] = {}
        for sym, item in items_by_sym.items():
            raw_type = str(item.get("asset_type") or "stock").lower()
            inst_type = type_mapping.get(raw_type, "EQUITY")
            prefix = "EQUITY" if inst_type == "EQUITY" else inst_type
            if raw_type == "derivative":
                prefix = "FUTURES"
            elif raw_type == "covered_warrant":
                prefix = "CW"
            elif "bond" in raw_type:
                prefix = "BOND"
            canonical_code = f"{prefix}:{sym}"
            ex = str(item.get("exchange") or "HOSE").upper()

            inst = existing_instruments.get(canonical_code)
            if inst is None:
                inst = Instrument(
                    id=uuid.uuid4(),
                    instrument_type=inst_type,
                    canonical_code=canonical_code,
                    exchange=ex,
                    currency="VND",
                    is_active=True,
                    created_at=now_utc,
                    updated_at=now_utc,
                )
                self.session.add(inst)
                existing_instruments[canonical_code] = inst
            else:
                inst.is_active = True
                inst.exchange = ex
                inst.updated_at = now_utc
                self.session.add(inst)

            all_instruments_by_sym[sym] = inst

        self.session.flush()

        # Batch query existing active InstrumentAlias
        symbols_list = list(items_by_sym.keys())
        existing_aliases: dict[str, InstrumentAlias] = {}
        for i in range(0, len(symbols_list), batch_size):
            chunk = symbols_list[i : i + batch_size]
            for alias in self.session.exec(
                select(InstrumentAlias).where(
                    col(InstrumentAlias.alias).in_(chunk),
                    col(InstrumentAlias.valid_to).is_(None),
                )
            ).all():
                existing_aliases[alias.alias] = alias

        for sym, inst in all_instruments_by_sym.items():
            alias = existing_aliases.get(sym)
            if alias is None:
                new_alias = InstrumentAlias(
                    id=uuid.uuid4(),
                    instrument_id=inst.id,
                    alias=sym,
                    alias_type="TICKER",
                    valid_from=date(2000, 1, 1),
                    valid_to=None,
                    created_at=now_utc,
                )
                self.session.add(new_alias)
                existing_aliases[sym] = new_alias
            elif alias.instrument_id != inst.id:
                alias.instrument_id = inst.id
                self.session.add(alias)

        self.session.flush()

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
                missing_records: list[dict[str, Any]] = []
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
                    missing_records.append(
                        {
                            "symbol": sym,
                            "exchange": exchange,
                            "asset_type": asset_type,
                        }
                    )
                self.session.flush()
                self._sync_asset_master(missing_records)
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
    def _parse_float(value: Any) -> float | None:
        """Parse various numeric formats safely to float using pattern matching."""
        match value:
            case None:
                return None
            case float() if math.isnan(value):
                return None
            case float() | int():
                return float(value)
            case str():
                try:
                    cleaned = value.strip().replace(",", "")
                    if cleaned in ("", "nan", "NaN", "None", "null", "-", "N/A"):
                        return None
                    return float(cleaned)
                except ValueError:
                    return None
            case _:
                try:
                    if pd.isna(value):
                        return None
                    return float(value)
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
                self.session.exec(stmt)
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
        self._sync_asset_master(sym_records)
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
        self._sync_asset_master(sym_records)
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

            raw_b_type = (
                self._extract_str(row, "type", "bond_type", default="corporate")
                or "corporate"
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

            raw_b_type = (
                self._extract_str(row, "type", "bond_type", default="corporate")
                or "corporate"
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
        self._sync_asset_master(sym_records)
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
                raw_exchange_str = self._extract_str(row, "exchange", "organCode")
                raw_exchange = raw_exchange_str.upper() if raw_exchange_str else None
                icb_code = self._extract_str(row, "icbCode", "icb_code")
                icb_name = self._extract_str(row, "icbName", "icb_name")
                industry = icb_name or self._extract_str(row, "industry")
                raw_type = self._extract_str(row, "type", "asset_type") or "stock"

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
            self._sync_asset_master(records)
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
                "company_name": self._extract_str(
                    data, "organ_name", "companyName", "company_name"
                ),
                "short_name": self._extract_str(
                    data, "organ_short_name", "shortName", "short_name"
                ),
                "industry_name": self._extract_str(
                    data, "sector", "industryName", "industry_name"
                ),
                "established_date": self._extract_str(
                    data, "founded_date", "establishedYear", "established_date"
                ),
                "listed_date": self._extract_str(
                    data, "listing_date", "listingDate", "listed_date"
                ),
                "charter_capital": self._extract_float(
                    data, "charter_capital", "charterCapital"
                ),
                "outstanding_shares": self._extract_float(
                    data, "issue_share", "outstanding_shares", "outstandingShare"
                ),
                "market_cap": self._extract_float(data, "market_cap", "marketCap"),
                "free_float_pct": self._extract_float(
                    data, "free_float_percentage", "free_float_pct"
                ),
                "foreign_ownership_pct": self._extract_float(
                    data, "foreigner_percentage", "foreign_ownership_pct"
                ),
                "max_foreign_ownership_pct": self._extract_float(
                    data,
                    "maximum_foreign_percentage",
                    "max_foreign_ownership_pct",
                ),
                "employee_count": self._extract_int(
                    data, "number_of_employees", "employee_count"
                ),
                "website": self._extract_str(data, "website", default=""),
                "address": self._extract_str(data, "address", default=""),
                "ceo_name": self._extract_str(data, "ceo_name", default=None),
                "auditor": self._extract_str(data, "auditor", default=None),
                "description": self._extract_str(
                    data,
                    "company_profile",
                    "companyProfile",
                    "history",
                    "business_model",
                    "description",
                    default="",
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
        period: str = "quarter",
    ) -> DataSyncLog:
        """Sync financial reports for a symbol bằng Bulk UPSERT."""

        def _task() -> int:
            clean_period = "quarter" if "quarter" in period.lower() else "year"
            df = self.svc.fetch_financials(
                symbol, report_type=report_type, period=clean_period
            )
            if df is None or df.empty:
                return 0

            self._ensure_symbol_exists(symbol)
            now_utc = datetime.now(VN_TZ)

            # Kiểm tra xem df có cột theo dạng kỳ (YYYY-Qx hoặc YYYY) hay không
            period_cols = [
                c
                for c in df.columns
                if any(char.isdigit() for char in str(c))
                and ("-" in str(c) or len(str(c).strip()) == 4)
            ]

            records: list[dict[str, Any]] = []

            if period_cols and ("item" in df.columns or "item_id" in df.columns):
                # DẠNG 1: Ma trận ngang (Cột là các kỳ YYYY-Qx, Hàng là các chỉ tiêu)
                period_records: dict[str, dict[str, Any]] = {}

                for col_name in period_cols:
                    col_str = str(col_name).strip()
                    parts = col_str.replace("_", "-").split("-")
                    year = int(parts[0]) if parts[0].isdigit() else 0
                    quarter: int | None = None
                    if len(parts) > 1 and "Q" in parts[1].upper():
                        q_str = parts[1].upper().replace("Q", "")
                        quarter = int(q_str) if q_str.isdigit() else None

                    if year > 0:
                        report_id = uuid.uuid4()
                        period_records[col_str] = {
                            "id": report_id,
                            "symbol": symbol,
                            "report_type": report_type,
                            "report_scope": "consolidated",
                            "period": clean_period,
                            "year": year,
                            "quarter": quarter,
                            "is_audited": False,
                            "data": {},
                            "source": self.svc.source,
                            "updated_at": now_utc,
                        }

                for _, row in df.iterrows():
                    item_id = str(row.get("item_id") or "").strip()
                    item_name = str(
                        row.get("item") or row.get("item_en") or item_id
                    ).strip()
                    metric_key = (
                        item_id if item_id else item_name.lower().replace(" ", "_")
                    )

                    for col_str in period_records:
                        raw_val = row.get(col_str)
                        try:
                            val = float(raw_val) if pd.notna(raw_val) else None
                        except (ValueError, TypeError):
                            val = None

                        if val is not None and metric_key:
                            period_records[col_str]["data"][metric_key] = val

                records = list(period_records.values())

            else:
                # DẠNG 2: Bảng dọc (Mỗi hàng là một kỳ báo cáo)
                for _, row in df.iterrows():
                    year = self._extract_int(row, "year", "yearReport", default=0)
                    quarter = self._extract_int(
                        row, "quarter", "lengthReport", default=None
                    )
                    if year == 0:
                        continue
                    row_dict = row.to_dict() if hasattr(row, "to_dict") else dict(row)
                    row_data = {
                        k: v
                        for k, v in row_dict.items()
                        if k not in META_FINANCIAL_KEYS
                    }

                    records.append(
                        {
                            "id": uuid.uuid4(),
                            "symbol": symbol,
                            "report_type": report_type,
                            "report_scope": "consolidated",
                            "period": clean_period,
                            "year": year,
                            "quarter": quarter,
                            "is_audited": False,
                            "data": row_data,
                            "source": self.svc.source,
                            "updated_at": now_utc,
                        }
                    )

            if not records:
                return 0

            # Phân giải canonical instrument_id nếu có
            alias_row = self.session.exec(
                select(InstrumentAlias.instrument_id)
                .where(InstrumentAlias.alias == symbol)
                .where(col(InstrumentAlias.valid_to).is_(None))
            ).first()
            inst_id = alias_row if alias_row else None

            # Điền các cột số học tường minh từ payload data
            for rec in records:
                summary_vals = _extract_financial_summary_fields(rec["data"])
                rec.update(summary_vals)
                if inst_id is not None:
                    rec["instrument_id"] = inst_id

            # Thực hiện cập nhật Master Record và ghi nhận FinancialReportRevision
            # đồng thời dưới Transaction Advisory Lock theo natural key trong cùng transaction
            count = 0
            for rec in records:
                q_val = rec.get("quarter")
                if inst_id is not None:
                    acquire_financial_report_lock(
                        self.session,
                        inst_id,
                        rec["report_type"],
                        rec["report_scope"],
                        rec["period"],
                        rec["year"],
                        q_val,
                    )

                query = (
                    select(FinancialReport)
                    .where(FinancialReport.symbol == symbol)
                    .where(FinancialReport.report_type == rec["report_type"])
                    .where(FinancialReport.report_scope == rec["report_scope"])
                    .where(FinancialReport.period == rec["period"])
                    .where(FinancialReport.year == rec["year"])
                )
                if q_val is not None:
                    query = query.where(FinancialReport.quarter == q_val)
                else:
                    query = query.where(col(FinancialReport.quarter).is_(None))

                master_report = self.session.exec(query).first()
                if master_report is None:
                    master_report = FinancialReport(
                        id=rec.get("id") or uuid.uuid4(),
                        symbol=symbol,
                        instrument_id=inst_id,
                        report_type=rec["report_type"],
                        report_scope=rec["report_scope"],
                        period=rec["period"],
                        year=rec["year"],
                        quarter=q_val,
                        is_audited=rec.get("is_audited", False),
                        data=rec["data"],
                        source=self.svc.source,
                        updated_at=now_utc,
                        revenue=rec.get("revenue"),
                        gross_profit=rec.get("gross_profit"),
                        operating_profit=rec.get("operating_profit"),
                        net_profit_parent=rec.get("net_profit_parent"),
                        total_assets=rec.get("total_assets"),
                        short_term_assets=rec.get("short_term_assets"),
                        cash_and_equivalents=rec.get("cash_and_equivalents"),
                        total_liabilities=rec.get("total_liabilities"),
                        short_term_debt=rec.get("short_term_debt"),
                        long_term_debt=rec.get("long_term_debt"),
                        owners_equity=rec.get("owners_equity"),
                        operating_cash_flow=rec.get("operating_cash_flow"),
                        investing_cash_flow=rec.get("investing_cash_flow"),
                        financing_cash_flow=rec.get("financing_cash_flow"),
                    )
                    self.session.add(master_report)
                else:
                    if inst_id is not None and master_report.instrument_id is None:
                        master_report.instrument_id = inst_id
                    master_report.data = rec["data"]
                    master_report.source = self.svc.source
                    master_report.updated_at = now_utc
                    for field in FINANCIAL_REPORT_UPDATE_FIELDS:
                        if field in rec and rec[field] is not None:
                            setattr(master_report, field, rec[field])
                    self.session.add(master_report)

                self.session.flush()

                pub_at = _extract_published_at(rec["data"])
                record_financial_report_revision(
                    session=self.session,
                    report=master_report,
                    data=rec["data"],
                    published_at=pub_at,
                    restated_reason="Sync update",
                )
                count += 1

            self.session.commit()
            logger.info(
                "Synced %d financial records and audit revisions for %s", count, symbol
            )
            return count

        return self._run_sync_task("financials", _task, symbol=symbol)

    def sync_financial_ratios(
        self,
        symbol: str,
        period: str = "quarter",
    ) -> DataSyncLog:
        """Đồng bộ bộ chỉ số tài chính định lượng & định giá bằng Bulk UPSERT vào các cột số học tường minh."""

        def _task() -> int:
            clean_period = "quarter" if "quarter" in period.lower() else "year"
            df = self.svc.fetch_financial_ratios(symbol)
            if df is None or df.empty:
                return 0

            self._ensure_symbol_exists(symbol)
            now_utc = datetime.now(VN_TZ)
            records: list[dict[str, Any]] = []

            # Phân loại 2 dạng cấu trúc trả về từ vnstock:
            period_cols = [
                c
                for c in df.columns
                if any(char.isdigit() for char in str(c))
                and ("-" in str(c) or len(str(c).strip()) == 4)
            ]

            if period_cols and ("item" in df.columns or "item_id" in df.columns):
                # Dạng 1: Ma trận xoay chiều (pivot)
                metric_row_map: dict[str, dict[str, Any]] = {}
                for col_name in period_cols:
                    col_str = str(col_name).strip()
                    parts = col_str.replace("_", "-").split("-")
                    year = int(parts[0]) if parts[0].isdigit() else 0
                    quarter = None
                    if len(parts) > 1 and "Q" in parts[1].upper():
                        q_str = parts[1].upper().replace("Q", "")
                        quarter = int(q_str) if q_str.isdigit() else None

                    metric_row_map[col_str] = {
                        "id": uuid.uuid4(),
                        "symbol": symbol,
                        "period": clean_period,
                        "year": year,
                        "quarter": quarter,
                        "pe": None,
                        "pb": None,
                        "ps": None,
                        "roe": None,
                        "roa": None,
                        "roic": None,
                        "eps": None,
                        "bvps": None,
                        "gross_margin": None,
                        "net_margin": None,
                        "debt_to_equity": None,
                        "quick_ratio": None,
                        "current_ratio": None,
                        "dividend_yield": None,
                        "ev_to_ebitda": None,
                        "ev_to_ebit": None,
                        "p_to_fcf": None,
                        "p_to_ocf": None,
                        "fcf": None,
                        "ebit_margin": None,
                        "ebitda_margin": None,
                        "asset_turnover": None,
                        "inventory_turnover": None,
                        "receivables_turnover": None,
                        "debt_to_assets": None,
                        "interest_coverage": None,
                        "cash_ratio": None,
                        "revenue_growth_yoy": None,
                        "net_profit_growth_yoy": None,
                        "revenue_growth_qoq": None,
                        "net_profit_growth_qoq": None,
                        "data": {},
                        "source": self.svc.source,
                        "updated_at": now_utc,
                    }

                for _, row in df.iterrows():
                    item_name = str(row.get("item", "")).lower()
                    item_id = str(row.get("item_id", "")).lower()
                    metric_raw_key = str(
                        row.get("item_id") or row.get("item") or ""
                    ).strip()
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
                    elif (
                        "ev/ebitda" in item_name
                        or "ev_to_ebitda" in item_id
                        or "ev_ebitda" in item_id
                    ):
                        target_field = "ev_to_ebitda"
                    elif (
                        "ev/ebit" in item_name
                        or "ev_to_ebit" in item_id
                        or "ev_ebit" in item_id
                    ):
                        target_field = "ev_to_ebit"
                    elif (
                        "p/fcf" in item_name
                        or "p_to_fcf" in item_id
                        or "giá/dòng tiền tự do" in item_name
                    ):
                        target_field = "p_to_fcf"
                    elif (
                        "p/ocf" in item_name
                        or "p_to_ocf" in item_id
                        or "giá/dòng tiền hđkd" in item_name
                    ):
                        target_field = "p_to_ocf"
                    elif (
                        "free cash flow" in item_name
                        or "fcf" == item_id
                        or "dòng tiền tự do" in item_name
                    ):
                        target_field = "fcf"
                    elif (
                        "ebit margin" in item_name
                        or "ebit_margin" in item_id
                        or "biên ebit" in item_name
                    ):
                        target_field = "ebit_margin"
                    elif (
                        "ebitda margin" in item_name
                        or "ebitda_margin" in item_id
                        or "biên ebitda" in item_name
                    ):
                        target_field = "ebitda_margin"
                    elif (
                        "vòng quay tổng tài sản" in item_name
                        or "asset_turnover" in item_id
                    ):
                        target_field = "asset_turnover"
                    elif (
                        "vòng quay hàng tồn kho" in item_name
                        or "inventory_turnover" in item_id
                    ):
                        target_field = "inventory_turnover"
                    elif (
                        "vòng quay các khoản phải thu" in item_name
                        or "receivables_turnover" in item_id
                    ):
                        target_field = "receivables_turnover"
                    elif (
                        "nợ/tổng tài sản" in item_name
                        or "debt_to_assets" in item_id
                        or "d/a" in item_name
                    ):
                        target_field = "debt_to_assets"
                    elif (
                        "khả năng trả lãi" in item_name
                        or "interest_coverage" in item_id
                    ):
                        target_field = "interest_coverage"
                    elif "thanh toán tiền mặt" in item_name or "cash_ratio" in item_id:
                        target_field = "cash_ratio"
                    elif (
                        "tăng trưởng doanh thu" in item_name and "cùng kỳ" in item_name
                    ) or "revenue_growth_yoy" in item_id:
                        target_field = "revenue_growth_yoy"
                    elif (
                        "tăng trưởng lợi nhuận" in item_name and "cùng kỳ" in item_name
                    ) or "net_profit_growth_yoy" in item_id:
                        target_field = "net_profit_growth_yoy"
                    elif (
                        "tăng trưởng doanh thu" in item_name
                        and "quý trước" in item_name
                    ) or "revenue_growth_qoq" in item_id:
                        target_field = "revenue_growth_qoq"
                    elif (
                        "tăng trưởng lợi nhuận" in item_name
                        and "quý trước" in item_name
                    ) or "net_profit_growth_qoq" in item_id:
                        target_field = "net_profit_growth_qoq"

                    for col_name in period_cols:
                        raw_val = row.get(col_name)
                        try:
                            val = float(raw_val) if pd.notna(raw_val) else None
                        except (ValueError, TypeError):
                            val = None

                        col_key = str(col_name).strip()
                        if col_key in metric_row_map:
                            if val is not None and metric_raw_key:
                                metric_row_map[col_key]["data"][metric_raw_key] = val
                            if target_field:
                                metric_row_map[col_key][target_field] = val

                records = [r for r in metric_row_map.values() if r["year"] > 0]
            else:
                # Dạng 2: Bảng chuẩn từng row là 1 kỳ
                for _, row in df.iterrows():
                    year = self._extract_int(row, "year", "yearReport", default=0)
                    quarter = self._extract_int(
                        row, "quarter", "lengthReport", default=None
                    )
                    if year == 0:
                        continue
                    row_dict = row.to_dict() if hasattr(row, "to_dict") else dict(row)
                    row_data = {
                        k: v
                        for k, v in row_dict.items()
                        if k not in META_FINANCIAL_KEYS
                    }
                    records.append(
                        {
                            "id": uuid.uuid4(),
                            "symbol": symbol,
                            "period": clean_period,
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
                            "ev_to_ebitda": self._extract_float(
                                row, "ev_to_ebitda", "ev/ebitda"
                            ),
                            "ev_to_ebit": self._extract_float(
                                row, "ev_to_ebit", "ev/ebit"
                            ),
                            "p_to_fcf": self._extract_float(row, "p_to_fcf", "p/fcf"),
                            "p_to_ocf": self._extract_float(row, "p_to_ocf", "p/ocf"),
                            "fcf": self._extract_float(row, "fcf", "free_cash_flow"),
                            "ebit_margin": self._extract_float(
                                row, "ebit_margin", "ebitMargin"
                            ),
                            "ebitda_margin": self._extract_float(
                                row, "ebitda_margin", "ebitdaMargin"
                            ),
                            "asset_turnover": self._extract_float(
                                row, "asset_turnover", "assetTurnover"
                            ),
                            "inventory_turnover": self._extract_float(
                                row, "inventory_turnover", "inventoryTurnover"
                            ),
                            "receivables_turnover": self._extract_float(
                                row, "receivables_turnover", "receivablesTurnover"
                            ),
                            "debt_to_assets": self._extract_float(
                                row, "debt_to_assets", "debtToAssets"
                            ),
                            "interest_coverage": self._extract_float(
                                row, "interest_coverage", "interestCoverage"
                            ),
                            "cash_ratio": self._extract_float(
                                row, "cash_ratio", "cashRatio"
                            ),
                            "revenue_growth_yoy": self._extract_float(
                                row, "revenue_growth_yoy", "revenueGrowth"
                            ),
                            "net_profit_growth_yoy": self._extract_float(
                                row, "net_profit_growth_yoy", "netProfitGrowth"
                            ),
                            "revenue_growth_qoq": self._extract_float(
                                row, "revenue_growth_qoq"
                            ),
                            "net_profit_growth_qoq": self._extract_float(
                                row, "net_profit_growth_qoq"
                            ),
                            "data": row_data,
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
                        "position": position[:255] if position else None,
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
                        "event_type": (event_type or "EVENT")[:30],
                        "event_title": (event_title or "")[:500],
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

    def sync_company_subsidiaries(self, symbol: str) -> DataSyncLog:
        """Đồng bộ danh sách công ty con & liên kết (Company.subsidiaries()) bằng Bulk UPSERT."""

        def _task() -> int:
            sym_clean = symbol.strip().upper()
            df = self.svc.fetch_company_subsidiaries(sym_clean)
            if df is None or df.empty:
                return 0

            self._ensure_symbol_exists(sym_clean)
            now_utc = datetime.now(VN_TZ)
            records: list[dict[str, Any]] = []

            for _, row in df.iterrows():
                sub_code = self._extract_str(
                    row,
                    "sub_organ_code",
                    "subOrganCode",
                    "symbol",
                    default="",
                )
                organ_name = self._extract_str(
                    row,
                    "organ_name",
                    "organName",
                    "company_name",
                    default="",
                )
                if not organ_name:
                    continue
                if not sub_code:
                    sub_code = organ_name[:50]

                ownership = (
                    self._extract_float(
                        row,
                        "ownership_percent",
                        "ownershipPercent",
                        "ownership_pct",
                        default=0.0,
                    )
                    or 0.0
                )

                records.append(
                    {
                        "id": uuid.uuid4(),
                        "symbol": sym_clean,
                        "sub_organ_code": sub_code[:50],
                        "organ_name": organ_name[:500],
                        "ownership_percent": ownership,
                        "updated_at": now_utc,
                    }
                )

            if not records:
                return 0

            count = self._bulk_upsert(
                CompanySubsidiary,
                records,
                ["symbol", "sub_organ_code"],
                COMPANY_SUBSIDIARY_UPDATE_FIELDS,
            )
            self.session.commit()
            logger.info("Synced %d subsidiaries for %s", count, sym_clean)
            return count

        return self._run_sync_task("subsidiaries", _task, symbol=symbol)

    def sync_insider_trading(self, symbol: str) -> DataSyncLog:
        """Đồng bộ nhật ký giao dịch người nội bộ và người có liên quan bằng Bulk UPSERT."""

        def _task() -> int:
            sym_clean = symbol.strip().upper()
            df = self.svc.fetch_company_insider_trading(sym_clean)
            if df is None or df.empty:
                return 0

            self._ensure_symbol_exists(sym_clean)
            now_utc = datetime.now(VN_TZ)
            records: list[dict[str, Any]] = []

            for _, row in df.iterrows():
                officer_name = self._extract_str(
                    row,
                    "officer_name",
                    "officerName",
                    "trader_name",
                    "traderName",
                    "name",
                    default="",
                )
                if not officer_name:
                    continue

                officer_position = self._extract_str(
                    row,
                    "officer_position",
                    "officerPosition",
                    "position",
                    default=None,
                )
                deal_action = self._extract_str(
                    row,
                    "deal_action",
                    "dealAction",
                    "action",
                    default="Mua/Bán",
                )

                raw_date = (
                    row.get("deal_announce_date")
                    or row.get("announce_date")
                    or row.get("date")
                )
                deal_date: date | None = None
                if raw_date and pd.notna(raw_date):
                    try:
                        deal_date = date.fromisoformat(str(raw_date)[:10])
                    except (ValueError, TypeError):
                        deal_date = None

                records.append(
                    {
                        "id": uuid.uuid4(),
                        "symbol": sym_clean,
                        "officer_name": officer_name[:255],
                        "officer_position": (
                            officer_position[:255] if officer_position else None
                        ),
                        "deal_action": (deal_action or "Mua/Bán")[:50],
                        "deal_quantity": self._extract_float(
                            row, "deal_quantity", "quantity", "dealQuantity"
                        ),
                        "deal_price": self._extract_float(
                            row, "deal_price", "price", "dealPrice"
                        ),
                        "deal_ratio": self._extract_float(
                            row, "deal_ratio", "ratio", "dealRatio"
                        ),
                        "deal_announce_date": deal_date,
                        "updated_at": now_utc,
                    }
                )

            if not records:
                return 0

            count = self._bulk_upsert(
                InsiderTrading,
                records,
                [
                    "symbol",
                    "officer_name",
                    "deal_action",
                    "deal_announce_date",
                ],
                INSIDER_TRADING_UPDATE_FIELDS,
            )
            self.session.commit()
            logger.info("Synced %d insider trading records for %s", count, sym_clean)
            return count

        return self._run_sync_task("insider_trading", _task, symbol=symbol)

    def sync_capital_history(self, symbol: str) -> DataSyncLog:
        """Đồng bộ lịch sử các đợt phát hành và tăng vốn điều lệ bằng Bulk UPSERT."""

        def _task() -> int:
            sym_clean = symbol.strip().upper()
            df = self.svc.fetch_company_capital_history(sym_clean)
            if df is None or df.empty:
                return 0

            self._ensure_symbol_exists(sym_clean)
            now_utc = datetime.now(VN_TZ)
            records: list[dict[str, Any]] = []

            for _, row in df.iterrows():
                raw_date = row.get("issue_date") or row.get("date") or row.get("year")
                issue_date: date | None = None
                if raw_date and pd.notna(raw_date):
                    try:
                        str_date = str(raw_date).strip()
                        if len(str_date) == 4 and str_date.isdigit():
                            issue_date = date(int(str_date), 1, 1)
                        else:
                            issue_date = date.fromisoformat(str_date[:10])
                    except (ValueError, TypeError):
                        issue_date = None

                charter_cap = self._extract_float(
                    row, "charter_capital", "charterCapital", "capital"
                )
                shares = self._extract_float(
                    row, "shares_issued", "sharesIssued", "issue_share", "shares"
                )
                desc = self._extract_str(
                    row, "description", "event_title", "notes", default=None
                )

                records.append(
                    {
                        "id": uuid.uuid4(),
                        "symbol": sym_clean,
                        "issue_date": issue_date,
                        "charter_capital": charter_cap,
                        "shares_issued": shares,
                        "description": desc[:500] if desc else None,
                        "updated_at": now_utc,
                    }
                )

            if not records:
                return 0

            count = self._bulk_upsert(
                CapitalHistory,
                records,
                ["symbol", "issue_date", "charter_capital"],
                CAPITAL_HISTORY_UPDATE_FIELDS,
            )
            self.session.commit()
            logger.info("Synced %d capital history records for %s", count, sym_clean)
            return count

        return self._run_sync_task("capital_history", _task, symbol=symbol)

    def sync_screener_snapshots(self, snapshot_date: date | None = None) -> DataSyncLog:
        """Sinh và đồng bộ ảnh chụp màn hình bộ lọc ScreenerSnapshot & Historical."""

        def _task() -> int:
            return ScreenerService.generate_daily_snapshot(
                self.session, snapshot_date=snapshot_date
            )

        return self._run_sync_task("screener", _task)

    def sync_company_full(self, symbol: str) -> dict[str, Any]:
        """Đồng bộ toàn diện thông tin doanh nghiệp (Hồ sơ + Cổ đông + Lãnh đạo + Sự kiện + Cty con + GDNB + Tăng vốn)."""
        sym_clean = symbol.strip().upper()
        results = {
            "profile": self.sync_company_profile(sym_clean),
            "shareholders": self.sync_company_shareholders(sym_clean),
            "officers": self.sync_company_officers(sym_clean),
            "events": self.sync_corporate_events(sym_clean),
            "subsidiaries": self.sync_company_subsidiaries(sym_clean),
            "insider_trading": self.sync_insider_trading(sym_clean),
            "capital_history": self.sync_capital_history(sym_clean),
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
                try:
                    if st == "profile":
                        sym_result["profile"] = self.sync_company_profile(
                            sym_clean
                        ).status
                    elif st == "shareholders":
                        sym_result["shareholders"] = self.sync_company_shareholders(
                            sym_clean
                        ).status
                    elif st == "officers":
                        sym_result["officers"] = self.sync_company_officers(
                            sym_clean
                        ).status
                    elif st == "events":
                        sym_result["events"] = self.sync_corporate_events(
                            sym_clean
                        ).status
                    elif st == "subsidiaries":
                        sym_result["subsidiaries"] = self.sync_company_subsidiaries(
                            sym_clean
                        ).status
                    elif st == "insider_trading":
                        sym_result["insider_trading"] = self.sync_insider_trading(
                            sym_clean
                        ).status
                    elif st == "capital_history":
                        sym_result["capital_history"] = self.sync_capital_history(
                            sym_clean
                        ).status
                    elif st == "financials":
                        sym_result["financials"] = self.sync_financials(
                            sym_clean
                        ).status
                    elif st == "ratios":
                        sym_result["ratios"] = self.sync_financial_ratios(
                            sym_clean
                        ).status
                    elif st == "institutional_flow":
                        sym_result["institutional_flow"] = self.sync_institutional_flow(
                            symbols=[sym_clean]
                        ).status
                    elif st == "daily":
                        daily_logs = self.sync_daily_incremental([sym_clean])
                        sym_result["daily"] = (
                            daily_logs[0].status if daily_logs else "success"
                        )
                    else:
                        sym_result[st] = "unknown_sync_type"
                except Exception as exc:
                    logger.error("Lỗi khi đồng bộ %s cho mã %s: %s", st, sym_clean, exc)
                    sym_result[st] = "failed"
                time.sleep(delay_sec)

            batch_summary[sym_clean] = sym_result
            time.sleep(delay_sec)

        return batch_summary

    def compute_daily_derivative_basis(self, trading_date: date | None = None) -> int:
        """Tính toán và lưu độ lệch cơ sở (basis = VN30F1M.close - VN30.close) vào StockOHLCVDaily."""
        target_date = trading_date or date.today()
        vn30 = self.session.exec(
            select(StockOHLCVDaily).where(
                StockOHLCVDaily.symbol == "VN30",
                StockOHLCVDaily.trading_date == target_date,
            )
        ).first()
        f1m = self.session.exec(
            select(StockOHLCVDaily).where(
                StockOHLCVDaily.symbol == "VN30F1M",
                StockOHLCVDaily.trading_date == target_date,
            )
        ).first()
        if vn30 and f1m:
            f1m.basis = round(f1m.close - vn30.close, 2)
            self.session.add(f1m)
            self.session.commit()
            return 1
        return 0

    def sync_institutional_flow(
        self,
        trading_date: date | None = None,
        symbols: list[str] | None = None,
    ) -> DataSyncLog:
        """Đồng bộ dòng tiền tổ chức: Khối ngoại & Tự doanh (Động cơ 2: Thanh khoản)."""
        target_date = trading_date or date.today()

        def _task() -> int:
            target_symbols = symbols
            if target_symbols is None:
                active = self.session.exec(
                    select(StockSymbol.symbol).where(StockSymbol.is_active == True)  # noqa: E712
                ).all()
                target_symbols = list(active)

            # Thử lấy dữ liệu dòng tiền khối ngoại và tự doanh trực tiếp từ API nếu có
            foreign_map: dict[str, Any] = {}
            prop_map: dict[str, Any] = {}
            fetch_foreign_fn = getattr(self.svc, "fetch_foreign_flow", None)
            if callable(fetch_foreign_fn):
                try:
                    f_df = fetch_foreign_fn(trading_date=target_date)
                    if f_df is not None and not f_df.empty:
                        sym_c = self._resolve_symbol_column(f_df) or "symbol"
                        for _, row in f_df.iterrows():
                            s = str(row.get(sym_c, "")).strip().upper()
                            if s:
                                foreign_map[s] = row
                except Exception:
                    pass

            fetch_prop_fn = getattr(self.svc, "fetch_prop_flow", None)
            if callable(fetch_prop_fn):
                try:
                    p_df = fetch_prop_fn(trading_date=target_date)
                    if p_df is not None and not p_df.empty:
                        sym_c = self._resolve_symbol_column(p_df) or "symbol"
                        for _, row in p_df.iterrows():
                            s = str(row.get(sym_c, "")).strip().upper()
                            if s:
                                prop_map[s] = row
                except Exception:
                    pass

            records: list[dict[str, Any]] = []

            for sym in target_symbols:
                sym_clean = sym.strip().upper()
                f_row = foreign_map.get(sym_clean)
                p_row = prop_map.get(sym_clean)

                daily_bar = self.session.exec(
                    select(StockOHLCVDaily).where(
                        StockOHLCVDaily.symbol == sym_clean,
                        StockOHLCVDaily.trading_date == target_date,
                    )
                ).first()

                close_price = daily_bar.close if daily_bar else 0.0

                # Khối ngoại
                if f_row is not None:
                    foreign_buy_vol = self._extract_int(
                        f_row, "buy_vol", "foreign_buy_volume", default=None
                    )
                    foreign_sell_vol = self._extract_int(
                        f_row, "sell_vol", "foreign_sell_volume", default=None
                    )
                    foreign_net_vol = self._extract_int(
                        f_row, "net_vol", "foreign_net_volume", default=None
                    )
                    foreign_buy_val = self._extract_float(
                        f_row, "buy_val", "foreign_buy_value"
                    )
                    foreign_sell_val = self._extract_float(
                        f_row, "sell_val", "foreign_sell_value"
                    )
                    foreign_net_val = self._extract_float(
                        f_row, "net_val", "foreign_net_value"
                    )
                    foreign_room_total = self._extract_int(
                        f_row, "room_total", "foreign_room_total", default=None
                    )
                    foreign_room_current = self._extract_int(
                        f_row, "room_current", "foreign_room_current", default=None
                    )
                    foreign_room_pct = self._extract_float(
                        f_row, "room_pct", "foreign_room_pct"
                    )
                else:
                    foreign_buy_vol = (
                        daily_bar.foreign_buy_volume if daily_bar else None
                    )
                    foreign_sell_vol = (
                        daily_bar.foreign_sell_volume if daily_bar else None
                    )
                    foreign_net_vol = (
                        daily_bar.foreign_net_volume if daily_bar else None
                    )
                    foreign_buy_val = (
                        float(foreign_buy_vol) * close_price
                        if foreign_buy_vol is not None
                        else None
                    )
                    foreign_sell_val = (
                        float(foreign_sell_vol) * close_price
                        if foreign_sell_vol is not None
                        else None
                    )
                    foreign_net_val = (
                        float(foreign_net_vol) * close_price
                        if foreign_net_vol is not None
                        else None
                    )
                    profile = self.session.exec(
                        select(CompanyProfile).where(CompanyProfile.symbol == sym_clean)
                    ).first()
                    foreign_room_pct = (
                        profile.foreign_ownership_pct if profile else None
                    )
                    if (
                        profile
                        and profile.outstanding_shares
                        and profile.max_foreign_ownership_pct is not None
                    ):
                        foreign_room_total = int(
                            profile.outstanding_shares
                            * (profile.max_foreign_ownership_pct / 100.0)
                        )
                    else:
                        foreign_room_total = None
                    foreign_room_current = None

                # Tự doanh
                if p_row is not None:
                    prop_buy_vol = self._extract_int(
                        p_row, "buy_vol", "prop_buy_volume", default=None
                    )
                    prop_sell_vol = self._extract_int(
                        p_row, "sell_vol", "prop_sell_volume", default=None
                    )
                    prop_net_vol = self._extract_int(
                        p_row, "net_vol", "prop_net_volume", default=None
                    )
                    prop_buy_val = self._extract_float(
                        p_row, "buy_val", "prop_buy_value"
                    )
                    prop_sell_val = self._extract_float(
                        p_row, "sell_val", "prop_sell_value"
                    )
                    prop_net_val = self._extract_float(
                        p_row, "net_val", "prop_net_value"
                    )
                else:
                    prop_buy_vol = None
                    prop_sell_vol = None
                    prop_net_vol = None
                    prop_buy_val = None
                    prop_sell_val = None
                    prop_net_val = None

                # Không tạo bản ghi NULL giả nếu không có bất kỳ dữ liệu dòng tiền thực tế nào
                has_foreign = (
                    foreign_buy_vol is not None
                    or foreign_sell_vol is not None
                    or foreign_net_vol is not None
                )
                has_prop = (
                    prop_buy_vol is not None
                    or prop_sell_vol is not None
                    or prop_net_vol is not None
                )
                if not has_foreign and not has_prop:
                    continue

                last_src = getattr(self.svc, "last_successful_source", None)
                if isinstance(last_src, str) and last_src:
                    actual_src = last_src
                else:
                    svc_src = getattr(self.svc, "source", None)
                    actual_src = (
                        svc_src if isinstance(svc_src, str) and svc_src else "VCI"
                    )
                records.append(
                    {
                        "id": uuid.uuid4(),
                        "trading_date": target_date,
                        "symbol": sym_clean,
                        "foreign_buy_volume": foreign_buy_vol,
                        "foreign_sell_volume": foreign_sell_vol,
                        "foreign_net_volume": foreign_net_vol,
                        "foreign_buy_value": foreign_buy_val,
                        "foreign_sell_value": foreign_sell_val,
                        "foreign_net_value": foreign_net_val,
                        "foreign_room_total": foreign_room_total,
                        "foreign_room_current": foreign_room_current,
                        "foreign_room_pct": foreign_room_pct,
                        "prop_buy_volume": prop_buy_vol,
                        "prop_sell_volume": prop_sell_vol,
                        "prop_net_volume": prop_net_vol,
                        "prop_buy_value": prop_buy_val,
                        "prop_sell_value": prop_sell_val,
                        "prop_net_value": prop_net_val,
                        "source": actual_src,
                    }
                )

            if not records:
                logger.info(
                    "Không có dữ liệu dòng tiền thực tế nào được tìm thấy cho ngày %s (bỏ qua ghi nhận NULL)",
                    target_date,
                )
                return 0

            count = self._bulk_upsert(
                InstitutionalFlow,
                records,
                ["trading_date", "symbol", "source"],
                INSTITUTIONAL_FLOW_UPDATE_FIELDS,
            )
            self.session.commit()
            logger.info(
                "Đã đồng bộ dòng tiền tổ chức cho %d mã ngày %s", count, target_date
            )
            return count

        return self._run_sync_task("institutional_flow", _task)


__all__ = [
    "BOND_SPECIFICATION_UPDATE_FIELDS",
    "BOND_TYPE_CONFIG",
    "CAPITAL_HISTORY_UPDATE_FIELDS",
    "COMPANY_OFFICER_UPDATE_FIELDS",
    "COMPANY_PROFILE_UPDATE_FIELDS",
    "COMPANY_SHAREHOLDER_UPDATE_FIELDS",
    "COMPANY_SUBSIDIARY_UPDATE_FIELDS",
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
    "INSIDER_TRADING_UPDATE_FIELDS",
    "INTRADAY_OHLCV_UPDATE_FIELDS",
    "META_FINANCIAL_KEYS",
    "STANDARD_INDEXES",
    "STOCK_SYMBOL_UPDATE_FIELDS",
    "get_third_thursday",
]
