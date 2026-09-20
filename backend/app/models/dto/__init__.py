"""Tập hợp toàn bộ các đối tượng truyền tải dữ liệu (DTOs / Pydantic Request & Response Schemas).

Được sử dụng bởi các tầng API Routes, Controllers và Services Serialization.
"""

from app.models.dto.common import (
    Message,
    NewPassword,
    Token,
    TokenPayload,
)
from app.models.dto.quant import (
    EnsembleSignalRequest,
    EnsembleSignalResponse,
    EnsembleWeightsResponse,
    EnsembleWeightsUpdate,
    FlowLiquidityEngineResponse,
    ForecastAggregateResponse,
    ForecastCreate,
    ForecastJournalPublic,
    ForecastResolve,
    ForecastScoredPublic,
    InstitutionalFlowPublic,
    MacroIndicatorPublic,
    MacroLatestResponse,
    QuantMLEngineResponse,
    SymbolGroupResponse,
    TechnicalEngineResponse,
)
from app.models.dto.simulation import (
    MarkToMarketRequest,
    OrderCreateRequest,
    OrderResponse,
    PortfolioCreateRequest,
    PortfolioResponse,
    PortfoliosResponse,
    PositionCloseRequest,
    PositionResponse,
    TradeResponse,
)
from app.models.dto.stock import (
    CompanyOverviewPublic,
    FinancialReportPublic,
    FinancialReportsResponse,
    OHLCVRecord,
    PriceHistoryResponse,
    StockSymbolPublic,
    StockSymbolsPublic,
    SyncStatusPublic,
)
from app.models.dto.user import (
    ItemCreate,
    ItemPublic,
    ItemsPublic,
    ItemUpdate,
    UpdatePassword,
    UserCreate,
    UserPublic,
    UserRegister,
    UsersPublic,
    UserUpdate,
    UserUpdateMe,
)
from app.models.dto.vnstock import (
    VnstockSymbolItem,
)

__all__ = [
    # common
    "Message",
    "NewPassword",
    "Token",
    "TokenPayload",
    # user
    "ItemCreate",
    "ItemPublic",
    "ItemUpdate",
    "ItemsPublic",
    "UpdatePassword",
    "UserCreate",
    "UserPublic",
    "UserRegister",
    "UserUpdate",
    "UserUpdateMe",
    "UsersPublic",
    # stock
    "CompanyOverviewPublic",
    "FinancialReportPublic",
    "FinancialReportsResponse",
    "OHLCVRecord",
    "PriceHistoryResponse",
    "StockSymbolPublic",
    "StockSymbolsPublic",
    "SyncStatusPublic",
    # quant
    "EnsembleSignalRequest",
    "EnsembleSignalResponse",
    "EnsembleWeightsResponse",
    "EnsembleWeightsUpdate",
    "FlowLiquidityEngineResponse",
    "ForecastAggregateResponse",
    "ForecastCreate",
    "ForecastJournalPublic",
    "ForecastResolve",
    "ForecastScoredPublic",
    "InstitutionalFlowPublic",
    "MacroIndicatorPublic",
    "MacroLatestResponse",
    "QuantMLEngineResponse",
    "SymbolGroupResponse",
    "TechnicalEngineResponse",
    # simulation / trading
    "MarkToMarketRequest",
    "OrderCreateRequest",
    "OrderResponse",
    "PortfolioCreateRequest",
    "PortfolioResponse",
    "PortfoliosResponse",
    "PositionCloseRequest",
    "PositionResponse",
    "TradeResponse",
    # vnstock
    "VnstockSymbolItem",
]
