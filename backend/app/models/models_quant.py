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
