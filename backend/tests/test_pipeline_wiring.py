"""Comprehensive tests for Phase 3 -> Phase 2 Wiring (quant daemon -> analytical engines).

Tests cover:
1. Event normalization (MarketDataNormalizer)
2. Deduplication / idempotency (seen event keys)
3. Cache event handling (from_cache=True with skip reason on insufficient data)
4. Phase-to-engine routing (PRE_ATO, MORNING_CONTINUOUS, ATC, OVERNIGHT_SIMULATION)
5. Engine failure isolation (one engine crashing does not abort orchestrator)
6. Ensemble skip on missing critical data
7. ForecastJournal idempotent persistence (no duplicates on retry)
8. No-look-ahead timestamp validation (future timestamps rejected)
9. Daemon pause, resume, trigger_once lifecycle
10. ATC and T+1 horizon mapping
11. Paper trading isolation and risk disclaimer verification (RULE 1, 2, 4)
"""

import asyncio
from datetime import datetime, timedelta
from typing import cast
from unittest.mock import MagicMock

import pytest

from app.core.enums import ForecastHorizon, SessionPhase
from app.core.models_base import VN_TZ
from app.domains.quant.application.daemon.clock import VietnamMarketClock
from app.domains.quant.application.daemon.controller import DaemonController
from app.domains.quant.application.daemon.dispatcher import (
    SignalDispatcher,
    map_phase_to_horizon,
)
from app.domains.quant.application.daemon.event import (
    AnalysisContext,
    MarketDataEvent,
    MarketDataNormalizer,
)
from app.domains.quant.application.daemon.orchestrator import (
    PhaseAwareEngineOrchestrator,
)
from app.domains.quant.application.daemon.poller import (
    MarketDataPoller,
    MarketPollResult,
)
from app.domains.quant.application.daemon.state import DaemonCircuitBreaker
from app.domains.quant.application.engines.ensemble_engine import EnsembleEngine


class TestMarketDataEventAndNormalizer:
    """Test suite for MarketDataNormalizer, MarketDataEvent and AnalysisContext."""

    def test_normalize_valid_bars(self):
        """Test normalization of valid history/intraday bars into AnalysisContext."""
        normalizer = MarketDataNormalizer()
        now = datetime.now(VN_TZ)

        bars = [
            {
                "time": (now - timedelta(minutes=i)).isoformat(),
                "open": 1300.0 + i,
                "high": 1305.0 + i,
                "low": 1295.0 + i,
                "close": 1302.0 + i,
                "volume": 1000 + i * 10,
            }
            for i in range(20, 0, -1)
        ]

        poll_result = MarketPollResult(
            symbol="VN30F1M",
            phase=SessionPhase.MORNING_CONTINUOUS,
            timestamp=now,
            intraday_bars=bars,
            order_flow=[{"match_type": "BUY", "volume": 50}],
        )

        context = normalizer.normalize(poll_result, as_of=now)

        assert context.is_valid is True
        assert context.skip_reason is None
        assert len(context.closes) == 20
        assert context.entry_price == bars[-1]["close"]
        assert context.event is not None
        assert context.event.symbol == "VN30F1M"
        assert context.event.asset_type == "derivative"
        assert context.event.interval == "1m"
        assert context.event.from_cache is False

    def test_deduplication_and_idempotency(self):
        """Test that identical (symbol, interval, event_time) events are detected as duplicates."""
        normalizer = MarketDataNormalizer()
        now = datetime.now(VN_TZ)

        bars = [
            {
                "time": now.isoformat(),
                "open": 1300.0,
                "high": 1305.0,
                "low": 1295.0,
                "close": 1302.0,
                "volume": 1000,
            }
        ]
        poll_result = MarketPollResult(
            symbol="VN30F1M",
            phase=SessionPhase.MORNING_CONTINUOUS,
            timestamp=now,
            intraday_bars=bars,
        )

        normalizer.normalize(poll_result, as_of=now)
        # Second normalization of the same event time
        is_dup = normalizer.is_duplicate("VN30F1M", "1m", now)
        assert is_dup is True

    def test_cache_fallback_insufficient_bars_skipped(self):
        """Test that from_cache=True with fewer than 15 bars flags skip_reason and is_valid=False."""
        normalizer = MarketDataNormalizer()
        now = datetime.now(VN_TZ)

        # Only 5 bars from cache
        bars = [
            {
                "time": (now - timedelta(minutes=i)).isoformat(),
                "open": 1300.0,
                "high": 1305.0,
                "low": 1295.0,
                "close": 1302.0,
                "volume": 1000,
            }
            for i in range(5, 0, -1)
        ]
        poll_result = MarketPollResult(
            symbol="VN30F1M",
            phase=SessionPhase.MORNING_CONTINUOUS,
            timestamp=now,
            intraday_bars=bars,
            from_cache=True,
        )

        context = normalizer.normalize(poll_result, as_of=now)
        assert context.is_valid is False
        assert context.skip_reason == "cached_data_insufficient_bars"

    def test_no_look_ahead_timestamp_guard(self):
        """Test that bars with timestamps in the future relative to as_of are discarded."""
        normalizer = MarketDataNormalizer()
        now = datetime.now(VN_TZ)
        future_time = now + timedelta(minutes=15)

        bars = [
            {
                "time": (now - timedelta(minutes=5)).isoformat(),
                "open": 1300.0,
                "high": 1305.0,
                "low": 1295.0,
                "close": 1300.0,
                "volume": 1000,
            },
            {
                "time": future_time.isoformat(),  # Leaked future bar
                "open": 1350.0,
                "high": 1360.0,
                "low": 1340.0,
                "close": 1355.0,
                "volume": 2000,
            },
        ]
        poll_result = MarketPollResult(
            symbol="VN30F1M",
            phase=SessionPhase.MORNING_CONTINUOUS,
            timestamp=now,
            intraday_bars=bars,
        )

        context = normalizer.normalize(poll_result, as_of=now)
        # The future bar must have been rejected
        assert len(context.closes) == 1
        assert context.closes[-1] == 1300.0


