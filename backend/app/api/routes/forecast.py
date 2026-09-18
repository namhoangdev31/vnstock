"""Forecast journal API — the RULE 3 audit ledger (AGENTS §9.1).

Endpoints:
- POST /forecast            record a new forecast (pending)
- GET  /forecast            list forecasts (filterable)
- GET  /forecast/{id}       fetch one
- POST /forecast/{id}/resolve  back-fill the realized outcome (no look-ahead)
- POST /forecast/{id}/score    compute MAE / directional accuracy
- GET  /forecast/aggregate  accuracy rollup (read-only Layer B input)

All endpoints are JWT-protected. Recording/resolving/scoring are SuperUser-only
since they mutate the learning substrate.
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import CurrentUser, SessionDep
from app.models.models_quant import (
    ForecastAggregateResponse,
    ForecastCreate,
    ForecastJournal,
    ForecastJournalPublic,
    ForecastResolve,
    ForecastScoredPublic,
)
from app.services.forecast_journal import ForecastJournalError, ForecastJournalService

router = APIRouter(prefix="/forecast", tags=["forecast"])


@router.post("", response_model=ForecastJournalPublic)
def create_forecast(
    session: SessionDep,
    current_user: CurrentUser,
    payload: ForecastCreate,
) -> Any:
    """Record a forecast emitted by the ensemble (status → pending)."""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough privileges")
    svc = ForecastJournalService(session)
    try:
        entry = svc.record(
            symbol=payload.symbol,
            predicted_at=payload.predicted_at,
            model_version=payload.model_version,
            horizon=payload.horizon,
            predicted_value=payload.predicted_value,
            predicted_direction=payload.predicted_direction,
            engine_weights=payload.engine_weights,
            parameter_snapshot=payload.parameter_snapshot,
        )
    except ForecastJournalError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return ForecastJournalPublic.model_validate(entry)


@router.get("", response_model=list[ForecastJournalPublic])
def list_forecasts(
    session: SessionDep,
    current_user: CurrentUser,  # noqa: ARG001
    symbol: str | None = None,
    horizon: str | None = None,
    status: str | None = None,
    model_version: str | None = None,
    limit: int = Query(default=50, ge=1, le=500),
) -> Any:
    """List forecasts with optional filters."""
    from sqlmodel import col, select

    query = select(ForecastJournal)
    if symbol is not None:
        query = query.where(ForecastJournal.symbol == symbol)
    if horizon is not None:
        query = query.where(ForecastJournal.horizon == horizon)
    if status is not None:
        query = query.where(ForecastJournal.status == status)
    if model_version is not None:
        query = query.where(ForecastJournal.model_version == model_version)
    rows = session.exec(
        query.order_by(col(ForecastJournal.predicted_at).desc()).limit(limit)
    ).all()
    return [ForecastJournalPublic.model_validate(r) for r in rows]


@router.get("/aggregate", response_model=ForecastAggregateResponse)
def aggregate_forecasts(
    session: SessionDep,
    current_user: CurrentUser,  # noqa: ARG001
    symbol: str | None = None,
    horizon: str | None = None,
    model_version: str | None = None,
) -> Any:
    """MAE & directional-accuracy rollup across scored forecasts."""
    svc = ForecastJournalService(session)
    return ForecastAggregateResponse(
        **svc.aggregate(symbol=symbol, horizon=horizon, model_version=model_version)
    )


@router.get("/{forecast_id}", response_model=ForecastJournalPublic)
def get_forecast(
    session: SessionDep,
    current_user: CurrentUser,  # noqa: ARG001
    forecast_id: UUID,
) -> Any:
    """Fetch a single forecast by id."""
    entry = session.get(ForecastJournal, forecast_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Forecast not found")
    return ForecastJournalPublic.model_validate(entry)


@router.post("/{forecast_id}/resolve", response_model=ForecastJournalPublic)
def resolve_forecast(
    session: SessionDep,
    current_user: CurrentUser,
    forecast_id: UUID,
    payload: ForecastResolve,
) -> Any:
    """Back-fill the realized outcome (status → resolved).

    The original ``predicted_at`` is never modified — this is the no-look-ahead
    anchor (TEST-JRN-02).
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough privileges")
    svc = ForecastJournalService(session)
    try:
        entry = svc.resolve(
            forecast_id,
            actual_value=payload.actual_value,
            actual_direction=payload.actual_direction,
            realized_at=payload.realized_at,
        )
    except ForecastJournalError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return ForecastJournalPublic.model_validate(entry)


@router.post("/{forecast_id}/score", response_model=ForecastScoredPublic)
def score_forecast(
    session: SessionDep,
    current_user: CurrentUser,
    forecast_id: UUID,
) -> Any:
    """Compute MAE / directional accuracy (status → scored)."""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough privileges")
    svc = ForecastJournalService(session)
    try:
        entry = svc.score(forecast_id)
    except ForecastJournalError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return ForecastScoredPublic.model_validate(entry)
