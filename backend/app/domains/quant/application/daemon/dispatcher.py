"""Signal routing to ensemble engine and simulation engine for the daemon."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.core.enums import SessionPhase
from app.core.models_base import VN_TZ
from app.domains.quant.application.daemon.poller import MarketPollResult


@dataclass
class DispatchResult:
    """Result of signal dispatch cycle."""
    phase: SessionPhase
    timestamp: datetime
    symbol: str
    signal_count: int = 0
    forecast_id: str | None = None
    paper_orders_placed: int = 0
    errors: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class SignalDispatcher:
    """Routes signals to engines and simulation layer."""

    def __init__(self) -> None:
        self._ensemble_engine = None
        self._simulation_engine = None

    def dispatch(self, poll_result: MarketPollResult) -> DispatchResult:
        """Dispatch poll data to engines for analysis and execution."""
        now = datetime.now(VN_TZ)
        result = DispatchResult(
            phase=poll_result.phase,
            timestamp=now,
            symbol=poll_result.symbol,
        )

        # Skip dispatch in non-trading phases
        if poll_result.phase in (
            SessionPhase.POST_MARKET,
            SessionPhase.OVERNIGHT_SIMULATION,
        ):
            result.errors.append({
                "reason": "non_trading_phase",
                "message": f"Skipping dispatch for phase {poll_result.phase}",
            })
            return result

        # Generate ensemble signal
        try:
            signal = self._generate_ensemble_signal(poll_result)
            if signal is not None:
                result.signal_count += 1
                result.forecast_id = signal.get("journal_id")
        except Exception as exc:
            result.errors.append({
                "error": "ensemble_generation_failed",
                "details": str(exc),
            })

        # Place paper orders (simulation only)
        if signal is not None and signal.get("signal_type") in ("BUY", "SELL"):
            try:
                paper_order = self._place_paper_order(signal, poll_result)
                if paper_order is not None:
                    result.paper_orders_placed += 1
            except Exception as exc:
                result.errors.append({
                    "error": "paper_order_failed",
                    "details": str(exc),
                })

        return result

    def _generate_ensemble_signal(self, poll_result: MarketPollResult) -> dict | None:
        """Generate ensemble signal from poll data."""
        # TODO: Integrate EnsembleEngine.generate_signal() from ensemble_engine.py
        # For now, return None as placeholder
        return None

    def _place_paper_order(self, signal: dict, poll_result: MarketPollResult) -> dict | None:
        """Place a paper order via SimulationEngine."""
        # TODO: Integrate SimulationEngine.place_order() for paper trading
        # No real brokerage calls allowed
        return None
