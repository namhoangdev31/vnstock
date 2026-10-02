"""Signal dispatch orchestration connecting analytical engines to Ensemble and Forecast Journal."""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlmodel import Session

from app.core.enums import (
    ForecastHorizon,
    OrderSide,
    SessionPhase,
)
from app.core.models_base import VN_TZ
from app.domains.quant.application.daemon.event import AnalysisContext, MarketDataEvent
from app.domains.quant.application.daemon.orchestrator import (
    PhaseAwareEngineOrchestrator,
)
from app.domains.quant.application.schemas import EnsembleSignalRequest

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


def map_phase_to_horizon(phase: SessionPhase) -> str:
    """Map the current market session phase to an analytical forecast horizon."""
    if phase in (SessionPhase.PRE_ATO, SessionPhase.ATO):
        return ForecastHorizon.ATO
    elif phase in (SessionPhase.PRE_ATC, SessionPhase.ATC):
        return ForecastHorizon.ATC
    elif phase in (SessionPhase.POST_MARKET, SessionPhase.OVERNIGHT_SIMULATION):
        return ForecastHorizon.T_PLUS_1
    return ForecastHorizon.INTRADAY


@dataclass
class DispatchResult:
    """Outcome of signal dispatch during a daemon cycle."""

    timestamp: datetime
    phase: SessionPhase
    ensemble_signals: int = 0
    simulation_orders: int = 0
    forecast_journals: int = 0
    duplicates_detected: int = 0
    skipped_signals: int = 0
    errors: dict[str, Any] = field(default_factory=dict)
    signals: list[dict[str, Any]] = field(default_factory=list)


_UNSET = object()


