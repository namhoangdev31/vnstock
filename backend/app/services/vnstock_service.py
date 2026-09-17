"""VnstockService — wrapper around the vnstock library.

Provides a clean interface for fetching stock data with:
- Modern vnstock API adapters (Quote, Listing, Company, Finance, Retail)
- Automatic source fallback (TCBS → VCI → KBS)
- Rate limiting between external requests (anti-ban, AGENTS §7.2)
- Error handling and logging
- DataFrame → dict conversion for API responses
"""

import logging
from datetime import date

import pandas as pd
from vnstock import Company, Finance, Listing, Quote, Retail , Trading

from app.core.config import settings
from app.services.rate_limit import RateLimiter

logger = logging.getLogger(__name__)


class VnstockServiceError(Exception):
    """Raised when vnstock API call fails on all sources."""


class VnstockService:
    """Wrap vnstock library with fallback source + error handling."""

    def __init__(
        self,
        source: str | None = None,
        fallback_source: str | None = None,
        tertiary_source: str | None = None,
        limiter: RateLimiter | None = None,
    ) -> None:
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
        """Ordered, de-duplicated list of sources to try.

        Not every vnstock adapter accepts every source (e.g. ``Listing`` rejects
        TCBS). The per-source ``try/except`` in each fetch method skips any
        source a given adapter does not support, so configuring a source the
        adapter rejects is harmless — it simply falls through to the next one.
        """
        ordered = [self.source, self.fallback_source, self.tertiary_source]
        seen: dict[str, None] = {}
        for s in ordered:
            if s and s not in seen:
                seen[s] = None
        return list(seen)

    def _throttle(self) -> None:
        """Enforce the minimum inter-request delay before an external call."""
        self._limiter.wait()

    # --- Public Methods ---

    def fetch_all_symbols(self) -> pd.DataFrame:
        """Fetch list of all stock symbols."""
        for src in self.sources:
            try:
                self._throttle()
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
                self._throttle()
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
                self._throttle()
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
                self._throttle()
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
                self._throttle()
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

    # --- New Phase 1 Methods ---

    def fetch_group_symbols(self, group: str = "VN30") -> list[str]:
        """Fetch the constituent symbols of an index group (e.g. VN30).

        ``Listing.symbols_by_group`` returns a ``pandas.Series`` of tickers. Only
        KBS/VCI/MSN support the Listing adapter, so unsupported sources in the
        configured chain fall through naturally.
        """
        for src in self.sources:
            try:
                self._throttle()
                lst = Listing(source=src, show_log=False)
                result = lst.symbols_by_group(group=group.upper())
                symbols = self._series_to_symbols(result)
                if symbols:
                    logger.info(
                        "Fetched %d symbols for group %s via %s",
                        len(symbols),
                        group,
                        src,
                    )
                    return symbols
            except Exception:
                logger.warning(
                    "Group symbols for %s failed on %s", group, src, exc_info=True
                )
                continue

        raise VnstockServiceError(f"Failed to fetch symbols for group {group}")

    @staticmethod
    def _series_to_symbols(result: object) -> list[str]:
        """Normalize a Series/list/Series-like result to a list of tickers."""
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

    def fetch_gold_prices(self, date_str: str | None = None) -> pd.DataFrame:
        """Fetch SJC domestic gold prices (buy/sell) via the Retail layer.

        Returns a DataFrame with columns: name, branch, buy_price, sell_price,
        date — or an empty DataFrame if the source is unavailable.
        """
        try:
            self._throttle()
            retail = Retail()
            df = retail.gold(source="sjc", date=date_str)
            if df is not None and not df.empty:
                logger.info("Fetched %d gold price rows", len(df))
                return df
        except Exception:
            logger.warning("Gold price fetch failed", exc_info=True)
        return pd.DataFrame()

    def fetch_exchange_rate(self, date_str: str = "") -> pd.DataFrame:
        """Fetch USD/VND exchange rates (Vietcombank) via the Retail layer.

        Returns a DataFrame with columns: currency_code, currency_name,
        buy_cash, buy_transfer, sell, date — or an empty DataFrame.
        """
        try:
            self._throttle()
            retail = Retail()
            df = retail.exchange_rate(date=date_str)
            if df is not None and not df.empty:
                logger.info("Fetched %d exchange-rate rows", len(df))
                return df
        except Exception:
            logger.warning("Exchange-rate fetch failed", exc_info=True)
        return pd.DataFrame()

    def fetch_tick_orderflow(
        self,
        symbol: str,
        page_size: int = 100,
    ) -> pd.DataFrame:
        """Fetch tick-by-tick matched trades and classify aggressive flow.

        Uses ``Quote.intraday``. vnstock normalizes the aggressor side into a
        ``match_type`` column with values ``Buy`` / ``Sell`` (plus ``ATO`` /
        ``ATC`` / ``unknown`` for auction & unlabeled prints). Returns the raw
        standardized frame: time, price, volume, match_type, id. Aggregation to
        per-minute buy/sell delta is performed downstream by the sync layer so
        the classification logic stays single-sourced.

        Raises:
            VnstockServiceError: when every configured source fails. An empty
                DataFrame is returned by vnstock for legitimately empty windows
                and is passed through (TEST-EXT-03).
        """
        for src in self.sources:
            try:
                self._throttle()
                q = Quote(symbol=symbol, source=src, show_log=False)
                df = q.intraday(symbol=symbol, page_size=page_size)
                if df is not None:
                    logger.info(
                        "Fetched %d tick records for %s via %s",
                        len(df),
                        symbol,
                        src,
                    )
                    return df
            except Exception:
                logger.warning(
                    "Tick orderflow for %s failed on %s", symbol, src, exc_info=True
                )
                continue

        raise VnstockServiceError(f"Failed to fetch tick orderflow for {symbol}")


# Singleton instance
vnstock_service = VnstockService()
