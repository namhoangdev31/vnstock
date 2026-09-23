"""Fundamental presentation router combining screener, corporate, and revision routers."""

from fastapi import APIRouter

from app.domains.fundamental.presentation.corporate_router import (
    router as corporate_router,
)
from app.domains.fundamental.presentation.revision_router import (
    router as revision_router,
)
from app.domains.fundamental.presentation.screener_router import (
    router as screener_router,
)

fundamental_router = APIRouter()
fundamental_router.include_router(screener_router)
fundamental_router.include_router(corporate_router)
fundamental_router.include_router(revision_router)
