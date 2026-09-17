"""VnstockService — wrapper around the vnstock library.

Provides a clean interface for fetching stock data with:
- Modern vnstock API adapters (Quote, Listing, Company, Finance)
- Automatic source fallback (TCBS → VCI)
- Error handling and logging
- DataFrame → dict conversion for API responses
"""

import logging
from datetime import date

import pandas as pd
from vnstock import Company, Finance, Listing, Quote

from app.core.config import settings

logger = logging.getLogger(__name__)


class VnstockServiceError(Exception):
    """Raised when vnstock API call fails on all sources."""


class VnstockService:
    """Wrap vnstock library with fallback source + error handling."""

    def __init__(
        self,
        source: str | None = None,
        fallback_source: str | None = None,
    ) -> None:
        self.source = (source or settings.VNSTOCK_SOURCE).lower()
        self.fallback_source = (
            fallback_source or settings.VNSTOCK_FALLBACK_SOURCE
        ).lower()

    @property
    def sources(self) -> list[str]:
        """Ordered list of sources to try."""
        return [self.source, self.fallback_source]

    # --- Public Methods ---

    def fetch_all_symbols(self) -> pd.DataFrame:
        """Fetch list of all stock symbols."""
        for src in self.sources:
            try:
                lst = Listing(source=src, show_log=False)
                df = lst.all_symbols()
                if df is not None and not df.empty:
                    logger.info("Fetched %d symbols via %s", len(df), src)
                    return df
            except Exception:
                logger.warning(
                    "Primary source %s failed for symbols, trying fallback",
                    src,
                    exc_info=True,
                )
                continue

        raise VnstockServiceError("Failed to fetch symbols from all sources")

    def fetch_price_history(
        self,
        symbol: str,
        start: date,
        end: date,
        interval: str = "1D",
    ) -> pd.DataFrame:
        """Fetch historical OHLCV data.

        Args:
            symbol: Stock symbol (e.g. "VNM", "VN30F1M")
            start: Start date
            end: End date
            interval: "1m", "5m", "15m", "1H", "1D"

        Returns:
            DataFrame with columns: time, open, high, low, close, volume
        """
        for src in self.sources:
            try:
                q = Quote(symbol=symbol, source=src, show_log=False)
                df = q.history(
                    start=start.strftime("%Y-%m-%d"),
                    end=end.strftime("%Y-%m-%d"),
                    interval=interval,
                )
                if df is not None and not df.empty:
                    logger.info(
                        "Fetched %d price records for %s (%s-%s, %s) via %s",
                        len(df),
                        symbol,
                        start,
                        end,
                        interval,
                        src,
                    )
                    return df
            except Exception:
                logger.warning(
                    "Price history for %s failed on %s", symbol, src, exc_info=True
                )
                continue

        raise VnstockServiceError(f"Failed to fetch price history for {symbol}")

    def fetch_company_overview(self, symbol: str) -> dict:
        """Fetch company overview/profile."""
        for src in self.sources:
            try:
                c = Company(symbol=symbol, source=src, show_log=False)
                df = c.overview()
                if df is not None and not df.empty:
                    return df.iloc[0].to_dict()
            except Exception:
                logger.warning(
                    "Company overview for %s failed on %s", symbol, src, exc_info=True
                )
                continue

        raise VnstockServiceError(f"Failed to fetch company overview for {symbol}")

    def fetch_financials(
        self,
        symbol: str,
        report_type: str = "income_statement",
        period: str = "quarterly",
    ) -> pd.DataFrame:
        """Fetch financial statements.

        Args:
            symbol: Stock symbol
            report_type: "income_statement", "balance_sheet", "cash_flow"
            period: "quarterly" or "annual"
        """
        period_clean = "quarter" if "quarter" in period else "annual"

        for src in self.sources:
            try:
                f = Finance(
                    symbol=symbol,
                    source=src,
                    period=period_clean,
                    show_log=False,
                )
                method_map = {
                    "income_statement": f.income_statement,
                    "balance_sheet": f.balance_sheet,
                    "cash_flow": f.cash_flow,
                }
                fetch_fn = method_map.get(report_type)
                if fetch_fn is None:
                    raise ValueError(f"Unknown report_type: {report_type}")

                df = fetch_fn(period=period_clean)
                if df is not None and not df.empty:
                    logger.info(
                        "Fetched %d financial records for %s (%s/%s) via %s",
                        len(df),
                        symbol,
                        report_type,
                        period,
                        src,
                    )
                    return df
            except VnstockServiceError:
                raise
            except Exception:
                logger.warning(
                    "Financials for %s failed on %s", symbol, src, exc_info=True
                )
                continue

        raise VnstockServiceError(f"Failed to fetch financials for {symbol}")

    def fetch_intraday(
        self,
        symbol: str,
        interval: str = "1m",
        count_back: int = 300,
    ) -> pd.DataFrame:
        """Fetch recent intraday data.

        Args:
            symbol: Stock symbol
            interval: "1m", "5m", "15m"
            count_back: Number of bars to fetch
        """
        for src in self.sources:
            try:
                q = Quote(symbol=symbol, source=src, show_log=False)
                df = q.history(
                    interval=interval,
                    count_back=count_back,
                )
                if df is not None and not df.empty:
                    logger.info(
                        "Fetched %d intraday records for %s (%s) via %s",
                        len(df),
                        symbol,
                        interval,
                        src,
                    )
                    return df
            except Exception:
                logger.warning(
                    "Intraday for %s failed on %s", symbol, src, exc_info=True
                )
                continue

        raise VnstockServiceError(f"Failed to fetch intraday data for {symbol}")


# Singleton instance
vnstock_service = VnstockService()
