"""Market data polling orchestration for the autonomous quant daemon.

TRD §4.1 — Rate-limiting & Retry:
  - 250 ms mandatory delay between consecutive API requests (anti-ban).
  - Per-request retry with exponential + jitter backoff:
      t_sleep = min(10, 0.5 * 2^attempt + uniform(0, 1))
  - Maximum 3 retry attempts per fetch call.
  - Smart rate-limit backoff: when vnai returns a rate-limit error with an
    explicit "Chờ X giây" / "Wait X seconds" hint, use that duration directly
    instead of the generic jitter backoff.  This avoids burning retries on
    requests that are guaranteed to fail until the quota window resets.

TRD §4.2 — Circuit Breaker Fallback:
  - When circuit breaker is OPEN, return the most recent cached result
    (last successful poll) instead of an empty result.  This ensures the
    downstream Ensemble Engine always has *some* data to work with.
"""

import logging
import random
import re
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


# Regex to extract the vnai-recommended wait duration from rate-limit messages.
# vnai prints both Vietnamese ("Chờ X giây") and English ("Wait X seconds") hints.
_RATE_LIMIT_WAIT_RE = re.compile(
    r"(?:Ch[oờ\u1edd]+|Wait(?:\s+to\s+retry)?)\s+(\d+)\s*(?:gi[aâ]y|seconds?)",
    re.IGNORECASE,
)
# Maximum wait we will honour in a single sleep inside _fetch_with_retry.
# Waits longer than this are deferred to the circuit-breaker OPEN phase.
_MAX_INLINE_WAIT_S: float = 65.0


def _parse_rate_limit_wait_s(exc: SystemExit) -> float | None:
    """Return the explicit wait seconds from a vnai rate-limit SystemExit, or None.

    vnai prints the banner to stdout **and** embeds the wait duration in the
    exception args.  We search both the str representation of the args and the
    full rendered banner captured in the process stdout buffer (not accessible
    here), so we rely on the args string only.
    """
    text = " ".join(str(a) for a in exc.args)
    m = _RATE_LIMIT_WAIT_RE.search(text)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            pass
    return None


def _fetch_with_retry(fn, label: str) -> Any:
    """Call *fn()* up to _MAX_RETRY_ATTEMPTS times with jittered backoff.

    Returns the function result on success, or None after all attempts fail.
    A 250 ms inter-request delay is inserted *before* every attempt (including
    the first) to comply with TRD §4.1 anti-ban policy.

    Rate-limit handling (smart backoff):
      vnai raises RateLimitExceeded which triggers sys.exit() inside a
      CleanErrorContext.__exit__, producing a SystemExit.  SystemExit is a
      BaseException (not Exception), so we explicitly catch it here and convert
      it to a plain RuntimeError so the circuit breaker can handle the failure
      without letting SystemExit propagate and kill the server.

      When vnai embeds an explicit wait hint ("Chờ X giây" / "Wait X seconds")
      in the exception message, we honour it directly.  If the recommended wait
      exceeds _MAX_INLINE_WAIT_S we give up immediately (the circuit breaker
      will open and enforce the longer back-off).
    """
    last_exc: BaseException | None = None
    for attempt in range(_MAX_RETRY_ATTEMPTS):
        # Mandatory 250 ms rate-limit delay before every API request.
        time.sleep(_REQUEST_DELAY_S)
        try:
            return fn()
        except SystemExit as exc:
            # vnai calls sys.exit() on RateLimitExceeded — convert to a
            # regular exception so the daemon can handle it gracefully.
            rate_err = RuntimeError(
                f"[rate-limit] vnstock API rate limit reached (sys.exit intercepted): {exc}"
            )
            last_exc = rate_err

            # Use the explicit wait hint from vnai if available.
            suggested_wait = _parse_rate_limit_wait_s(exc)
            if suggested_wait is not None:
                if suggested_wait > _MAX_INLINE_WAIT_S:
                    # Wait too long to block here — abort retries immediately
                    # and let the circuit breaker handle the recovery.
                    logger.warning(
                        f"[poller] {label} attempt {attempt + 1}/{_MAX_RETRY_ATTEMPTS} "
                        f"rate-limited; vnai requests {suggested_wait:.0f}s wait "
                        f"(> {_MAX_INLINE_WAIT_S:.0f}s limit) — aborting retries."
                    )
                    break
                sleep_s = suggested_wait
                logger.warning(
                    f"[poller] {label} attempt {attempt + 1}/{_MAX_RETRY_ATTEMPTS} "
                    f"rate-limited; honouring vnai hint: waiting {sleep_s:.0f}s before retry."
                )
            else:
                sleep_s = _jittered_backoff(attempt)
                logger.warning(
                    f"[poller] {label} attempt {attempt + 1}/{_MAX_RETRY_ATTEMPTS} "
                    f"rate-limited (sys.exit). Waiting {sleep_s:.2f}s before retry."
                )
            time.sleep(sleep_s)
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
            # Overnight/post-market: dùng nến ngày (1D) để phân tích T+1
            result.history_bars = self._fetch_history(symbol, limit_history, interval="1D")

        # Update last-known cache on every successful (non-error) poll.
        if not result.errors:
            self._last_known[symbol] = result

        return result

    # ------------------------------------------------------------------
    # Private fetch helpers — each uses _fetch_with_retry for TRD §4.1
    # ------------------------------------------------------------------

    def _fetch_history(self, symbol: str, limit: int, interval: str = "1m") -> list[Any]:
        """Fetch historical bars via VnstockService with retry + rate-limit.

        interval: '1m' cho giao dịch intraday, '1D' cho phân tích overnight/T+1.
        """
        from app.domains.market_data.infrastructure.vnstock_adapter import (
            vnstock_service,
        )

        today: date = datetime.now(VN_TZ).date()
        if interval == "1D":
            # Nến ngày: start đủ rộng để lấy `limit` ngày giao dịch (bù nghỉ lễ/cuối tuần)
            start: date = today - timedelta(days=max(limit * 2, 180))
        else:
            # Nến phút: start trong ngày hôm nay là đủ
            start = today - timedelta(days=max(limit * 2, 60))

        def _call() -> list[Any]:
            df = vnstock_service.fetch_price_history(
                symbol=symbol,
                start=start,
                end=today,
                count=limit,
                interval=interval,
            )
            if df is not None and not df.empty:
                return df.to_dict("records")
            return []

        result = _fetch_with_retry(_call, label=f"history:{symbol}:{interval}")
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
