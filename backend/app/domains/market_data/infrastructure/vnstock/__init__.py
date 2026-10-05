"""Vnstock v4 integration infrastructure package.

Provides unified adapters, capability registry, and rate limiting for
official Vnstock v4 modules (Quote, Listing, Company, Finance, Reference, Market, Fundamental, Retail).
"""

from __future__ import annotations

from app.domains.market_data.infrastructure.vnstock.adapter import (
    VnstockService,
    VnstockServiceError,
    vnstock_service,
)
from app.domains.market_data.infrastructure.vnstock.registry import (
    CapabilityInfo,
    CapabilityStatus,
    DataAvailability,
    ProviderResponse,
    VnstockCapabilityRegistry,
)

__all__ = [
    "CapabilityInfo",
    "CapabilityStatus",
    "DataAvailability",
    "ProviderResponse",
    "VnstockCapabilityRegistry",
    "VnstockService",
    "VnstockServiceError",
    "vnstock_service",
]
