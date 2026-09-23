"""Root API Router Aggregator (Composition Root).

Tập hợp tất cả routers từ các bounded context:
- Identity Domain: authentication, user management, items
- Market Data Domain: symbols, OHLCV, ticks, vnstock capabilities
- Fundamental Domain: financials, ratios, corporate governance, keyset screener
- Quant Domain: technical, liquidity, basis/ML engines, ensemble signals
- Simulation Domain: paper trading, order placement, portfolios, settlements
- System / Core: health-check, diagnostics, private dev routes
"""

from fastapi import APIRouter

from app.api.private_router import router as private_router
from app.api.system_router import router as system_router
from app.core.config import settings
from app.domains.fundamental.presentation.router import fundamental_router
from app.domains.identity.presentation.router import identity_router
from app.domains.market_data.presentation.router import router as market_data_router
from app.domains.market_data.presentation.vnstock_router import (
    router as vnstock_router,
)
from app.domains.quant.presentation.forecast_router import router as forecast_router
from app.domains.quant.presentation.quant_router import router as quant_router
from app.domains.simulation.presentation.router import router as simulation_router

api_router = APIRouter()
api_router.include_router(identity_router)
api_router.include_router(system_router)
api_router.include_router(market_data_router)
api_router.include_router(vnstock_router)
api_router.include_router(fundamental_router)
api_router.include_router(forecast_router)
api_router.include_router(simulation_router)
api_router.include_router(quant_router)

if settings.FASTAPI_ENV == "development":
    api_router.include_router(private_router)

__all__ = ["api_router"]
