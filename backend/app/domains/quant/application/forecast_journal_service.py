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
from datetime import date, datetime, timedelta

from sqlmodel import Session, col, select

from app.core.enums import (
    ForecastDirection,
    ForecastHorizon,
    ForecastStatus,
)
from app.core.models_base import VN_TZ
from app.domains.quant.domain.exceptions import (
    ForecastJournalError,
    ForecastNotFoundError,
)
from app.domains.quant.domain.models import ForecastJournal

logger = logging.getLogger(__name__)


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
        predicted_probability: float | None = None,
        predicted_price_low: float | None = None,
        predicted_price_high: float | None = None,
        engine_weights: dict | None = None,
        parameter_snapshot: dict | None = None,
    ) -> ForecastJournal:
        """Persist a new forecast in ``pending`` state.

        ``predicted_at`` MUST be timezone-aware (enforced by the model). It is the
        no-look-ahead anchor and is immutable after this point.
        """
        if predicted_at.tzinfo is None:
            raise ForecastJournalError(
                "predicted_at must be timezone-aware (VN_TZ) to anchor no-look-ahead"
            )
        if predicted_at > datetime.now(VN_TZ) + timedelta(seconds=2):
            raise ForecastJournalError(
                "predicted_at cannot be in the future (look-ahead violation)"
            )
        if horizon not in {item.value for item in ForecastHorizon}:
            raise ForecastJournalError(f"Unsupported forecast horizon: {horizon}")
        if predicted_direction not in {item.value for item in ForecastDirection}:
            raise ForecastJournalError(
                f"Unsupported forecast direction: {predicted_direction}"
            )
        if (
            predicted_probability is not None
            and not 0.0 <= predicted_probability <= 1.0
        ):
            raise ForecastJournalError("predicted_probability must be between 0 and 1")

        entry = ForecastJournal(
            symbol=symbol,
            horizon=horizon,
            predicted_at=predicted_at,
            predicted_value=predicted_value,
            predicted_direction=predicted_direction,
            predicted_probability=predicted_probability,
            predicted_price_low=predicted_price_low,
            predicted_price_high=predicted_price_high,
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
            raise ForecastNotFoundError(f"Forecast {forecast_id} not found")
        if entry.status != ForecastStatus.PENDING:
            raise ForecastJournalError(
                f"Forecast {forecast_id} is already {entry.status} and cannot be re-resolved"
            )
        real_dt = realized_at or datetime.now(VN_TZ)
        if real_dt.tzinfo is None:
            raise ForecastJournalError("realized_at must be timezone-aware")
        pred_dt = entry.predicted_at
        if pred_dt.tzinfo is None:
            pred_dt = pred_dt.replace(tzinfo=real_dt.tzinfo)
        if real_dt > datetime.now(VN_TZ) + timedelta(seconds=10):
            raise ForecastJournalError(
                "realized_at cannot be in the future (outcome not resolved yet)"
            )
        if real_dt < pred_dt:
            raise ForecastJournalError(
                "realized_at cannot precede predicted_at (look-ahead violation)"
            )
        if realized_at is not None:
            # Keep this branch explicit for readability in the audit path.
            real_dt = realized_at

        entry.actual_value = actual_value
        entry.actual_direction = actual_direction
        entry.realized_at = real_dt
        entry.status = ForecastStatus.RESOLVED
        entry.updated_at = datetime.now(VN_TZ)
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
            raise ForecastNotFoundError(f"Forecast {forecast_id} not found")
        if entry.status == ForecastStatus.PENDING:
            raise ForecastJournalError(
                f"Forecast {forecast_id} is still pending; resolve it before scoring"
            )

        error = None
        if entry.predicted_value is not None and entry.actual_value is not None:
            error = math.fabs(entry.predicted_value - entry.actual_value)

        actual_direction = entry.actual_direction
        entry_price = entry.parameter_snapshot.get("entry_price")
        if entry_price is not None and entry.actual_value is not None:
            delta = float(entry.actual_value) - float(entry_price)
            actual_direction = (
                ForecastDirection.BULLISH.value
                if delta > 0
                else ForecastDirection.BEARISH.value
                if delta < 0
                else ForecastDirection.NEUTRAL.value
            )
            entry.actual_direction = actual_direction

        directional_correct = self._directional_correct(
            entry.predicted_direction, actual_direction
        )
        score = None if directional_correct is None else float(directional_correct)
        brier = None
        if entry.predicted_probability is not None and actual_direction in (
            ForecastDirection.BULLISH,
            ForecastDirection.BEARISH,
            ForecastDirection.BULLISH.value,
            ForecastDirection.BEARISH.value,
        ):
            outcome = (
                1.0
                if str(actual_direction).upper() == ForecastDirection.BULLISH
                else 0.0
            )
            brier = (entry.predicted_probability - outcome) ** 2

        entry.error = error
        entry.absolute_error = error
        entry.score = score
        entry.directional_correct = directional_correct
        entry.brier_score = brier
        entry.status = ForecastStatus.SCORED
        entry.updated_at = datetime.now(VN_TZ)
        self.session.add(entry)
        self.session.commit()
        self.session.refresh(entry)
        logger.info("Scored forecast %s -> error=%s score=%s", entry.id, error, score)
        return entry

    @staticmethod
    def _directional_correct(predicted: str | None, actual: str | None) -> bool | None:
        """Return correctness, excluding neutral outcomes from DA metrics."""
        if predicted is None or actual is None:
            return None
        p = str(predicted).upper()
        a = str(actual).upper()
        if p == ForecastDirection.NEUTRAL or a == ForecastDirection.NEUTRAL:
            return None
        return p == a

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
        scores = [
            float(r.directional_correct)
            for r in rows
            if r.directional_correct is not None
        ]
        briers = [r.brier_score for r in rows if r.brier_score is not None]
        mae = (sum(errors) / len(errors)) if errors else None
        directional_accuracy = (sum(scores) / len(scores)) if scores else None
        return {
            "count": len(rows),
            "mae": mae,
            "directional_accuracy": directional_accuracy,
            "scored_with_error": len(errors),
            "directional_count": len(scores),
            "mean_brier": sum(briers) / len(briers) if briers else None,
            "rmse": math.sqrt(sum(error * error for error in errors) / len(errors))
            if errors
            else None,
            "win_rate": directional_accuracy,
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

    def resolve_and_score_due_forecasts(
        self, *, as_of: date | None = None
    ) -> dict[str, int]:
        """Automatically resolve and score pending forecasts whose outcome date has arrived.

        Follows RULE 3 / AGENTS §9.1:
        - Never looks ahead: uses only StockOHLCVDaily bars on or before as_of.
        - Calculates actual_value and actual_direction from realized market prices.
        - Status transitions: PENDING -> RESOLVED -> SCORED.
        """
        from app.domains.market_data.domain.models import StockOHLCVDaily

        as_of_date = as_of or datetime.now(VN_TZ).date()
        pending_rows = self.pending(limit=200)

        resolved_count = 0
        skipped_count = 0

        for entry in pending_rows:
            pred_date = entry.predicted_at.date()

            # Determine target resolution date based on horizon
            if entry.horizon in (ForecastHorizon.ATC, ForecastHorizon.INTRADAY):
                target_date = pred_date
            elif entry.horizon == ForecastHorizon.T_PLUS_1:
                target_date = pred_date + timedelta(days=1)
            elif entry.horizon == ForecastHorizon.T_PLUS_2:
                target_date = pred_date + timedelta(days=2)
            elif entry.horizon == ForecastHorizon.WEEKLY:
                target_date = pred_date + timedelta(days=7)
            elif entry.horizon == ForecastHorizon.MONTHLY:
                target_date = pred_date + timedelta(days=30)
            elif entry.horizon == ForecastHorizon.QUARTERLY:
                target_date = pred_date + timedelta(days=90)
            else:
                target_date = pred_date + timedelta(days=1)

            if target_date > as_of_date:
                skipped_count += 1
                continue

            bar = self.session.exec(
                select(StockOHLCVDaily)
                .where(StockOHLCVDaily.symbol == entry.symbol)
                .where(col(StockOHLCVDaily.trading_date) >= target_date)
                .where(col(StockOHLCVDaily.trading_date) <= as_of_date)
                .order_by(col(StockOHLCVDaily.trading_date).asc())
                .limit(1)
            ).first()

            if bar is None:
                skipped_count += 1
                continue

            actual_value = bar.close
            reference_price = entry.parameter_snapshot.get("entry_price")
            if reference_price is None:
                reference_price = entry.predicted_value
            if reference_price is not None:
                diff = actual_value - float(reference_price)
                if diff > 0:
                    actual_dir = ForecastDirection.BULLISH
                elif diff < 0:
                    actual_dir = ForecastDirection.BEARISH
                else:
                    actual_dir = ForecastDirection.NEUTRAL
            else:
                actual_dir = (
                    ForecastDirection.BULLISH
                    if bar.close >= bar.open
                    else ForecastDirection.BEARISH
                )

            realized_dt = datetime.combine(
                bar.trading_date, datetime.min.time()
            ).replace(hour=14, minute=45, tzinfo=VN_TZ)
            now_vn = datetime.now(VN_TZ)
            if realized_dt > now_vn:
                realized_dt = now_vn

            try:
                self.resolve(
                    entry.id,
                    actual_value=actual_value,
                    actual_direction=actual_dir,
                    realized_at=realized_dt,
                )
                self.score(entry.id)
                resolved_count += 1
            except Exception as e:
                logger.warning("Failed to auto-resolve forecast %s: %s", entry.id, e)
                skipped_count += 1

        return {
            "resolved": resolved_count,
            "skipped": skipped_count,
            "pending_remaining": len(pending_rows) - resolved_count,
        }
