import logging

from fastapi.routing import APIRouter

from app.services.vnstock_service import VnstockService

route = APIRouter(prefix="vnstock", tags=["vnstock"])
logger = logging.getLogger(__name__)


@route.get("/", response_model=list[str])
def get_vnstock():
    logger.info("get_vnstock", VnstockService.sources)
    return VnstockService.sources
