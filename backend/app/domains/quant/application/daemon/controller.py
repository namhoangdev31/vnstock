"""Autonomous quant daemon controller orchestrating the market session lifecycle."""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import SessionPhase
from app.core.models_base import VN_TZ
from app.domains.quant.application.daemon.clock import VietnamMarketClock
from app.domains.quant.application.daemon.dispatcher import SignalDispatcher
from app.domains.quant.application.daemon.poller import MarketDataPoller
from app.domains.quant.application.daemon.state import (
    STATE_POLL_INTERVALS,
    DaemonCircuitBreaker,
    QuantDaemonState,
)
from app.domains.quant.domain.models import DaemonSessionLog

logger = logging.getLogger(__name__)


@dataclass
class DaemonCycleMetrics:
    """Snapshot of a single daemon cycle's performance."""

    phase: SessionPhase
    cycle_num: int
    polled_symbols: int
    signals_generated: int
    orders_simulated: int
    errors: dict[str, Any]
    duration_ms: float
    poll_interval_next: float


class DaemonController:
    """Orchestrates background polling and signal dispatch."""

    def __init__(
        self,
        clock: VietnamMarketClock,
        circuit_breaker: DaemonCircuitBreaker,
        poller: MarketDataPoller,
        dispatcher: SignalDispatcher,
    ):
        """Initialize daemon with market clock, circuit breaker, and engines."""
        self.clock = clock
        self.circuit_breaker = circuit_breaker
        self.poller = poller
        self.dispatcher = dispatcher
        self.metrics: list[DaemonCycleMetrics] = []
        self.state = QuantDaemonState()
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start the daemon in background."""
        if self.state.running:
            return

        self.state.running = True
        self.state.paused = False
        self.state.status = "running"
        self.state.last_started_at = datetime.now(VN_TZ)

        logger.info("Daemon started")

    async def stop(self) -> None:
        """Stop the daemon."""
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        self.state.running = False
        self.state.paused = False
        self.state.status = "stopped"
        self.state.last_stopped_at = datetime.now(VN_TZ)

        logger.info("Daemon stopped")

    def pause(self) -> None:
        """Pause the daemon loop."""
        if self.state.running:
            self.state.paused = True
            self.state.status = "paused"
            logger.info("Daemon paused")

    def resume(self) -> None:
        """Resume the daemon loop and reset circuit breaker."""
        if self.state.running and self.state.paused:
            self.state.paused = False
            self.state.status = "running"
            self.circuit_breaker.reset()
            logger.info("Daemon resumed")

    def status(self) -> dict[str, Any]:
        """Get daemon operational status."""
        snapshot = self.clock.snapshot()
        self.state.session_phase = snapshot.session_phase.value

        return self.state.as_dict(self.circuit_breaker)

    async def trigger_once(self) -> dict[str, Any]:
        """Trigger a single execution cycle off-schedule."""
        snapshot = self.clock.snapshot()
        phase = snapshot.session_phase

        # Run one cycle (non-persistent for manual trigger)
        # In production, this would use db session
        try:
            dispatch_result = await self.dispatcher.dispatch(
                phase=phase,
                symbols=["VN30F1M"],
                market_data={},
            )
            self.state.last_run_at = datetime.now(VN_TZ)
            self.state.last_success_at = datetime.now(VN_TZ)
            self.state.last_error = None
            logger.info(
                f"Manual trigger executed: phase={phase.value}, "
                f"signals={dispatch_result.ensemble_signals}, "
                f"orders={dispatch_result.simulation_orders}"
            )
        except Exception as e:
            self.state.last_error_at = datetime.now(VN_TZ)
            self.state.last_error = str(e)
            self.circuit_breaker.record_failure(e)
            logger.error(f"Manual trigger failed: {e}", exc_info=True)

        return self.status()

    async def run(
        self,
        db: AsyncSession,
        symbols: list[str],
        daemon_name: str = "quant-daemon",
        run_duration_seconds: float | None = None,
    ) -> None:
        """
        Run daemon until stopped or run_duration_seconds elapses.

        Args:
            db: AsyncSession for persistence
            symbols: List of symbols to poll
            daemon_name: Name for logging/identification
            run_duration_seconds: Max runtime; None = run forever
        """
        start_time = datetime.now(VN_TZ)
        cycle_count = 0
        failure_count = 0
        instance_id = f"{daemon_name}-{int(start_time.timestamp())}"

        session_log = DaemonSessionLog(
            daemon_name=daemon_name,
            instance_id=instance_id,
            status="RUNNING",
            started_at=start_time,
        )

        logger.info(
            f"Daemon {daemon_name} started",
            extra={
                "daemon_name": daemon_name,
                "instance_id": instance_id,
                "symbols": symbols,
            },
        )

        try:
            while self.state.running and not self.state.paused:
                if (
                    run_duration_seconds
                    and (datetime.now(VN_TZ) - start_time).total_seconds()
                    > run_duration_seconds
                ):
                    logger.info(
                        f"Daemon {daemon_name} reached run_duration_seconds",
                        extra={"duration_seconds": run_duration_seconds},
                    )
                    break

                cycle_count += 1
                cycle_start = datetime.now(VN_TZ)

                try:
                    # Get current phase
                    snapshot = self.clock.snapshot()
                    phase = snapshot.session_phase
                    self.state.session_phase = phase.value

                    logger.debug(
                        f"Daemon cycle {cycle_count}: {phase.value}",
                        extra={"cycle": cycle_count, "phase": phase.value},
                    )

                    # Poll market data (single-symbol poll; aggregate for multi-symbol)
                    poll_errors: dict[str, Any] = {}
                    all_market_data: dict[str, Any] = {}
                    for symbol in symbols:
                        try:
                            poll_result = self.poller.poll(symbol, phase)
                            if poll_result.errors:
                                poll_errors[symbol] = poll_result.errors
                            # Extract market data from poll result
                            all_market_data[symbol] = {
                                "entry_price": None,
                                "spot_price": None,
                                "highs": poll_result.history_bars,
                                "lows": None,
                                "closes": None,
                                "volumes": None,
                                "order_flow": poll_result.order_flow,
                                "flows": None,
                                "breadth": None,
                            }
                        except Exception as poll_exc:
                            poll_errors[symbol] = [str(poll_exc)]
                    polled_count = len([s for s in symbols if s not in poll_errors])

                    # Dispatch signals and simulate orders
                    dispatch_result = await self.dispatcher.dispatch(
                        phase=phase,
                        symbols=symbols,
                        market_data=all_market_data,
                    )

                    cycle_duration = (
                        datetime.now(VN_TZ) - cycle_start
                    ).total_seconds() * 1000

                    # Get adaptive poll interval from state
                    next_interval = STATE_POLL_INTERVALS.get(phase, 60.0)

                    metric = DaemonCycleMetrics(
                        phase=phase,
                        cycle_num=cycle_count,
                        polled_symbols=polled_count,
                        signals_generated=dispatch_result.ensemble_signals,
                        orders_simulated=dispatch_result.simulation_orders,
                        errors={**poll_errors, **dispatch_result.errors},
                        duration_ms=cycle_duration,
                        poll_interval_next=next_interval,
                    )
                    self.metrics.append(metric)

                    logger.info(
                        f"Daemon cycle {cycle_count} completed in {cycle_duration:.1f}ms",
                        extra=metric.__dict__,
                    )

                    # Update session log heartbeat
                    session_log.last_heartbeat_at = datetime.now(VN_TZ)
                    session_log.last_phase = phase.value
                    session_log.cycle_count = cycle_count

                    # Reset failure count on success
                    failure_count = 0
                    self.circuit_breaker.record_success()
                    self.state.last_success_at = datetime.now(VN_TZ)

                    await asyncio.sleep(next_interval)

                except Exception as e:
                    failure_count += 1
                    session_log.failure_count = failure_count
                    session_log.last_error = str(e)
                    self.state.last_error_at = datetime.now(VN_TZ)
                    self.state.last_error = str(e)

                    logger.error(
                        f"Daemon cycle {cycle_count} failed: {e}",
                        exc_info=True,
                        extra={"cycle": cycle_count, "failure_count": failure_count},
                    )

                    # Check circuit breaker
                    self.circuit_breaker.record_failure(e)
                    if self.circuit_breaker.is_open:
                        logger.warning(
                            "Circuit breaker OPEN; entering cooldown",
                            extra={"opened_at": self.circuit_breaker.opened_at},
                        )

                    # Back off on error
                    await asyncio.sleep(
                        STATE_POLL_INTERVALS.get(
                            SessionPhase.OVERNIGHT_SIMULATION, 60.0
                        )
                    )

        except asyncio.CancelledError:
            logger.info(f"Daemon {daemon_name} cancelled")
            session_log.status = "CANCELLED"
        except Exception as e:
            logger.error(f"Daemon {daemon_name} crashed: {e}", exc_info=True)
            session_log.status = "CRASHED"
            session_log.last_error = str(e)
            self.state.status = "crashed"
            self.state.last_error = str(e)
        finally:
            session_log.stopped_at = datetime.now(VN_TZ)
            if session_log.status not in ("CANCELLED", "CRASHED"):
                session_log.status = "STOPPED"

            self.state.running = False
            self.state.status = "stopped"
            self.state.last_stopped_at = datetime.now(VN_TZ)

            logger.info(
                f"Daemon {daemon_name} stopped after {cycle_count} cycles",
                extra={
                    "cycles": cycle_count,
                    "failures": failure_count,
                    "status": session_log.status,
                },
            )
