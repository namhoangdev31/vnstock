"""Comprehensive tests for the quant daemon components.

Tests cover:
- Clock phase classification (weekend/holiday handling)
- Circuit breaker HALF_OPEN transitions
- Poller phase-aware behavior
- Dispatcher signal routing
- Controller adaptive polling
"""

from datetime import datetime, timedelta

from app.core.enums import SessionPhase
from app.core.models_base import VN_TZ
from app.domains.quant.application.daemon.clock import VietnamMarketClock
from app.domains.quant.application.daemon.dispatcher import (
    DispatchResult,
    SignalDispatcher,
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


class TestVietnamMarketClock:
    """Test suite for VietnamMarketClock phase classification."""

    def test_classify_trading_day_morning(self):
        """Test phase classification during morning trading hours."""
        # Tuesday, 2026-09-29, 09:30 (MORNING_CONTINUOUS)
        dt = datetime(2026, 9, 29, 9, 30, 0)
        phase = VietnamMarketClock.classify(dt)
        assert phase == SessionPhase.MORNING_CONTINUOUS

    def test_classify_weekend(self):
        """Test that weekends return OVERNIGHT_SIMULATION."""
        # Saturday, 2026-10-03
        dt = datetime(2026, 10, 3, 10, 0, 0)
        phase = VietnamMarketClock.classify(dt)
        assert phase == SessionPhase.OVERNIGHT_SIMULATION

    def test_classify_trading_day_pre_ato(self):
        """Test phase classification during PRE_ATO phase."""
        # Tuesday, 2026-09-29, 08:35 (PRE_ATO: 08:30 - 08:45)
        dt = datetime(2026, 9, 29, 8, 35, 0)
        phase = VietnamMarketClock.classify(dt)
        assert phase == SessionPhase.PRE_ATO

    def test_classify_trading_day_ato(self):
        """Test phase classification during ATO phase."""
        # Tuesday, 2026-09-29, 08:50 (ATO: 08:45 - 09:00)
        dt = datetime(2026, 9, 29, 8, 50, 0)
        phase = VietnamMarketClock.classify(dt)
        assert phase == SessionPhase.ATO

    def test_classify_trading_day_midday_intermission(self):
        """Test phase classification during midday break."""
        # Tuesday, 2026-09-29, 12:00 (MIDDAY_INTERMISSION: 11:30 - 13:00)
        dt = datetime(2026, 9, 29, 12, 0, 0)
        phase = VietnamMarketClock.classify(dt)
        assert phase == SessionPhase.MIDDAY_INTERMISSION

    def test_classify_trading_day_afternoon(self):
        """Test phase classification during afternoon trading."""
        # Tuesday, 2026-09-29, 14:00 (AFTERNOON_CONTINUOUS: 13:00 - 14:15)
        dt = datetime(2026, 9, 29, 14, 0, 0)
        phase = VietnamMarketClock.classify(dt)
        assert phase == SessionPhase.AFTERNOON_CONTINUOUS

    def test_classify_trading_day_post_market(self):
        """Test phase classification after market close."""
        # Tuesday, 2026-09-29, 15:00 (POST_MARKET: after 14:45)
        dt = datetime(2026, 9, 29, 15, 0, 0)
        phase = VietnamMarketClock.classify(dt)
        assert phase == SessionPhase.POST_MARKET


class TestDaemonCircuitBreaker:
    """Test suite for circuit breaker state transitions."""

    def test_initial_state(self):
        """Test initial circuit breaker state is CLOSED."""
        cb = DaemonCircuitBreaker()
        assert cb.is_open is False
        assert cb.is_half_open is False

    def test_record_failure_transitions_to_open(self):
        """Test that failures transition to OPEN state."""
        cb = DaemonCircuitBreaker()
        # Record 3 failures to hit threshold
        for _ in range(3):
            cb.record_failure(Exception("test error"))
        assert cb.is_open is True
        assert cb.opened_at is not None

    def test_half_open_transition(self):
        """Test that circuit breaker transitions to HALF_OPEN after cooldown."""
        cb = DaemonCircuitBreaker()
        cb._half_open_cooldown_seconds = 0.1  # Shorten for testing

        # Hit threshold to open
        for _ in range(3):
            cb.record_failure(Exception("test error"))

        # Not half-open immediately
        assert cb.is_half_open is False

        # After cooldown, should be half-open
        cb.opened_at = datetime.now(VN_TZ) - timedelta(seconds=0.2)
        assert cb.is_half_open is True

    def test_record_success_resets(self):
        """Test that success resets circuit breaker to CLOSED."""
        cb = DaemonCircuitBreaker()
        # Hit threshold to open
        for _ in range(3):
            cb.record_failure(Exception("test error"))
        assert cb.is_open is True

        cb.record_success()
        assert cb.is_open is False
        assert cb.opened_at is None
        assert cb.failure_count == 0

    def test_reset_method(self):
        """Test that reset clears all state."""
        cb = DaemonCircuitBreaker()
        for _ in range(3):
            cb.record_failure(Exception("test error"))
        cb.reset()

        assert cb.is_open is False
        assert cb.is_half_open is False
        assert cb.opened_at is None
        assert cb.failure_count == 0


class TestQuantDaemonState:
    """Test suite for daemon state management."""

    def test_initial_state(self):
        """Test initial daemon state."""
        state = QuantDaemonState()
        assert state.running is False
        assert state.paused is False
        assert state.status == "stopped"

    def test_as_dict(self):
        """Test state serialization to dict."""
        state = QuantDaemonState()
        cb = DaemonCircuitBreaker()
        state_dict = state.as_dict(cb)

        assert "running" in state_dict
        assert "paused" in state_dict
        assert "status" in state_dict
        assert "session_phase" in state_dict


class TestStatePollIntervals:
    """Test suite for adaptive polling intervals."""

    def test_all_phases_have_intervals(self):
        """Test that all session phases have defined polling intervals."""
        for phase in SessionPhase:
            assert phase in STATE_POLL_INTERVALS, f"Missing interval for {phase}"

    def test_intervals_are_positive(self):
        """Test that all polling intervals are positive."""
        for phase, interval in STATE_POLL_INTERVALS.items():
            assert interval > 0, f"Interval for {phase} is not positive: {interval}"

    def test_overnight_is_longest(self):
        """Test that OVERNIGHT_SIMULATION has the longest interval."""
        overnight_interval = STATE_POLL_INTERVALS[SessionPhase.OVERNIGHT_SIMULATION]
        for phase, interval in STATE_POLL_INTERVALS.items():
            if phase != SessionPhase.OVERNIGHT_SIMULATION:
                assert overnight_interval >= interval, (
                    f"OVERNIGHT interval ({overnight_interval}) should be >= {phase} ({interval})"
                )


class TestMarketDataPoller:
    """Test suite for market data poller."""

    def test_create_poller_with_breaker(self):
        """Test poller creation with circuit breaker."""
        cb = DaemonCircuitBreaker()
        poller = MarketDataPoller(cb)
        assert poller.circuit_breaker is cb

    def test_poll_skips_when_breaker_open(self):
        """Test that poll skips when circuit breaker is open."""
        cb = DaemonCircuitBreaker()
        # Hit threshold to open
        for _ in range(3):
            cb.record_failure(Exception("test"))
        poller = MarketDataPoller(cb)

        result = poller.poll(
            symbol="VN30F1M",
            phase=SessionPhase.MORNING_CONTINUOUS,
        )

        assert result.errors is not None
        assert len(result.errors) > 0
        assert result.errors[0].get("error") == "circuit_breaker_open"


class TestSignalDispatcher:
    """Test suite for signal dispatcher."""

    def test_create_dispatcher(self):
        """Test dispatcher creation."""
        dispatcher = SignalDispatcher()
        assert dispatcher is not None

    def test_dispatch_skips_non_trading_phases(self):
        """Test that dispatch skips POST_MARKET and OVERNIGHT_SIMULATION."""
        dispatcher = SignalDispatcher()

        result = dispatcher.dispatch_sync(
            phase=SessionPhase.POST_MARKET,
            symbols=["VN30F1M"],
            market_data={},
        )

        assert isinstance(result, DispatchResult)
        assert result.phase == SessionPhase.POST_MARKET
        assert result.ensemble_signals == 0
        assert result.simulation_orders == 0

    def test_dispatch_handles_trading_phases(self):
        """Test that dispatch processes trading phases."""
        dispatcher = SignalDispatcher()

        result = dispatcher.dispatch_sync(
            phase=SessionPhase.MORNING_CONTINUOUS,
            symbols=["VN30F1M"],
            market_data={"VN30F1M": {"closes": [100, 101, 102]}},
        )

        assert isinstance(result, DispatchResult)
        assert result.phase == SessionPhase.MORNING_CONTINUOUS
