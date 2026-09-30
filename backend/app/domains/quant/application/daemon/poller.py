"""Market data polling orchestration for the autonomous quant daemon.

TRD §4.1 — Rate-limiting & Retry:
  - 250 ms mandatory delay between consecutive API requests (anti-ban).
  - Per-request retry with exponential + jitter backoff:
      t_sleep = min(10, 0.5 * 2^attempt + uniform(0, 1))
  - Maximum 3 retry attempts per fetch call.

TRD §4.2 — Circuit Breaker Fallback:
  - When circuit breaker is OPEN, return the most recent cached result
    (last successful poll) instead of an empty result.  This ensures the
    downstream Ensemble Engine always has *some* data to work with.
"""

import logging
import random
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any

from app.core.enums import SessionPhase
from app.core.models_base import VN_TZ
from app.domains.quant.application.daemon.state import DaemonCircuitBreaker

logger = logging.getLogger(__name__)

# TRD §4.1 — mandatory inter-request delay (seconds)
_REQUEST_DELAY_S: float = 0.25

# TRD §4.1 — retry parameters
_MAX_RETRY_ATTEMPTS: int = 3
_RETRY_BASE_S: float = 0.5
_RETRY_MAX_S: float = 10.0


@dataclass
class MarketPollResult:
    """Phase-aware polling result from market data extraction."""

    symbol: str
    phase: SessionPhase
    timestamp: datetime
    history_bars: list[Any] = field(default_factory=list)
    intraday_bars: list[Any] = field(default_factory=list)
    order_flow: list[Any] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    # Set to True when result was served from the last-known-data cache.
    from_cache: bool = False


def _jittered_backoff(attempt: int) -> float:
    """Compute t_sleep = min(MAX, BASE * 2^attempt + uniform(0, 1)) per TRD §4.1."""
    jitter = random.uniform(0.0, 1.0)
    return min(_RETRY_MAX_S, _RETRY_BASE_S * (2**attempt) + jitter)


def _fetch_with_retry(fn, label: str) -> Any:
    """Call *fn()* up to _MAX_RETRY_ATTEMPTS times with jittered backoff.

    Returns the function result on success, or None after all attempts fail.
    A 250 ms inter-request delay is inserted *before* every attempt (including
    the first) to comply with TRD §4.1 anti-ban policy.
    """
    last_exc: Exception | None = None
    for attempt in range(_MAX_RETRY_ATTEMPTS):
        # Mandatory 250 ms rate-limit delay before every API request.
        time.sleep(_REQUEST_DELAY_S)
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            sleep_s = _jittered_backoff(attempt)
            logger.warning(
                f"[poller] {label} attempt {attempt + 1}/{_MAX_RETRY_ATTEMPTS} "
                f"failed: {exc}. Retrying in {sleep_s:.2f}s"
            )
            time.sleep(sleep_s)

    logger.error(
        f"[poller] {label} exhausted {_MAX_RETRY_ATTEMPTS} attempts: {last_exc}"
    )
    return None


