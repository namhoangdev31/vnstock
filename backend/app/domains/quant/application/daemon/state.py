"""State and circuit breaker primitives for the autonomous quant daemon."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.core.enums import SessionPhase
from app.core.models_base import VN_TZ

# Adaptive polling intervals per session phase (in seconds)
STATE_POLL_INTERVALS: dict[SessionPhase, float] = {
    SessionPhase.PRE_ATO: 30.0,
    SessionPhase.ATO: 1.0,
    SessionPhase.MORNING_CONTINUOUS: 1.0,
    SessionPhase.MIDDAY_INTERMISSION: 60.0,
    SessionPhase.AFTERNOON_CONTINUOUS: 1.0,
    SessionPhase.PRE_ATC: 0.5,
    SessionPhase.ATC: 0.5,
    SessionPhase.POST_MARKET: 60.0,
    SessionPhase.OVERNIGHT_SIMULATION: 300.0,
}


@dataclass
class DaemonCircuitBreaker:
    failure_threshold: int = 5
    failure_count: int = 0
    opened_at: datetime | None = None
    last_error: str | None = None
    _half_open_cooldown_seconds: float = 60.0

    @property
    def is_open(self) -> bool:
        return self.opened_at is not None

    @property
    def is_half_open(self) -> bool:
        if self.opened_at is None:
            return False
        now = datetime.now(VN_TZ)
        # Half-open if cooldown has passed since circuit opened
        return (
            now - self.opened_at
        ).total_seconds() >= self._half_open_cooldown_seconds

    def record_success(self) -> None:
        self.failure_count = 0
        self.opened_at = None
        self.last_error = None

    def record_failure(self, exc: Exception) -> None:
        self.failure_count += 1
        self.last_error = str(exc)

        if self.failure_count >= self.failure_threshold and not self.is_open:
            self.opened_at = datetime.now(VN_TZ)

    def reset(self) -> None:
        self.record_success()


@dataclass
class QuantDaemonState:
    running: bool = False
    paused: bool = False
    degraded: bool = False
    status: str = "stopped"
    session_phase: str | None = None
    last_started_at: datetime | None = None
    last_stopped_at: datetime | None = None
    last_run_at: datetime | None = None
    last_success_at: datetime | None = None
    last_error_at: datetime | None = None
    last_error: str | None = None
    last_degraded_reason: str | None = None
    last_forecast_id: str | None = None
    last_snapshot: dict[str, Any] = field(default_factory=dict)

    def as_dict(self, breaker: DaemonCircuitBreaker) -> dict[str, Any]:
        return {
            "running": self.running,
            "paused": self.paused,
            "degraded": self.degraded,
            "status": self.status,
            "session_phase": self.session_phase,
            "last_started_at": self.last_started_at,
            "last_stopped_at": self.last_stopped_at,
            "last_run_at": self.last_run_at,
            "last_success_at": self.last_success_at,
            "last_error_at": self.last_error_at,
            "last_error": self.last_error,
            "last_degraded_reason": self.last_degraded_reason,
            "last_forecast_id": self.last_forecast_id,
            "last_snapshot": self.last_snapshot,
            "circuit_breaker": {
                "is_open": breaker.is_open,
                "failure_count": breaker.failure_count,
                "failure_threshold": breaker.failure_threshold,
                "opened_at": breaker.opened_at,
                "last_error": breaker.last_error,
            },
        }
