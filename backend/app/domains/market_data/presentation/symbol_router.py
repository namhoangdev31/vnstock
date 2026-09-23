"""Market Data Presentation: Symbol & Index Routes.

Cung cấp các endpoints tra cứu danh mục mã chứng khoán và rổ chỉ số.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException

from app.api.deps import CurrentUser, SessionDep
from app.domains.market_data.application.schemas import (
    IndexConstituentsResponse,
    StockSymbolPublic,
    StockSymbolsPublic,
)
from app.domains.market_data.application.symbol_service import SymbolService
from app.domains.market_data.domain.exceptions import SymbolNotFoundError
from app.domains.market_data.infrastructure.vnstock_adapter import VnstockServiceError
from app.domains.quant.application.schemas import SymbolGroupResponse

router = APIRouter()


@router.get("/symbols", response_model=StockSymbolsPublic)
def list_symbols(
    session: SessionDep,
    current_user: CurrentUser,  # noqa: ARG001
    skip: int = 0,
    limit: int = 100,
    exchange: str | None = None,
    asset_type: str | None = None,
    search: str | None = None,
) -> Any:
    """Danh sách các mã chứng khoán kèm số lượng và bộ lọc."""
    return SymbolService.list_symbols(
        session=session,
        skip=skip,
        limit=limit,
        exchange=exchange,
        asset_type=asset_type,
        search=search,
    )


@router.get("/symbol/by-id/{symbol_id}", response_model=StockSymbolPublic)
def get_symbol_by_id(
    session: SessionDep,
    current_user: CurrentUser,  # noqa: ARG001
    symbol_id: uuid.UUID,
) -> Any:
    """Tra cứu thông tin mã chứng khoán theo UUID định danh nội bộ."""
    try:
        return SymbolService.get_symbol_by_id(session, symbol_id)
    except SymbolNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Stock symbol not found for ID: {symbol_id}",
        )


@router.get("/symbols/group/{group}", response_model=SymbolGroupResponse)
def get_symbol_group(
    current_user: CurrentUser,  # noqa: ARG001
    group: str,
) -> Any:
    """Danh sách các mã cổ phiếu thuộc nhóm/rổ chỉ số (e.g. VN30, VN100)."""
    try:
        return SymbolService.get_symbol_group(group)
    except VnstockServiceError:
        raise HTTPException(
            status_code=503,
            detail=f"Symbol group {group} unavailable from all data sources",
        )


@router.get("/index-constituents/{group}", response_model=IndexConstituentsResponse)
def get_index_constituents(
    session: SessionDep,
    current_user: CurrentUser,  # noqa: ARG001
    group: str,
) -> Any:
    """Tra cứu thành phần và tỷ trọng rổ chỉ số (VN30, VN100, VNFINLEAD)."""
    return SymbolService.get_index_constituents(session, group)
