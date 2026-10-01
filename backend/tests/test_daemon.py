"""Comprehensive tests for the quant daemon components.

Tests cover:
- Clock phase classification (weekend/holiday handling)
- Circuit breaker HALF_OPEN transitions
- Poller phase-aware behavior
- Dispatcher signal routing
- Controller adaptive polling
"""

from datetime import datetime, timedelta
from unittest.mock import patch

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
    _fetch_with_retry,
    _parse_rate_limit_wait_s,
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
        for _ in range(5):
            cb.record_failure(Exception("test error"))
        assert cb.is_open is True
        assert cb.opened_at is not None

    def test_half_open_transition(self):
        """Test that circuit breaker transitions to HALF_OPEN after cooldown."""
        cb = DaemonCircuitBreaker()
        cb._half_open_cooldown_seconds = 0.1  # Shorten for testing

        # Hit threshold to open
        for _ in range(5):
            cb.record_failure(Exception("test error"))

        # Not half-open immediately
        assert cb.is_half_open is False

        # After cooldown, should be half-open
        cb.opened_at = datetime.now(VN_TZ) - timedelta(seconds=0.2)
        assert cb.is_half_open is True

    def test_record_success_resets(self):
        """Test that success resets circuit breaker to CLOSED."""
        cb = DaemonCircuitBreaker()
        # Hit threshold to open (TRD §3.2: failure_threshold=5)
        for _ in range(5):
            cb.record_failure(Exception("test error"))
        assert cb.is_open is True

        cb.record_success()
        assert cb.is_open is False
        assert cb.opened_at is None
        assert cb.failure_count == 0

    def test_reset_method(self):
        """Test that reset clears all state."""
        cb = DaemonCircuitBreaker()
        for _ in range(5):
            cb.record_failure(Exception("test error"))
        cb.reset()

        assert cb.is_open is False
        assert cb.is_half_open is False
        assert cb.opened_at is None
        assert cb.failure_count == 0

    def test_half_open_to_closed_on_success(self):
        """TEST-DAEMON-05: HALF_OPEN → CLOSED when record_success() is called.

        Spec: after cooldown elapses the circuit enters HALF_OPEN.  A single
        successful probe must fully close the circuit (opened_at=None,
        failure_count=0, is_open=False, is_half_open=False).
        """
        cb = DaemonCircuitBreaker()
        cb._half_open_cooldown_seconds = 0.1

        # Drive circuit OPEN (TRD §3.2: failure_threshold=5)
        for _ in range(5):
            cb.record_failure(Exception("probe failed"))
        assert cb.is_open is True

        # Fast-forward past cooldown so it enters HALF_OPEN
        cb.opened_at = datetime.now(VN_TZ) - timedelta(seconds=0.2)
        assert cb.is_half_open is True, "precondition: should be HALF_OPEN now"

        # One successful probe → CLOSED
        cb.record_success()

        assert cb.is_open is False, "circuit must be CLOSED after success"
        assert cb.is_half_open is False, "circuit must not be HALF_OPEN after success"
        assert cb.opened_at is None, "opened_at must be cleared"
        assert cb.failure_count == 0, "failure_count must reset to 0"

    def test_half_open_to_open_on_failure(self):
        """TEST-DAEMON-05b: HALF_OPEN → OPEN when the probe cycle fails again.

        If a failure is recorded while the circuit is HALF_OPEN, is_open stays
        True (opened_at is refreshed / not cleared).
        """
        cb = DaemonCircuitBreaker()
        cb._half_open_cooldown_seconds = 0.1

        # Drive circuit OPEN (TRD §3.2: failure_threshold=5)
        for _ in range(5):
            cb.record_failure(Exception("initial failure"))

        # Fast-forward past cooldown → HALF_OPEN
        cb.opened_at = datetime.now(VN_TZ) - timedelta(seconds=0.2)
        assert cb.is_half_open is True

        # Another failure in the probe window
        cb.record_failure(Exception("probe failure"))

        # Circuit must remain OPEN (opened_at was already set before this call)
        assert cb.is_open is True
        assert cb.failure_count == 6, "failure_count increments on every record_failure"


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
        """Test that poll returns CB-open error when circuit breaker is open and no cache."""
        cb = DaemonCircuitBreaker()
        # Hit threshold to open (TRD §3.2: failure_threshold=5)
        for _ in range(5):
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


