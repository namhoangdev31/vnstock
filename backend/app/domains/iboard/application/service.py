"""Application Facade for iBoard Trading Board (Bảng giá v2).

Kiến trúc Clean Architecture & Domain-Driven Design (DDD):
- Domain Layer (Business Policies & Rules):
    `app.domains.iboard.domain.policy`
- Infrastructure Layer (External Gateways & I/O):
    `app.domains.iboard.infrastructure.external_indices`
- Application Layer (Specialized Use-Case Services):
    - `candles_service.py`: IBoardCandlesService
    - `indices_service.py`: IBoardIndicesService
    - `board_service.py`: IBoardTableService
    - `detail_service.py`: IBoardDetailService
    - `pulse_service.py`: IBoardPulseService
    - `ws_manager.py`: IBoardWSManager
- Facade Layer (IBoardService):
    Tập hợp và điều phối các use case cho presentation layer (FastAPI routers).
"""

from __future__ import annotations

from typing import Any

from sqlmodel import Session

from app.domains.iboard.application.board_service import IBoardTableService
from app.domains.iboard.application.candles_service import IBoardCandlesService
from app.domains.iboard.application.detail_service import IBoardDetailService
from app.domains.iboard.application.indices_service import IBoardIndicesService
from app.domains.iboard.application.pulse_service import IBoardPulseService
from app.domains.iboard.application.schemas import (
    IBoardCandleBar,
    IBoardIndexItem,
    IBoardMarketPulse,
    IBoardStockDetail,
    IBoardStockRow,
)
from app.domains.iboard.infrastructure.external_indices import (
    DowJonesGateway,
    IndexSparklineGateway,
)


class IBoardService:
    """Application Facade điều phối các use case của bảng giá iBoard v2."""

    # 1. Candles & Charts Use Case (100 phiên chuẩn DNSE/TradingView)
    @staticmethod
    def get_candles(
        session: Session,
        symbol: str,
        timeframe: str = "1D",
        limit: int = 60,
    ) -> list[IBoardCandleBar]:
        return IBoardCandlesService.get_candles(
            session=session, symbol=symbol, timeframe=timeframe, limit=limit
        )

    # 2. Market Indices Strip Use Case
    @classmethod
    def get_indices(cls, session: Session) -> list[IBoardIndexItem]:
        return IBoardIndicesService.get_indices(session)

    # 3. Multi-Category Board Table Use Case
    @staticmethod
    def get_board(
        session: Session,
        category: str = "listed",
        group: str = "VN30",
        sector: str | None = None,
        search: str | None = None,
        limit: int = 50,
    ) -> list[IBoardStockRow]:
        return IBoardTableService.get_board(
            session=session,
            category=category,
            group=group,
            sector=sector,
            search=search,
            limit=limit,
        )

    # 4. Stock Detail, Order Book & Ticks Use Case
    @staticmethod
    def get_stock_detail(
        session: Session, symbol: str, timeframe: str = "1D"
    ) -> IBoardStockDetail:
        return IBoardDetailService.get_stock_detail(
            session=session, symbol=symbol, timeframe=timeframe
        )

    # 5. Market Pulse & Quantitative AI Insight Use Case
    @classmethod
    def get_market_pulse(cls, session: Session) -> IBoardMarketPulse:
        return IBoardPulseService.get_market_pulse(session)

    @classmethod
    def _get_index_intraday_sparkline(
        cls,
        code: str,
        vn: Any,
        fallback_daily: list[float],
        cur_close: float,
    ) -> list[float]:
        return IndexSparklineGateway.get_sparkline(
            code=code,
            vn=vn,
            fallback_daily=fallback_daily,
            cur_close=cur_close,
        )

    @classmethod
    def _get_dow_jones_futures(cls) -> IBoardIndexItem | None:
        return DowJonesGateway.get_dow_jones_futures()


__all__ = [
    "IBoardCandleBar",
    "IBoardIndexItem",
    "IBoardMarketPulse",
    "IBoardService",
    "IBoardStockDetail",
    "IBoardStockRow",
]
