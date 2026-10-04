"""Application Facade for iBoard Trading Board (Bảng giá v2).

Kiến trúc Clean Architecture & Domain-Driven Design (DDD):
- Domain Layer (Business Policies & Rules):
    `app.domains.market_data.domain.iboard_policy`
    Chứa các quy tắc phân loại giá, chuẩn hoá thang giá (1/1000 cho cổ phiếu,
    1.0 cho phái sinh), trích xuất sổ lệnh 3 cấp, và tính toán độ rộng thị trường.
- Infrastructure Layer (External Gateways & I/O):
    `app.domains.market_data.infrastructure.external_indices`
    Chứa cổng kết nối dữ liệu vnstock_adapter, Yahoo Finance (Dow Jones), và sparkline cache.
- Application Layer (Specialized Use-Case Services):
    - `iboard_candles.py`: IBoardCandlesService (Chuỗi nến 100 phiên theo chuẩn TradingView/DNSE).
    - `iboard_indices.py`: IBoardIndicesService (Dải chỉ số thị trường VN30, VNINDEX, DOW JONES).
    - `iboard_board.py`: IBoardTableService (Bảng giá đa danh mục: Niêm yết, Phái sinh, Chứng quyền, ETF).
    - `iboard_detail.py`: IBoardDetailService (Sổ lệnh 3 cấp, khớp lệnh trực tiếp, hồ sơ tài chính).
    - `iboard_pulse.py`: IBoardPulseService (Nhịp đập thị trường, độ rộng ngành & AI insight).
- Facade Layer (IBoardService):
    Tập hợp và điều phối các use case cho presentation layer (FastAPI routers).
"""

from __future__ import annotations

from typing import Any

from sqlmodel import Session

from app.domains.market_data.application.iboard_board import IBoardTableService
from app.domains.market_data.application.iboard_candles import IBoardCandlesService
from app.domains.market_data.application.iboard_detail import IBoardDetailService
from app.domains.market_data.application.iboard_indices import IBoardIndicesService
from app.domains.market_data.application.iboard_pulse import IBoardPulseService
from app.domains.market_data.application.iboard_schemas import (
    IBoardCandleBar,
    IBoardIndexItem,
    IBoardMarketPulse,
    IBoardStockDetail,
    IBoardStockRow,
)
from app.domains.market_data.domain.iboard_policy import (
    build_order_book_levels,
    classify_price_status,
    make_stock_row,
    parse_eod_price_block,
    parse_live_price_block,
    safe_num,
)
from app.domains.market_data.infrastructure.external_indices import (
    DowJonesGateway,
    IBoardDataGateway,
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

    # Internal helpers preserved for backward compatibility
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


# ---------------------------------------------------------------------------
# Backward Compatibility Aliases for Domain Helpers and Gateways
# (Giữ vững tương thích ngược 100% với các test suite và module phụ thuộc)
# ---------------------------------------------------------------------------
_safe_num = safe_num
_price_status = classify_price_status
_build_order_book = build_order_book_levels
_live_price_block = parse_live_price_block
_eod_price_block = parse_eod_price_block
_make_stock_row = make_stock_row
_backfill_ohlcv_daily = IBoardDataGateway.backfill_ohlcv_daily
_fetch_batch_quotes = IBoardDataGateway.fetch_batch_quotes

__all__ = [
    "IBoardCandleBar",
    "IBoardIndexItem",
    "IBoardMarketPulse",
    "IBoardService",
    "IBoardStockDetail",
    "IBoardStockRow",
    "_backfill_ohlcv_daily",
    "_build_order_book",
    "_eod_price_block",
    "_fetch_batch_quotes",
    "_live_price_block",
    "_make_stock_row",
    "_price_status",
    "_safe_num",
]
