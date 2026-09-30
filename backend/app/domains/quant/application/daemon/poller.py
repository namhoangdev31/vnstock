"""Market data polling orchestration for the autonomous quant daemon."""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.core.enums import SessionPhase
from app.core.models_base import VN_TZ
from app.domains.quant.application.daemon.state import DaemonCircuitBreaker

logger = logging.getLogger(__name__)


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


class MarketDataPoller:
    """Orchestrates market data extraction from Vnstock API with phase awareness."""

    def __init__(self, circuit_breaker: DaemonCircuitBreaker) -> None:
        self.circuit_breaker = circuit_breaker
        self._vnstock_service = None

    def poll(
        self,
        symbol: str,
        phase: SessionPhase,
        limit_history: int = 120,
        limit_intraday: int = 50,
        limit_orderflow: int = 40,
    ) -> MarketPollResult:
        """Poll market data based on current session phase."""
        now = datetime.now(VN_TZ)
        result = MarketPollResult(symbol=symbol, phase=phase, timestamp=now)

        # Circuit breaker check
        if self.circuit_breaker.is_open:
            result.errors.append(
                {
                    "error": "circuit_breaker_open",
                    "reason": "Circuit breaker is OPEN, skipping poll",
                }
            )
            return result

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
            # Post-market/overnight: minimal polling, history for next-day analysis
            result.history_bars = self._fetch_history(symbol, min(limit_history, 30))

        return result

    def _fetch_history(self, symbol: str, limit: int) -> list[Any]:
        """Fetch historical bars via VnstockService."""
        try:
            from app.domains.market_data.infrastructure.vnstock_adapter import (
                vnstock_service,
            )

            df = vnstock_service.fetch_price_history(
                symbol=symbol,
                interval="1D",
                count=limit,
            )
            if df is not None and not df.empty:
                return df.to_dict("records")
            return []
        except Exception as exc:
            logger.warning(f"Error fetching history for {symbol}: {exc}")
            return []

    def _fetch_intraday(self, symbol: str, limit: int) -> list[Any]:
        """Fetch intraday bars via VnstockService."""
        try:
            from app.domains.market_data.infrastructure.vnstock_adapter import (
                vnstock_service,
            )

            df = vnstock_service.fetch_intraday(
                symbol=symbol,
                interval="1m",
                count_back=limit,
            )
            if df is not None and not df.empty:
                return df.to_dict("records")
            return []
        except Exception as exc:
            logger.warning(f"Error fetching intraday bars for {symbol}: {exc}")
            return []

    def _fetch_order_flow(self, symbol: str, limit: int) -> list[Any]:
        """Fetch tick-level order flow (Aggressive Buy/Sell) via VnstockService."""
        try:
            from app.domains.market_data.infrastructure.vnstock_adapter import (
                vnstock_service,
            )

            df = vnstock_service.fetch_tick_orderflow(symbol=symbol, page_size=limit)
            if df is not None and not df.empty:
                return df.to_dict("records")
            return []
        except Exception as exc:
            logger.warning(f"Error fetching order flow for {symbol}: {exc}")
            return []