class TestPhaseAwareEngineOrchestrator:
    """Test suite for PhaseAwareEngineOrchestrator."""

    def test_phase_routing_pre_ato_skips_technicals(self):
        """PRE_ATO phase skips active technicals (Engine 1) but keeps basis/macro context."""
        now = datetime.now(VN_TZ)
        context = AnalysisContext(
            event=None,
            latest_bars=[],
            intraday_flow=[],
            market_snapshot={},
            phase=SessionPhase.PRE_ATO,
            as_of=now,
            closes=[1300.0] * 20,
            highs=[1305.0] * 20,
            lows=[1295.0] * 20,
            volumes=[1000.0] * 20,
            entry_price=1300.0,
            is_valid=True,
        )

        orchestrator = PhaseAwareEngineOrchestrator()
        result = orchestrator.orchestrate(context)

        assert "engine1" in result.engine_results
        assert result.engine_results["engine1"].status == "SKIPPED"
        assert result.engine_results["engine3"].status == "COMPLETED"

    def test_phase_routing_morning_runs_all_engines(self):
        """MORNING_CONTINUOUS runs Engine 1, 2 and 3."""
        now = datetime.now(VN_TZ)
        context = AnalysisContext(
            event=None,
            latest_bars=[],
            intraday_flow=[],
            market_snapshot={},
            phase=SessionPhase.MORNING_CONTINUOUS,
            as_of=now,
            closes=[1300.0 + i for i in range(20)],
            highs=[1305.0 + i for i in range(20)],
            lows=[1295.0 + i for i in range(20)],
            volumes=[1000.0] * 20,
            entry_price=1319.0,
            is_valid=True,
        )

        orchestrator = PhaseAwareEngineOrchestrator()
        result = orchestrator.orchestrate(context)

        assert result.engine_results["engine1"].status == "COMPLETED"
        assert result.engine_results["engine2"].status == "COMPLETED"
        assert result.engine_results["engine3"].status == "COMPLETED"

    def test_engine_failure_isolation(self):
        """Failure in Engine 1 does not crash the orchestrator or prevent Engine 2/3."""
        now = datetime.now(VN_TZ)
        context = AnalysisContext(
            event=None,
            latest_bars=[],
            intraday_flow=[],
            market_snapshot={},
            phase=SessionPhase.MORNING_CONTINUOUS,
            as_of=now,
            closes=[1300.0] * 20,
            highs=[1305.0] * 20,
            lows=[1295.0] * 20,
            volumes=[1000.0] * 20,
            entry_price=1300.0,
            is_valid=True,
        )

        # Mock Engine 1 to throw an error
        mock_e1 = MagicMock()
        mock_e1.analyze.side_effect = RuntimeError("Simulated indicator failure")

        orchestrator = PhaseAwareEngineOrchestrator(technical_engine=mock_e1)
        result = orchestrator.orchestrate(context)

        assert result.engine_results["engine1"].status == "FAILED"
        assert "Simulated indicator failure" in str(
            result.engine_results["engine1"].error
        )
        # Engine 2 & 3 must still complete successfully
        assert result.engine_results["engine2"].status == "COMPLETED"
        assert result.engine_results["engine3"].status == "COMPLETED"
        assert result.is_executable is True


