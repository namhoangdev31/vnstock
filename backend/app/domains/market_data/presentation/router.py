"""Aggregated Presentation Router for Market Data & Ingestion."""

from fastapi import APIRouter

from app.domains.market_data.presentation.price_router import router as price_router
from app.domains.market_data.presentation.symbol_router import router as symbol_router
from app.domains.market_data.presentation.sync_router import router as sync_router

router = APIRouter(prefix="/stock", tags=["stock"])

router.include_router(symbol_router)
router.include_router(price_router)
router.include_router(sync_router)

__all__ = ["router"]
