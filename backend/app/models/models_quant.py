"""Quantitative analytics models — Phase 1.

Tables: forecast_journal, macro_indicator, tick_flow_aggregated,
institutional_flow, market_breadth.

All timestamps are UTC-aware (enforced by ``AwareSQLModel``). Monetary and
metric columns use ``float`` for consistency with the existing stock models.
``ForecastJournal`` is the mandatory audit ledger required by RULE 3: every
forecast is persisted at prediction time with its engine weights and model
version, then back-filled with the realized outcome and score.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import DateTime, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.models.enums import (
    ForecastDirection,
    ForecastHorizon,
    ForecastStatus,
)
from app.models.models_base import (
    AwareSQLModel,
    JSONBVariant,
    get_datetime_utc,
)

# ---------------------------------------------------------------------------
# forecast_journal — Audit & self-learning substrate (RULE 3, AGENTS §9.1)
# ---------------------------------------------------------------------------


class ForecastJournal(AwareSQLModel, table=True):
    __tablename__ = "forecast_journal"
    __table_args__ = (UniqueConstraint("symbol", "horizon", "predicted_at"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    symbol: str = Field(max_length=20, index=True)
    horizon: str = Field(default=ForecastHorizon.T_PLUS_1, max_length=20)
    # Anchor of the no-look-ahead guarantee: set once, never mutated on resolve.
    predicted_at: datetime = Field(
        sa_type=DateTime(timezone=True),  # type: ignore
        index=True,
    )
    predicted_value: float | None = None
    predicted_direction: str = Field(default=ForecastDirection.NEUTRAL, max_length=10)
    engine_weights: dict = Field(default_factory=dict, sa_type=JSONBVariant)  # type: ignore
    model_version: str = Field(max_length=40)
    parameter_snapshot: dict = Field(default_factory=dict, sa_type=JSONBVariant)  # type: ignore

    # Back-filled once reality resolves.
    actual_value: float | None = None
    actual_direction: str | None = Field(default=None, max_length=10)
    realized_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    error: float | None = None
    score: float | None = None
    status: str = Field(default=ForecastStatus.PENDING, max_length=10, index=True)

    created_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    updated_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


# ---------------------------------------------------------------------------
# macro_indicator — Gold (SJC/world) & USD/VND (Engine 2 context)
# ---------------------------------------------------------------------------


class MacroIndicator(AwareSQLModel, table=True):
    __tablename__ = "macro_indicator"
    __table_args__ = (UniqueConstraint("indicator_code", "recorded_date", "source"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    recorded_date: date = Field(index=True)
    indicator_code: str = Field(max_length=30, index=True)
    value: float
    change_pct: float | None = None
    source: str = Field(max_length=20)
    created_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


# ---------------------------------------------------------------------------
# tick_flow_aggregated — 1-minute order-flow delta (Engine 1)
# ---------------------------------------------------------------------------


class TickFlowAggregated(AwareSQLModel, table=True):
    __tablename__ = "tick_flow_aggregated"
    __table_args__ = (UniqueConstraint("symbol", "timestamp"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    symbol: str = Field(max_length=20, index=True)
    timestamp: datetime = Field(
        sa_type=DateTime(timezone=True),  # type: ignore
        index=True,
    )
    aggressive_buy_volume: int = 0
    aggressive_sell_volume: int = 0
    volume_delta: int = 0
    trade_count: int = 0
    vwap: float | None = None
    source: str = Field(max_length=20)


# ---------------------------------------------------------------------------
# institutional_flow — Foreign & proprietary desk flow (schema only, Phase 1)
# ---------------------------------------------------------------------------
# NOTE: vnstock v4 exposes no proprietary-desk (tự doanh) buy/sell values and no
# foreign buy/sell *values* (only live snapshot volumes on KBS). This table is
# created now so a verified data source can populate it later. No sync path is
# wired in Phase 1 — fabricating values would violate RULE 3.


class InstitutionalFlow(AwareSQLModel, table=True):
    __tablename__ = "institutional_flow"
    __table_args__ = (UniqueConstraint("trading_date", "symbol", "source"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    trading_date: date = Field(index=True)
    # Either a specific symbol or an aggregate bucket like "HOSE" / "VN30".
    symbol: str = Field(max_length=20, index=True)
    foreign_buy_value: float | None = None
    foreign_sell_value: float | None = None
    foreign_net_value: float | None = None
    prop_buy_value: float | None = None
    prop_sell_value: float | None = None
    prop_net_value: float | None = None
    source: str = Field(max_length=20)


# ---------------------------------------------------------------------------
# market_breadth — Advance/decline & limit counts per exchange (schema only)
# ---------------------------------------------------------------------------
# NOTE: vnstock v4 has no market-breadth endpoint. Created now for a future
# verified source; no sync in Phase 1 (RULE 3 — no fabricated counts).


class MarketBreadth(AwareSQLModel, table=True):
    __tablename__ = "market_breadth"
    __table_args__ = (UniqueConstraint("trading_date", "exchange"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    trading_date: date = Field(index=True)
    exchange: str = Field(max_length=10)
    advancers: int = 0
    decliners: int = 0
    unchanged: int = 0
    ceiling_count: int = 0
    floor_count: int = 0
    total_volume: int = 0
    total_value: float = 0.0


# ---------------------------------------------------------------------------
# Response / Request models (non-table, for API use)
# ---------------------------------------------------------------------------


class MacroIndicatorPublic(SQLModel):
    indicator_code: str
    recorded_date: date
    value: float
    change_pct: float | None = None
    source: str


class MacroLatestResponse(SQLModel):
    """Latest macro snapshot keyed by indicator code."""

    as_of: date
    data: list[MacroIndicatorPublic]


class SymbolGroupResponse(SQLModel):
    group: str
    count: int
    symbols: list[str]


class ForecastJournalPublic(SQLModel):
    id: uuid.UUID
    symbol: str
    horizon: str
    predicted_at: datetime
    predicted_value: float | None = None
    predicted_direction: str
    engine_weights: dict
    model_version: str
    parameter_snapshot: dict
    actual_value: float | None = None
    actual_direction: str | None = None
    realized_at: datetime | None = None
    error: float | None = None
    score: float | None = None
    status: str


class ForecastCreate(SQLModel):
    """Payload to record a new forecast (engine-emitted)."""

    symbol: str = Field(max_length=20)
    horizon: str = Field(default=ForecastHorizon.T_PLUS_1, max_length=20)
    predicted_at: datetime
    predicted_value: float | None = None
    predicted_direction: str = Field(default=ForecastDirection.NEUTRAL, max_length=10)
    engine_weights: dict = Field(default_factory=dict)
    model_version: str = Field(max_length=40)
    parameter_snapshot: dict = Field(default_factory=dict)


class ForecastResolve(SQLModel):
    actual_value: float
    actual_direction: str = Field(max_length=10)
    realized_at: datetime | None = None


class ForecastScoredPublic(SQLModel):
    id: uuid.UUID
    error: float | None = None
    score: float | None = None
    status: str


class ForecastAggregateResponse(SQLModel):
    count: int
    mae: float | None = None
    directional_accuracy: float | None = None
    scored_with_error: int


class InstitutionalFlowPublic(SQLModel):
    trading_date: date
    symbol: str
    foreign_buy_value: float | None = None
    foreign_sell_value: float | None = None
    foreign_net_value: float | None = None
    prop_buy_value: float | None = None
    prop_sell_value: float | None = None
    prop_net_value: float | None = None
    source: str


class TechnicalEngineResponse(SQLModel):
    """Response payload for Engine 1 (Technical & Price-Action Engine)."""

    symbol: str
    as_of: datetime
    score: float  # -1.0 to +1.0
    rsi: float | None = None
    macd: dict = Field(
        default_factory=dict
    )  # {"dif": float, "dea": float, "hist": float}
    vwap: float | None = None
    order_imbalance: float = 0.0  # -1.0 to +1.0
    volume_delta: int = 0
    camarilla_levels: dict = Field(
        default_factory=dict
    )  # {"r4": ..., "r3": ..., "s3": ..., "s4": ...}
    fvg_detected: bool = False
    fvg_details: dict = Field(default_factory=dict)
    liquidity_sweeps: dict = Field(default_factory=dict)


class FlowLiquidityEngineResponse(SQLModel):
    """Response payload for Engine 2 (Liquidity, Flow & T+2 Cashflow Engine)."""

    as_of: datetime
    score: float  # -1.0 to +1.0
    institutional_momentum: float = 0.0
    market_breadth: float = 0.0
    t2_pressure: float = 0.0  # 0.0 to 1.0
    macro_sentiment: float = 0.0


class QuantMLEngineResponse(SQLModel):
    """Response payload for Engine 3 (Quantitative ML & Statistical Engine)."""

    symbol: str
    as_of: datetime
    score: float  # -1.0 to +1.0
    basis_value: float = 0.0
    basis_zscore: float = 0.0
    historical_vol: float = 0.0
    parkinson_vol: float = 0.0
    session_phase: str = "CONTINUOUS"
    monte_carlo_targets: dict = Field(
        default_factory=dict
    )  # {"p05": ..., "p50": ..., "p95": ...}


class EnsembleSignalRequest(SQLModel):
    """Payload to request an ensemble prediction & trigger auto-ledger logging."""

    symbol: str = Field(default="VN30F1M", max_length=20)
    horizon: str = Field(default=ForecastHorizon.INTRADAY, max_length=20)
    custom_weights: dict | None = (
        None  # Optional override {"w1": float, "w2": float, "w3": float}
    )


class EnsembleSignalResponse(SQLModel):
    """Response payload for Ensemble Decision System & Audit Journal confirmation."""

    journal_id: uuid.UUID
    symbol: str
    horizon: str
    predicted_at: datetime
    predicted_direction: str  # "LONG", "SHORT", "NEUTRAL"
    ensemble_score: float  # -1.0 to +1.0
    confidence: float  # 0.0 to 1.0
    entry_price: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    engine_weights: dict  # {"w1": ..., "w2": ..., "w3": ...}
    engine_scores: dict  # {"engine1": ..., "engine2": ..., "engine3": ...}
    model_version: str = "v2.0.0"
    disclaimer: str = (
        "CẢNH BÁO RỦI RO (RULE 4): Tín hiệu mô phỏng định lượng mang tính chất tham khảo "
        "và nghiên cứu giáo dục, không phải là lời khuyên đầu tư tài chính hay khuyến nghị đặt lệnh."
    )


class EnsembleWeightsResponse(SQLModel):
    """Current dynamic time-of-day weights structure."""

    session_phase: str
    current_time_utc: datetime
    weights: dict  # {"w1": float, "w2": float, "w3": float}
    schedule: dict


class EnsembleWeightsUpdate(SQLModel):
    """Payload to update custom ensemble weights."""

    w1: float = Field(ge=0.0, le=1.0)
    w2: float = Field(ge=0.0, le=1.0)
    w3: float = Field(ge=0.0, le=1.0)
