"""FastAPI Router for iBoard Professional Trading Board (Bảng giá v2)."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.api.deps import SessionDep
from app.domains.iboard.application.schemas import (
    IBoardCandleBar,
    IBoardIndexItem,
    IBoardMarketPulse,
    IBoardStockDetail,
    IBoardStockRow,
)
from app.domains.iboard.application.service import IBoardService
from app.domains.iboard.application.ws_manager import iboard_ws_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stock/iboard", tags=["iboard"])


@router.get("/indices", response_model=list[IBoardIndexItem])
def get_iboard_indices(
    session: SessionDep,
) -> Any:
    """Truy xuất dải chỉ số thị trường (VN30, VNINDEX, HNX30, HNX, VN30F1M)."""
    return IBoardService.get_indices(session)


@router.get("/board", response_model=list[IBoardStockRow])
def get_iboard_board(
    session: SessionDep,
    category: str = Query(
        default="listed",
        description="listed, derivatives, warrants, etf, sectors, watchlist, put_through",
    ),
    group: str = Query(
        default="VN30",
        description="VN30, HSX, HNX, UPCOM, MARGIN_DISCOUNT",
    ),
    sector: str | None = Query(
        default=None,
        description="Mã nhóm ngành (bank, real_estate, logistics, materials, food_beverage, industrial, utilities, telecom, retail)",
    ),
    search: str | None = Query(
        default=None,
        description="Tìm kiếm theo mã CK hoặc tên tổ chức",
    ),
    limit: int = Query(default=50, ge=1, le=200),
) -> Any:
    """Lấy danh sách bảng giá cổ phiếu, phái sinh, chứng quyền, ETF tương ứng."""
    return IBoardService.get_board(
        session=session,
        category=category,
        group=group,
        sector=sector,
        search=search,
        limit=limit,
    )


@router.get("/stock-detail/{symbol}", response_model=IBoardStockDetail)
def get_iboard_stock_detail(
    symbol: str,
    session: SessionDep,
    timeframe: str = Query(
        default="1D",
        description="Khung thời gian nến (1m, 5m, 15m, 1H, 1D, 1W)",
    ),
) -> Any:
    """Truy xuất chi tiết một mã: sổ lệnh 3 cấp, nến kỹ thuật, khớp lệnh thời gian và hồ sơ."""
    return IBoardService.get_stock_detail(
        session=session, symbol=symbol, timeframe=timeframe
    )


@router.get("/candles/{symbol}", response_model=list[IBoardCandleBar])
def get_iboard_candles(
    symbol: str,
    session: SessionDep,
    timeframe: str = Query(
        default="1D",
        description="Khung thời gian nến: 1m, 5m, 15m, 1H, 1D, 1W",
    ),
    limit: int = Query(default=60, ge=5, le=300),
) -> Any:
    """Truy xuất chuỗi nến kỹ thuật theo khung thời gian từ DB và vnstock_adapter."""
    return IBoardService.get_candles(
        session=session,
        symbol=symbol,
        timeframe=timeframe,
        limit=limit,
    )


@router.get("/market-pulse", response_model=IBoardMarketPulse)
def get_iboard_market_pulse(
    session: SessionDep,
) -> Any:
    """Truy xuất nhận định định lượng và top cổ phiếu biến động."""
    return IBoardService.get_market_pulse(session=session)


@router.websocket("/ws")
async def iboard_websocket_endpoint(websocket: WebSocket) -> None:
    """Realtime WebSocket streaming endpoint for iBoard trading board.

    Supports dynamic channel subscriptions:
    - `indices`: Real-time market indices updates (VNINDEX, VN30, HNX, HNX30, etc.)
    - `board`: Live quotes and orderbook changes across tracked symbols
    - `stock:{symbol}`: Individual stock depth and Time & Sales matched ticks
    - Bidirectional Ping/Pong heartbeats and instant snapshots
    """
    await iboard_ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await iboard_ws_manager.handle_client_message(websocket, data)
    except WebSocketDisconnect:
        await iboard_ws_manager.disconnect(websocket)
    except Exception as e:
        logger.debug("[IBoardRouter] WebSocket disconnected with error: %s", e)
        await iboard_ws_manager.disconnect(websocket)


__all__ = ["router"]