class TestPollerCacheFallback:
    """TRD §4.2 — Last-known-data fallback when circuit breaker is OPEN."""

    def test_open_cb_with_cache_returns_cached_data(self):
        """CB OPEN + populated cache → from_cache=True with last known bars."""
        cb = DaemonCircuitBreaker()
        poller = MarketDataPoller(cb)

        # Seed the internal cache directly (simulates a prior successful poll).
        from datetime import datetime

        fake_result = MarketPollResult(
            symbol="VN30F1M",
            phase=SessionPhase.MORNING_CONTINUOUS,
            timestamp=datetime.now(VN_TZ),
            history_bars=[{"close": 1300.0}],
            intraday_bars=[{"vol": 5000}],
            order_flow=[{"side": "buy"}],
        )
        poller._last_known["VN30F1M"] = fake_result

        # Now open the circuit breaker (TRD §3.2: failure_threshold=5).
        for _ in range(5):
            cb.record_failure(Exception("network error"))
        assert cb.is_open

        result = poller.poll(symbol="VN30F1M", phase=SessionPhase.AFTERNOON_CONTINUOUS)

        assert result.from_cache is True
        assert result.history_bars == [{"close": 1300.0}]
        assert result.intraday_bars == [{"vol": 5000}]
        assert result.order_flow == [{"side": "buy"}]
        assert result.errors[0]["error"] == "circuit_breaker_open"

    def test_open_cb_without_cache_returns_empty(self):
        """CB OPEN + no cache → error flagged, empty lists, from_cache=False."""
        cb = DaemonCircuitBreaker()
        poller = MarketDataPoller(cb)

        # Open CB immediately, no prior poll (TRD §3.2: failure_threshold=5).
        for _ in range(5):
            cb.record_failure(Exception("error"))

        result = poller.poll(symbol="VN30F1M", phase=SessionPhase.MORNING_CONTINUOUS)

        assert result.from_cache is False
        assert result.history_bars == []
        assert result.errors[0]["error"] == "circuit_breaker_open"

    def test_successful_poll_updates_cache(self):
        """A successful poll (CB CLOSED, no API errors) must update _last_known."""
        cb = DaemonCircuitBreaker()
        poller = MarketDataPoller(cb)

        # _fetch_history / etc. raise — we patch to return deterministic data.
        with (
            patch.object(poller, "_fetch_history", return_value=[{"close": 999.0}]),
            patch.object(poller, "_fetch_intraday", return_value=[]),
            patch.object(poller, "_fetch_order_flow", return_value=[]),
        ):
            result = poller.poll(symbol="FPT", phase=SessionPhase.MORNING_CONTINUOUS)

        assert result.from_cache is False
        assert "FPT" in poller._last_known
        assert poller._last_known["FPT"].history_bars == [{"close": 999.0}]


class TestDaemonSIGTERM:
    """TEST-DAEMON-07: SIGTERM / SIGINT graceful shutdown.

    Verifies that the _register_signal_handlers method wires up correctly
    and that a simulated SIGTERM causes stop() to be invoked.
    """

    def test_register_signal_handlers_outside_loop_is_noop(self):
        """TEST-DAEMON-07a: _register_signal_handlers is a no-op outside an event loop.

        In a synchronous test context there is no running asyncio loop, so
        the method must return without raising an exception.
        """
        from app.domains.quant.application.daemon import quant_daemon_controller

        # Should not raise — the method guards against missing event loop.
        quant_daemon_controller._register_signal_handlers()

    def test_sigterm_triggers_stop_via_loop(self):
        """TEST-DAEMON-07b: Within a running event loop, SIGTERM schedules stop().

        Uses os.kill(getpid(), SIGTERM) to fire a real OS-level signal into the
        running asyncio event loop so the registered handler is invoked without
        relying on CPython-internal Handle._callback internals.
        """
        import asyncio
        import os
        import signal

        from app.domains.quant.application.daemon.clock import VietnamMarketClock
        from app.domains.quant.application.daemon.controller import DaemonController
        from app.domains.quant.application.daemon.dispatcher import SignalDispatcher
        from app.domains.quant.application.daemon.state import DaemonCircuitBreaker

        async def run():
            cb = DaemonCircuitBreaker()
            poller = MarketDataPoller(cb)
            ctrl = DaemonController(
                clock=VietnamMarketClock(),
                circuit_breaker=cb,
                poller=poller,
                dispatcher=SignalDispatcher(),
            )

            await ctrl.start()
            assert ctrl.state.running is True

            loop = asyncio.get_running_loop()
            # Verify our handler was registered before firing the signal.
            signal_handlers = getattr(loop, "_signal_handlers", {})
            assert signal.SIGTERM in signal_handlers, (
                "_register_signal_handlers must add SIGTERM to the running loop"
            )

            # Fire a real SIGTERM into this process. The asyncio loop will
            # dispatch it to our registered handler on the next iteration.
            os.kill(os.getpid(), signal.SIGTERM)

            # Give the loop several cycles to process the signal and the
            # stop() coroutine that the handler schedules.
            for _ in range(5):
                await asyncio.sleep(0)

            # stop() should have been called by the signal handler.
            assert ctrl.state.running is False
            assert ctrl.state.status == "stopped"

        asyncio.run(run())


