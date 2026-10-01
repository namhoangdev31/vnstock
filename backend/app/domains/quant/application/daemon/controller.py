"""Autonomous quant daemon controller orchestrating the market session lifecycle."""

import asyncio
import logging
import random
import signal
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import SessionPhase
from app.core.models_base import VN_TZ
from app.domains.quant.application.daemon.clock import VietnamMarketClock
from app.domains.quant.application.daemon.dispatcher import SignalDispatcher
from app.domains.quant.application.daemon.event import MarketDataNormalizer
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
        normalizer: MarketDataNormalizer | None = None,
    ):
        """Initialize daemon with market clock, circuit breaker, engines, and normalizer."""
        self.clock = clock
        self.circuit_breaker = circuit_breaker
        self.poller = poller
        self.dispatcher = dispatcher
        self.normalizer = normalizer or MarketDataNormalizer()
        self.metrics: list[DaemonCycleMetrics] = []
        self.state = QuantDaemonState()
        self._task: asyncio.Task | None = None
        self.instance_id: str | None = None

    async def start(
        self,
        daemon_name: str = "quant-daemon",
        symbols: list[str] | None = None,
    ) -> None:
        """Start the daemon as a background asyncio.Task.

        Creates a persistent background task via asyncio.create_task so the
        polling loop runs concurrently without blocking the calling coroutine.
        Idempotent: calling start() while already running is a no-op.
        """
        if self.state.running:
            return

        started_at = datetime.now(VN_TZ)
        self.instance_id = f"{daemon_name}-{int(started_at.timestamp())}"
        self.state.running = True
        self.state.paused = False
        self.state.status = "running"
        self.state.last_started_at = started_at

        # Spawn the main loop as a fire-and-forget background task.
        # We pass db=None here — the run() loop handles the case gracefully
        # by skipping DB persistence when no session is available (offline mode).
        self._task = asyncio.create_task(
            self.run(
                db=None,  # type: ignore[arg-type]
                symbols=symbols or ["VN30F1M"],
                daemon_name=daemon_name,
            ),
            name=self.instance_id,
        )
        # TRD §6 — register OS signal handlers for graceful shutdown.
        self._register_signal_handlers()
        logger.info("Daemon started", extra={"instance_id": self.instance_id})

    def _register_signal_handlers(self) -> None:
        """Register SIGTERM / SIGINT handlers per TRD §6 Step 5.

        Both signals trigger an orderly stop: the background asyncio.Task is
        cancelled, the DaemonSessionLog is finalised, and the process exits
        cleanly.  Handlers are only registered when an asyncio event loop is
        running (i.e. inside a FastAPI lifespan / uvicorn worker).
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop (e.g. during unit tests) — skip silently.
            logger.debug("_register_signal_handlers: no running event loop, skipping")
            return

        def _handle_signal(sig: signal.Signals) -> None:
            logger.warning(
                f"Received {sig.name} — initiating graceful daemon shutdown",
                extra={"signal": sig.name, "instance_id": self.instance_id},
            )
            # Schedule stop() as a coroutine on the running loop so it runs
            # in the asyncio thread (signal handlers cannot be async).
            loop.create_task(self.stop(), name="daemon-signal-stop")

        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                loop.add_signal_handler(sig, lambda s=sig: _handle_signal(s))
                logger.debug(f"Registered {sig.name} handler")
            except (NotImplementedError, OSError):
                # Windows / environments that don't support add_signal_handler.
                logger.debug(f"Cannot register {sig.name} handler on this platform")

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

    def pause(self) -> dict[str, Any]:
        """Pause the daemon loop and return current status."""
        if self.state.running:
            self.state.paused = True
            self.state.status = "paused"
            logger.info("Daemon paused")
        return self.status()

    def resume(self) -> dict[str, Any]:
        """Resume the daemon loop, reset circuit breaker, and return current status."""
        if self.state.running and self.state.paused:
            self.state.paused = False
            self.state.status = "running"
            self.circuit_breaker.reset()
            logger.info("Daemon resumed")
        return self.status()

    def status(self) -> dict[str, Any]:
        """Get daemon operational status."""
        snapshot = self.clock.snapshot()
        self.state.session_phase = snapshot.session_phase.value

        return self.state.as_dict(self.circuit_breaker)

    async def trigger_once(self) -> dict[str, Any]:
        """Trigger a single execution cycle off-schedule."""
        snapshot = self.clock.snapshot()
        phase = snapshot.session_phase

        try:
            poll_result = self.poller.poll("VN30F1M", phase)
            context = self.normalizer.normalize(poll_result, as_of=snapshot.as_of)
            market_data = {
                "VN30F1M": {
                    "context": context,
                    "entry_price": context.entry_price,
                    "spot_price": context.spot_price,
                    "highs": context.highs,
                    "lows": context.lows,
                    "closes": context.closes,
                    "volumes": context.volumes,
                    "order_flow": context.order_flow,
                    "flows": context.flows,
                    "breadth": context.breadth,
                }
            }
            if context.event:
                self.state.last_event_id = context.event.event_id

            dispatch_result = await self.dispatcher.dispatch(
                phase=phase,
                symbols=["VN30F1M"],
                market_data=market_data,
                session_id=self.instance_id or "manual_trigger",
                cycle_id=self.state.last_cycle_id + 1,
            )
            self.state.last_run_at = datetime.now(VN_TZ)
            self.state.last_success_at = datetime.now(VN_TZ)
            self.state.last_error = None
            self.state.forecasts_created_count += dispatch_result.forecast_journals
            self.state.events_skipped_count += dispatch_result.skipped_signals
            self.state.duplicates_detected_count += dispatch_result.duplicates_detected
            if dispatch_result.signals:
                self.state.last_forecast_id = dispatch_result.signals[-1]["journal_id"]

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
        db: AsyncSession | None,
        symbols: list[str],
        daemon_name: str = "quant-daemon",
        run_duration_seconds: float | None = None,
    ) -> None:
        """
        Run daemon until stopped or run_duration_seconds elapses.

        Persists a DaemonSessionLog row to PostgreSQL at startup, updates the
        heartbeat every cycle, and finalises the status on exit.  When *db* is
        None (e.g. launched from start() without a request-scoped session) the
        persistence layer is silently skipped so the daemon can still run in
        memory-only mode.

        Args:
            db: AsyncSession for persistence (None → offline/no-persist mode)
            symbols: List of symbols to poll
            daemon_name: Name for logging/identification
            run_duration_seconds: Max runtime; None = run forever
        """
        start_time = datetime.now(VN_TZ)
        cycle_count = 0
        failure_count = 0
        # Reuse instance_id set by start(); fall back if run() called directly.
        instance_id = self.instance_id or f"{daemon_name}-{int(start_time.timestamp())}"
        self.instance_id = instance_id

        session_log = DaemonSessionLog(
            daemon_name=daemon_name,
            instance_id=instance_id,
            status="RUNNING",
            started_at=start_time,
        )

        # Persist the initial session log row if a DB session is available.
        if db is not None:
            db.add(session_log)
            await db.commit()

        logger.info(
            f"Daemon {daemon_name} started",
            extra={
                "daemon_name": daemon_name,
                "instance_id": instance_id,
                "symbols": symbols,
            },
        )

        try:
            while self.state.running:
                if self.state.paused:
                    # Keep the task alive while paused so resume() can clear
                    # the flag and continue the same daemon session.
                    await asyncio.sleep(1.0)
                    continue

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
                                if any(
                                    isinstance(e, dict)
                                    and e.get("error") == "circuit_breaker_open"
                                    for e in poll_result.errors
                                ):
                                    self.state.errors_by_type["circuit_breaker"] = (
                                        self.state.errors_by_type.get(
                                            "circuit_breaker", 0
                                        )
                                        + 1
                                    )
                                else:
                                    self.state.errors_by_type["api"] = (
                                        self.state.errors_by_type.get("api", 0) + 1
                                    )

                            context = self.normalizer.normalize(
                                poll_result=poll_result,
                                as_of=cycle_start,
                            )
                            if not context.is_valid:
                                self.state.errors_by_type["validation"] = (
                                    self.state.errors_by_type.get("validation", 0) + 1
                                )

                            all_market_data[symbol] = {
                                "context": context,
                                "entry_price": context.entry_price,
                                "spot_price": context.spot_price,
                                "highs": context.highs,
                                "lows": context.lows,
                                "closes": context.closes,
                                "volumes": context.volumes,
                                "order_flow": context.order_flow,
                                "flows": context.flows,
                                "breadth": context.breadth,
                            }
                            if context.event:
                                self.state.last_event_id = context.event.event_id

                        except SystemExit as se:
                            # vnai sys.exit() safety net — should already be
                            # intercepted in poller, but guard here too.
                            poll_errors[symbol] = [f"rate-limit-sysexit: {se}"]
                            self.state.errors_by_type["api"] = (
                                self.state.errors_by_type.get("api", 0) + 1
                            )
                            logger.warning(
                                f"[daemon] SystemExit from poller for {symbol} — rate limit hit",
                                extra={"symbol": symbol, "phase": phase.value},
                            )
                        except Exception as poll_exc:
                            poll_errors[symbol] = [str(poll_exc)]
                            self.state.errors_by_type["api"] = (
                                self.state.errors_by_type.get("api", 0) + 1
                            )
                    polled_count = len([s for s in symbols if s not in poll_errors])

                    # Dispatch signals and simulate orders
                    sync_db = getattr(db, "sync_session", None) or (
                        db if not hasattr(db, "sync_session") else None
                    )
                    dispatch_result = await self.dispatcher.dispatch(
                        phase=phase,
                        symbols=symbols,
                        market_data=all_market_data,
                        session_id=instance_id,
                        cycle_id=cycle_count,
                        db=sync_db,
                    )

                    self.state.last_cycle_id = cycle_count
                    self.state.forecasts_created_count += (
                        dispatch_result.forecast_journals
                    )
                    self.state.events_skipped_count += dispatch_result.skipped_signals
                    self.state.duplicates_detected_count += (
                        dispatch_result.duplicates_detected
                    )
                    if dispatch_result.errors:
                        self.state.errors_by_type["engine"] = (
                            self.state.errors_by_type.get("engine", 0)
                            + len(dispatch_result.errors)
                        )
                    if dispatch_result.signals:
                        self.state.last_forecast_id = dispatch_result.signals[-1][
                            "journal_id"
                        ]

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

                    # Persist heartbeat update to DB (every cycle).
                    if db is not None:
                        db.add(session_log)
                        await db.commit()

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

                    # Persist failure state to DB.
                    if db is not None:
                        try:
                            db.add(session_log)
                            await db.commit()
                        except Exception as db_err:
                            logger.warning(
                                f"Failed to persist session log on error: {db_err}"
                            )

                    # Check circuit breaker
                    self.circuit_breaker.record_failure(e)
                    if self.circuit_breaker.is_open:
                        logger.warning(
                            "Circuit breaker OPEN; entering cooldown",
                            extra={"opened_at": self.circuit_breaker.opened_at},
                        )

                    # Jittered backoff on error (TRD §4.1)
                    base_interval = STATE_POLL_INTERVALS.get(
                        SessionPhase.OVERNIGHT_SIMULATION, 60.0
                    )
                    jitter = random.uniform(0.0, base_interval * 0.2)
                    await asyncio.sleep(base_interval + jitter)

        except asyncio.CancelledError:
            logger.info(f"Daemon {daemon_name} cancelled")
            session_log.status = "CANCELLED"
        except SystemExit as se:
            # Catch sys.exit() that escapes poller — should not happen after
            # the poller fix, but guard here to prevent uvicorn from dying.
            logger.error(
                f"Daemon {daemon_name} intercepted SystemExit (rate-limit): {se}",
                exc_info=True,
            )
            session_log.status = "CRASHED"
            session_log.last_error = f"SystemExit: {se}"
            self.state.status = "crashed"
            self.state.last_error = f"[rate-limit] {se}"
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

            # Final DB flush — record the terminal state.
            if db is not None:
                try:
                    db.add(session_log)
                    await db.commit()
                except Exception as db_err:
                    logger.warning(f"Failed to persist final session log: {db_err}")

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
