"""DataSyncManager — orchestrates data synchronization from vnstock → PostgreSQL.

3 sync modes:
1. Historical Backfill  — one-time full data import
2. Incremental Daily    — daily update after market close
3. Intraday Collector   — realtime bar collection during trading session
"""

import logging
from datetime import UTC, date, datetime

import pandas as pd
from sqlmodel import Session, col, select

from app.models.models_stock import (
    CompanyProfile,
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
        self.session.commit()
        self.session.refresh(log)
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
        self.session.refresh(log)
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
            if deriv_df is not None and not deriv_df.empty:
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
        except Exception as exc:
            logger.warning("Could not fetch extra derivatives list: %s", exc)

        return count

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

                batch_size = 1000
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

            # Sync VN30 group & Derivatives
            self._sync_vn30_group()
            deriv_count = self._sync_derivatives()
            count += deriv_count

            self.session.commit()
            logger.info(
                "Synced %d symbols (including %d derivatives)", count, deriv_count
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

    def _ensure_symbol_exists(self, symbol: str) -> None:
        """Ensure a symbol record exists in stock_symbol table."""
        existing = self.session.get(StockSymbol, symbol)
        if not existing:
            sym = StockSymbol(
                symbol=symbol,
                asset_type="stock",  # default, will be updated on next symbols sync
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