class MarketDataPoller:
    """Orchestrates market data extraction from Vnstock API with phase awareness.

    Implements TRD §4.1 (rate-limiting + jittered retry) and TRD §4.2
    (last-known-data fallback when the circuit breaker is OPEN).
    """

    def __init__(self, circuit_breaker: DaemonCircuitBreaker) -> None:
        self.circuit_breaker = circuit_breaker
        self._vnstock_service = None
        # TRD §4.2 — in-memory cache: last successful result per symbol.
        self._last_known: dict[str, MarketPollResult] = {}

    def poll(
        self,
        symbol: str,
        phase: SessionPhase,
        limit_history: int = 120,
        limit_intraday: int = 50,
        limit_orderflow: int = 40,
    ) -> MarketPollResult:
        """Poll market data based on current session phase.

        When the circuit breaker is OPEN (TRD §4.2), returns the most recent
        cached result for *symbol* rather than an empty payload.
        """
        now = datetime.now(VN_TZ)

        # TRD §4.2 — circuit breaker OPEN → return last known data
        if self.circuit_breaker.is_open:
            cached = self._last_known.get(symbol)
            if cached is not None:
                logger.info(
                    f"[poller] CB OPEN — serving last-known data for {symbol} "
                    f"(cached at {cached.timestamp.isoformat()})"
                )
                # Return a copy tagged as from_cache so callers can act on it.
                return MarketPollResult(
                    symbol=symbol,
                    phase=phase,
                    timestamp=now,
                    history_bars=cached.history_bars,
                    intraday_bars=cached.intraday_bars,
                    order_flow=cached.order_flow,
                    from_cache=True,
                    errors=[
                        {
                            "error": "circuit_breaker_open",
                            "reason": "Circuit breaker is OPEN — returning cached data",
                        }
                    ],
                )

            # No cache available yet — surface the CB state explicitly.
            return MarketPollResult(
                symbol=symbol,
                phase=phase,
                timestamp=now,
                errors=[
                    {
                        "error": "circuit_breaker_open",
                        "reason": "Circuit breaker is OPEN, no cached data available",
                    }
                ],
            )

        result = MarketPollResult(symbol=symbol, phase=phase, timestamp=now)

        # Phase-aware polling
        if phase in (
            SessionPhase.MORNING_CONTINUOUS,
            SessionPhase.AFTERNOON_CONTINUOUS,
            SessionPhase.ATO,
            SessionPhase.ATC,
        ):
            # Active trading: fetch full data
            result.history_bars = self._fetch_history(symbol, limit_history)
            result.intraday_bars = self._fetch_intraday(symbol, limit_intraday)
            result.order_flow = self._fetch_order_flow(symbol, limit_orderflow)
        elif phase in (
            SessionPhase.PRE_ATO,
            SessionPhase.PRE_ATC,
            SessionPhase.MIDDAY_INTERMISSION,
        ):
            # Pre-market or intermission: history only
            result.history_bars = self._fetch_history(symbol, limit_history)
        elif phase in (SessionPhase.POST_MARKET, SessionPhase.OVERNIGHT_SIMULATION):
            # Post-market/overnight: minimal polling for next-day analysis
            result.history_bars = self._fetch_history(symbol, min(limit_history, 30))

        # Update last-known cache on every successful (non-error) poll.
        if not result.errors:
            self._last_known[symbol] = result

        return result

    # ------------------------------------------------------------------
    # Private fetch helpers — each uses _fetch_with_retry for TRD §4.1
    # ------------------------------------------------------------------

    def _fetch_history(self, symbol: str, limit: int) -> list[Any]:
        """Fetch historical bars via VnstockService with retry + rate-limit."""
        from app.domains.market_data.infrastructure.vnstock_adapter import (
            vnstock_service,
        )

        today: date = datetime.now(VN_TZ).date()
        start: date = today - timedelta(days=max(limit * 2, 60))

        def _call() -> list[Any]:
            df = vnstock_service.fetch_price_history(
                symbol=symbol,
                start=start,
                end=today,
                count=limit,
                interval="1m",
            )
            if df is not None and not df.empty:
                return df.to_dict("records")
            return []

        result = _fetch_with_retry(_call, label=f"history:{symbol}")
        return result if result is not None else []

    def _fetch_intraday(self, symbol: str, limit: int) -> list[Any]:
        """Fetch intraday bars via VnstockService with retry + rate-limit."""
        from app.domains.market_data.infrastructure.vnstock_adapter import (
            vnstock_service,
        )

        def _call() -> list[Any]:
            df = vnstock_service.fetch_intraday(
                symbol=symbol,
                interval="1m",
                count_back=limit,
            )
            if df is not None and not df.empty:
                return df.to_dict("records")
            return []

        result = _fetch_with_retry(_call, label=f"intraday:{symbol}")
        return result if result is not None else []

    def _fetch_order_flow(self, symbol: str, limit: int) -> list[Any]:
        """Fetch tick-level order flow (Aggressive Buy/Sell) via VnstockService."""
        from app.domains.market_data.infrastructure.vnstock_adapter import (
            vnstock_service,
        )

        def _call() -> list[Any]:
            df = vnstock_service.fetch_tick_orderflow(symbol=symbol, page_size=limit)
            if df is not None and not df.empty:
                return df.to_dict("records")
            return []

        result = _fetch_with_retry(_call, label=f"orderflow:{symbol}")
        return result if result is not None else []
