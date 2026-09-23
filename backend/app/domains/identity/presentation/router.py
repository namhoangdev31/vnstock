"""Aggregated Presentation Router for Identity Domain."""

from fastapi import APIRouter

from app.domains.identity.presentation.auth_router import router as auth_router
from app.domains.identity.presentation.items_router import router as items_router
from app.domains.identity.presentation.users_router import router as users_router

identity_router = APIRouter()
identity_router.include_router(auth_router)
identity_router.include_router(users_router)
identity_router.include_router(items_router)

__all__ = ["auth_router", "identity_router", "items_router", "users_router"]