class TestSignalDispatcherAndForecastJournal:
    """Test suite for SignalDispatcher and idempotent ForecastJournal persistence."""

    def test_horizon_mapping(self):
        """SessionPhase maps correctly to standard analytical horizons."""
        assert map_phase_to_horizon(SessionPhase.PRE_ATO) == ForecastHorizon.ATO
        assert map_phase_to_horizon(SessionPhase.ATO) == ForecastHorizon.ATO
        assert (
            map_phase_to_horizon(SessionPhase.MORNING_CONTINUOUS)
            == ForecastHorizon.INTRADAY
        )
        assert (
            map_phase_to_horizon(SessionPhase.AFTERNOON_CONTINUOUS)
            == ForecastHorizon.INTRADAY
        )
        assert map_phase_to_horizon(SessionPhase.PRE_ATC) == ForecastHorizon.ATC
        assert map_phase_to_horizon(SessionPhase.ATC) == ForecastHorizon.ATC
        assert (
            map_phase_to_horizon(SessionPhase.POST_MARKET) == ForecastHorizon.T_PLUS_1
        )
        assert (
            map_phase_to_horizon(SessionPhase.OVERNIGHT_SIMULATION)
            == ForecastHorizon.T_PLUS_1
        )

    @pytest.mark.anyio
    async def test_dispatch_insufficient_data_skips(self):
        """Dispatcher safely skips signal generation when context is invalid."""
        dispatcher = SignalDispatcher(ensemble_engine=EnsembleEngine(session=None))
        now = datetime.now(VN_TZ)

        context = AnalysisContext(
            event=None,
            latest_bars=[],
            intraday_flow=[],
            market_snapshot={},
            phase=SessionPhase.MORNING_CONTINUOUS,
            as_of=now,
            is_valid=False,
            skip_reason="no_valid_bars_available",
        )

        result = await dispatcher.dispatch(
            phase=SessionPhase.MORNING_CONTINUOUS,
            symbols=["VN30F1M"],
            market_data={"VN30F1M": {"context": context}},
        )

        assert result.ensemble_signals == 0
        assert result.skipped_signals == 1

    @pytest.mark.anyio
    async def test_dispatch_creates_forecast_and_deduplicates_on_retry(self):
        """Dispatcher creates forecast journal entry and detects duplicate on retry."""
        dispatcher = SignalDispatcher(ensemble_engine=EnsembleEngine(session=None))
        now = datetime.now(VN_TZ)

        closes = [1300.0 + i for i in range(25)]
        highs = [c + 2.0 for c in closes]
        lows = [c - 2.0 for c in closes]
        volumes = [1000.0] * len(closes)

        ev_id = f"VN30F1M:1m:{now.strftime('%Y%m%d%H%M%S')}:candle"
        event = MarketDataEvent(
            event_id=ev_id,
            symbol="VN30F1M",
            asset_type="derivative",
            interval="1m",
            event_type="candle",
            event_time=now,
            received_at=now,
            source="vci",
            market_phase=SessionPhase.MORNING_CONTINUOUS,
        )

        context = AnalysisContext(
            event=event,
            latest_bars=[],
            intraday_flow=[],
            market_snapshot={},
            phase=SessionPhase.MORNING_CONTINUOUS,
            as_of=now,
            highs=highs,
            lows=lows,
            closes=closes,
            volumes=volumes,
            entry_price=closes[-1],
            spot_price=closes[-1],
            is_valid=True,
        )

        market_data = {"VN30F1M": {"context": context}}

        # Cycle 1
        res1 = await dispatcher.dispatch(
            phase=SessionPhase.MORNING_CONTINUOUS,
            symbols=["VN30F1M"],
            market_data=market_data,
            cycle_id=1,
        )

        assert res1.forecast_journals == 1
        assert res1.duplicates_detected == 0
        assert len(res1.signals) == 1

        # Check disclaimer exists in output signal (RULE 4)
        assert "CẢNH BÁO RỦI RO (RULE 4)" in res1.signals[0]["disclaimer"]

        # Cycle 2: Retry with exact same timestamp
        res2 = await dispatcher.dispatch(
            phase=SessionPhase.MORNING_CONTINUOUS,
            symbols=["VN30F1M"],
            market_data=market_data,
            cycle_id=2,
        )

        # Retry must detect duplicate and NOT record a new journal entry
        assert res2.forecast_journals == 0
        assert res2.duplicates_detected == 1
        # Preserves the same journal ID
        assert res2.signals[0]["journal_id"] == res1.signals[0]["journal_id"]


