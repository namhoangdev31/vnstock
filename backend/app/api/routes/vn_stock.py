"""Router quản lý thông tin cấu hình và trạng thái dịch vụ vnstock."""

import logging

from fastapi import APIRouter

from app.services.vnstock_service import vnstock_service

router = APIRouter(prefix="/vnstock", tags=["vnstock"])
logger = logging.getLogger(__name__)


@router.get("", response_model=list[str])
def get_vnstock() -> list[str]:
    """Lấy danh sách các nguồn dữ liệu đang được cấu hình và hoạt động của vnstock."""
    sources = vnstock_service.sources
    logger.info("Danh sách nguồn dữ liệu vnstock: %s", sources)
    return sources
