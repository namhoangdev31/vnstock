"""Comprehensive tests for the quant daemon components.

Tests cover:
- Clock phase classification (weekend/holiday handling)
- Circuit breaker HALF_OPEN transitions
- Poller phase-aware behavior
- Dispatcher signal routing
- Controller adaptive polling
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.enums import SessionPhase
from app.domains.quant.application.daemon.clock import VietnamMarketClock
from app.domains.quant.application.daemon.state import (
    DaemonCircuitBreaker,
    QuantDaemonState,
    STATE_POLL_INTERVALS,
)
from app.domains.quant.application.daemon.poller import MarketDataPoller, MarketPollResult
from app.domains.quant.application.daemon.dispatcher import SignalDispatcher, DispatchResult


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
        cb.record_failure(Exception("test error"))
        assert cb.is_open is True
        assert cb.opened_at is not None

    def test_half_open_transition(self):
        """Test that circuit breaker transitions to HALF_OPEN after cooldown."""
        cb = DaemonCircuitBreaker()
        cb._half_open_cooldown_seconds = 0.1  # Shorten for testing
        cb.record_failure(Exception("test error"))

        # Not half-open immediately
        assert cb.is_half_open is False

        # After cooldown, should be half-open
        cb.opened_at = datetime.now() - timedelta(seconds=0.2)
        assert cb.is_half_open is True

    def test_record_success_resets(self):
        """Test that success resets circuit breaker to CLOSED."""
        cb = DaemonCircuitBreaker()
        cb.record_failure(Exception("test error"))
        assert cb.is_open is True

        cb.record_success()
        assert cb.is_open is False
        assert cb.opened_at is None
        assert cb.half_open_at is None

    def test_reset_method(self):
        """Test that reset clears all state."""
        cb = DaemonCircuitBreaker()
        cb.record_failure(Exception("test error"))
        cb.reset()

        assert cb.is_open is False
        assert cb.is_half_open is False
        assert cb.opened_at is None
        assert cb.half_open_at is None


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
        assert poller.breaker is cb

    def test_poll_returns_result(self):
        """Test that poll returns a MarketPollResult."""
        cb = DaemonCircuitBreaker()
        poller = MarketDataPoller(cb)

        result = poller.poll(
            symbol="VN30F1M",
            phase=SessionPhase.MORNING_CONTINUOUS,
            limit_history=120,
            limit_intraday=50,
            limit_orderflow=40,
        )

        assert isinstance(result, MarketPollResult)
        assert result.symbol == "VN30F1M"
        assert result.phase == SessionPhase.MORNING_CONTINUOUS
        assert result.timestamp is not None

    def test_poll_skips_when_breaker_open(self):
        """Test that poll skips when circuit breaker is open."""
        cb = DaemonCircuitBreaker()
        cb.record_failure(Exception("test"))
        poller = MarketDataPoller(cb)

        result = poller.poll(
            symbol="VN30F1M",
            phase=SessionPhase.MORNING_CONTINUOUS,
        )

        assert result.errors is not None
        assert len(result.errors) > 0
        assert "circuit_breaker_open" in str(result.errors[0])


class TestSignalDispatcher:
    """Test suite for signal dispatcher."""

    def test_create_dispatcher(self):
        """Test dispatcher creation."""
        dispatcher = SignalDispatcher()
        assert dispatcher is not None

    def test_dispatch_skips_non_trading_phases(self):
        """Test that dispatch skips POST_MARKET and OVERNIGHT_SIMULATION."""
        dispatcher = SignalDispatcher()

        poll_result = MarketPollResult(
            symbol="VN30F1M",
            phase=SessionPhase.POST_MARKET,
            timestamp=datetime.now(),
        )

        result = dispatcher.dispatch(poll_result)

        assert isinstance(result, DispatchResult)
        assert result.phase == SessionPhase.POST_MARKET
        assert result.signal_count == 0

    def test_dispatch_handles_trading_phases(self):
        """Test that dispatch processes trading phases."""
        dispatcher = SignalDispatcher()

        poll_result = MarketPollResult(
            symbol="VN30F1M",
            phase=SessionPhase.MORNING_CONTINUOUS,
            timestamp=datetime.now(),
        )

        result = dispatcher.dispatch(poll_result)

        assert isinstance(result, DispatchResult)
        assert result.phase == SessionPhase.MORNING_CONTINUOUS


class TestQuantDaemonController:
    """Test suite for quant daemon controller."""

    @pytest.mark.asyncio
    async def test_start_stop_lifecycle(self):
        """Test daemon start/stop lifecycle."""
        controller = QuantDaemonController()

        await controller.start()
        assert controller.state.running is True
        assert controller.state.status == "running"

        await controller.stop()
        assert controller.state.running is False
        assert controller.state.status == "stopped"

    @pytest.mark.asyncio
    async def test_pause_resume(self):
        """Test daemon pause/resume."""
        controller = QuantDaemonController()

        await controller.start()
        assert controller.state.paused is False

        controller.pause()
        assert controller.state.paused is True
        assert controller.state.status == "paused"

        controller.resume()
        assert controller.state.paused is False

    @pytest.mark.asyncio
    async def test_get_status(self):
        """Test daemon status reporting."""
        controller = QuantDaemonController()
        status = controller.status()

        assert "running" in status
        assert "paused" in status
        assert "session_phase" in status
        assert "circuit_breaker" in status

    def test_trigger_once(self):
        """Test single manual trigger."""
        controller = QuantDaemonController()

        # This would fail in isolation due to database dependencies,
        # but verifies the method exists and can be called
        result = asyncio.get_event_loop().run_until_complete(
            controller.trigger_once()
        )

        assert "running" in result
        assert "session_phase" in result
