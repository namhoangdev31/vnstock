"""Autonomous quant daemon controller orchestrating the market session lifecycle."""

import asyncio
import logging
import random
import signal
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlmodel import Session

from app.core.enums import SessionPhase
from app.core.models_base import VN_TZ
from app.domains.quant.application.daemon.clock import VietnamMarketClock
from app.domains.quant.application.daemon.dispatcher import SignalDispatcher
from app.domains.quant.application.daemon.event import MarketDataNormalizer
from app.domains.quant.application.daemon.lease import PostgresAdvisoryLease
from app.domains.quant.application.daemon.poller import MarketDataPoller
from app.domains.quant.application.daemon.scheduled_hooks import dispatch_phase_hooks
from app.domains.quant.application.daemon.state import (
    STATE_POLL_INTERVALS,
    DaemonCircuitBreaker,
    QuantDaemonState,
)
from app.domains.quant.application.daemon.symbol_registry import SymbolRegistry
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
        session_factory: Callable[[], Session] | None = None,
        lease: PostgresAdvisoryLease | None = None,
        symbol_registry: SymbolRegistry | None = None,
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
        self.session_factory = session_factory
        self.lease = lease
        # Symbol registry: manages active symbols across asset classes.
        # Defaults to a new registry seeded with always-on symbols (VN30F1M).
        self.symbol_registry: SymbolRegistry = symbol_registry or SymbolRegistry()

    @staticmethod
    def _apply_session_log_persistence(
        session: Session, session_log: DaemonSessionLog, create: bool = False
    ) -> None:
        """Safely apply session log changes to a database session without letting

        the in-memory controller session_log become attached or expired.
        """
        s_dict = session_log.__dict__
        log_id = s_dict.get("id") or getattr(session_log, "id", None)
        if log_id is None:
            return

        if create:
            record = DaemonSessionLog(
                id=log_id,
                daemon_name=s_dict.get("daemon_name", "quant-background-daemon"),
                instance_id=s_dict.get("instance_id", str(log_id)),
                status=s_dict.get("status", "RUNNING"),
                started_at=s_dict.get("started_at") or datetime.now(VN_TZ),
                stopped_at=s_dict.get("stopped_at"),
                last_heartbeat_at=s_dict.get("last_heartbeat_at"),
                last_phase=s_dict.get("last_phase"),
                cycle_count=s_dict.get("cycle_count", 0),
                failure_count=s_dict.get("failure_count", 0),
                last_error=s_dict.get("last_error"),
                metadata_info=dict(s_dict.get("metadata_info") or {}),
            )
            session.add(record)
        else:
            stored = session.get(DaemonSessionLog, log_id)
            if stored is not None:
                for field_name in (
                    "status",
                    "stopped_at",
                    "last_heartbeat_at",
                    "last_phase",
                    "cycle_count",
                    "failure_count",
                    "last_error",
                    "metadata_info",
                ):
                    if field_name in s_dict:
                        setattr(stored, field_name, s_dict[field_name])
                session.add(stored)
        session.commit()

    def _persist_session_log(
        self, session_log: DaemonSessionLog, create: bool = False
    ) -> None:
        """Persist one daemon heartbeat using a short-lived sync DB session."""
        if self.session_factory is None:
            return
        with self.session_factory() as session:
            self._apply_session_log_persistence(session, session_log, create=create)

    async def start(
        self,
        daemon_name: str = "quant-daemon",
        symbols: list[str] | None = None,
        force: bool = False,
    ) -> None:
        """Start the daemon as a background asyncio.Task.

        If another worker holds the advisory lease, enters standby mode with
        a background supervisor that probes the lease and promotes to active
        leader as soon as the other worker terminates (e.g. rolling deploy).
        """
        if self.state.running and self.state.status == "running" and not force:
            return

        if self._task and not self._task.done():
            if force:
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass
            elif self.state.status == "standby":
                return

        if self.lease is not None:
            acquired = await asyncio.to_thread(self.lease.acquire, force=force)
            if not acquired:
                self.state.running = True
                self.state.status = "standby"
                logger.warning(
                    f"Daemon {daemon_name} start deferred to STANDBY: another worker holds the lease. "
                    "Starting background standby supervisor to monitor and auto-promote..."
                )
                self._task = asyncio.create_task(
                    self._standby_loop(daemon_name=daemon_name, symbols=symbols),
                    name=f"{daemon_name}-standby",
                )
                self._register_signal_handlers()
                return

        started_at = datetime.now(VN_TZ)
        self.instance_id = f"{daemon_name}-{int(started_at.timestamp())}"
        self.state.running = True
        self.state.paused = False
        self.state.status = "running"
        self.state.last_started_at = started_at

        # Determine symbols: caller-supplied list overrides registry.
        # If no override, derive from the SymbolRegistry so all asset classes
        # (derivatives + equities) are polled from the start.
        effective_symbols = (
            symbols
            if symbols is not None
            else self.symbol_registry.get_active_symbols()
        )

        # Spawn the main loop as a fire-and-forget background task.
        self._task = asyncio.create_task(
            self.run(
                db=None,
                symbols=effective_symbols,
                daemon_name=daemon_name,
            ),
            name=self.instance_id,
        )
        # TRD §6 — register OS signal handlers for graceful shutdown.
        self._register_signal_handlers()
        logger.info(
            "Daemon started",
            extra={
                "instance_id": self.instance_id,
                "symbols": effective_symbols,
                "registry_summary": self.symbol_registry.summary(),
            },
        )

    async def _standby_loop(
        self,
        daemon_name: str = "quant-daemon",
        symbols: list[str] | None = None,
        probe_interval: float = 5.0,
    ) -> None:
        """Standby supervisor task: periodically probes the advisory lease and

        promotes from standby to active leader as soon as the lease becomes available.
        """
        logger.info(
            f"Daemon {daemon_name} standby supervisor active (probing lease every {probe_interval}s)"
        )
        try:
            while self.state.running and self.state.status == "standby":
                await asyncio.sleep(probe_interval)
                if not self.state.running:
                    break
                if self.lease is not None:
                    acquired = await asyncio.to_thread(self.lease.acquire)
                    if acquired:
                        logger.info(
                            f"Daemon {daemon_name} acquired advisory lease from standby! "
                            "Promoting to active leader..."
                        )
                        started_at = datetime.now(VN_TZ)
                        self.instance_id = (
                            f"{daemon_name}-{int(started_at.timestamp())}"
                        )
                        self.state.status = "running"
                        self.state.last_started_at = started_at
                        effective_symbols = (
                            symbols
                            if symbols is not None
                            else self.symbol_registry.get_active_symbols()
                        )
                        await self.run(
                            db=None,
                            symbols=effective_symbols,
                            daemon_name=daemon_name,
                        )
                        break
        except asyncio.CancelledError:
            logger.info(f"Daemon {daemon_name} standby supervisor cancelled")
        finally:
            if self.state.status == "standby":
                self.state.running = False
                self.state.status = "stopped"

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
            except (NotImplementedError, OSError, RuntimeError):
                # Windows / non-main threads that don't support add_signal_handler.
                logger.debug(
                    f"Cannot register {sig.name} handler on this platform/thread"
                )

    async def stop(self) -> None:
        """Stop the daemon."""
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        if self.lease is not None:
            await asyncio.to_thread(self.lease.release)

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
        symbols = self.symbol_registry.get_active_symbols()

        try:
            poll_errors, _, _, dispatch_result = await asyncio.to_thread(
                self._poll_and_dispatch,
                phase=phase,
                symbols=symbols,
                session_id=self.instance_id or "manual_trigger",
                cycle_id=self.state.last_cycle_id + 1,
                cycle_start=snapshot.as_of,
                db=None,
            )
            if poll_errors:
                raise RuntimeError(str(poll_errors))
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

    def _poll_and_dispatch(
        self,
        *,
        phase: SessionPhase,
        symbols: list[str],
        session_id: str,
        cycle_id: int,
        cycle_start: datetime,
        db: Session | None,
    ) -> tuple[dict[str, Any], dict[str, Any], int, Any]:
        """Run blocking adapters and sync DB work off the asyncio event loop.

        Performs three operations in order:
        1. Poll market data for each active symbol (multi-asset: derivatives + equities).
        2. Dispatch market data to Tri-Engine ensemble for signal generation.
        3. Run phase-aware scheduled hooks (T+2 settlement, EOD screener, equity universe refresh).
        """
        poll_errors: dict[str, Any] = {}
        all_market_data: dict[str, Any] = {}
        for symbol in symbols:
            try:
                poll_result = self.poller.poll(symbol, phase)
                if poll_result.errors:
                    poll_errors[symbol] = poll_result.errors
                    error_type = (
                        "circuit_breaker"
                        if any(
                            isinstance(error, dict)
                            and error.get("error")
                            in {
                                "circuit_breaker_open",
                                "circuit_breaker_probe_in_progress",
                            }
                            for error in poll_result.errors
                        )
                        else "api"
                    )
                    self.state.errors_by_type[error_type] = (
                        self.state.errors_by_type.get(error_type, 0) + 1
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
            except SystemExit as exc:
                poll_errors[symbol] = [f"rate-limit-sysexit: {exc}"]
                self.state.errors_by_type["api"] = (
                    self.state.errors_by_type.get("api", 0) + 1
                )
            except Exception as exc:
                poll_errors[symbol] = [str(exc)]
                self.state.errors_by_type["api"] = (
                    self.state.errors_by_type.get("api", 0) + 1
                )

        cycle_db = db
        owns_db = False
        if cycle_db is None and self.session_factory is not None:
            cycle_db = self.session_factory()
            owns_db = True
        try:
            dispatch_result = self.dispatcher.dispatch_sync(
                phase=phase,
                symbols=symbols,
                market_data=all_market_data,
                session_id=session_id,
                cycle_id=cycle_id,
                db=cycle_db,
            )
        finally:
            if owns_db and cycle_db is not None:
                cycle_db.close()

        # ---- Phase-aware scheduled hooks (T+2 settlement, EOD screener, equity refresh) ----
        # These are idempotent: each runs at most once per trading day.
        try:
            hook_results = dispatch_phase_hooks(
                phase=phase,
                session_factory=self.session_factory,
                symbol_registry=self.symbol_registry,
            )
            if hook_results:
                logger.debug(
                    "Scheduled hooks ran for phase %s: %s",
                    phase.value,
                    {k: v for k, v in hook_results.items() if not v.get("skipped")},
                )
                # Surface hook errors as daemon warnings (non-fatal).
                for hook_name, result in hook_results.items():
                    if result.get("errors"):
                        self.state.errors_by_type[f"hook_{hook_name}"] = (
                            self.state.errors_by_type.get(f"hook_{hook_name}", 0)
                            + len(result["errors"])
                        )
        except Exception as hook_exc:
            logger.warning("Scheduled hooks dispatch failed: %s", hook_exc)

        return (
            poll_errors,
            all_market_data,
            len(symbols) - len(poll_errors),
            dispatch_result,
        )

    async def run(
        self,
        db: Session | None,
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

        # A manually supplied session remains supported for tests/one-shot
        # callers; the production daemon uses session_factory instead.
        try:
            if db is not None:
                self._apply_session_log_persistence(db, session_log, create=True)
            elif self.session_factory is not None:
                await asyncio.to_thread(self._persist_session_log, session_log, True)
        except Exception as exc:
            self.state.running = False
            self.state.status = "crashed"
            self.state.last_error = f"session_log_persist_failed: {exc}"
            if self.lease is not None:
                await asyncio.to_thread(self.lease.release)
            logger.error(
                "Daemon refused to run without durable session log", exc_info=True
            )
            return

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

                    (
                        poll_errors,
                        all_market_data,
                        polled_count,
                        dispatch_result,
                    ) = await asyncio.to_thread(
                        self._poll_and_dispatch,
                        phase=phase,
                        symbols=symbols,
                        session_id=instance_id,
                        cycle_id=cycle_count,
                        cycle_start=cycle_start,
                        db=db,
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
                        self._apply_session_log_persistence(
                            db, session_log, create=False
                        )
                    elif self.session_factory is not None:
                        await asyncio.to_thread(self._persist_session_log, session_log)

                    # Reset failure count on success
                    self.state.last_run_at = datetime.now(VN_TZ)
                    cycle_has_errors = bool(poll_errors or dispatch_result.errors)
                    if cycle_has_errors:
                        failure_count += 1
                        reason = ", ".join(
                            list(poll_errors) + list(dispatch_result.errors)
                        )
                        self.state.degraded = True
                        self.state.status = "degraded"
                        self.state.last_degraded_reason = reason
                        self.state.last_error = reason
                        session_log.failure_count = failure_count
                        session_log.last_error = reason[:500]
                        self.circuit_breaker.record_failure(
                            RuntimeError(f"daemon cycle degraded: {reason}")
                        )
                    else:
                        failure_count = 0
                        self.state.degraded = False
                        self.state.status = "running"
                        self.state.last_degraded_reason = None
                        self.state.last_error = None
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
                            self._apply_session_log_persistence(
                                db, session_log, create=False
                            )
                        except Exception as db_err:
                            logger.warning(
                                f"Failed to persist session log on error: {db_err}"
                            )
                    elif self.session_factory is not None:
                        try:
                            await asyncio.to_thread(
                                self._persist_session_log, session_log
                            )
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
                    self._apply_session_log_persistence(db, session_log, create=False)
                except Exception as db_err:
                    logger.warning(f"Failed to persist final session log: {db_err}")
            elif self.session_factory is not None:
                try:
                    await asyncio.to_thread(self._persist_session_log, session_log)
                except Exception as db_err:
                    logger.warning(f"Failed to persist final session log: {db_err}")

            if self.lease is not None:
                await asyncio.to_thread(self.lease.release)

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
