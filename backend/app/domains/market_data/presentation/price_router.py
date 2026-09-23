"""Market Data Presentation: Price & Asset Routes.

Cung cấp các endpoints dữ liệu giá nến lịch sử ngày, giá thời gian thực,
mạng lưới liên kết tài sản, chứng quyền và trái phiếu.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import and_, col, func, select

from app.api.deps import CurrentUser, SessionDep
from app.domains.market_data.application.price_service import PriceService
from app.domains.market_data.application.schemas import (
    BondSpecificationPublic,
    CoveredWarrantPublic,
    PriceHistoryResponse,
    RelatedAssetsResponse,
)
from app.domains.market_data.domain.exceptions import SymbolNotFoundError
from app.domains.market_data.infrastructure.vnstock_adapter import VnstockServiceError
from app.domains.quant.application.schemas import (
    InstitutionalFlowPublic,
    MacroLatestResponse,
)
from app.domains.quant.domain.models import InstitutionalFlow, MacroIndicator

router = APIRouter()


@router.get("/{symbol}/price/daily", response_model=PriceHistoryResponse)
def get_daily_price(
    session: SessionDep,
    current_user: CurrentUser,  # noqa: ARG001
    symbol: str,
    start: date = Query(description="Start date (YYYY-MM-DD)"),
    end: date = Query(default_factory=date.today, description="End date"),
) -> Any:
    """Lấy dữ liệu nến lịch sử giao dịch hàng ngày (OHLCV Daily) từ PostgreSQL.

    Nếu thiếu dữ liệu, tự động kích hoạt tiến trình backfill từ vnstock.
    """
    try:
        return PriceService.get_daily_price(session, symbol, start, end)
    except VnstockServiceError:
        raise HTTPException(
            status_code=503,
            detail=f"No data available for {symbol} and external source is unavailable",
        )


@router.get("/{symbol}/price/realtime")
def get_realtime_price(
    current_user: CurrentUser,  # noqa: ARG001
    symbol: str,
) -> Any:
    """Lấy giá thời gian thực gần nhất với bộ đệm in-memory (3-5 giây)."""
    try:
        return PriceService.get_realtime_price(symbol)
    except VnstockServiceError:
        raise HTTPException(
            status_code=503,
            detail=f"Realtime data for {symbol} unavailable from all sources",
        )


@router.get("/{symbol}/related-assets", response_model=RelatedAssetsResponse)
def get_related_assets(
    session: SessionDep,
    current_user: CurrentUser,  # noqa: ARG001
    symbol: str,
) -> Any:
    """Truy xuất mạng lưới tài sản liên kết chéo của một mã chứng khoán (CP, CW, Trái phiếu, Phái sinh, Index)."""
    try:
        return PriceService.get_related_assets(session, symbol)
    except SymbolNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Không tìm thấy mã chứng khoán: {symbol}",
        )


@router.get("/warrants", response_model=list[CoveredWarrantPublic])
def list_covered_warrants(
    session: SessionDep,
    current_user: CurrentUser,  # noqa: ARG001
    underlying_symbol: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """Danh sách các chứng quyền có bảo đảm kèm bộ lọc theo mã cổ phiếu cơ sở."""
    return PriceService.list_covered_warrants(
        session=session,
        underlying_symbol=underlying_symbol,
        skip=skip,
        limit=limit,
    )


@router.get("/bonds", response_model=list[BondSpecificationPublic])
def list_bonds(
    session: SessionDep,
    current_user: CurrentUser,  # noqa: ARG001
    bond_type: str | None = None,
    issuer_symbol: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """Danh sách trái phiếu doanh nghiệp & trái phiếu chính phủ kèm bộ lọc."""
    return PriceService.list_bonds(
        session=session,
        bond_type=bond_type,
        issuer_symbol=issuer_symbol,
        skip=skip,
        limit=limit,
    )


@router.get("/macro/latest", response_model=MacroLatestResponse)
def get_macro_latest(
    session: SessionDep,
    current_user: CurrentUser,  # noqa: ARG001
) -> Any:
    """Latest macro indicator per code (USD/VND, SJC gold buy/sell)."""
    subq = (
        select(
            MacroIndicator.indicator_code,
            func.max(MacroIndicator.recorded_date).label("max_date"),
        )
        .group_by(col(MacroIndicator.indicator_code))
        .subquery()
    )
    rows = session.exec(
        select(MacroIndicator)
        .join(
            subq,
            and_(
                col(MacroIndicator.indicator_code) == subq.c.indicator_code,
                col(MacroIndicator.recorded_date) == subq.c.max_date,
            ),
        )
        .order_by(col(MacroIndicator.indicator_code))
    ).all()

    data = list(rows)
    as_of = max((r.recorded_date for r in rows), default=None)
    if as_of is None:
        raise HTTPException(status_code=404, detail="No macro data available yet")
    return MacroLatestResponse(as_of=as_of, data=data)


@router.get("/institutional-flow", response_model=list[InstitutionalFlowPublic])
def get_institutional_flow(
    session: SessionDep,
    current_user: CurrentUser,  # noqa: ARG001
    trading_date: date | None = None,
    symbol: str | None = None,
    limit: int = Query(default=30, ge=1, le=200),
) -> Any:
    """Persisted institutional flow rows (foreign + proprietary desk)."""
    query = select(InstitutionalFlow)
    if trading_date is not None:
        query = query.where(InstitutionalFlow.trading_date == trading_date)
    if symbol is not None:
        query = query.where(InstitutionalFlow.symbol == symbol)
    rows = session.exec(
        query.order_by(col(InstitutionalFlow.trading_date).desc()).limit(limit)
    ).all()
    return [InstitutionalFlowPublic.model_validate(r) for r in rows]
