"""Market data events, analysis contexts, and data normalization for quant daemon."""

import collections
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

import pandas as pd

from app.core.enums import SessionPhase
from app.core.models_base import VN_TZ
from app.domains.quant.application.daemon.poller import MarketPollResult

logger = logging.getLogger(__name__)


@dataclass
class MarketDataEvent:
    """Internal event model representing normalized incoming market data."""

    event_id: str
    symbol: str
    asset_type: str  # "derivative" | "equity" | "index"
    interval: str | None
    event_type: str  # "candle" | "tick" | "orderflow"
    event_time: datetime
    received_at: datetime
    open: Decimal | None = None
    high: Decimal | None = None
    low: Decimal | None = None
    close: Decimal | None = None
    volume: Decimal | None = None
    buy_volume: Decimal | None = None
    sell_volume: Decimal | None = None
    source: str = "vci"
    from_cache: bool = False
    market_phase: SessionPhase = SessionPhase.MORNING_CONTINUOUS
    is_closed: bool = True
    is_duplicate: bool = False


@dataclass
class AnalysisContext:
    """Unified context passed to analytical engines and ensemble decision."""

    event: MarketDataEvent | None
    latest_bars: list[dict[str, Any]]
    intraday_flow: list[dict[str, Any]]
    market_snapshot: dict[str, Any]
    phase: SessionPhase
    as_of: datetime
    highs: list[float] = field(default_factory=list)
    lows: list[float] = field(default_factory=list)
    closes: list[float] = field(default_factory=list)
    volumes: list[float] = field(default_factory=list)
    entry_price: float = 0.0
    spot_price: float = 0.0
    order_flow: Any = None
    flows: list[Any] | None = None
    breadth: Any = None
    macro: list[Any] | None = None
    skip_reason: str | None = None
    is_valid: bool = True


