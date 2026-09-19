from fastapi import APIRouter

from app.api.routes import (
    forecast,
    items,
    login,
    private,
    quant,
    simulation,
    stock,
    users,
    utils,
)
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(utils.router)
api_router.include_router(items.router)
api_router.include_router(stock.router)
api_router.include_router(forecast.router)
api_router.include_router(simulation.router)
api_router.include_router(quant.router)


if settings.FASTAPI_ENV == "development":
    api_router.include_router(private.router)
