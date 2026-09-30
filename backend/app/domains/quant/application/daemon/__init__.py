"""Quant background session daemon - Phase 3 autonomous lifecycle management.

This package implements the background session daemon with:
- 9-state FSM (PRE_ATO → ATO → MORNING_CONTINUOUS → ... → OVERNIGHT_SIMULATION)
- Adaptive polling intervals (0.5s–300s per phase)
- Circuit breaker with HALF_OPEN state and 60s cooldown
- Signal dispatch to EnsembleEngine and SimulationEngine
- Forecast journal logging with Brier Score evaluation
"""

from app.domains.quant.application.daemon.clock import VietnamMarketClock
from app.domains.quant.application.daemon.controller import DaemonController
from app.domains.quant.application.daemon.dispatcher import SignalDispatcher
from app.domains.quant.application.daemon.poller import MarketDataPoller
from app.domains.quant.application.daemon.state import (
    STATE_POLL_INTERVALS,
    DaemonCircuitBreaker,
    QuantDaemonState,
)

# Alias for backward compatibility
QuantDaemonController = DaemonController

# Singleton instance for API routers
quant_daemon_controller = DaemonController(
    clock=VietnamMarketClock(),
    circuit_breaker=DaemonCircuitBreaker(),
    poller=MarketDataPoller(circuit_breaker=DaemonCircuitBreaker()),
    dispatcher=SignalDispatcher(ensemble_engine=None, simulation_engine=None),
)

__all__ = [
    "DaemonCircuitBreaker",
    "DaemonController",
    "MarketDataPoller",
    "QuantDaemonController",
    "QuantDaemonState",
    "SignalDispatcher",
    "STATE_POLL_INTERVALS",
    "VietnamMarketClock",
    "quant_daemon_controller",
]
