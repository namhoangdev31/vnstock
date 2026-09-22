"""Router quản lý thông tin danh mục mã và cấu hình dịch vụ vnstock."""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from app.models.models_vnstock import VnstockSymbolResponse
from app.services.vnstock_registry import (
    CapabilityInfo,
    CapabilityStatus,
    VnstockCapabilityRegistry,
)
from app.services.vnstock_service import vnstock_service

router = APIRouter(prefix="/vnstock", tags=["vnstock"])
logger = logging.getLogger(__name__)


@router.get("/", response_model=list[VnstockSymbolResponse])
def get_vnstock(
    exchange: str | None = Query(
        default=None,
        description="Lọc theo sàn giao dịch (ví dụ: 'HOSE', 'HNX', 'UPCOM'). Bỏ trống để lấy toàn bộ các sàn.",
    ),
) -> list[dict[str, Any]]:
    """Lấy danh sách tất cả các mã cổ phiếu kèm thông tin sàn niêm yết (HOSE, HNX, UPCOM) từ vnstock."""
    df = vnstock_service.fetch_symbols_by_exchange(exchange=exchange)
    cols = [c for c in ["symbol", "organ_name", "exchange"] if c in df.columns]
    sub_df: Any = df[cols]
    records: list[dict[str, Any]] = sub_df.where(pd.notnull(sub_df), None).to_dict(
        orient="records"
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


@router.get("/capabilities", response_model=dict[str, CapabilityInfo])
def get_vnstock_capabilities(
    status: CapabilityStatus | None = Query(
        default=None,
        description="Lọc theo trạng thái năng lực: 'available', 'unavailable', hoặc 'out_of_scope'.",
    ),
    module: str | None = Query(
        default=None,
        description="Lọc theo tên module (ví dụ: Quote, Listing, Company, Finance, Retail, Market, Reference, Flow, External).",
    ),
) -> dict[str, CapabilityInfo]:
    """Lấy toàn bộ ma trận năng lực và nguồn cấp dữ liệu của hệ sinh thái vnstock v4."""
    capabilities = VnstockCapabilityRegistry.CAPABILITIES
    result: dict[str, CapabilityInfo] = {}
    for key, info in capabilities.items():
        if status is not None and info.status != status:
            continue
        if module is not None and info.module.lower() != module.lower():
            continue
        result[key] = info
    logger.info("Trả về %d capabilities từ VnstockCapabilityRegistry", len(result))
    return result


@router.get("/capabilities/{key}", response_model=CapabilityInfo)
def get_vnstock_capability_detail(key: str) -> CapabilityInfo:
    """Tra cứu chi tiết một tính năng cụ thể trong ma trận năng lực vnstock."""
    info = VnstockCapabilityRegistry.CAPABILITIES.get(key)
    if not info:
        raise HTTPException(
            status_code=404,
            detail=f"Capability '{key}' không tồn tại trong VnstockCapabilityRegistry",
        )
    return info