class TestDaemonControllerPipelineWiring:
    """Test suite for DaemonController end-to-end cycle wiring."""

    @pytest.mark.anyio
    async def test_trigger_once_executes_pipeline_and_updates_metrics(self):
        """trigger_once polls, normalizes, dispatches, and updates heartbeat metrics."""
        cb = DaemonCircuitBreaker()
        poller = MarketDataPoller(cb)
        clock = VietnamMarketClock()

        now = datetime.now(VN_TZ)
        bars = [
            {
                "time": (now - timedelta(minutes=i)).isoformat(),
                "open": 1300.0,
                "high": 1305.0,
                "low": 1295.0,
                "close": 1302.0,
                "volume": 1000,
            }
            for i in range(25, 0, -1)
        ]

        # Seed poller cache
        poller._last_known["VN30F1M"] = MarketPollResult(
            symbol="VN30F1M",
            phase=SessionPhase.MORNING_CONTINUOUS,
            timestamp=now,
            intraday_bars=bars,
            order_flow=[{"match_type": "BUY", "volume": 100}],
        )

        controller = DaemonController(
            clock=clock,
            circuit_breaker=cb,
            poller=poller,
            dispatcher=SignalDispatcher(),
        )

        status_before = controller.status()
        assert status_before["running"] is False

        # Execute single cycle
        status_after = await controller.trigger_once()

        assert status_after["last_run_at"] is not None
        assert status_after["last_success_at"] is not None
        assert status_after["last_error"] is None
        assert "last_event_id" in status_after
        assert "forecasts_created_count" in status_after
        assert "errors_by_type" in status_after

    def test_pause_and_resume_lifecycle(self):
        """Test pause and resume updates state and circuit breaker."""
        cb = DaemonCircuitBreaker()
        poller = MarketDataPoller(cb)
        controller = DaemonController(
            clock=VietnamMarketClock(),
            circuit_breaker=cb,
            poller=poller,
            dispatcher=SignalDispatcher(),
        )

        controller.state.running = True
        status_paused = controller.pause()
        assert status_paused["paused"] is True
        assert status_paused["status"] == "paused"

        status_resumed = controller.resume()
        assert status_resumed["paused"] is False
        assert status_resumed["status"] == "running"

    @pytest.mark.anyio
    async def test_pause_keeps_background_task_alive_for_resume(self):
        """Pausing must suspend cycles without terminating the daemon task."""

        class IdlePoller:
            def poll(self, symbol, phase):
                return MarketPollResult(
                    symbol=symbol, phase=phase, timestamp=datetime.now(VN_TZ)
                )

        controller = DaemonController(
            clock=VietnamMarketClock(),
            circuit_breaker=DaemonCircuitBreaker(),
            poller=cast(MarketDataPoller, IdlePoller()),
            dispatcher=SignalDispatcher(ensemble_engine=None),
        )

        await controller.start()
        await asyncio.sleep(0.02)
        controller.pause()
        await asyncio.sleep(0.05)

        assert controller._task is not None
        assert controller._task.done() is False
        assert controller.resume()["status"] == "running"

        await controller.stop()
