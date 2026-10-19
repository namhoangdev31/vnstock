"""Schemas and DTOs for iBoard Trading Price Board (Bảng giá v2)."""

from __future__ import annotations

from sqlmodel import SQLModel

from app.domains.dnse.schemas import (
    DNSEIndexBreadth as IBoardIndexBreadth,
)
from app.domains.dnse.schemas import (
    MarketBreadthDetailResponse,
    MarketBreadthPoint,
    MarketBreadthSeriesResponse,
)


class IBoardIndexItem(SQLModel):
    id: str
    name: str
    price: str
    change: str
    change_percent: str
    is_positive: bool
    is_unchanged: bool = False
    volume: str
    value: str
    breadth: IBoardIndexBreadth | None = None
    sparkline: list[float | None] = []
    ref_price: float | None = None
    raw_volume: float | None = None
    raw_value: float | None = None


class OrderBookLevel(SQLModel):
    price: float
    volume: int


class IBoardStockRow(SQLModel):
    symbol: str
    name: str
    exchange: str
    last_price: float
    ref_price: float
    ceiling_price: float
    floor_price: float
    high_price: float
    low_price: float
    avg_price: float
    change: float
    change_percent: float
    volume: int
    value_billion: float
    buy_ratio: int
    sell_ratio: int
    foreign_buy: int
    foreign_sell: int
    foreign_room: int
    status: str
    sparkline: list[float]
    bid_book: list[OrderBookLevel]
    ask_book: list[OrderBookLevel]
    category: str
    sector: str | None = None
    expiry_date: str | None = None


class MatchedTickDTO(SQLModel):
    time: str
    price: float
    volume: int
    side: str


class CompanyOverviewDTO(SQLModel):
    market_cap_billion: float
    pe: float
    pb: float
    roe: float


class CorporateEventDTO(SQLModel):
    date: str
    title: str


class ShareholderDTO(SQLModel):
    name: str
    share_percent: float
    quantity: int | None = None


class IBoardCandleBar(SQLModel):
    time: str
    open: float
    high: float
    low: float
    close: float
    volume: int


class IBoardStockDetail(SQLModel):
    stock: IBoardStockRow
    matched_ticks: list[MatchedTickDTO]
    overview: CompanyOverviewDTO
    events: list[CorporateEventDTO]
    candles: list[IBoardCandleBar]
    company_profile: str | None = None
    shareholders: list[ShareholderDTO] = []
    performance_5d: float | None = None
    performance_1y: float | None = None
    active_buy_vol: int = 0
    active_sell_vol: int = 0
    total_bid_qtty: int = 0
    total_ask_qtty: int = 0


class TopMoverItem(SQLModel):
    symbol: str
    name: str
    price: str
    change: str
    change_percent: float = 0.0
    volume: str = ""


class IBoardMarketPulse(SQLModel):
    ai_insight: str
    top_gainers: list[TopMoverItem]
    top_losers: list[TopMoverItem]
    top_volume: list[TopMoverItem] = []
    sector_performance: dict[str, float] = {}


class IBoardNewsItem(SQLModel):
    symbol: str
    title: str
    published_at: str
    url: str | None = None
    source: str = "CafeF"


class PutThroughTradeDTO(SQLModel):
    time: str
    symbol: str
    price: float
    volume: int


class IBoardPutThroughSummary(SQLModel):
    exchange: str
    total_volume: int
    total_value_billion: float
    trades: list[PutThroughTradeDTO]
    is_today: bool = False


__all__ = [
    "CompanyOverviewDTO",
    "CorporateEventDTO",
    "IBoardCandleBar",
    "IBoardIndexBreadth",
    "IBoardIndexItem",
    "IBoardMarketPulse",
    "IBoardNewsItem",
    "IBoardStockDetail",
    "IBoardStockRow",
    "MarketBreadthDetailResponse",
    "MarketBreadthPoint",
    "MarketBreadthSeriesResponse",
    "MatchedTickDTO",
    "OrderBookLevel",
    "ShareholderDTO",
    "TopMoverItem",
]
