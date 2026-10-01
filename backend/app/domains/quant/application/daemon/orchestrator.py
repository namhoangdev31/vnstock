"""Phase-aware engine orchestrator with failure isolation for quant daemon."""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlmodel import Session

from app.core.enums import SessionPhase
from app.core.models_base import VN_TZ
from app.domains.quant.application.daemon.event import AnalysisContext

if TYPE_CHECKING:
    from app.domains.quant.application.engines.flow_engine import FlowLiquidityEngine
    from app.domains.quant.application.engines.quant_ml_engine import QuantMLEngine
    from app.domains.quant.application.engines.technical_engine import TechnicalEngine

logger = logging.getLogger(__name__)


@dataclass
class EngineExecutionResult:
    """Standardized result of a single analytical engine execution."""

    engine_name: str
    version: str
    status: str  # "COMPLETED" | "SKIPPED" | "FAILED"
    score: float = 0.0
    confidence: float = 0.0
    metrics: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    missing_data: list[str] = field(default_factory=list)
    executed_at: datetime = field(default_factory=lambda: datetime.now(VN_TZ))
    skip_reason: str | None = None
    error: str | None = None
    response_obj: Any = None


@dataclass
class OrchestratorResult:
    """Consolidated outcome of running analytical engines for a daemon cycle."""

    phase: SessionPhase
    as_of: datetime
    engine_results: dict[str, EngineExecutionResult]
    is_executable: bool
    skip_reason: str | None = None


