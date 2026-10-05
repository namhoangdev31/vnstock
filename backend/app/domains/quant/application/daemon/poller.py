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

from app.core.config import settings
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
    history_bars: list[Any] | None = field(default_factory=list)
    intraday_bars: list[Any] | None = field(default_factory=list)
    order_flow: list[Any] | None = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    # Set to True when result was served from the last-known-data cache.
    from_cache: bool = False
    # Market context: spot_price (VN30), institutional flows, breadth, macro.
    # Populated by _fetch_market_snapshot() and passed into AnalysisContext.
    market_snapshot: dict[str, Any] = field(default_factory=dict)


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
    """Call *fn()* up to _MAX_RETRY_ATTEMPTS times with jittered backoff (sync).

    NOTE: This function uses blocking time.sleep(). It MUST be called from
    asyncio.to_thread() in an async context to avoid blocking the event loop.

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

    def __init__(
        self,
        circuit_breaker: DaemonCircuitBreaker,
        cache_ttl_seconds: float | None = None,
        session_factory: Any | None = None,
    ) -> None:
        self.circuit_breaker = circuit_breaker
        self.cache_ttl_seconds = float(
            settings.VNSTOCK_REALTIME_CACHE_TTL
            if cache_ttl_seconds is None
            else cache_ttl_seconds
        )
        self._vnstock_service = None
        self.session_factory = session_factory
        # TRD §4.2 — in-memory cache: last successful result per symbol.
        self._last_known: dict[str, MarketPollResult] = {}
        # Cache for market snapshot — refreshed at most once per cycle (60s TTL).
        self._snapshot_cache: dict[str, Any] | None = None
        self._snapshot_cache_at: datetime | None = None
        self._SNAPSHOT_TTL_S: float = 60.0

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

        cached = self._last_known.get(symbol)
        cache_age = (
            (now - cached.timestamp).total_seconds() if cached is not None else None
        )

        # TRD §4.2 — circuit breaker OPEN → return last known data
        if self.circuit_breaker.is_open:
            if (
                cached is not None
                and cache_age is not None
                and cache_age <= self.cache_ttl_seconds
            ):
                stale_threshold_s = 300.0  # 5 minutes
                is_stale = cache_age > stale_threshold_s
                logger.info(
                    "[poller] CB OPEN — serving %sdata for %s (cached at %s, age=%.0fs)",
                    "STALE " if is_stale else "",
                    symbol,
                    cached.timestamp.isoformat(),
                    cache_age,
                )
                # Return a copy tagged as from_cache so callers can act on it.
                return MarketPollResult(
                    symbol=symbol,
                    phase=phase,
                    timestamp=now,
                    history_bars=cached.history_bars,
                    intraday_bars=cached.intraday_bars,
                    order_flow=cached.order_flow,
                    market_snapshot=cached.market_snapshot,
                    from_cache=True,
                    metadata={
                        "cache_age_seconds": cache_age,
                        "_stale": is_stale,
                        "_age_seconds": cache_age,
                    },
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
                        "error": "cache_expired"
                        if cached is not None
                        else "circuit_breaker_open",
                        "reason": "Circuit breaker is OPEN and no fresh cached data is available",
                    }
                ],
            )

        probe_started = False
        if self.circuit_breaker.is_half_open:
            probe_started = self.circuit_breaker.try_start_probe()
            if not probe_started:
                if (
                    cached is not None
                    and cache_age is not None
                    and cache_age <= self.cache_ttl_seconds
                ):
                    return MarketPollResult(
                        symbol=symbol,
                        phase=phase,
                        timestamp=now,
                        history_bars=cached.history_bars,
                        intraday_bars=cached.intraday_bars,
                        order_flow=cached.order_flow,
                        market_snapshot=cached.market_snapshot,
                        from_cache=True,
                        metadata={"cache_age_seconds": cache_age},
                        errors=[{"error": "circuit_breaker_probe_in_progress"}],
                    )
                return MarketPollResult(
                    symbol=symbol,
                    phase=phase,
                    timestamp=now,
                    errors=[{"error": "circuit_breaker_probe_in_progress"}],
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
            if result.history_bars is None:
                result.errors.append(
                    {"error": "history_fetch_failed", "symbol": symbol}
                )
            if result.intraday_bars is None:
                result.errors.append(
                    {"error": "intraday_fetch_failed", "symbol": symbol}
                )
            if result.order_flow is None:
                result.errors.append(
                    {"error": "orderflow_fetch_failed", "symbol": symbol}
                )
            # Fetch market snapshot (spot price, institutional flows, breadth, macro)
            result.market_snapshot = self._fetch_market_snapshot(now)
        elif phase in (
            SessionPhase.PRE_ATO,
            SessionPhase.PRE_ATC,
            SessionPhase.MIDDAY_INTERMISSION,
        ):
            # Pre-market or intermission: history only
            result.history_bars = self._fetch_history(symbol, limit_history)
            if result.history_bars is None:
                result.errors.append(
                    {"error": "history_fetch_failed", "symbol": symbol}
                )
            result.market_snapshot = self._fetch_market_snapshot(now)
        elif phase in (SessionPhase.POST_MARKET, SessionPhase.OVERNIGHT_SIMULATION):
            # Overnight/post-market: dùng nến ngày (1D) để phân tích T+1
            result.history_bars = self._fetch_history(
                symbol, limit_history, interval="1D"
            )
            if result.history_bars is None:
                result.errors.append(
                    {"error": "history_fetch_failed", "symbol": symbol}
                )
            result.market_snapshot = self._fetch_market_snapshot(now)

        # Update last-known cache on every successful (non-error) poll.
        if not result.errors:
            self._last_known[symbol] = result

        if probe_started:
            self.circuit_breaker.finish_probe(not result.errors)

        return result

    # ------------------------------------------------------------------
    # Private fetch helpers — each uses _fetch_with_retry for TRD §4.1
    # ------------------------------------------------------------------

    def _fetch_history(
        self, symbol: str, limit: int, interval: str = "1m"
    ) -> list[Any] | None:
        """Fetch historical bars via VnstockService with retry + rate-limit.

        interval: '1m' cho giao dịch intraday, '1D' cho phân tích overnight/T+1.
        """
        from app.domains.market_data.infrastructure.vnstock import (
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
        return result

    def _fetch_intraday(self, symbol: str, limit: int) -> list[Any] | None:
        """Fetch intraday bars via VnstockService with retry + rate-limit."""
        from app.domains.market_data.infrastructure.vnstock import (
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
        return result

    def _fetch_order_flow(self, symbol: str, limit: int) -> list[Any] | None:
        """Fetch tick-level order flow (Aggressive Buy/Sell) via VnstockService."""
        from app.domains.market_data.infrastructure.vnstock import (
            vnstock_service,
        )

        def _call() -> list[Any]:
            df = vnstock_service.fetch_tick_orderflow(symbol=symbol, page_size=limit)
            if df is not None and not df.empty:
                return df.to_dict("records")
            return []

        result = _fetch_with_retry(_call, label=f"orderflow:{symbol}")
        return result

    def _fetch_market_snapshot(self, as_of: datetime) -> dict[str, Any]:
        """Fetch market context for Engine 2 and Engine 3.

        Returns a dict with:
          - spot_price: float — VN30 index price (for basis calculation in Engine 3)
          - flows: list[dict] — InstitutionalFlow records from DB (Engine 2)
          - breadth: dict | None — MarketBreadth record from DB (Engine 2)
          - macro: list[dict] — MacroIndicator records from DB (Engine 2)

        Uses a 60-second in-memory cache so that multiple symbols polled
        within the same daemon cycle share the same snapshot (avoids N DB
        round-trips per cycle).
        """
        # 60s in-memory cache — shared across all symbols in a cycle
        if (
            self._snapshot_cache is not None
            and self._snapshot_cache_at is not None
            and (as_of - self._snapshot_cache_at).total_seconds() < self._SNAPSHOT_TTL_S
        ):
            return self._snapshot_cache

        snapshot: dict[str, Any] = {
            "spot_price": 0.0,
            "flows": [],
            "breadth": None,
            "macro": [],
        }

        # ---- Spot price: VN30 index last close ----
        try:
            from app.domains.market_data.infrastructure.vnstock import (
                vnstock_service,
            )

            today = as_of.date()
            from datetime import timedelta

            start = today - timedelta(days=5)
            # Use 1m history for VN30 index — gives latest intraday spot
            df_spot = vnstock_service.fetch_price_history(
                symbol="VN30",
                start=start,
                end=today,
                count=3,
                interval="1m",
            )
            if df_spot is not None and not df_spot.empty:
                close_col = next(
                    (c for c in ("close", "Close", "CLOSE") if c in df_spot.columns),
                    None,
                )
                if close_col:
                    snapshot["spot_price"] = float(df_spot[close_col].iloc[-1])
        except Exception as exc:
            logger.debug("[poller] VN30 spot fetch failed: %s", exc)

        # ---- DB-sourced data: flows, breadth, macro ----
        if self.session_factory is not None:
            try:
                from sqlmodel import col, select

                from app.domains.quant.domain.models import (
                    InstitutionalFlow,
                    MacroIndicator,
                    MarketBreadth,
                )

                with self.session_factory() as session:
                    # Institutional flows: last 10 trading days for momentum calc
                    flows = session.exec(
                        select(InstitutionalFlow)
                        .order_by(col(InstitutionalFlow.trading_date).desc())
                        .limit(10)
                    ).all()
                    snapshot["flows"] = [
                        {
                            "trading_date": f.trading_date,
                            "foreign_net_value": f.foreign_net_value,
                            "prop_net_value": f.prop_net_value,
                        }
                        for f in flows
                    ]

                    # Market breadth: most recent record
                    breadth = session.exec(
                        select(MarketBreadth)
                        .order_by(col(MarketBreadth.trading_date).desc())
                        .limit(1)
                    ).first()
                    if breadth is not None:
                        snapshot["breadth"] = {
                            "advancers": breadth.advancers,
                            "decliners": breadth.decliners,
                            "unchanged": breadth.unchanged,
                            "ceiling_count": breadth.ceiling_count,
                            "floor_count": breadth.floor_count,
                        }

                    # Macro indicators: last 5 records (USD/VND + gold)
                    macro = session.exec(
                        select(MacroIndicator)
                        .order_by(col(MacroIndicator.recorded_date).desc())
                        .limit(5)
                    ).all()
                    snapshot["macro"] = [
                        {
                            "indicator_code": m.indicator_code,
                            "value": m.value,
                            "change_pct": m.change_pct,
                        }
                        for m in macro
                    ]
            except Exception as exc:
                logger.warning("[poller] DB market snapshot fetch failed: %s", exc)

        self._snapshot_cache = snapshot
        self._snapshot_cache_at = as_of
        logger.debug(
            "[poller] Market snapshot refreshed: spot=%.2f flows=%d breadth=%s macro=%d",
            snapshot["spot_price"],
            len(snapshot["flows"]),
            "yes" if snapshot["breadth"] else "no",
            len(snapshot["macro"]),
        )
        return snapshot
