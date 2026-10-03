"""Governed Phase 5 calibration and walk-forward promotion logic."""

from __future__ import annotations

import logging
import math
from datetime import date, datetime, timedelta

from sqlmodel import Session, col, select

from app.core.enums import ForecastStatus
from app.core.models_base import VN_TZ, get_datetime_utc
from app.domains.quant.domain.models import ForecastJournal, ModelVersionSnapshot

BASELINE_WEIGHTS = {"w1": 0.33, "w2": 0.33, "w3": 0.34}
MIN_WEIGHT = 0.15
MAX_WEIGHT = 0.60
MAX_DELTA = 0.05
logger = logging.getLogger(__name__)


def project_weights(
    proposal: dict[str, float], active: dict[str, float]
) -> dict[str, float]:
    """Project onto the simplex with bounds and an active-version delta cap."""
    keys = ("w1", "w2", "w3")
    lower = {key: max(MIN_WEIGHT, active[key] - MAX_DELTA) for key in keys}
    upper = {key: min(MAX_WEIGHT, active[key] + MAX_DELTA) for key in keys}
    values = {
        key: min(upper[key], max(lower[key], float(proposal.get(key, active[key]))))
        for key in keys
    }
    # Distribute the residual across non-saturated coordinates. Three weights and
    # a small bounded interval make this deterministic and easy to audit.
    for _ in range(8):
        residual = 1.0 - sum(values.values())
        if abs(residual) < 1e-10:
            break
        candidates = [
            key for key in keys if lower[key] + 1e-10 < values[key] < upper[key] - 1e-10
        ]
        if not candidates:
            candidates = [
                key
                for key in keys
                if (residual > 0 and values[key] < upper[key])
                or (residual < 0 and values[key] > lower[key])
            ]
        if not candidates:
            break
        share = residual / len(candidates)
        for key in candidates:
            values[key] = min(upper[key], max(lower[key], values[key] + share))
    return {key: round(values[key], 8) for key in keys}


def softmax(values: list[float], alpha: float = 0.50) -> list[float]:
    scaled = [alpha * value for value in values]
    peak = max(scaled, default=0.0)
    exps = [math.exp(value - peak) for value in scaled]
    total = sum(exps) or 1.0
    return [value / total for value in exps]


def _metrics(rows: list[ForecastJournal]) -> dict[str, float | int | None]:
    directionals = [
        row.directional_correct for row in rows if row.directional_correct is not None
    ]
    briers = [row.brier_score for row in rows if row.brier_score is not None]
    errors = [
        row.absolute_error if row.absolute_error is not None else row.error
        for row in rows
    ]
    errors = [value for value in errors if value is not None]
    return {
        "count": len(rows),
        "da": sum(directionals) / len(directionals) if directionals else None,
        "brier": sum(briers) / len(briers) if briers else None,
        "mae": sum(errors) / len(errors) if errors else None,
    }


def candidate_weights(
    rows: list[ForecastJournal], active: dict[str, float]
) -> dict[str, float]:
    scores: list[float] = []
    for key in ("engine1", "engine2", "engine3"):
        engine_rows = [
            row
            for row in rows
            if key in row.parameter_snapshot.get("engine_forecasts", {})
        ]
        metrics = _metrics(engine_rows)
        da = float(metrics["da"] or 0.5)
        brier = float(metrics["brier"] if metrics["brier"] is not None else 0.5)
        scores.append(0.5 * da + 0.5 * (1.0 - brier))
    raw = dict(zip(("w1", "w2", "w3"), softmax(scores), strict=True))
    return project_weights(raw, active)


