"""Signal dispatch orchestration for the autonomous quant daemon."""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

from app.core.enums import SessionPhase
from app.core.models_base import VN_TZ
from app.domains.quant.application.schemas import EnsembleSignalRequest

if TYPE_CHECKING:
    from app.domains.quant.application.engines.ensemble_engine import EnsembleEngine
    from app.domains.quant.application.engines.simulation_engine import SimulationEngine

logger = logging.getLogger(__name__)


@dataclass
class DispatchResult:
    """Outcome of signal dispatch during a daemon cycle."""

    timestamp: datetime
    phase: SessionPhase
    ensemble_signals: int = 0
    simulation_orders: int = 0
    forecast_journals: int = 0
    errors: dict[str, Any] = field(default_factory=dict)


class SignalDispatcher:
    """Routes ensemble signals to SimulationEngine for paper trading."""

    def __init__(
        self,
        ensemble_engine: "EnsembleEngine | None" = None,
        simulation_engine: "SimulationEngine | None" = None,
    ):
        """Initialize dispatcher with engine references."""
        self.ensemble = ensemble_engine
        self.simulation = simulation_engine

    async def dispatch(
        self,
        phase: SessionPhase,
        symbols: list[str],
        market_data: dict[str, Any],
    ) -> DispatchResult:
        """
        Dispatch signals to ensemble, then paper-trade via simulation.

        Args:
            phase: Current SessionPhase
            symbols: Symbols to generate signals for
            market_data: Phase-aware market data (history, intraday, orderflow)

        Returns:
            DispatchResult with signal and order counts
        """
        result = DispatchResult(
            timestamp=datetime.now(VN_TZ),
            phase=phase,
        )

        try:
            # Generate ensemble signals
            for symbol in symbols:
                try:
                    # Prepare EnsembleSignalRequest with phase-aware market data
                    request = EnsembleSignalRequest(
                        symbol=symbol,
                        horizon=phase.value,
                        custom_weights=None,
                    )

                    # Extract market data for this symbol
                    symbol_data = market_data.get(symbol, {})

                    # Call ensemble engine with market data
                    signal_resp = self.ensemble.generate_signal(
                        request=request,
                        entry_price=symbol_data.get("entry_price", 0.0),
                        spot_price=symbol_data.get("spot_price", 0.0),
                        highs=symbol_data.get("highs"),
                        lows=symbol_data.get("lows"),
                        closes=symbol_data.get("closes"),
                        volumes=symbol_data.get("volumes"),
                        df_ticks=symbol_data.get("order_flow"),
                        flows=symbol_data.get("flows"),
                        breadth=symbol_data.get("breadth"),
                        as_of=result.timestamp,
                    )

                    if signal_resp and signal_resp.signal:
                        result.ensemble_signals += 1

                        # Forward to simulation engine for paper trading
                        try:
                            order_resp = self.simulation.simulate_order(
                                symbol=symbol,
                                signal=signal_resp.signal,
                                phase=phase,
                                timestamp=result.timestamp,
                            )

                            if order_resp:
                                result.simulation_orders += 1

                                # Journal the forecast (RULE 3: PERSISTENCE)
                                if hasattr(self.simulation, "journal_forecast"):
                                    self.simulation.journal_forecast(
                                        symbol=symbol,
                                        signal=signal_resp.signal,
                                        order_id=getattr(order_resp, "id", None),
                                        phase=phase,
                                    )
                                    result.forecast_journals += 1

                        except Exception as e:
                            result.errors[f"simulate:{symbol}"] = str(e)
                            logger.warning(
                                f"Simulation failed for {symbol}: {e}",
                                extra={"symbol": symbol, "phase": phase.value},
                            )

                except Exception as e:
                    result.errors[f"ensemble:{symbol}"] = str(e)
                    logger.warning(
                        f"Signal generation failed for {symbol}: {e}",
                        extra={"symbol": symbol, "phase": phase.value},
                    )

        except Exception as e:
            result.errors["dispatch"] = str(e)
            logger.error(f"Dispatch failed: {e}", exc_info=True)

        return result

    def dispatch_sync(
        self,
        phase: SessionPhase,
        symbols: list[str],
        market_data: dict[str, Any],
    ) -> DispatchResult:
        """
        Synchronous dispatch wrapper for tests and non-async contexts.

        Args:
            phase: Current SessionPhase
            symbols: Symbols to generate signals for
            market_data: Phase-aware market data (history, intraday, orderflow)

        Returns:
            DispatchResult with signal and order counts
        """
        import asyncio

        return asyncio.run(
            self.dispatch(phase=phase, symbols=symbols, market_data=market_data)
        )
