"""Signal dispatch orchestration connecting analytical engines to Ensemble and Forecast Journal."""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlmodel import Session, col, select

from app.core.enums import (
    ForecastDirection,
    ForecastHorizon,
    ForecastStatus,
    OrderSide,
    SessionPhase,
)
from app.core.models_base import VN_TZ
from app.domains.quant.application.daemon.event import AnalysisContext, MarketDataEvent
from app.domains.quant.application.daemon.orchestrator import (
    PhaseAwareEngineOrchestrator,
)
from app.domains.quant.application.schemas import EnsembleSignalRequest
from app.domains.quant.domain.models import ForecastJournal

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
    persists records idempotently to ForecastJournal, and executes paper-trades.
    """

    def __init__(
        self,
        ensemble_engine: Any = _UNSET,
        simulation_engine: Any = _UNSET,
        orchestrator: PhaseAwareEngineOrchestrator | None = None,
        session: Session | None = None,
    ) -> None:
        self._ensemble = ensemble_engine
        self._simulation = simulation_engine
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

    def _persist_journal(
        self,
        symbol: str,
        horizon: str,
        predicted_at: datetime,
        entry_price: float,
        predicted_direction: str,
        predicted_score: float,
        engine_weights: dict[str, float],
        engine_scores: dict[str, float],
        parameter_snapshot: dict[str, Any],
        db_session: Session | None,
        model_version: str,
        log_extra: dict[str, Any],
    ) -> tuple[uuid.UUID, bool]:
        """
        Idempotently persists forecast to ForecastJournal.

        Returns (journal_id, is_duplicate).
        """
        # Ensure predicted_at has timezone
        if predicted_at.tzinfo is None:
            predicted_at = predicted_at.replace(tzinfo=VN_TZ)

        pred_key = (symbol, horizon, predicted_at.isoformat())
        active_db = db_session or self.session

        if active_db is not None:
            try:
                # Query existing row by UniqueConstraint("symbol", "horizon", "predicted_at")
                existing = active_db.exec(
                    select(ForecastJournal).where(
                        col(ForecastJournal.symbol) == symbol,
                        col(ForecastJournal.horizon) == horizon,
                        col(ForecastJournal.predicted_at) == predicted_at,
                    )
                ).first()

                if existing:
                    logger.info(
                        "forecast_journal_duplicate: forecast already recorded for %s/%s at %s (id=%s)",
                        symbol,
                        horizon,
                        predicted_at.isoformat(),
                        existing.id,
                        extra=log_extra,
                    )
                    return existing.id, True

                mapped_direction = (
                    ForecastDirection.BULLISH
                    if predicted_direction in ("LONG", ForecastDirection.BULLISH)
                    else ForecastDirection.BEARISH
                    if predicted_direction in ("SHORT", ForecastDirection.BEARISH)
                    else ForecastDirection.NEUTRAL
                )

                new_id = uuid.uuid4()
                entry = ForecastJournal(
                    id=new_id,
                    symbol=symbol,
                    horizon=horizon,
                    predicted_at=predicted_at,
                    predicted_value=entry_price,
                    predicted_direction=mapped_direction,
                    engine_weights=engine_weights,
                    model_version=model_version,
                    parameter_snapshot={
                        **parameter_snapshot,
                        "engine_scores": engine_scores,
                        "predicted_score": predicted_score,
                    },
                    status=ForecastStatus.PENDING,
                )
                active_db.add(entry)
                active_db.commit()
                active_db.refresh(entry)

                logger.info(
                    "forecast_journal_written: persisted forecast %s for %s/%s (model=%s)",
                    entry.id,
                    symbol,
                    horizon,
                    model_version,
                    extra=log_extra,
                )
                return entry.id, False
            except Exception as e:
                logger.error(
                    "Database error while persisting forecast journal: %s",
                    e,
                    extra=log_extra,
                    exc_info=True,
                )
                active_db.rollback()
                # Fall back to in-memory tracking

        # In-memory / offline mode
        if pred_key in self.journal_ledger:
            existing_id = self.journal_ledger[pred_key]["id"]
            logger.info(
                "forecast_journal_duplicate (in-memory): forecast %s for %s/%s at %s",
                existing_id,
                symbol,
                horizon,
                predicted_at.isoformat(),
                extra=log_extra,
            )
            return existing_id, True

        journal_id = uuid.uuid4()
        self.journal_ledger[pred_key] = {
            "id": journal_id,
            "symbol": symbol,
            "horizon": horizon,
            "predicted_at": predicted_at,
            "predicted_value": entry_price,
            "predicted_direction": predicted_direction,
            "engine_weights": engine_weights,
            "engine_scores": engine_scores,
            "parameter_snapshot": parameter_snapshot,
            "model_version": model_version,
            "status": "pending",
        }
        logger.info(
            "forecast_journal_written (in-memory): recorded forecast %s for %s/%s",
            journal_id,
            symbol,
            horizon,
            extra=log_extra,
        )
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
        3. All generated signals are persisted idempotently to ForecastJournal.
        4. Paper trading orders are strictly isolated from real broker endpoints.
        """
        now = datetime.now(VN_TZ)
        result = DispatchResult(timestamp=now, phase=phase)

        if self.ensemble is None:
            return result

        for symbol in symbols:
            log_extra = {
                "session_id": session_id or "default",
                "cycle_id": cycle_id or 0,
                "symbol": symbol,
                "market_phase": phase.value,
                "model_version": getattr(self.ensemble, "MODEL_VERSION", "v2.0.0"),
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
                    spot_p = float(symbol_data.get("spot_price") or entry_p)

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

                # Run phase-aware orchestrator to execute applicable engines
                orch_result = self.orchestrator.orchestrate(
                    context, session_id=session_id, cycle_id=cycle_id
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
                signal_resp = self.ensemble.generate_signal(
                    request=request,
                    entry_price=context.entry_price or 1300.0,
                    spot_price=context.spot_price or context.entry_price or 1300.0,
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

                # Idempotent Forecast Journal recording
                journal_id, is_duplicate = self._persist_journal(
                    symbol=symbol,
                    horizon=horizon,
                    predicted_at=pred_time,
                    entry_price=context.entry_price or 1300.0,
                    predicted_direction=signal_resp.predicted_direction,
                    predicted_score=signal_resp.ensemble_score,
                    engine_weights=signal_resp.engine_weights,
                    engine_scores=signal_resp.engine_scores,
                    parameter_snapshot={
                        "confidence": signal_resp.confidence,
                        "stop_loss": signal_resp.stop_loss,
                        "take_profit": signal_resp.take_profit,
                        "source_event_id": event_id,
                        "market_phase": phase.value,
                        "from_cache": context.event.from_cache
                        if context.event
                        else False,
                        "disclaimer": signal_resp.disclaimer,
                    },
                    db_session=db,
                    model_version=signal_resp.model_version,
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
                    if self.simulation is not None:
                        try:
                            sim_fn = getattr(self.simulation, "simulate_order", None)
                            if callable(sim_fn):
                                order_resp = sim_fn(
                                    symbol=symbol,
                                    signal=signal_dir,
                                    phase=phase,
                                    timestamp=now,
                                )
                                if order_resp:
                                    result.simulation_orders += 1
                            elif hasattr(self.simulation, "place_order"):
                                # If SimulationEngine is passed with an active portfolio
                                user_portfolios = getattr(
                                    self.simulation, "_default_portfolio", None
                                )
                                if user_portfolios is not None:
                                    side = (
                                        OrderSide.BUY
                                        if signal_dir == "LONG"
                                        else OrderSide.SELL
                                    )
                                    self.simulation.place_order(
                                        portfolio=user_portfolios,
                                        symbol=symbol,
                                        side=side,
                                        quantity=1,
                                        price=context.entry_price or 1300.0,
                                    )
                                    result.simulation_orders += 1
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