class RecalibrationEngine:
    """DB-backed evaluator with an atomic, evidence-gated promotion path."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def active_snapshot(self) -> ModelVersionSnapshot:
        row = self.session.exec(
            select(ModelVersionSnapshot)
            .where(ModelVersionSnapshot.is_active == True)  # noqa: E712
            .order_by(col(ModelVersionSnapshot.created_at).desc())
        ).first()
        if row is None:
            row = ModelVersionSnapshot(
                version_tag="v2.0.0",
                parameter_snapshot={"source": "phase5-baseline"},
                **BASELINE_WEIGHTS,
                is_active=True,
                promoted_at=get_datetime_utc(),
            )
            self.session.add(row)
            self.session.commit()
            self.session.refresh(row)
        return row

    def auto_run(self, *, now: datetime | None = None) -> dict:
        now = now or datetime.now(VN_TZ)
        breaker = self.evaluate_circuit_breaker(now=now)
        if breaker is not None:
            return breaker
        cutoff = now.date() - timedelta(days=45)
        rows = list(
            self.session.exec(
                select(ForecastJournal)
                .where(ForecastJournal.status == ForecastStatus.SCORED)
                .where(
                    col(ForecastJournal.predicted_at)
                    >= datetime.combine(cutoff, datetime.min.time(), tzinfo=VN_TZ)
                )
                .order_by(col(ForecastJournal.predicted_at))
            ).all()
        )
        complete = [
            row
            for row in rows
            if row.brier_score is not None
            and row.absolute_error is not None
            and row.parameter_snapshot.get("engine_forecasts")
        ]
        active = self.active_snapshot()
        if len(complete) < 30:
            return {
                "status": "insufficient_evidence",
                "reason": "at least 30 complete scored forecasts are required",
                "metrics": {"count": len(complete)},
            }
        training, validation = complete[:-9], complete[-9:]
        weights = candidate_weights(
            training, {"w1": active.w1, "w2": active.w2, "w3": active.w3}
        )
        baseline_metrics = _metrics(validation)
        # Candidate metrics are calculated counterfactually from immutable engine targets.
        candidate_errors = []
        candidate_briers = []
        candidate_directions = []
        for row in validation:
            forecasts = row.parameter_snapshot["engine_forecasts"]
            if row.actual_value is None:
                continue
            mapping = (("w1", "engine1"), ("w2", "engine2"), ("w3", "engine3"))
            target = sum(
                weights[weight] * float(forecasts[engine]["target_price"])
                for weight, engine in mapping
                if engine in forecasts
            )
            candidate_errors.append(abs(target - float(row.actual_value)))
            probability = sum(
                weights[weight] * float(forecasts[engine]["probability"])
                for weight, engine in mapping
                if engine in forecasts
            )
            outcome = 1.0 if str(row.actual_direction).upper() == "BULLISH" else 0.0
            candidate_briers.append((probability - outcome) ** 2)
            candidate_directions.append(
                (
                    target
                    >= float(
                        row.parameter_snapshot.get(
                            "entry_price", row.predicted_value or target
                        )
                    )
                )
                == (outcome == 1.0)
            )
        candidate_mae = sum(candidate_errors) / len(candidate_errors)
        candidate = {
            "da": sum(candidate_directions) / len(candidate_directions),
            "brier": sum(candidate_briers) / len(candidate_briers),
            "mae": candidate_mae,
        }
        passes = (
            candidate["brier"] is not None
            and baseline_metrics["brier"] is not None
            and candidate["brier"] < baseline_metrics["brier"]
            and candidate_mae < float(baseline_metrics["mae"] or math.inf)
            and float(candidate["da"] or 0.0) >= float(baseline_metrics["da"] or 0.0)
        )
        if not passes or not active.auto_promotion_enabled:
            return {
                "status": "rejected",
                "reason": "walk-forward gate failed or auto-promotion is disabled",
                "metrics": {"baseline": baseline_metrics, "candidate": candidate},
            }
        tag = f"v{now.strftime('%Y%m%d%H%M%S')}"
        active.is_active = False
        active.updated_at = get_datetime_utc()
        promoted = ModelVersionSnapshot(
            version_tag=tag,
            parameter_snapshot={
                "alpha": 0.50,
                "tau": 0.5,
                "training_count": len(training),
                "validation_count": len(validation),
            },
            **weights,
            is_active=True,
            auto_promoted=True,
            baseline_version_tag=active.version_tag,
            rolling_da=float(candidate["da"] or 0),
            rolling_brier=float(candidate["brier"] or 0),
            rolling_mae=candidate_mae,
            promoted_at=get_datetime_utc(),
        )
        self.session.add_all([active, promoted])
        self.session.commit()
        self.session.refresh(promoted)
        return {
            "status": "promoted",
            "version": promoted,
            "metrics": {"baseline": baseline_metrics, "candidate": candidate},
        }

    def evaluate_circuit_breaker(self, *, now: datetime | None = None) -> dict | None:
        """Trip on three consecutive ledger days below the active DA baseline."""
        active = self.active_snapshot()
        rows = list(
            self.session.exec(
                select(ForecastJournal)
                .where(ForecastJournal.status == ForecastStatus.SCORED)
                .where(
                    col(ForecastJournal.predicted_at)
                    >= datetime.now(VN_TZ) - timedelta(days=45)
                )
                .order_by(col(ForecastJournal.predicted_at).desc())
            ).all()
        )
        by_day: dict[date, list[ForecastJournal]] = {}
        for row in rows:
            if row.directional_correct is not None:
                by_day.setdefault(row.predicted_at.date(), []).append(row)
        days = sorted(by_day)[-3:]
        if len(days) < 3:
            return None
        baseline_da = active.rolling_da or _metrics(rows[:30])["da"]
        if baseline_da is None:
            return None
        daily_da = [
            sum(bool(row.directional_correct) for row in by_day[day]) / len(by_day[day])
            for day in days
        ]
        if not all(value < float(baseline_da) for value in daily_da):
            return None
        active.is_active = False
        active.auto_promotion_enabled = False
        active.updated_at = get_datetime_utc()
        current_time = now or datetime.now(VN_TZ)
        defensive = ModelVersionSnapshot(
            version_tag=f"defensive-{current_time.strftime('%Y%m%d%H%M%S')}",
            parameter_snapshot={
                "source": "ledger-circuit-breaker",
                "failed_days": [str(day) for day in days],
            },
            **BASELINE_WEIGHTS,
            is_active=True,
            circuit_breaker_triggered=True,
            auto_promotion_enabled=False,
            baseline_version_tag=active.version_tag,
            promoted_at=get_datetime_utc(),
        )
        self.session.add_all([active, defensive])
        self.session.commit()
        self.session.refresh(defensive)
        logger.error("Phase 5 circuit breaker tripped for days %s", days)
        return {
            "status": "circuit_breaker_triggered",
            "version": defensive,
            "metrics": {"daily_da": daily_da, "baseline_da": baseline_da},
        }