class PhaseAwareEngineOrchestrator:
    """
    Directs incoming market events to appropriate analytical engines based on session phase.

    Guarantees:
    1. Engine Failure Isolation: A crash in one engine will not kill the daemon or cycle.
    2. Phase-Aware Routing: Only executes engines suited for the active trading window.
    3. Structured Logging: Emits engine_started, engine_completed, engine_failed events.
    """

    def __init__(
        self,
        session: Session | None = None,
        technical_engine: "TechnicalEngine | None" = None,
        flow_engine: "FlowLiquidityEngine | None" = None,
        quant_ml_engine: "QuantMLEngine | None" = None,
    ) -> None:
        self.session = session
        self._engine1 = technical_engine
        self._engine2 = flow_engine
        self._engine3 = quant_ml_engine

    @property
    def engine1(self) -> Any:
        if self._engine1 is None:
            from app.domains.quant.application.engines.technical_engine import (
                TechnicalEngine,
            )

            self._engine1 = TechnicalEngine(self.session)
        return self._engine1

    @engine1.setter
    def engine1(self, val: Any) -> None:
        self._engine1 = val

    @property
    def engine2(self) -> Any:
        if self._engine2 is None:
            from app.domains.quant.application.engines.flow_engine import (
                FlowLiquidityEngine,
            )

            self._engine2 = FlowLiquidityEngine(self.session)
        return self._engine2

    @engine2.setter
    def engine2(self, val: Any) -> None:
        self._engine2 = val

    @property
    def engine3(self) -> Any:
        if self._engine3 is None:
            from app.domains.quant.application.engines.quant_ml_engine import (
                QuantMLEngine,
            )

            self._engine3 = QuantMLEngine(self.session)
        return self._engine3

    @engine3.setter
    def engine3(self, val: Any) -> None:
        self._engine3 = val

    def orchestrate(
        self,
        context: AnalysisContext,
        session_id: str | None = None,
        cycle_id: int | None = None,
    ) -> OrchestratorResult:
        """Execute phase-appropriate engines with full isolation."""
        phase = context.phase
        as_of = context.as_of
        symbol = context.event.symbol if context.event else "VN30F1M"
        event_id = context.event.event_id if context.event else "no_event"

        log_extra = {
            "session_id": session_id or "default",
            "cycle_id": cycle_id or 0,
            "event_id": event_id,
            "symbol": symbol,
            "market_phase": phase.value,
        }

        # Check if context was marked invalid during normalization
        if not context.is_valid:
            logger.info(
                "market_data_event_skipped: %s (reason: %s)",
                event_id,
                context.skip_reason,
                extra=log_extra,
            )
            return OrchestratorResult(
                phase=phase,
                as_of=as_of,
                engine_results={},
                is_executable=False,
                skip_reason=context.skip_reason,
            )

        results: dict[str, EngineExecutionResult] = {}

        # -------------------------------------------------------------
        # 1. Engine 1: Technical & Price-Action Engine
        # -------------------------------------------------------------
        should_run_e1 = phase in (
            SessionPhase.ATO,
            SessionPhase.MORNING_CONTINUOUS,
            SessionPhase.AFTERNOON_CONTINUOUS,
            SessionPhase.PRE_ATC,
            SessionPhase.ATC,
            SessionPhase.MIDDAY_INTERMISSION,
            SessionPhase.OVERNIGHT_SIMULATION,
        )

        if not should_run_e1:
            results["engine1"] = EngineExecutionResult(
                engine_name="TechnicalEngine",
                version="v2.0.0",
                status="SKIPPED",
                skip_reason=f"Phase {phase.value} does not evaluate active technicals",
            )
            logger.debug("Engine 1 skipped for phase %s", phase.value, extra=log_extra)
        else:
            logger.info("engine_started: engine1 (TechnicalEngine)", extra=log_extra)
            try:
                e1_resp = self.engine1.analyze(
                    symbol=symbol,
                    highs=context.highs,
                    lows=context.lows,
                    closes=context.closes,
                    volumes=context.volumes,
                    df_ticks=context.order_flow,
                    as_of=as_of,
                )
                warnings: list[str] = []
                missing_data: list[str] = []
                if len(context.closes) < 15:
                    warnings.append(
                        "Insufficient bars (<15); indicators may be uncalibrated"
                    )
                if context.order_flow is None:
                    missing_data.append("df_ticks orderflow missing")

                results["engine1"] = EngineExecutionResult(
                    engine_name="TechnicalEngine",
                    version="v2.0.0",
                    status="COMPLETED",
                    score=e1_resp.score,
                    confidence=0.7 if len(context.closes) >= 15 else 0.4,
                    metrics={
                        "rsi": e1_resp.rsi,
                        "order_imbalance": e1_resp.order_imbalance,
                        "volume_delta": e1_resp.volume_delta,
                        "regime": e1_resp.regime,
                        "camarilla_levels": e1_resp.camarilla_levels,
                    },
                    warnings=warnings,
                    missing_data=missing_data,
                    response_obj=e1_resp,
                )
                logger.info(
                    "engine_completed: engine1 score=%.4f",
                    e1_resp.score,
                    extra=log_extra,
                )
            except Exception as exc:
                logger.error(
                    "engine_failed: engine1 failed with error: %s",
                    exc,
                    extra=log_extra,
                    exc_info=True,
                )
                results["engine1"] = EngineExecutionResult(
                    engine_name="TechnicalEngine",
                    version="v2.0.0",
                    status="FAILED",
                    error=str(exc),
                )

        # -------------------------------------------------------------
        # 2. Engine 2: Liquidity, Flow & T+2 Cash Flow Engine
        # -------------------------------------------------------------
        should_run_e2 = phase in (
            SessionPhase.PRE_ATO,
            SessionPhase.ATO,
            SessionPhase.MORNING_CONTINUOUS,
            SessionPhase.MIDDAY_INTERMISSION,
            SessionPhase.AFTERNOON_CONTINUOUS,
            SessionPhase.PRE_ATC,
            SessionPhase.ATC,
            SessionPhase.POST_MARKET,
            SessionPhase.OVERNIGHT_SIMULATION,
        )

        if not should_run_e2:
            results["engine2"] = EngineExecutionResult(
                engine_name="FlowLiquidityEngine",
                version="v2.0.0",
                status="SKIPPED",
                skip_reason=f"Phase {phase.value} skipped for FlowLiquidityEngine",
            )
        else:
            logger.info(
                "engine_started: engine2 (FlowLiquidityEngine)", extra=log_extra
            )
            try:
                e2_resp = self.engine2.analyze(
                    flows=context.flows,
                    breadth=context.breadth,
                    as_of=as_of,
                )
                results["engine2"] = EngineExecutionResult(
                    engine_name="FlowLiquidityEngine",
                    version="v2.0.0",
                    status="COMPLETED",
                    score=e2_resp.score,
                    confidence=0.6,
                    metrics={
                        "institutional_momentum": e2_resp.institutional_momentum,
                        "market_breadth": e2_resp.market_breadth,
                        "t2_pressure": e2_resp.t2_pressure,
                        "macro_sentiment": e2_resp.macro_sentiment,
                    },
                    response_obj=e2_resp,
                )
                logger.info(
                    "engine_completed: engine2 score=%.4f",
                    e2_resp.score,
                    extra=log_extra,
                )
            except Exception as exc:
                logger.error(
                    "engine_failed: engine2 failed with error: %s",
                    exc,
                    extra=log_extra,
                    exc_info=True,
                )
                results["engine2"] = EngineExecutionResult(
                    engine_name="FlowLiquidityEngine",
                    version="v2.0.0",
                    status="FAILED",
                    error=str(exc),
                )

        # -------------------------------------------------------------
        # 3. Engine 3: Quantitative ML, Basis & Probability Engine
        # -------------------------------------------------------------
        # Engine 3 runs across all phases (ATO gap, basis, QMC T+1)
        logger.info("engine_started: engine3 (QuantMLEngine)", extra=log_extra)
        try:
            e3_resp = self.engine3.analyze(
                symbol=symbol,
                futures_price=context.entry_price or 1300.0,
                spot_index_price=context.spot_price or context.entry_price or 1300.0,
                highs=context.highs,
                lows=context.lows,
                closes=context.closes,
                as_of=as_of,
            )
            results["engine3"] = EngineExecutionResult(
                engine_name="QuantMLEngine",
                version="v2.0.0",
                status="COMPLETED",
                score=e3_resp.score,
                confidence=0.7,
                metrics={
                    "basis_value": e3_resp.basis_value,
                    "basis_zscore": e3_resp.basis_zscore,
                    "historical_vol": e3_resp.historical_vol,
                    "lr_trend_score": e3_resp.lr_trend_score,
                },
                response_obj=e3_resp,
            )
            logger.info(
                "engine_completed: engine3 score=%.4f",
                e3_resp.score,
                extra=log_extra,
            )
        except Exception as exc:
            logger.error(
                "engine_failed: engine3 failed with error: %s",
                exc,
                extra=log_extra,
                exc_info=True,
            )
            results["engine3"] = EngineExecutionResult(
                engine_name="QuantMLEngine",
                version="v2.0.0",
                status="FAILED",
                error=str(exc),
            )

        # Determine if at least one engine completed successfully
        has_completed = any(r.status == "COMPLETED" for r in results.values())

        return OrchestratorResult(
            phase=phase,
            as_of=as_of,
            engine_results=results,
            is_executable=has_completed,
            skip_reason=None if has_completed else "All applicable engines failed",
        )

    def validate_context(
        self,
        context: AnalysisContext,
        session_id: str | None = None,
        cycle_id: int | None = None,
    ) -> OrchestratorResult:
        """Validate dispatch eligibility without executing analytical engines.

        The daemon's EnsembleEngine is the single engine execution path.  The
        old dispatcher called ``orchestrate`` and then called Ensemble again,
        which doubled API/CPU/DB work and could emit two different decisions.
        Direct callers can still use ``orchestrate`` for the detailed engine
        report; the daemon uses this gate before the one authoritative Ensemble
        execution.
        """
        del session_id, cycle_id
        if not context.is_valid:
            return OrchestratorResult(
                phase=context.phase,
                as_of=context.as_of,
                engine_results={},
                is_executable=False,
                skip_reason=context.skip_reason,
            )
        return OrchestratorResult(
            phase=context.phase,
            as_of=context.as_of,
            engine_results={},
            is_executable=True,
        )
