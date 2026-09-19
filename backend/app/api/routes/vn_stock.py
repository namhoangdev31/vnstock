"""Router quản lý thông tin danh mục mã và cấu hình dịch vụ vnstock."""

import logging
from typing import Any

import pandas as pd
from fastapi import APIRouter, Query

from app.models.models_vnstock import VnstockSymbolItem
from app.services.vnstock_service import vnstock_service

router = APIRouter(prefix="/vnstock", tags=["vnstock"])
logger = logging.getLogger(__name__)


@router.get("/", response_model=list[VnstockSymbolItem])
def get_vnstock(
    exchange: str | None = Query(
        default=None,
        description="Lọc theo sàn giao dịch (ví dụ: 'HOSE', 'HNX', 'UPCOM'). Bỏ trống để lấy toàn bộ các sàn.",
    ),
) -> list[dict[str, Any]]:
    """Lấy danh sách tất cả các mã cổ phiếu kèm thông tin sàn niêm yết (HOSE, HNX, UPCOM) từ vnstock."""
    df = vnstock_service.fetch_symbols_by_exchange(exchange=exchange)
    cols = [c for c in ["symbol", "organ_name", "exchange"] if c in df.columns]
    records: list[dict[str, Any]] = (
        df[cols].where(pd.notnull(df[cols]), None).to_dict(orient="records")
    )
    logger.info(
        "Đã tải %d mã cổ phiếu (sàn: %s) từ vnstock",
        len(records),
        exchange or "tất cả",
    )
    return records


@router.get("/sources", response_model=list[str])
def get_vnstock_sources() -> list[str]:
    """Lấy danh sách các nguồn dữ liệu đang được cấu hình và hoạt động của vnstock."""
    sources = vnstock_service.sources
    logger.info("Danh sách nguồn dữ liệu vnstock: %s", sources)
    return sources
