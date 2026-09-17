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
    FinancialReport,
    StockOHLCVDaily,
    StockOHLCVIntraday,
    StockSymbol,
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

    def _create_log(self, sync_type: str, symbol: str | None = None) -> DataSyncLog:
        """Create a sync log entry with status 'started'."""
        log = DataSyncLog(
            sync_type=sync_type,
            symbol=symbol,
            source=self.svc.source,
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

    def sync_symbols(self) -> DataSyncLog:
        """Sync all stock symbols to the database."""
        log = self._create_log("symbols")

        try:
            df = self.svc.fetch_all_symbols()
            if df is None or df.empty:
                return self._finish_log(log, "failed", error_message="Empty response")

            count = 0
            for _, row in df.iterrows():
                symbol_str = str(row.get("ticker", row.get("symbol", "")))
                if not symbol_str:
                    continue

                existing = self.session.get(StockSymbol, symbol_str)
                if existing:
                    existing.organ_name = (
                        str(row.get("organName", row.get("organ_name", "")))
                        or existing.organ_name
                    )
                    existing.exchange = str(
                        row.get("exchange", existing.exchange or "")
                    )
                    existing.updated_at = datetime.now(UTC)
                    self.session.add(existing)
                else:
                    sym = StockSymbol(
                        symbol=symbol_str,
                        organ_name=str(row.get("organName", row.get("organ_name", ""))),
                        exchange=str(row.get("exchange", "")),
                        industry=str(row.get("industry", row.get("icbName", ""))),
                        asset_type=str(row.get("type", "stock")),
                    )
                    self.session.add(sym)
                count += 1

            self.session.commit()
            logger.info("Synced %d symbols", count)
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
