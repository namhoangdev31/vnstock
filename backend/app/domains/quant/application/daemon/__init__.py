"""Quant background session daemon - Phase 3 autonomous lifecycle management.

This package implements the background session daemon with:
- 9-state FSM (PRE_ATO → ATO → MORNING_CONTINUOUS → ... → OVERNIGHT_SIMULATION)
- Adaptive polling intervals (0.5s–300s per phase)
- Circuit breaker with HALF_OPEN state and 60s cooldown
- Signal dispatch to EnsembleEngine and SimulationEngine
- Forecast journal logging with Brier Score evaluation
"""

from app.domains.quant.application.daemon.clock import VietnamMarketClock
from app.domains.quant.application.daemon.controller import QuantDaemonController
from app.domains.quant.application.daemon.dispatcher import SignalDispatcher
from app.domains.quant.application.daemon.poller import MarketDataPoller
from app.domains.quant.application.daemon.state import (
    DaemonCircuitBreaker,
    QuantDaemonState,
    STATE_POLL_INTERVALS,
)

__all__ = [
    "DaemonCircuitBreaker",
    "MarketDataPoller",
    "QuantDaemonController",
    "QuantDaemonState",
    "SignalDispatcher",
    "STATE_POLL_INTERVALS",
    "VietnamMarketClock",
]
