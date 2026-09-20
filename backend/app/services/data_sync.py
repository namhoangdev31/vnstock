"""DataSyncManager — orchestrates data synchronization from vnstock → PostgreSQL.

3 sync modes:
1. Historical Backfill  — one-time full data import
2. Incremental Daily    — daily update after market close
3. Intraday Collector   — realtime bar collection during trading session
"""

import logging
import uuid
from datetime import UTC, date, datetime
from typing import Any

import pandas as pd
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

    def _create_log(self, sync_type: str, symbol: str | None = None) -> DataSyncLog:
        """Create a sync log entry with status 'started'."""
        source_str = (
            str(self.svc.source) if getattr(self.svc, "source", None) else "VCI"
        )
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

    # ------------------------------------------------------------------
    # Sync: Symbols
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

            bind = self.session.get_bind()
            dialect_name = getattr(getattr(bind, "dialect", None), "name", "")
            if dialect_name == "postgresql":
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
        for symbol_code, exp_date, desc in contracts:
            sym = self.session.get(StockSymbol, symbol_code)
            if sym:
                sym.organ_name = desc
                sym.exchange = "DERIV"
                sym.asset_type = "derivative"
                sym.lot_size = 1
                sym.is_active = True
                sym.updated_at = datetime.now(UTC)
                self.session.add(sym)
            else:
                sym = StockSymbol(
                    symbol=symbol_code,
                    organ_name=desc,
                    exchange="DERIV",
                    industry="Derivatives",
                    asset_type="derivative",
                    lot_size=1,
                    is_active=True,
                )
                self.session.add(sym)

            contract = self.session.get(DerivativeContract, symbol_code)
            if contract:
                contract.expiration_date = exp_date
                contract.underlying_symbol = "VN30"
                contract.multiplier = 100_000.0
                contract.is_active = True
                contract.updated_at = datetime.now(UTC)
                self.session.add(contract)
            else:
                contract = DerivativeContract(
                    symbol=symbol_code,
                    underlying_symbol="VN30",
                    multiplier=100_000.0,
                    expiration_date=exp_date,
                    is_active=True,
                )
                self.session.add(contract)
            count += 1

        try:
            deriv_df = self.svc.fetch_derivatives_list()
            if isinstance(deriv_df, pd.DataFrame) and not deriv_df.empty:
                for _, row in deriv_df.iterrows():
                    code = str(row.get("ticker", row.get("symbol", ""))).strip().upper()
                    if not code or code in [c[0] for c in contracts]:
                        continue
                    exp = None
                    if len(code) == 9 and code.startswith("VN30F"):
                        try:
                            yy = 2000 + int(code[5:7])
                            mm = int(code[7:9])
                            exp = get_third_thursday(yy, mm)
                        except (ValueError, IndexError):
                            pass
                    if not exp:
                        exp = m1_exp

                    sym = self.session.get(StockSymbol, code)
                    if not sym:
                        sym = StockSymbol(
                            symbol=code,
                            organ_name=f"Hợp đồng tương lai {code}",
                            exchange="DERIV",
                            industry="Derivatives",
                            asset_type="derivative",
                            lot_size=1,
                            is_active=True,
                        )
                        self.session.add(sym)
                    contract = self.session.get(DerivativeContract, code)
                    if not contract:
                        contract = DerivativeContract(
                            symbol=code,
                            underlying_symbol="VN30",
                            multiplier=100_000.0,
                            expiration_date=exp,
                            is_active=True,
                        )
                        self.session.add(contract)
                    count += 1
            elif isinstance(deriv_df, pd.Series) and not deriv_df.empty:
                for val in deriv_df:
                    code = str(val).strip().upper()
                    if not code or code in [c[0] for c in contracts]:
                        continue
                    exp = m1_exp
                    sym = self.session.get(StockSymbol, code)
                    if not sym:
                        sym = StockSymbol(
                            symbol=code,
                            organ_name=f"Hợp đồng tương lai {code}",
                            exchange="DERIV",
                            industry="Derivatives",
                            asset_type="derivative",
                            lot_size=1,
                            is_active=True,
                        )
                        self.session.add(sym)
                    contract = self.session.get(DerivativeContract, code)
                    if not contract:
                        contract = DerivativeContract(
                            symbol=code,
                            underlying_symbol="VN30",
                            multiplier=100_000.0,
                            expiration_date=exp,
                            is_active=True,
                        )
                        self.session.add(contract)
                    count += 1
        except Exception as exc:
            logger.warning("Could not fetch extra derivatives list: %s", exc)

        return count

    # ------------------------------------------------------------------
    # Sync: Covered Warrants (CW)
    # ------------------------------------------------------------------

    def sync_covered_warrants(self) -> DataSyncLog:
        """Đồng bộ riêng danh mục chứng quyền có bảo đảm (Covered Warrants)."""
        log = self._create_log("covered_warrants")
        try:
            count = self._sync_covered_warrants()
            return self._finish_log(log, "success", rows_synced=count)
        except Exception as exc:
            self.session.rollback()
            return self._finish_log(log, "failed", error_message=str(exc))

    def _sync_covered_warrants(self) -> int:
        """Đồng bộ danh mục chứng quyền có bảo đảm (CW) vào StockSymbol và CoveredWarrant sử dụng Bulk UPSERT."""
        try:
            cw_data = self.svc.fetch_covered_warrants_list()
            if cw_data is None:
                return 0

            if isinstance(cw_data, pd.Series):
                df = pd.DataFrame({"symbol": cw_data})
            elif isinstance(cw_data, list):
                df = pd.DataFrame({"symbol": cw_data})
            elif isinstance(cw_data, pd.DataFrame):
                df = cw_data
            else:
                return 0

            if df.empty:
                return 0

            col_sym = (
                "symbol"
                if "symbol" in df.columns
                else ("ticker" if "ticker" in df.columns else df.columns[0])
            )

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
                underlying = (
                    str(raw_und).strip().upper()
                    if raw_und and pd.notna(raw_und)
                    else None
                )

                if not underlying:
                    if code.startswith(("C", "P")) and len(code) == 8:
                        underlying = code[1:4]
                    elif code.startswith(("C", "P")) and len(code) >= 6:
                        underlying = code[1:-4] if len(code) > 6 else code[1:4]

                if not underlying:
                    continue

                underlying_codes.add(underlying)

                w_type_raw = str(row.get("warrant_type", row.get("type", ""))).lower()
                if w_type_raw in ("call", "put"):
                    warrant_type = w_type_raw
                else:
                    warrant_type = "call" if code.startswith("C") else "put"

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
                issue_date = self._parse_date(
                    row.get("issue_date", row.get("issueDate"))
                )
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

                is_active = True
                if maturity_date and maturity_date < today_d:
                    is_active = False

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

            # 1. Đảm bảo tất cả mã cơ sở (underlying_symbol) đã tồn tại trong stock_symbol trước khi insert CW
            existing_und = set(
                self.session.exec(
                    select(StockSymbol.symbol).where(
                        col(StockSymbol.symbol).in_(list(underlying_codes))
                    )
                ).all()
            )
            missing_und = underlying_codes - existing_und
            if missing_und:
                for und in missing_und:
                    self.session.add(
                        StockSymbol(
                            id=uuid.uuid4(),
                            symbol=und,
                            organ_name=f"Cổ phiếu cơ sở {und}",
                            exchange="HOSE",
                            industry="Equities",
                            asset_type="stock",
                            lot_size=100,
                            is_active=True,
                            updated_at=now_utc,
                        )
                    )
                self.session.flush()

            # 2. Bulk UPSERT
            bind = self.session.get_bind()
            dialect_name = getattr(getattr(bind, "dialect", None), "name", "")
            batch_size = 500
            sym_records = list(sym_map.values())
            cw_records = list(cw_map.values())

            if dialect_name == "postgresql":
                from sqlalchemy.dialects.postgresql import insert as pg_insert

                for i in range(0, len(sym_records), batch_size):
                    batch_sym = sym_records[i : i + batch_size]
                    stmt_sym = pg_insert(StockSymbol).values(batch_sym)
                    stmt_sym = stmt_sym.on_conflict_do_update(
                        index_elements=["symbol"],
                        set_={
                            "organ_name": stmt_sym.excluded.organ_name,
                            "exchange": stmt_sym.excluded.exchange,
                            "industry": stmt_sym.excluded.industry,
                            "asset_type": stmt_sym.excluded.asset_type,
                            "lot_size": stmt_sym.excluded.lot_size,
                            "is_active": stmt_sym.excluded.is_active,
                            "updated_at": stmt_sym.excluded.updated_at,
                        },
                    )
                    self.session.execute(stmt_sym)

                for i in range(0, len(cw_records), batch_size):
                    batch_cw = cw_records[i : i + batch_size]
                    stmt_cw = pg_insert(CoveredWarrant).values(batch_cw)
                    stmt_cw = stmt_cw.on_conflict_do_update(
                        index_elements=["symbol"],
                        set_={
                            "underlying_symbol": stmt_cw.excluded.underlying_symbol,
                            "issuer_name": stmt_cw.excluded.issuer_name,
                            "warrant_type": stmt_cw.excluded.warrant_type,
                            "exercise_price": stmt_cw.excluded.exercise_price,
                            "conversion_ratio": stmt_cw.excluded.conversion_ratio,
                            "exercise_ratio": stmt_cw.excluded.exercise_ratio,
                            "issue_date": stmt_cw.excluded.issue_date,
                            "maturity_date": stmt_cw.excluded.maturity_date,
                            "last_trading_date": stmt_cw.excluded.last_trading_date,
                            "settlement_type": stmt_cw.excluded.settlement_type,
                            "is_active": stmt_cw.excluded.is_active,
                            "updated_at": stmt_cw.excluded.updated_at,
                        },
                    )
                    self.session.execute(stmt_cw)
            else:
                for rec_sym in sym_records:
                    s_code = rec_sym["symbol"]
                    existing_s = self.session.get(StockSymbol, s_code)
                    if existing_s:
                        for k, v in rec_sym.items():
                            if k != "id" and v is not None:
                                setattr(existing_s, k, v)
                        self.session.add(existing_s)
                    else:
                        self.session.add(StockSymbol(**rec_sym))

                self.session.flush()

                for rec_cw in cw_records:
                    cw_code = rec_cw["symbol"]
                    existing_cw = self.session.exec(
                        select(CoveredWarrant).where(CoveredWarrant.symbol == cw_code)
                    ).first()
                    if existing_cw:
                        for k, v in rec_cw.items():
                            if k != "id" and v is not None:
                                setattr(existing_cw, k, v)
                        self.session.add(existing_cw)
                    else:
                        self.session.add(CoveredWarrant(**rec_cw))

            self.session.commit()
            return len(cw_records)
        except Exception as exc:
            logger.warning("Lỗi đồng bộ danh mục chứng quyền: %s", exc)
            return 0

    # ------------------------------------------------------------------
    # Sync: Bonds (Corporate & Government)
    # ------------------------------------------------------------------

    def sync_bonds(self) -> DataSyncLog:
        """Đồng bộ riêng danh mục trái phiếu doanh nghiệp & chính phủ."""
        log = self._create_log("bonds")
        try:
            count = self._sync_bonds()
            return self._finish_log(log, "success", rows_synced=count)
        except Exception as exc:
            self.session.rollback()
            return self._finish_log(log, "failed", error_message=str(exc))

    def _sync_bonds(self) -> int:
        """Đồng bộ danh mục trái phiếu doanh nghiệp & chính phủ vào StockSymbol và BondSpecification sử dụng Bulk UPSERT."""
        try:
            df = self.svc.fetch_bonds_list(bond_type="all")
            if df is None or df.empty:
                return 0

            col_sym = (
                "symbol"
                if "symbol" in df.columns
                else ("ticker" if "ticker" in df.columns else df.columns[0])
            )

            now_utc = datetime.now(UTC)
            today_d = date.today()

            sym_map: dict[str, dict[str, Any]] = {}
            bond_map: dict[str, dict[str, Any]] = {}
            candidate_issuers: set[str] = set()

            for _, row in df.iterrows():
                code = str(row.get(col_sym, "")).strip().upper()
                if not code:
                    continue

                b_type = str(row.get("type", row.get("bond_type", "corporate"))).lower()
                if b_type not in ("corporate", "government"):
                    b_type = "corporate"

                if b_type == "corporate":
                    raw_issuer = row.get(
                        "issuer_symbol",
                        row.get("issuerSymbol", row.get("company_code")),
                    )
                    if raw_issuer and pd.notna(raw_issuer):
                        candidate_issuers.add(str(raw_issuer).strip().upper())
                    else:
                        candidate_issuers.add(code[:3])

            existing_issuers: set[str] = set()
            if candidate_issuers:
                existing_issuers = set(
                    self.session.exec(
                        select(StockSymbol.symbol).where(
                            col(StockSymbol.symbol).in_(list(candidate_issuers))
                        )
                    ).all()
                )

            for _, row in df.iterrows():
                code = str(row.get(col_sym, "")).strip().upper()
                if not code:
                    continue

                b_type = str(row.get("type", row.get("bond_type", "corporate"))).lower()
                if b_type not in ("corporate", "government"):
                    b_type = "corporate"

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
                issue_date = self._parse_date(
                    row.get("issue_date", row.get("issueDate"))
                )
                maturity_date = self._parse_date(
                    row.get(
                        "maturity_date",
                        row.get("maturityDate", row.get("expiration_date")),
                    )
                )

                is_active = True
                if maturity_date and maturity_date < today_d:
                    is_active = False

                organ_label = (
                    f"Trái phiếu DN {code}"
                    if b_type == "corporate"
                    else f"Trái phiếu Chính phủ {code}"
                )
                asset_label = (
                    "corporate_bond" if b_type == "corporate" else "government_bond"
                )

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

            bind = self.session.get_bind()
            dialect_name = getattr(getattr(bind, "dialect", None), "name", "")
            batch_size = 500
            sym_records = list(sym_map.values())
            bond_records = list(bond_map.values())

            if dialect_name == "postgresql":
                from sqlalchemy.dialects.postgresql import insert as pg_insert

                for i in range(0, len(sym_records), batch_size):
                    batch_sym = sym_records[i : i + batch_size]
                    stmt_sym = pg_insert(StockSymbol).values(batch_sym)
                    stmt_sym = stmt_sym.on_conflict_do_update(
                        index_elements=["symbol"],
                        set_={
                            "organ_name": stmt_sym.excluded.organ_name,
                            "exchange": stmt_sym.excluded.exchange,
                            "industry": stmt_sym.excluded.industry,
                            "asset_type": stmt_sym.excluded.asset_type,
                            "lot_size": stmt_sym.excluded.lot_size,
                            "is_active": stmt_sym.excluded.is_active,
                            "updated_at": stmt_sym.excluded.updated_at,
                        },
                    )
                    self.session.execute(stmt_sym)

                for i in range(0, len(bond_records), batch_size):
                    batch_bond = bond_records[i : i + batch_size]
                    stmt_bond = pg_insert(BondSpecification).values(batch_bond)
                    stmt_bond = stmt_bond.on_conflict_do_update(
                        index_elements=["symbol"],
                        set_={
                            "bond_type": stmt_bond.excluded.bond_type,
                            "issuer_symbol": stmt_bond.excluded.issuer_symbol,
                            "issuer_name": stmt_bond.excluded.issuer_name,
                            "par_value": stmt_bond.excluded.par_value,
                            "coupon_rate": stmt_bond.excluded.coupon_rate,
                            "coupon_type": stmt_bond.excluded.coupon_type,
                            "tenor_years": stmt_bond.excluded.tenor_years,
                            "issue_date": stmt_bond.excluded.issue_date,
                            "maturity_date": stmt_bond.excluded.maturity_date,
                            "is_active": stmt_bond.excluded.is_active,
                            "updated_at": stmt_bond.excluded.updated_at,
                        },
                    )
                    self.session.execute(stmt_bond)
            else:
                for rec_sym in sym_records:
                    s_code = rec_sym["symbol"]
                    existing_s = self.session.get(StockSymbol, s_code)
                    if existing_s:
                        for k, v in rec_sym.items():
                            if k != "id" and v is not None:
                                setattr(existing_s, k, v)
                        self.session.add(existing_s)
                    else:
                        self.session.add(StockSymbol(**rec_sym))

                self.session.flush()

                for rec_bond in bond_records:
                    b_code = rec_bond["symbol"]
                    existing_b = self.session.exec(
                        select(BondSpecification).where(
                            BondSpecification.symbol == b_code
                        )
                    ).first()
                    if existing_b:
                        for k, v in rec_bond.items():
                            if k != "id" and v is not None:
                                setattr(existing_b, k, v)
                        self.session.add(existing_b)
                    else:
                        self.session.add(BondSpecification(**rec_bond))

            self.session.commit()
            return len(bond_records)
        except Exception as exc:
            logger.warning("Lỗi đồng bộ danh mục trái phiếu: %s", exc)
            return 0

    def sync_symbols(self) -> DataSyncLog:
        """Sync all stock symbols to the database."""
        log = self._create_log("symbols")

        try:
            df = self.svc.fetch_all_symbols()
            if df is None or df.empty:
                return self._finish_log(log, "failed", error_message="Empty response")

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
                exchange = (
                    str(row.get("exchange", row.get("organCode", ""))).upper() or None
                )
                icb_code = str(row.get("icbCode", row.get("icb_code", ""))) or None
                icb_name = str(row.get("icbName", row.get("icb_name", ""))) or None
                industry = icb_name or str(row.get("industry", "")) or None

                if "VN30F" in symbol_str:
                    asset_type = "derivative"
                    lot_size = 1
                    exchange = exchange or "DERIV"
                elif (
                    symbol_str.startswith("E1VFVN30")
                    or symbol_str.startswith("FUE")
                    or "ETF" in symbol_str
                ):
                    asset_type = "etf"
                    lot_size = 100
                elif symbol_str in ("VNINDEX", "VN30", "HNX", "HNX30", "UPCOM"):
                    asset_type = "index"
                    lot_size = 1
                else:
                    asset_type = str(
                        row.get("type", row.get("asset_type", "stock"))
                    ).lower()
                    lot_size = 100

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

            bind = self.session.get_bind()
            dialect_name = getattr(getattr(bind, "dialect", None), "name", "")

            if dialect_name == "postgresql" and records:
                from sqlalchemy.dialects.postgresql import insert as pg_insert

                batch_size = 500
                for i in range(0, len(records), batch_size):
                    batch = records[i : i + batch_size]
                    stmt = pg_insert(StockSymbol).values(batch)
                    stmt = stmt.on_conflict_do_update(
                        index_elements=["symbol"],
                        set_={
                            "organ_name": stmt.excluded.organ_name,
                            "exchange": stmt.excluded.exchange,
                            "industry": stmt.excluded.industry,
                            "icb_code": stmt.excluded.icb_code,
                            "icb_name": stmt.excluded.icb_name,
                            "asset_type": stmt.excluded.asset_type,
                            "lot_size": stmt.excluded.lot_size,
                            "is_active": stmt.excluded.is_active,
                            "updated_at": stmt.excluded.updated_at,
                        },
                    )
                    self.session.execute(stmt)
                count = len(records)
            else:
                existing_symbols = {
                    s.symbol: s for s in self.session.exec(select(StockSymbol)).all()
                }
                for rec in records:
                    sym_code = rec["symbol"]
                    existing = existing_symbols.get(sym_code)
                    if existing:
                        for k, v in rec.items():
                            if v is not None:
                                setattr(existing, k, v)
                        self.session.add(existing)
                    else:
                        sym = StockSymbol(**rec)
                        self.session.add(sym)
                        existing_symbols[sym_code] = sym
                count = len(records)

            del records
            import gc

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
            return self._finish_log(log, "success", rows_synced=count)

        except VnstockServiceError as exc:
            return self._finish_log(log, "failed", error_message=str(exc))
        except Exception as exc:
            self.session.rollback()
            return self._finish_log(log, "failed", error_message=str(exc))

    # ------------------------------------------------------------------
    # Sync: Daily OHLCV (Backfill + Incremental)
    # ------------------------------------------------------------------

    def backfill_daily(
        self,
        symbol: str,
        start: date,
        end: date | None = None,
    ) -> DataSyncLog:
        """Backfill historical daily OHLCV data for a symbol.

        Smart fill: checks existing data in DB and only fetches missing ranges.
        """
        end = end or date.today()
        log = self._create_log("daily_ohlcv", symbol=symbol)

        try:
            # Check what we already have
            existing = self.session.exec(
                select(col(StockOHLCVDaily.trading_date))
                .where(StockOHLCVDaily.symbol == symbol)
                .where(StockOHLCVDaily.trading_date >= start)
                .where(StockOHLCVDaily.trading_date <= end)
                .order_by(col(StockOHLCVDaily.trading_date))
            ).all()
            existing_dates = set(existing)

            # Fetch from vnstock
            df = self.svc.fetch_price_history(symbol, start, end, interval="1D")
            if df is None or df.empty:
                return self._finish_log(log, "success", rows_synced=0)

            # Ensure symbol exists in stock_symbol table
            self._ensure_symbol_exists(symbol)

            # Insert only missing dates
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
            return self._finish_log(log, "success", rows_synced=count)

        except VnstockServiceError as exc:
            return self._finish_log(log, "failed", error_message=str(exc))
        except Exception as exc:
            self.session.rollback()
            logger.exception("Backfill failed for %s", symbol)
            return self._finish_log(log, "failed", error_message=str(exc))

    def sync_daily_incremental(
        self, symbols: list[str] | None = None
    ) -> list[DataSyncLog]:
        """Update daily OHLCV for all active symbols (or a specified list).

        Fetches only data after the last date in DB for each symbol.
        """
        if symbols is None:
            # Get all active symbols
            active = self.session.exec(
                select(StockSymbol.symbol).where(StockSymbol.is_active == True)  # noqa: E712
            ).all()
            symbols = list(active)

        logs: list[DataSyncLog] = []
        today = date.today()

        for symbol in symbols:
            # Find last date in DB
            last_date_result = self.session.exec(
                select(col(StockOHLCVDaily.trading_date))
                .where(StockOHLCVDaily.symbol == symbol)
                .order_by(col(StockOHLCVDaily.trading_date).desc())
                .limit(1)
            ).first()

            if last_date_result is None:
                # No data yet, backfill last 30 days
                from datetime import timedelta

                start = today - timedelta(days=30)
            else:
                from datetime import timedelta

                start = last_date_result + timedelta(days=1)

            if start > today:
                continue  # Already up to date

            log = self.backfill_daily(symbol, start, today)
            logs.append(log)

        return logs

    # ------------------------------------------------------------------
    # Sync: Intraday OHLCV
    # ------------------------------------------------------------------

    def collect_intraday(
        self,
        symbol: str,
        interval: str = "1m",
        count_back: int = 300,
    ) -> DataSyncLog:
        """Collect intraday bars for a symbol."""
        log = self._create_log("intraday", symbol=symbol)

        try:
            df = self.svc.fetch_intraday(
                symbol, interval=interval, count_back=count_back
            )
            if df is None or df.empty:
                return self._finish_log(log, "success", rows_synced=0)

            self._ensure_symbol_exists(symbol)

            count = 0
            for _, row in df.iterrows():
                ts = self._parse_datetime(row.get("time", row.get("date", "")))
                if ts is None:
                    continue

                # Check for existing (upsert logic)
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
            return self._finish_log(log, "success", rows_synced=count)

        except VnstockServiceError as exc:
            return self._finish_log(log, "failed", error_message=str(exc))
        except Exception as exc:
            self.session.rollback()
            logger.exception("Intraday collection failed for %s", symbol)
            return self._finish_log(log, "failed", error_message=str(exc))

    # ------------------------------------------------------------------
    # Sync: Company Profile
    # ------------------------------------------------------------------

    def sync_company_profile(self, symbol: str) -> DataSyncLog:
        """Sync company profile/overview data."""
        log = self._create_log("profile", symbol=symbol)

        try:
            data = self.svc.fetch_company_overview(symbol)
            if not data:
                return self._finish_log(log, "failed", error_message="Empty response")

            self._ensure_symbol_exists(symbol)

            existing = self.session.get(CompanyProfile, symbol)
            if existing:
                existing.company_name = (
                    str(data.get("companyName", data.get("company_name", "")))
                    or existing.company_name
                )
                existing.short_name = (
                    str(data.get("shortName", data.get("short_name", "")))
                    or existing.short_name
                )
                existing.industry_name = (
                    str(data.get("industryName", data.get("industry_name", "")))
                    or existing.industry_name
                )
                existing.charter_capital = data.get(
                    "charterCapital", data.get("charter_capital")
                )
                existing.outstanding_shares = data.get(
                    "outstandingShare", data.get("outstanding_shares")
                )
                existing.market_cap = data.get("marketCap", data.get("market_cap"))
                existing.website = str(data.get("website", "")) or existing.website
                existing.description = (
                    str(data.get("companyProfile", data.get("description", "")))
                    or existing.description
                )
                existing.updated_at = datetime.now(UTC)
                self.session.add(existing)
            else:
                profile = CompanyProfile(
                    symbol=symbol,
                    company_name=str(
                        data.get("companyName", data.get("company_name", ""))
                    ),
                    short_name=str(data.get("shortName", data.get("short_name", ""))),
                    industry_name=str(
                        data.get("industryName", data.get("industry_name", ""))
                    ),
                    established_date=str(
                        data.get("establishedYear", data.get("established_date", ""))
                    ),
                    listed_date=str(
                        data.get("listingDate", data.get("listed_date", ""))
                    ),
                    charter_capital=data.get(
                        "charterCapital", data.get("charter_capital")
                    ),
                    outstanding_shares=data.get(
                        "outstandingShare", data.get("outstanding_shares")
                    ),
                    market_cap=data.get("marketCap", data.get("market_cap")),
                    website=str(data.get("website", "")),
                    description=str(
                        data.get("companyProfile", data.get("description", ""))
                    ),
                )
                self.session.add(profile)

            self.session.commit()
            return self._finish_log(log, "success", rows_synced=1)

        except VnstockServiceError as exc:
            return self._finish_log(log, "failed", error_message=str(exc))
        except Exception as exc:
            self.session.rollback()
            logger.exception("Profile sync failed for %s", symbol)
            return self._finish_log(log, "failed", error_message=str(exc))

    # ------------------------------------------------------------------
    # Sync: Financial Reports
    # ------------------------------------------------------------------

    def sync_financials(
        self,
        symbol: str,
        report_type: str = "income_statement",
        period: str = "quarterly",
    ) -> DataSyncLog:
        """Sync financial reports for a symbol."""
        log = self._create_log("financials", symbol=symbol)

        try:
            df = self.svc.fetch_financials(
                symbol, report_type=report_type, period=period
            )
            if df is None or df.empty:
                return self._finish_log(log, "success", rows_synced=0)

            self._ensure_symbol_exists(symbol)

            count = 0
            for _, row in df.iterrows():
                year = int(row.get("year", row.get("yearReport", 0)))
                quarter = row.get("quarter", row.get("lengthReport"))
                quarter_int = (
                    int(quarter) if quarter is not None and pd.notna(quarter) else None
                )

                # Check existing
                existing = self.session.exec(
                    select(FinancialReport)
                    .where(FinancialReport.symbol == symbol)
                    .where(FinancialReport.report_type == report_type)
                    .where(FinancialReport.period == period)
                    .where(FinancialReport.year == year)
                    .where(FinancialReport.quarter == quarter_int)
                ).first()

                row_data = row.to_dict()
                # Remove meta fields from the data payload
                for key in [
                    "year",
                    "yearReport",
                    "quarter",
                    "lengthReport",
                    "ticker",
                    "symbol",
                ]:
                    row_data.pop(key, None)

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
            return self._finish_log(log, "success", rows_synced=count)

        except VnstockServiceError as exc:
            return self._finish_log(log, "failed", error_message=str(exc))
        except Exception as exc:
            self.session.rollback()
            logger.exception("Financials sync failed for %s", symbol)
            return self._finish_log(log, "failed", error_message=str(exc))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _ensure_symbol_exists(
        self,
        symbol: str,
        organ_name: str | None = None,
        asset_type: str = "stock",
        exchange: str | None = None,
        lot_size: int = 100,
    ) -> None:
        """Ensure a symbol exists in stock_symbol before adding related records."""
        existing = self.session.get(StockSymbol, symbol)
        if not existing:
            sym = StockSymbol(
                symbol=symbol,
                organ_name=organ_name,
                exchange=exchange,
                asset_type=asset_type,
                lot_size=lot_size,
                is_active=True,
            )
            self.session.add(sym)
            self.session.commit()

    @staticmethod
    def _parse_date(value: object) -> date | None:
        """Parse various date formats to date object."""
        if isinstance(value, date):
            return value
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, pd.Timestamp):
            return value.date()
        if isinstance(value, str) and value:
            try:
                return datetime.strptime(value[:10], "%Y-%m-%d").date()
            except ValueError:
                return None
        return None

    @staticmethod
    def _parse_datetime(value: object) -> datetime | None:
        """Parse various datetime formats."""
        if isinstance(value, datetime):
            return value
        if isinstance(value, pd.Timestamp):
            return value.to_pydatetime()
        if isinstance(value, str) and value:
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
                try:
                    return datetime.strptime(value, fmt)
                except ValueError:
                    continue
        return None

    @staticmethod
    def _parse_float(value: object) -> float | None:
        """Parse various numeric formats safely to float."""
        if value is None or pd.isna(value):
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
