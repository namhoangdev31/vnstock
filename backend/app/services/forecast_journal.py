"""ForecastJournalService — the mandatory forecast ledger (RULE 3, AGENTS §9.1).

Three lifecycle operations:

- ``record``: persist a forecast at prediction time with status ``pending``.
  Requires ``predicted_at``, ``engine_weights`` and ``model_version`` so every
  signal is traceable (TEST-JRN-01).
- ``resolve``: back-fill the realized outcome → status ``resolved``. The original
  ``predicted_at`` is never mutated, which is the anchor that prevents look-ahead
  bias (TEST-JRN-02).
- ``score``: compute MAE (value targets) and directional accuracy → status
  ``scored`` (TEST-JRN-03).

Scoring is deterministic and side-effect free apart from the persisted score.
"""

import logging
import math
from datetime import UTC, datetime

from sqlmodel import Session, col, select

from app.models.enums import (
    ForecastDirection,
    ForecastHorizon,
    ForecastStatus,
)
from app.models.models_quant import ForecastJournal

logger = logging.getLogger(__name__)


class ForecastJournalError(Exception):
    """Raised on invalid forecast-journal operations."""


class ForecastJournalService:
    """Record, resolve and score forecasts in the audit ledger."""

    def __init__(self, session: Session) -> None:
        self.session = session

    # ------------------------------------------------------------------
    # Layer A — record (predict)
    # ------------------------------------------------------------------

    def record(
        self,
        *,
        symbol: str,
        predicted_at: datetime,
        model_version: str,
        horizon: str = ForecastHorizon.T_PLUS_1,
        predicted_value: float | None = None,
        predicted_direction: str = ForecastDirection.NEUTRAL,
        engine_weights: dict | None = None,
        parameter_snapshot: dict | None = None,
    ) -> ForecastJournal:
        """Persist a new forecast in ``pending`` state.

        ``predicted_at`` MUST be timezone-aware (enforced by the model). It is the
        no-look-ahead anchor and is immutable after this point.
        """
        if predicted_at.tzinfo is None:
            raise ForecastJournalError(
                "predicted_at must be timezone-aware (UTC) to anchor no-look-ahead"
            )

        entry = ForecastJournal(
            symbol=symbol,
            horizon=horizon,
            predicted_at=predicted_at,
            predicted_value=predicted_value,
            predicted_direction=predicted_direction,
            engine_weights=engine_weights or {},
            model_version=model_version,
            parameter_snapshot=parameter_snapshot or {},
            status=ForecastStatus.PENDING,
        )
        self.session.add(entry)
        self.session.commit()
        self.session.refresh(entry)
        logger.info(
            "Recorded forecast %s for %s/%s (model=%s)",
            entry.id,
            symbol,
            horizon,
            model_version,
        )
        return entry

    # ------------------------------------------------------------------
    # Layer A — resolve (back-fill reality)
    # ------------------------------------------------------------------

    def resolve(
        self,
        forecast_id,
        *,
        actual_value: float,
        actual_direction: str,
        realized_at: datetime | None = None,
    ) -> ForecastJournal:
        """Back-fill the realized outcome. Status → ``resolved``.

        Deliberately does NOT touch ``predicted_at`` — it must remain the value
        captured at prediction time (TEST-JRN-02).
        """
        entry = self.session.get(ForecastJournal, forecast_id)
        if entry is None:
            raise ForecastJournalError(f"Forecast {forecast_id} not found")
        if entry.status == ForecastStatus.SCORED:
            raise ForecastJournalError(
                f"Forecast {forecast_id} is already scored and cannot be re-resolved"
            )
        if realized_at is not None and realized_at < entry.predicted_at:
            raise ForecastJournalError(
                "realized_at cannot precede predicted_at (look-ahead violation)"
            )

        entry.actual_value = actual_value
        entry.actual_direction = actual_direction
        entry.realized_at = realized_at or datetime.now(UTC)
        entry.status = ForecastStatus.RESOLVED
        entry.updated_at = datetime.now(UTC)
        self.session.add(entry)
        self.session.commit()
        self.session.refresh(entry)
        logger.info("Resolved forecast %s -> actual=%s", entry.id, actual_value)
        return entry

    # ------------------------------------------------------------------
    # Layer A — score (measure)
    # ------------------------------------------------------------------

    def score(self, forecast_id) -> ForecastJournal:
        """Compute MAE / directional accuracy. Status → ``scored``.

        ``error`` is the absolute price error (MAE for a single observation).
        ``score`` is a directional-accuracy reward in [0, 1]: 1.0 when the
        predicted direction matches reality, 0.0 otherwise, and 0.5 when either
        side is NEUTRAL/undefined (no information).
        """
        entry = self.session.get(ForecastJournal, forecast_id)
        if entry is None:
            raise ForecastJournalError(f"Forecast {forecast_id} not found")
        if entry.status == ForecastStatus.PENDING:
            raise ForecastJournalError(
                f"Forecast {forecast_id} is still pending; resolve it before scoring"
            )

        error = None
        if entry.predicted_value is not None and entry.actual_value is not None:
            error = math.fabs(entry.predicted_value - entry.actual_value)

        score = self._directional_score(
            entry.predicted_direction, entry.actual_direction
        )

        entry.error = error
        entry.score = score
        entry.status = ForecastStatus.SCORED
        entry.updated_at = datetime.now(UTC)
        self.session.add(entry)
        self.session.commit()
        self.session.refresh(entry)
        logger.info("Scored forecast %s -> error=%s score=%s", entry.id, error, score)
        return entry

    @staticmethod
    def _directional_score(predicted: str | None, actual: str | None) -> float:
        """Directional accuracy reward in [0, 1]."""
        if predicted is None or actual is None:
            return 0.5
        p = str(predicted).upper()
        a = str(actual).upper()
        if p == ForecastDirection.NEUTRAL or a == ForecastDirection.NEUTRAL:
            return 0.5
        return 1.0 if p == a else 0.0

    # ------------------------------------------------------------------
    # Aggregation helpers
    # ------------------------------------------------------------------

    def aggregate(
        self,
        *,
        symbol: str | None = None,
        horizon: str | None = None,
        model_version: str | None = None,
    ) -> dict:
        """Aggregate MAE and directional accuracy across ``scored`` forecasts.

        Returns a summary used by the (Phase 2) governed recalibration loop —
        Layer B in AGENTS §9.2. Read-only; never mutates the ledger.
        """
        query = select(ForecastJournal).where(
            ForecastJournal.status == ForecastStatus.SCORED
        )
        if symbol is not None:
            query = query.where(ForecastJournal.symbol == symbol)
        if horizon is not None:
            query = query.where(ForecastJournal.horizon == horizon)
        if model_version is not None:
            query = query.where(ForecastJournal.model_version == model_version)

        rows = self.session.exec(query).all()
        errors = [r.error for r in rows if r.error is not None]
        scores = [r.score for r in rows if r.score is not None]
        mae = (sum(errors) / len(errors)) if errors else None
        directional_accuracy = (sum(scores) / len(scores)) if scores else None
        return {
            "count": len(rows),
            "mae": mae,
            "directional_accuracy": directional_accuracy,
            "scored_with_error": len(errors),
        }

    def pending(self, *, limit: int = 100) -> list[ForecastJournal]:
        """Return unresolved forecasts, oldest first (for batch resolution)."""
        return list(
            self.session.exec(
                select(ForecastJournal)
                .where(ForecastJournal.status == ForecastStatus.PENDING)
                .order_by(col(ForecastJournal.predicted_at))
                .limit(limit)
            ).all()
        )
