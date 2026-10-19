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

from app.domains.dnse import DNSEMarketBreadthGateway
from app.domains.iboard.application.board_service import IBoardTableService
from app.domains.iboard.application.candles_service import IBoardCandlesService
from app.domains.iboard.application.detail_service import IBoardDetailService
from app.domains.iboard.application.indices_service import IBoardIndicesService
from app.domains.iboard.application.news_service import IBoardNewsService
from app.domains.iboard.application.pulse_service import IBoardPulseService
from app.domains.iboard.application.schemas import (
    IBoardCandleBar,
    IBoardIndexItem,
    IBoardMarketPulse,
    IBoardNewsItem,
    IBoardPutThroughSummary,
    IBoardStockDetail,
    IBoardStockRow,
    MarketBreadthDetailResponse,
    MarketBreadthSeriesResponse,
)
from app.domains.iboard.infrastructure.external_indices import (
    IndexSparklineGateway,
)


class IBoardService:
    """Application Facade điều phối các use case của bảng giá iBoard v2."""

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

    @classmethod
    def get_indices(cls, session: Session) -> list[IBoardIndexItem]:
        return IBoardIndicesService.get_indices(session)

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

    @staticmethod
    def get_stock_detail(
        session: Session, symbol: str, timeframe: str = "1D"
    ) -> IBoardStockDetail:
        return IBoardDetailService.get_stock_detail(
            session=session, symbol=symbol, timeframe=timeframe
        )

    @classmethod
    def get_market_pulse(cls, session: Session) -> IBoardMarketPulse:
        return IBoardPulseService.get_market_pulse(session)

    @classmethod
    def get_news(
        cls, session: Session, limit: int = 30, randomize: bool = False
    ) -> list[IBoardNewsItem]:
        return IBoardNewsService.get_recent_news(
            session=session, limit=limit, randomize=randomize
        )

    @classmethod
    def get_market_breadth_series(cls, index_code: str) -> MarketBreadthSeriesResponse:
        return DNSEMarketBreadthGateway.get_market_breadth_series(index_code)

    @classmethod
    def get_market_breadth_detail(cls, index_code: str) -> MarketBreadthDetailResponse:
        return DNSEMarketBreadthGateway.get_market_breadth_detail(index_code)

    @classmethod
    def get_put_through_summary(
        cls, session: Session, exchange: str = "HSX"
    ) -> IBoardPutThroughSummary:
        from app.domains.iboard.application.put_through_service import (
            IBoardPutThroughService,
        )

        return IBoardPutThroughService.get_put_through_summary(
            session=session, exchange=exchange
        )

    @classmethod
    def _get_index_intraday_sparkline(
        cls,
        code: str,
        vn: Any,
        fallback_daily: list[float],
        cur_close: float,
    ) -> list[float | None]:
        return IndexSparklineGateway.get_sparkline(
            code=code,
            vn=vn,
            fallback_daily=fallback_daily,
            cur_close=cur_close,
        )


__all__ = [
    "IBoardCandleBar",
    "IBoardIndexItem",
    "IBoardMarketPulse",
    "IBoardNewsItem",
    "IBoardService",
    "IBoardStockDetail",
    "IBoardStockRow",
]