class MarketDataNormalizer:
    """Normalizes poller outputs, deduplicates events, and prepares AnalysisContext."""

    def __init__(self, cache_size: int = 5000) -> None:
        self.cache_size = cache_size
        self._seen_events: collections.OrderedDict[
            tuple[str, str | None, str], bool
        ] = collections.OrderedDict()

    def _mark_seen(self, key: tuple[str, str | None, str]) -> bool:
        """Record event key; returns True if seen before (duplicate), False otherwise."""
        if key in self._seen_events:
            return True
        self._seen_events[key] = True
        if len(self._seen_events) > self.cache_size:
            self._seen_events.popitem(last=False)
        return False

    def is_duplicate(
        self, symbol: str, interval: str | None, event_time: datetime
    ) -> bool:
        """Check if an event key has already been processed."""
        key = (symbol, interval, event_time.isoformat())
        return key in self._seen_events

    def normalize(
        self,
        poll_result: MarketPollResult,
        as_of: datetime | None = None,
        market_snapshot: dict[str, Any] | None = None,
    ) -> AnalysisContext:
        """
        Normalize a MarketPollResult into a validated AnalysisContext and MarketDataEvent.

        Performs:
        1. Timestamps validation (timezone-aware Vietnam time, no look-ahead).
        2. Candle / tick extraction and float array building.
        3. Event deduplication and idempotency tagging.
        4. Fallback cache check and minimum bar sufficiency.
        """
        now = as_of or datetime.now(VN_TZ)
        if now.tzinfo is None:
            now = now.replace(tzinfo=VN_TZ)

        symbol = poll_result.symbol
        phase = poll_result.phase
        from_cache = poll_result.from_cache

        # Choose primary bars series: intraday_bars if present, else history_bars
        raw_bars = poll_result.intraday_bars or poll_result.history_bars or []
        order_flow_raw = poll_result.order_flow or []

        highs: list[float] = []
        lows: list[float] = []
        closes: list[float] = []
        volumes: list[float] = []

        valid_bars: list[dict[str, Any]] = []

        for bar in raw_bars:
            if not isinstance(bar, dict):
                continue

            bar_time = bar.get("time")
            if bar_time is not None:
                if isinstance(bar_time, str):
                    try:
                        bar_dt = datetime.fromisoformat(bar_time)
                    except ValueError:
                        bar_dt = None
                elif isinstance(bar_time, datetime):
                    bar_dt = bar_time
                elif hasattr(bar_time, "to_pydatetime"):
                    bar_dt = bar_time.to_pydatetime()
                else:
                    bar_dt = None

                if bar_dt is not None:
                    if bar_dt.tzinfo is None:
                        bar_dt = bar_dt.replace(tzinfo=VN_TZ)

                    # Look-ahead bias check: future timestamps relative to as_of (with 10s leeway for clock drift)
                    if bar_dt > now + timedelta(seconds=10):
                        logger.warning(
                            "Skipping future bar time %s exceeding as_of %s (Look-ahead guard)",
                            bar_dt,
                            now,
                        )
                        continue

            c = bar.get("close")
            if c is not None:
                try:
                    c_float = float(c)
                    h_float = float(bar.get("high", c_float))
                    l_float = float(bar.get("low", c_float))
                    v_float = float(bar.get("volume", 0.0))

                    highs.append(h_float)
                    lows.append(l_float)
                    closes.append(c_float)
                    volumes.append(v_float)
                    valid_bars.append(bar)
                except (ValueError, TypeError):
                    continue

        asset_type = "derivative" if symbol.upper().startswith("VN30F") else "equity"
        interval = (
            "1D"
            if phase in (SessionPhase.POST_MARKET, SessionPhase.OVERNIGHT_SIMULATION)
            else "1m"
        )

        latest_event: MarketDataEvent | None = None
        skip_reason: str | None = None
        is_valid = True

        if not valid_bars:
            if from_cache:
                skip_reason = "cached_data_empty"
            else:
                skip_reason = "no_valid_bars_available"
            is_valid = False

        if valid_bars:
            last_bar = valid_bars[-1]
            last_bar_time = last_bar.get("time")
            if isinstance(last_bar_time, str):
                try:
                    event_time = datetime.fromisoformat(last_bar_time)
                except ValueError:
                    event_time = now
            elif isinstance(last_bar_time, datetime):
                event_time = last_bar_time
            elif hasattr(last_bar_time, "to_pydatetime"):
                event_time = last_bar_time.to_pydatetime()
            else:
                event_time = now

            if event_time.tzinfo is None:
                event_time = event_time.replace(tzinfo=VN_TZ)

            # Determine whether the candle is closed or forming
            # A 1m candle is considered forming if within 60s of current time
            is_closed = True
            if interval == "1m":
                is_closed = (now - event_time).total_seconds() >= 60.0

            # Deduplication key check
            dedup_key = (symbol, interval, event_time.isoformat())
            is_dup = self._mark_seen(dedup_key)
            if is_dup:
                logger.debug(
                    "Duplicate market data event detected for %s at %s",
                    symbol,
                    event_time.isoformat(),
                )

            # Build deterministic event_id
            event_id = (
                f"{symbol}:{interval}:{event_time.strftime('%Y%m%d%H%M%S')}:candle"
            )

            open_val = Decimal(str(last_bar.get("open", closes[-1])))
            high_val = Decimal(str(last_bar.get("high", highs[-1])))
            low_val = Decimal(str(last_bar.get("low", lows[-1])))
            close_val = Decimal(str(last_bar.get("close", closes[-1])))
            volume_val = Decimal(str(last_bar.get("volume", volumes[-1])))

            latest_event = MarketDataEvent(
                event_id=event_id,
                symbol=symbol,
                asset_type=asset_type,
                interval=interval,
                event_type="candle",
                event_time=event_time,
                received_at=now,
                open=open_val,
                high=high_val,
                low=low_val,
                close=close_val,
                volume=volume_val,
                buy_volume=None,
                sell_volume=None,
                source="vci",
                from_cache=from_cache,
                market_phase=phase,
                is_closed=is_closed,
                is_duplicate=is_dup,
            )

        entry_price = closes[-1] if closes else 0.0
        # Merge snapshots: poll_result.market_snapshot (primary, freshly fetched)
        # overrides the optional market_snapshot parameter (legacy/test injection).
        snapshot = {**(poll_result.market_snapshot or {}), **(market_snapshot or {})}
        # spot_price > 0 means VN30 index was fetched; otherwise fall back to entry_price
        raw_spot = snapshot.get("spot_price", 0.0)
        spot_price = float(raw_spot) if raw_spot else float(entry_price)

        # Check sufficiency: if from_cache=True and insufficient bars (< 15 bars)
        if from_cache and len(closes) < 15:
            skip_reason = "cached_data_insufficient_bars"
            is_valid = False
        elif len(closes) < 5:
            skip_reason = "insufficient_bars_minimum_5_required"
            is_valid = False

        # Orderflow conversion to DataFrame if available
        df_order_flow = None
        if order_flow_raw:
            try:
                df_order_flow = pd.DataFrame(order_flow_raw)
            except Exception:
                df_order_flow = order_flow_raw

        return AnalysisContext(
            event=latest_event,
            latest_bars=valid_bars,
            intraday_flow=order_flow_raw,
            market_snapshot=snapshot,
            phase=phase,
            as_of=now,
            highs=highs,
            lows=lows,
            closes=closes,
            volumes=volumes,
            entry_price=entry_price,
            spot_price=spot_price,
            order_flow=df_order_flow,
            flows=snapshot.get("flows"),
            breadth=snapshot.get("breadth"),
            macro=snapshot.get("macro"),
            skip_reason=skip_reason,
            is_valid=is_valid,
        )
