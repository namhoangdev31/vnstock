"""Quant background session daemon - Phase 3 autonomous lifecycle management.

This package implements the background session daemon with:
- 9-state FSM (PRE_ATO → ATO → MORNING_CONTINUOUS → ... → OVERNIGHT_SIMULATION)
- Adaptive polling intervals (0.5s–300s per phase)
- Circuit breaker with HALF_OPEN state and 60s cooldown
- Market data normalization with idempotency and deduplication
- Phase-aware engine orchestration with failure isolation
- Signal dispatch to EnsembleEngine and SimulationEngine
- Forecast journal logging with Brier Score evaluation
"""

from sqlmodel import Session

from app.core.db import engine
from app.domains.quant.application.daemon.clock import VietnamMarketClock
from app.domains.quant.application.daemon.controller import DaemonController
from app.domains.quant.application.daemon.dispatcher import (
    DispatchResult,
    SignalDispatcher,
    map_phase_to_horizon,
)
from app.domains.quant.application.daemon.event import (
    AnalysisContext,
    MarketDataEvent,
    MarketDataNormalizer,
)
from app.domains.quant.application.daemon.lease import PostgresAdvisoryLease
from app.domains.quant.application.daemon.orchestrator import (
    EngineExecutionResult,
    OrchestratorResult,
    PhaseAwareEngineOrchestrator,
)
from app.domains.quant.application.daemon.poller import (
    MarketDataPoller,
    MarketPollResult,
)
from app.domains.quant.application.daemon.state import (
    STATE_POLL_INTERVALS,
    DaemonCircuitBreaker,
    QuantDaemonState,
)

# Alias for backward compatibility
QuantDaemonController = DaemonController

default_orchestrator = PhaseAwareEngineOrchestrator(session=None)
default_circuit_breaker = DaemonCircuitBreaker()
default_lease = PostgresAdvisoryLease(engine, "vnstock.quant.daemon")


def _daemon_session_factory() -> Session:
    return Session(engine)


quant_daemon_controller = DaemonController(
    clock=VietnamMarketClock(),
    circuit_breaker=default_circuit_breaker,
    poller=MarketDataPoller(circuit_breaker=default_circuit_breaker),
    dispatcher=SignalDispatcher(
        orchestrator=default_orchestrator,
    ),
    session_factory=_daemon_session_factory,
    lease=default_lease,
)

__all__ = [
    "AnalysisContext",
    "DaemonCircuitBreaker",
    "DaemonController",
    "DispatchResult",
    "EngineExecutionResult",
    "MarketDataEvent",
    "MarketDataNormalizer",
    "MarketDataPoller",
    "MarketPollResult",
    "OrchestratorResult",
    "PhaseAwareEngineOrchestrator",
    "QuantDaemonController",
    "QuantDaemonState",
    "STATE_POLL_INTERVALS",
    "SignalDispatcher",
    "VietnamMarketClock",
    "map_phase_to_horizon",
    "quant_daemon_controller",
]
