"""Authenticated Phase 5 model governance endpoints."""

from fastapi import APIRouter, HTTPException
from sqlmodel import col, select

from app.api.deps import CurrentUser, SessionDep
from app.core.models_base import get_datetime_utc
from app.domains.quant.application.recalibration_engine import (
    BASELINE_WEIGHTS,
    RecalibrationEngine,
)
from app.domains.quant.application.schemas import (
    ModelVersionPublic,
    RecalibrationResponse,
)
from app.domains.quant.domain.models import ModelVersionSnapshot

router = APIRouter(prefix="/quant", tags=["quant-model-governance"])


@router.get("/versions", response_model=list[ModelVersionPublic])
def list_versions(
    session: SessionDep, current_user: CurrentUser
) -> list[ModelVersionSnapshot]:
    if not current_user.is_active:
        raise HTTPException(status_code=403, detail="Inactive user")
    return list(
        session.exec(
            select(ModelVersionSnapshot).order_by(
                col(ModelVersionSnapshot.created_at).desc()
            )
        ).all()
    )


@router.post("/recalibrate/auto-run", response_model=RecalibrationResponse)
def auto_recalibrate(
    session: SessionDep, current_user: CurrentUser
) -> RecalibrationResponse:
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough privileges")
    result = RecalibrationEngine(session).auto_run()
    return RecalibrationResponse(**result)


@router.post("/versions/{version_tag}/rollback", response_model=ModelVersionPublic)
def rollback_version(
    version_tag: str, session: SessionDep, current_user: CurrentUser
) -> ModelVersionSnapshot:
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough privileges")
    target = session.exec(
        select(ModelVersionSnapshot).where(
            ModelVersionSnapshot.version_tag == version_tag
        )
    ).first()
    if target is None:
        raise HTTPException(status_code=404, detail="Model version not found")
    active = session.exec(
        select(ModelVersionSnapshot).where(ModelVersionSnapshot.is_active)
    ).first()
    if active is not None and active.id != target.id:
        active.is_active = False
        active.updated_at = get_datetime_utc()
        session.add(active)
    target.is_active = True
    target.auto_promotion_enabled = True
    target.rolled_back_at = get_datetime_utc()
    target.rollback_reason = "manual rollback"
    target.updated_at = get_datetime_utc()
    session.add(target)
    session.commit()
    session.refresh(target)
    return target


@router.post("/circuit-breaker/reset", response_model=ModelVersionPublic)
def reset_circuit_breaker(
    session: SessionDep, current_user: CurrentUser
) -> ModelVersionSnapshot:
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough privileges")
    active = session.exec(
        select(ModelVersionSnapshot).where(ModelVersionSnapshot.is_active)
    ).first()
    if active is not None:
        active.is_active = False
        active.updated_at = get_datetime_utc()
        session.add(active)
    snapshot = ModelVersionSnapshot(
        version_tag=f"defensive-{get_datetime_utc().strftime('%Y%m%d%H%M%S')}",
        parameter_snapshot={"source": "manual-breaker-reset"},
        **BASELINE_WEIGHTS,
        is_active=True,
        auto_promotion_enabled=True,
        promoted_at=get_datetime_utc(),
    )
    session.add(snapshot)
    session.commit()
    session.refresh(snapshot)
    return snapshot