class TestDaemonStatusHTTP:
    """TEST-DAEMON-08: /daemon/status HTTP response shape validation.

    Verifies that the status endpoint returns the exact keys required by the
    API contract without needing a real database or live daemon loop.
    """

    def test_status_response_contains_required_top_level_keys(self):
        """TEST-DAEMON-08a: Top-level keys match QuantDaemonState.as_dict() contract."""
        from app.domains.quant.application.daemon import quant_daemon_controller

        payload = quant_daemon_controller.status()

        required_keys = {
            "running",
            "paused",
            "degraded",
            "status",
            "session_phase",
            "last_started_at",
            "last_stopped_at",
            "last_run_at",
            "last_success_at",
            "last_error_at",
            "last_error",
            "circuit_breaker",
        }
        missing = required_keys - payload.keys()
        assert not missing, f"Status response missing keys: {missing}"

    def test_status_circuit_breaker_shape(self):
        """TEST-DAEMON-08b: Nested circuit_breaker dict has correct sub-keys."""
        from app.domains.quant.application.daemon import quant_daemon_controller

        payload = quant_daemon_controller.status()
        cb = payload["circuit_breaker"]

        required_cb_keys = {
            "is_open",
            "failure_count",
            "failure_threshold",
            "opened_at",
            "last_error",
        }
        missing = required_cb_keys - cb.keys()
        assert not missing, f"circuit_breaker missing keys: {missing}"

    def test_status_types_are_correct(self):
        """TEST-DAEMON-08c: Boolean and string fields have correct Python types."""
        from app.domains.quant.application.daemon import quant_daemon_controller

        payload = quant_daemon_controller.status()

        assert isinstance(payload["running"], bool)
        assert isinstance(payload["paused"], bool)
        assert isinstance(payload["degraded"], bool)
        assert isinstance(payload["status"], str)
        assert isinstance(payload["circuit_breaker"]["is_open"], bool)
        assert isinstance(payload["circuit_breaker"]["failure_count"], int)

    def test_status_stopped_daemon_defaults(self):
        """TEST-DAEMON-08d: Stopped daemon reports expected default values."""
        from app.domains.quant.application.daemon import quant_daemon_controller

        # Controller is freshly initialised (not started) in test env
        payload = quant_daemon_controller.status()

        assert payload["running"] is False
        assert payload["paused"] is False
        assert payload["status"] == "stopped"
        assert payload["circuit_breaker"]["is_open"] is False
        assert payload["circuit_breaker"]["failure_count"] == 0


class TestParseRateLimitWaitS:
    """Unit tests for the vnai rate-limit hint parser."""

    def test_parses_vietnamese_hint(self):
        """TEST-POLLER-RL-01: Vietnamese 'Chờ X giây' is parsed correctly."""
        exc = SystemExit("Chờ 22 giây để tiếp tục")
        assert _parse_rate_limit_wait_s(exc) == 22.0

    def test_parses_english_hint(self):
        """TEST-POLLER-RL-02: English 'Wait X seconds' is parsed correctly."""
        exc = SystemExit("Wait 45 seconds")
        assert _parse_rate_limit_wait_s(exc) == 45.0

    def test_parses_wait_to_retry_hint(self):
        """TEST-POLLER-RL-03: 'Wait to retry' variant is parsed."""
        exc = SystemExit("Wait to retry 30 seconds")
        assert _parse_rate_limit_wait_s(exc) == 30.0

    def test_returns_none_when_no_hint(self):
        """TEST-POLLER-RL-04: Returns None when the message carries no wait hint."""
        exc = SystemExit("Rate limit exceeded.")
        assert _parse_rate_limit_wait_s(exc) is None

    def test_returns_none_for_empty_args(self):
        """TEST-POLLER-RL-05: Returns None for an exception with no args."""
        exc = SystemExit()
        assert _parse_rate_limit_wait_s(exc) is None


class TestFetchWithRetrySmartBackoff:
    """Integration tests for _fetch_with_retry smart rate-limit handling."""

    def test_honours_vnai_hint_on_first_attempt_then_succeeds(self):
        """TEST-POLLER-RL-06: Waits the hinted duration, then retries successfully."""
        call_count = 0

        def fn():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise SystemExit("Chờ 1 giây để tiếp tục")
            return "ok"

        with patch("app.domains.quant.application.daemon.poller.time.sleep"):
            result = _fetch_with_retry(fn, label="test")

        assert result == "ok"
        assert call_count == 2

    def test_aborts_retries_when_hint_exceeds_max_inline_wait(self):
        """TEST-POLLER-RL-07: Aborts immediately when hint > _MAX_INLINE_WAIT_S."""
        call_count = 0

        def fn():
            nonlocal call_count
            call_count += 1
            raise SystemExit("Chờ 70 giây để tiếp tục")

        with patch("app.domains.quant.application.daemon.poller.time.sleep"):
            result = _fetch_with_retry(fn, label="test")

        # Should have aborted after the first attempt (no further retries).
        assert result is None
        assert call_count == 1

    def test_falls_back_to_jitter_when_no_hint(self):
        """TEST-POLLER-RL-08: Falls back to jittered backoff when no hint present."""
        call_count = 0

        def fn():
            nonlocal call_count
            call_count += 1
            raise SystemExit("Rate limit exceeded.")

        with patch("app.domains.quant.application.daemon.poller.time.sleep"):
            result = _fetch_with_retry(fn, label="test")

        # All 3 attempts should run (no early abort).
        assert result is None
        assert call_count == 3
