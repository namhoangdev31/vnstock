"""Fundamental Presentation Layer."""

from app.domains.fundamental.presentation.corporate_router import (
    router as corporate_router,
)
from app.domains.fundamental.presentation.revision_router import (
    router as revision_router,
)
from app.domains.fundamental.presentation.router import fundamental_router
from app.domains.fundamental.presentation.screener_router import (
    router as screener_router,
)

__all__ = [
    "corporate_router",
    "fundamental_router",
    "revision_router",
    "screener_router",
]