class SignalDispatcher:
    """
    Routes normalized market data to analytical engines, generates Ensemble decisions,
    uses the Ensemble-owned ForecastJournal write and executes paper-trades.
    """

    def __init__(
        self,
        ensemble_engine: Any = _UNSET,
        simulation_engine: Any = _UNSET,
        orchestrator: PhaseAwareEngineOrchestrator | None = None,
        session: Session | None = None,
        default_portfolio: Any = None,
    ) -> None:
        self._ensemble = ensemble_engine
        self._simulation = simulation_engine
        self.default_portfolio = default_portfolio
        self.orchestrator = orchestrator or PhaseAwareEngineOrchestrator(
            session=session
        )
        self.session = session
        # In-memory journal ledger for offline mode and duplicate prevention across cycles
        self.journal_ledger: dict[tuple[str, str, str], dict[str, Any]] = {}

    @property
    def ensemble(self) -> Any:
        """Lazily load EnsembleEngine when not explicitly configured."""
        if self._ensemble is _UNSET:
            try:
                from app.domains.quant.application.engines.ensemble_engine import (
                    EnsembleEngine,
                )

                self._ensemble = EnsembleEngine(session=self.session)
            except Exception:
                self._ensemble = None
        return self._ensemble

    @ensemble.setter
    def ensemble(self, val: Any) -> None:
        self._ensemble = val

    @property
    def simulation(self) -> Any:
        """Lazily load SimulationEngine when not explicitly configured."""
        if self._simulation is _UNSET:
            if self.session is not None:
                try:
                    from app.domains.simulation.application.engine import (
                        SimulationEngine,
                    )

                    self._simulation = SimulationEngine(session=self.session)
                except Exception:
                    self._simulation = None
            else:
                self._simulation = None
        return self._simulation

    @simulation.setter
    def simulation(self, val: Any) -> None:
        self._simulation = val

    @staticmethod
    def _journal_key(
        symbol: str, horizon: str, predicted_at: datetime
    ) -> tuple[str, str, str]:
        """Build the same idempotency key as ForecastJournal's unique index."""
        if predicted_at.tzinfo is None:
            predicted_at = predicted_at.replace(tzinfo=VN_TZ)
        return symbol, horizon, predicted_at.isoformat()

    def _track_journal_reference(
        self,
        *,
        symbol: str,
        horizon: str,
        predicted_at: datetime,
        journal_id: uuid.UUID,
        log_extra: dict[str, Any],
    ) -> tuple[uuid.UUID, bool]:
        """Track the already-persisted Ensemble journal without writing again."""
        key = self._journal_key(symbol, horizon, predicted_at)
        existing = self.journal_ledger.get(key)
        if existing is not None:
            existing_id = existing["id"]
            logger.info(
                "forecast_journal_duplicate: forecast already tracked for %s/%s at %s (id=%s)",
                symbol,
                horizon,
                predicted_at.isoformat(),
                existing_id,
                extra=log_extra,
            )
            return existing_id, True

        self.journal_ledger[key] = {"id": journal_id}
        return journal_id, False

    async def dispatch(
        self,
        phase: SessionPhase,
        symbols: list[str],
        market_data: dict[str, Any],
        session_id: str | None = None,
        cycle_id: int | None = None,
        db: Session | None = None,
    ) -> DispatchResult:
        """
        Dispatch signals to analytical engines, aggregate via Ensemble, and paper trade.

        Guarantees:
        1. Non-trading phases (POST_MARKET, OVERNIGHT_SIMULATION without bars) safely skip.
        2. Insufficient or missing data triggers market_data_event_skipped.
        3. All generated signals are persisted idempotently by EnsembleEngine.
        4. Paper trading orders are strictly isolated from real broker endpoints.
        """
        now = datetime.now(VN_TZ)
        result = DispatchResult(timestamp=now, phase=phase)

        ensemble = self.ensemble
        if ensemble is None:
            return result

        # The daemon owns a short-lived DB session per cycle.  Never reuse an
        # engine bound to a previous request/session (or a closed connection).
        if db is not None:
            try:
                from app.domains.quant.application.engines.ensemble_engine import (
                    EnsembleEngine,
                )

                if getattr(ensemble, "session", None) is not db:
                    ensemble = EnsembleEngine(session=db)
            except Exception:
                logger.exception("Unable to bind ensemble engine to cycle session")
                return result

        orchestrator = self.orchestrator
        if db is not None and getattr(orchestrator, "session", None) is not db:
            orchestrator = PhaseAwareEngineOrchestrator(session=db)

        simulation = self.simulation
        if db is not None and simulation is None and self._simulation is _UNSET:
            try:
                from app.domains.simulation.application.engine import SimulationEngine

                simulation = SimulationEngine(session=db)
            except Exception:
                simulation = None

        for symbol in symbols:
            log_extra = {
                "session_id": session_id or "default",
                "cycle_id": cycle_id or 0,
                "symbol": symbol,
                "market_phase": phase.value,
                "model_version": getattr(ensemble, "MODEL_VERSION", "v2.0.0"),
            }

            try:
                symbol_data = market_data.get(symbol, {})
                context: AnalysisContext | None = symbol_data.get("context")

                # If AnalysisContext not explicitly passed, construct a lightweight context
                if context is None:
                    closes = symbol_data.get("closes") or []
                    highs = symbol_data.get("highs") or closes
                    lows = symbol_data.get("lows") or closes
                    volumes = symbol_data.get("volumes") or [1.0] * len(closes)
                    entry_p = float(
                        symbol_data.get("entry_price")
                        or (closes[-1] if closes else 0.0)
                    )
                    spot_p_raw = symbol_data.get("spot_price")
                    spot_p = (
                        float(spot_p_raw)
                        if spot_p_raw and float(spot_p_raw) > 0.0
                        else float(entry_p)
                    )

                    # Create placeholder event
                    ev_time = now
                    ev_id = f"{symbol}:1m:{ev_time.strftime('%Y%m%d%H%M%S')}:candle"
                    event = MarketDataEvent(
                        event_id=ev_id,
                        symbol=symbol,
                        asset_type="derivative"
                        if symbol.startswith("VN30F")
                        else "equity",
                        interval="1m",
                        event_type="candle",
                        event_time=ev_time,
                        received_at=now,
                        source="vci",
                        market_phase=phase,
                    )

                    context = AnalysisContext(
                        event=event,
                        latest_bars=[],
                        intraday_flow=[],
                        market_snapshot={},
                        phase=phase,
                        as_of=now,
                        highs=highs,
                        lows=lows,
                        closes=closes,
                        volumes=volumes,
                        entry_price=entry_p,
                        spot_price=spot_p,
                        order_flow=symbol_data.get("order_flow"),
                        flows=symbol_data.get("flows"),
                        breadth=symbol_data.get("breadth"),
                        is_valid=len(closes) > 0,
                        skip_reason=None if len(closes) > 0 else "no_price_bars",
                    )

                event_id = (
                    context.event.event_id if context.event else f"{symbol}:unknown"
                )
                log_extra["event_id"] = event_id

                logger.info(
                    "market_data_event_received: event_id=%s, symbol=%s, phase=%s",
                    event_id,
                    symbol,
                    phase.value,
                    extra=log_extra,
                )

                # Skip conditions: non-trading phase with no bars or invalid context
                if not context.is_valid:
                    result.skipped_signals += 1
                    logger.info(
                        "market_data_event_skipped: symbol=%s, reason=%s",
                        symbol,
                        context.skip_reason,
                        extra=log_extra,
                    )
                    continue

                if not context.closes or len(context.closes) == 0:
                    result.skipped_signals += 1
                    logger.info(
                        "market_data_event_skipped: symbol=%s, reason=no_closes",
                        symbol,
                        extra=log_extra,
                    )
                    continue

                if context.event is not None and not context.event.is_closed:
                    result.skipped_signals += 1
                    logger.info(
                        "market_data_event_skipped: symbol=%s, reason=forming_candle",
                        symbol,
                        extra=log_extra,
                    )
                    continue

                if getattr(context.event, "is_duplicate", False):
                    result.duplicates_detected += 1
                    result.skipped_signals += 1
                    logger.info(
                        "market_data_event_skipped: symbol=%s, reason=duplicate_event",
                        symbol,
                        extra=log_extra,
                    )
                    continue

                # Run phase-aware orchestrator to execute applicable engines
                validate_context = getattr(orchestrator, "validate_context", None)
                if callable(validate_context):
                    orch_result = validate_context(
                        context, session_id=session_id, cycle_id=cycle_id
                    )
                else:
                    # Compatibility for injected test/dedicated orchestrators.
                    orch_result = orchestrator.orchestrate(
                        context, session_id=session_id, cycle_id=cycle_id
                    )

                # Tick-driven paper order matcher for pending orders (Phase 4, RULE 1/2/3)
                if db is not None and context.entry_price and context.entry_price > 0:
                    try:
                        from app.domains.simulation.application.order_matcher import (
                            match_pending_orders,
                        )

                        vol = int(context.volumes[-1]) if context.volumes else 100
                        atr14_val = None
                        if (
                            context.highs
                            and context.lows
                            and context.closes
                            and len(context.closes) >= 15
                        ):
                            from app.domains.quant.domain.indicators import compute_atr

                            atr14_val = compute_atr(
                                context.highs, context.lows, context.closes, 14
                            )
                        matched = match_pending_orders(
                            db,
                            symbol,
                            tick_price=context.entry_price,
                            tick_volume=vol,
                            tick_time=now,
                            atr14=atr14_val,
                        )
                        if matched:
                            result.simulation_orders += len(matched)
                    except Exception as match_err:
                        logger.debug(
                            "Order matcher execution failed for %s: %s",
                            symbol,
                            match_err,
                        )

                if not orch_result.is_executable:
                    result.skipped_signals += 1
                    logger.info(
                        "market_data_event_skipped: symbol=%s, reason=%s",
                        symbol,
                        orch_result.skip_reason,
                        extra=log_extra,
                    )
                    continue

                horizon = map_phase_to_horizon(phase)
                request = EnsembleSignalRequest(
                    symbol=symbol,
                    horizon=horizon,
                    custom_weights=None,
                )

                pred_time = context.as_of if context and context.as_of else now
                if pred_time.tzinfo is None:
                    pred_time = pred_time.replace(tzinfo=VN_TZ)

                # Generate Ensemble Decision
                # Guard: skip signal when price data is missing (RULE 3)
                if not context.entry_price or context.entry_price <= 0.0:
                    result.skipped_signals += 1
                    logger.warning(
                        "signal_skipped_no_price: symbol=%s entry_price=%s spot_price=%s",
                        symbol,
                        context.entry_price,
                        context.spot_price,
                        extra=log_extra,
                    )
                    continue

                effective_spot = (
                    context.spot_price
                    if context.spot_price and context.spot_price > 0.0
                    else context.entry_price
                )

                signal_resp = ensemble.generate_signal(
                    request=request,
                    entry_price=context.entry_price,
                    spot_price=effective_spot,
                    highs=context.highs,
                    lows=context.lows,
                    closes=context.closes,
                    volumes=context.volumes,
                    df_ticks=context.order_flow,
                    flows=context.flows,
                    breadth=context.breadth,
                    as_of=pred_time,
                )

                logger.info(
                    "ensemble_completed: symbol=%s direction=%s score=%.4f confidence=%.2f",
                    symbol,
                    signal_resp.predicted_direction,
                    signal_resp.ensemble_score,
                    signal_resp.confidence,
                    extra=log_extra,
                )

                # EnsembleEngine already wrote this journal entry. Dispatcher
                # only tracks the returned id to report retries accurately.
                journal_id, is_duplicate = self._track_journal_reference(
                    symbol=symbol,
                    horizon=horizon,
                    predicted_at=pred_time,
                    journal_id=getattr(signal_resp, "journal_id", None) or uuid.uuid4(),
                    log_extra=log_extra,
                )

                if is_duplicate:
                    result.duplicates_detected += 1
                else:
                    result.forecast_journals += 1

                signal_dir = signal_resp.predicted_direction
                signal_data = {
                    "journal_id": str(journal_id),
                    "symbol": symbol,
                    "direction": signal_dir,
                    "score": signal_resp.ensemble_score,
                    "confidence": signal_resp.confidence,
                    "entry_price": signal_resp.entry_price,
                    "stop_loss": signal_resp.stop_loss,
                    "take_profit": signal_resp.take_profit,
                    "horizon": horizon,
                    "disclaimer": signal_resp.disclaimer,
                }
                result.signals.append(signal_data)

                if signal_dir in ("LONG", "SHORT"):
                    result.ensemble_signals += 1

                    # Isolated Paper Trading Simulation
                    if simulation is not None and not is_duplicate:
                        try:
                            sim_fn = getattr(simulation, "simulate_order", None)
                            if callable(sim_fn):
                                order_resp = sim_fn(
                                    symbol=symbol,
                                    signal=signal_dir,
                                    phase=phase,
                                    timestamp=now,
                                )
                                if order_resp:
                                    result.simulation_orders += 1
                            else:
                                place_order = getattr(simulation, "place_order", None)
                                portfolio = (
                                    self.default_portfolio
                                    or getattr(
                                        self.simulation, "default_portfolio", None
                                    )
                                    or getattr(
                                        self.simulation, "_default_portfolio", None
                                    )
                                )
                                if callable(place_order) and portfolio is not None:
                                    side = (
                                        OrderSide.BUY
                                        if signal_dir == "LONG"
                                        else OrderSide.SELL
                                    )
                                    order_resp = place_order(
                                        portfolio=portfolio,
                                        symbol=symbol,
                                        side=side,
                                        quantity=1,
                                        price=context.entry_price,
                                        source_signal_id=str(journal_id),
                                    )
                                    if order_resp is not None:
                                        result.simulation_orders += 1
                                elif callable(place_order):
                                    result.errors[f"simulate:{symbol}"] = (
                                        "paper_portfolio_not_configured"
                                    )
                        except Exception as sim_e:
                            result.errors[f"simulate:{symbol}"] = str(sim_e)
                            logger.warning(
                                "Simulation failed for %s: %s",
                                symbol,
                                sim_e,
                                extra=log_extra,
                            )

            except Exception as e:
                result.errors[f"pipeline:{symbol}"] = str(e)
                logger.error(
                    "pipeline_cycle_failed for %s: %s",
                    symbol,
                    e,
                    extra=log_extra,
                    exc_info=True,
                )

        return result

    def dispatch_sync(
        self,
        phase: SessionPhase,
        symbols: list[str],
        market_data: dict[str, Any],
        session_id: str | None = None,
        cycle_id: int | None = None,
        db: Session | None = None,
    ) -> DispatchResult:
        """Synchronous dispatch wrapper for tests and non-async contexts."""
        import asyncio

        return asyncio.run(
            self.dispatch(
                phase=phase,
                symbols=symbols,
                market_data=market_data,
                session_id=session_id,
                cycle_id=cycle_id,
                db=db,
            )
        )
