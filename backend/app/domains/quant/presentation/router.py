"""Quant presentation router composition."""

from fastapi import APIRouter

from app.domains.quant.presentation.daemon_router import router as daemon_router
from app.domains.quant.presentation.forecast_router import router as forecast_router
from app.domains.quant.presentation.quant_router import router as quant_router

router = APIRouter()
router.include_router(quant_router)
router.include_router(forecast_router)
router.include_router(daemon_router)

__all__ = [
    "daemon_router",
    "forecast_router",
    "quant_router",
    "router",
]
