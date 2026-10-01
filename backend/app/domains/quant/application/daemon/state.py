"""State and circuit breaker primitives for the autonomous quant daemon."""

import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.core.enums import SessionPhase
from app.core.models_base import VN_TZ

# Adaptive polling intervals per session phase (in seconds)
# Calibrated for Community Tier (60 requests/minute max):
# Each cycle polls 2 endpoints (VN30F1M + VN30 1m).
# 3.0s interval = 20 cycles/min * 2 = 40 requests/min, leaving 20 req/min margin for other services.
COMMUNITY_POLL_INTERVALS: dict[SessionPhase, float] = {
    SessionPhase.PRE_ATO: 30.0,
    SessionPhase.ATO: 3.0,
    SessionPhase.MORNING_CONTINUOUS: 3.0,
    SessionPhase.MIDDAY_INTERMISSION: 60.0,
    SessionPhase.AFTERNOON_CONTINUOUS: 3.0,
    SessionPhase.PRE_ATC: 2.0,
    SessionPhase.ATC: 2.0,
    SessionPhase.POST_MARKET: 60.0,
    SessionPhase.OVERNIGHT_SIMULATION: 300.0,
}

SPONSOR_POLL_INTERVALS: dict[SessionPhase, float] = {
    SessionPhase.PRE_ATO: 15.0,
    SessionPhase.ATO: 1.0,
    SessionPhase.MORNING_CONTINUOUS: 1.0,
    SessionPhase.MIDDAY_INTERMISSION: 30.0,
    SessionPhase.AFTERNOON_CONTINUOUS: 1.0,
    SessionPhase.PRE_ATC: 0.5,
    SessionPhase.ATC: 0.5,
    SessionPhase.POST_MARKET: 30.0,
    SessionPhase.OVERNIGHT_SIMULATION: 120.0,
}

STATE_POLL_INTERVALS: dict[SessionPhase, float] = COMMUNITY_POLL_INTERVALS


@dataclass
class DaemonCircuitBreaker:
    failure_threshold: int = 5
    failure_count: int = 0
    opened_at: datetime | None = None
    last_error: str | None = None
    _half_open_cooldown_seconds: float = 60.0
    _probe_lock: threading.Lock = field(
        default_factory=threading.Lock, init=False, repr=False
    )
    _probe_in_flight: bool = field(default=False, init=False, repr=False)

    @property
    def is_open(self) -> bool:
        # Once the cooldown expires the breaker is HALF_OPEN and must allow
        # one probe request through. Treating HALF_OPEN as OPEN would keep the
        # poller serving stale cache data forever.
        return self.opened_at is not None and not self.is_half_open

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
        with self._probe_lock:
            self.failure_count = 0
            self.opened_at = None
            self.last_error = None
            self._probe_in_flight = False

    def record_failure(self, exc: Exception) -> None:
        with self._probe_lock:
            self.failure_count += 1
            self.last_error = str(exc)
            self._probe_in_flight = False
            if self.failure_count >= self.failure_threshold and not self.is_open:
                self.opened_at = datetime.now(VN_TZ)

    def try_start_probe(self) -> bool:
        """Allow at most one recovery request while HALF_OPEN."""
        with self._probe_lock:
            if not self.is_half_open or self._probe_in_flight:
                return False
            self._probe_in_flight = True
            return True

    def finish_probe(self, success: bool) -> None:
        """Close the HALF_OPEN probe and transition the breaker accordingly."""
        if success:
            self.record_success()
        else:
            self.record_failure(RuntimeError("circuit breaker half-open probe failed"))

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
    last_event_id: str | None = None
    last_cycle_id: int = 0
    engine_run_status: dict[str, str] = field(default_factory=dict)
    forecasts_created_count: int = 0
    events_skipped_count: int = 0
    duplicates_detected_count: int = 0
    errors_by_type: dict[str, int] = field(
        default_factory=lambda: {
            "validation": 0,
            "api": 0,
            "circuit_breaker": 0,
            "engine": 0,
            "db": 0,
        }
    )

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
            "last_event_id": self.last_event_id,
            "last_cycle_id": self.last_cycle_id,
            "engine_run_status": self.engine_run_status,
            "forecasts_created_count": self.forecasts_created_count,
            "events_skipped_count": self.events_skipped_count,
            "duplicates_detected_count": self.duplicates_detected_count,
            "errors_by_type": self.errors_by_type,
            "circuit_breaker": {
                "is_open": breaker.is_open,
                "failure_count": breaker.failure_count,
                "failure_threshold": breaker.failure_threshold,
                "opened_at": breaker.opened_at,
                "last_error": breaker.last_error,
                "is_half_open": breaker.is_half_open,
            },
        }
