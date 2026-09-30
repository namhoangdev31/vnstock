"""Lifecycle controller for the autonomous quant session daemon."""

import asyncio
import logging
from datetime import datetime
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, select

from app.api.deps import get_db
from app.core.enums import ForecastHorizon, SessionPhase
from app.core.models_base import VN_TZ
from app.domains.market_data.domain.models import StockOHLCVDaily
from app.domains.quant.application.daemon.clock import VietnamMarketClock
from app.domains.quant.application.daemon.dispatcher import SignalDispatcher
from app.domains.quant.application.daemon.poller import MarketDataPoller
from app.domains.quant.application.daemon.state import (
    DaemonCircuitBreaker,
    QuantDaemonState,
    STATE_POLL_INTERVALS,
)
from app.domains.quant.application.engines.ensemble_engine import EnsembleEngine
from app.domains.quant.application.schemas import EnsembleSignalRequest
from app.domains.quant.domain.models import TickFlowAggregated

logger = logging.getLogger(__name__)


class QuantDaemonController:
    def __init__(self) -> None:
        self.clock = VietnamMarketClock()
        self.state = QuantDaemonState()
        self.breaker = DaemonCircuitBreaker()
        self.poller = MarketDataPoller(self.breaker)
        self.dispatcher = SignalDispatcher()
        self._task: asyncio.Task[None] | None = None
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        async with self._lock:
            if self._task is not None and not self._task.done():
                return
            self.breaker.reset()
            self.state.running = True
            self.state.status = "running"
            self.state.last_started_at = datetime.now(VN_TZ)
            self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        async with self._lock:
            task = self._task
            self._task = None
            self.state.running = False
            self.state.status = "stopped"
            self.state.last_stopped_at = datetime.now(VN_TZ)
            if task is not None and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

    def pause(self) -> dict[str, Any]:
        self.state.paused = True
        self.state.status = "paused"
        return self.status()

    def resume(self) -> dict[str, Any]:
        self.state.paused = False
        self.state.status = "running" if self.state.running else "stopped"
        if self.breaker.is_open:
            self.breaker.reset()
        return self.status()

    def status(self) -> dict[str, Any]:
        clock_snapshot = self.clock.snapshot()
        self.state.session_phase = clock_snapshot.session_phase
        return self.state.as_dict(self.breaker)

    async def trigger_once(self) -> dict[str, Any]:
        await asyncio.to_thread(self._run_once)
        return self.status()

    async def _run_loop(self) -> None:
        try:
            while True:
                if not self.state.paused:
                    if self.breaker.is_open and not self.breaker.is_half_open:
                        # Circuit breaker open, wait for half-open cooldown
                        await asyncio.sleep(1.0)
                        continue
                    await asyncio.to_thread(self._run_once)

                # Get current phase for adaptive polling
                clock_snapshot = self.clock.snapshot()
                phase = SessionPhase(clock_snapshot.session_phase)
                poll_interval = STATE_POLL_INTERVALS.get(phase, 30.0)

                logger.debug(f"Phase {phase} → sleeping {poll_interval}s")
                await asyncio.sleep(poll_interval)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Quant daemon loop crashed")
            self.state.running = False
            self.state.status = "failed"
            raise

    def _run_once(self) -> None:
        now = datetime.now(VN_TZ)
        self.state.last_run_at = now
        clock_snapshot = self.clock.snapshot(now)
        phase = SessionPhase(clock_snapshot.session_phase)
        self.state.session_phase = clock_snapshot.session_phase

        try:
            with next(get_db()) as session:
                # Poll market data based on phase
                poll_result = self.poller.poll(
                    symbol="VN30F1M",
                    phase=phase,
                    limit_history=120,
                    limit_intraday=50,
                    limit_orderflow=40,
                )

                # Dispatch signals
                dispatch_result = self.dispatcher.dispatch(poll_result)

                self.breaker.record_success()
                self.state.last_error = None
                self.state.last_error_at = None
                self.state.last_snapshot = dispatch_result.__dict__
                self.state.degraded = dispatch_result.errors is not None and len(dispatch_result.errors) > 0
                self.state.status = "degraded" if self.state.degraded else "running"
                self.state.last_success_at = datetime.now(VN_TZ)
                if dispatch_result.forecast_id is not None:
                    self.state.last_forecast_id = str(dispatch_result.forecast_id)
        except Exception as exc:
            self.breaker.record_failure(exc)
            self.state.degraded = True
            self.state.status = "degraded" if self.state.running else "failed"
            self.state.last_error = str(exc)
            self.state.last_error_at = datetime.now(VN_TZ)
            self.state.last_degraded_reason = str(exc)
            logger.exception("Quant daemon run failed")


quant_daemon_controller = QuantDaemonController()

