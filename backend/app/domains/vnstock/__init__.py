"""Vnstock v4 integration domain package.

Provides unified adapters, capability registry, and rate limiting for
official Vnstock v4 modules (Quote, Listing, Company, Finance, Reference, Market, Fundamental, Retail).
"""

from __future__ import annotations

from app.domains.vnstock.adapter import (
    VnstockService,
    vnstock_service,
)
from app.domains.vnstock.exceptions import VnstockServiceError
from app.domains.vnstock.presentation.router import router as vnstock_router
from app.domains.vnstock.registry import (
    CapabilityInfo,
    CapabilityStatus,
    DataAvailability,
    ProviderResponse,
    VnstockCapabilityRegistry,
)
from app.domains.vnstock.schemas import VnstockSymbolResponse

__all__ = [
    "CapabilityInfo",
    "CapabilityStatus",
    "DataAvailability",
    "ProviderResponse",
    "VnstockCapabilityRegistry",
    "VnstockService",
    "VnstockServiceError",
    "VnstockSymbolResponse",
    "vnstock_router",
    "vnstock_service",
]
