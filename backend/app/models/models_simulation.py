"""Isolated paper-trading / simulation models — Phase 1.

RULE 1 & RULE 2 (AGENTS.md §5): these tables model a *simulation only*. They
carry NO brokerage credentials, API keys, passwords, PINs, OTP tokens, or
session secrets of any kind, and there is no code path that executes a real
order. Internal fields use clean domain terminology (``balance``, ``price``,
``volume``, ``pnl``, ``status``) — no redundant ``simulated_`` / ``virtual_``
prefixes — while the *table and class names* make the simulation context
explicit (``simulation_*``).
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import DateTime, UniqueConstraint
from sqlmodel import Field, Relationship

from app.models.enums import (
    DEFAULT_INITIAL_BALANCE,
    DERIVATIVE_MULTIPLIER,
    OrderSide,
    OrderStatus,
    OrderType,
    PositionSide,
    PositionStatus,
)
from app.models.models_base import AwareSQLModel, get_datetime_utc

# ---------------------------------------------------------------------------
# simulation_portfolio — Isolated paper-trading account
# ---------------------------------------------------------------------------


class SimulationPortfolio(AwareSQLModel, table=True):
    __tablename__ = "simulation_portfolio"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, index=True, ondelete="CASCADE"
    )
    name: str = Field(max_length=255)
    initial_balance: float = DEFAULT_INITIAL_BALANCE
    cash_balance: float = DEFAULT_INITIAL_BALANCE
    equity: float = DEFAULT_INITIAL_BALANCE
    margin_used: float = 0.0
    created_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    updated_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )

    orders: list["SimulationOrder"] = Relationship(  # noqa: UP037
        back_populates="portfolio", cascade_delete=True
    )
    positions: list["SimulationPosition"] = Relationship(  # noqa: UP037
        back_populates="portfolio", cascade_delete=True
    )
    trades: list["SimulationTrade"] = Relationship(  # noqa: UP037
        back_populates="portfolio", cascade_delete=True
    )


# ---------------------------------------------------------------------------
# simulation_order — Paper order
# ---------------------------------------------------------------------------


class SimulationOrder(AwareSQLModel, table=True):
    __tablename__ = "simulation_order"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    portfolio_id: uuid.UUID = Field(
        foreign_key="simulation_portfolio.id",
        nullable=False,
        index=True,
        ondelete="CASCADE",
    )
    symbol: str = Field(max_length=20, index=True)
    side: str = Field(default=OrderSide.BUY, max_length=10)
    order_type: str = Field(default=OrderType.MARKET, max_length=10)
    price: float
    stop_price: float | None = None
    quantity: int
    filled_quantity: int = 0
    filled_price: float | None = None
    fee: float = 0.0
    tax: float = 0.0
    status: str = Field(default=OrderStatus.PENDING, max_length=10, index=True)
    reject_reason: str | None = Field(default=None, max_length=255)
    created_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    updated_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )

    portfolio: SimulationPortfolio | None = Relationship(back_populates="orders")


# ---------------------------------------------------------------------------
# simulation_position — Open/closed paper position
# ---------------------------------------------------------------------------


class SimulationPosition(AwareSQLModel, table=True):
    __tablename__ = "simulation_position"
    __table_args__ = (
        UniqueConstraint("portfolio_id", "symbol", "side", name="uq_position_symbol"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    portfolio_id: uuid.UUID = Field(
        foreign_key="simulation_portfolio.id",
        nullable=False,
        index=True,
        ondelete="CASCADE",
    )
    symbol: str = Field(max_length=20, index=True)
    side: str = Field(default=PositionSide.LONG, max_length=10)
    quantity: int = 0
    entry_price: float = 0.0
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    margin_required: float = 0.0
    # T+2 for equities, T+0 for derivatives — tracks when shares become sellable.
    settlement_date: date | None = None
    status: str = Field(default=PositionStatus.OPEN, max_length=10, index=True)
    created_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    updated_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )

    portfolio: SimulationPortfolio | None = Relationship(back_populates="positions")


# ---------------------------------------------------------------------------
# simulation_trade — Executed (filled) paper trade ledger entry
# ---------------------------------------------------------------------------


class SimulationTrade(AwareSQLModel, table=True):
    __tablename__ = "simulation_trade"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    portfolio_id: uuid.UUID = Field(
        foreign_key="simulation_portfolio.id",
        nullable=False,
        index=True,
        ondelete="CASCADE",
    )
    order_id: uuid.UUID | None = Field(
        default=None, foreign_key="simulation_order.id", index=True
    )
    symbol: str = Field(max_length=20, index=True)
    side: str = Field(max_length=10)
    quantity: int
    price: float
    fee: float = 0.0
    tax: float = 0.0
    realized_pnl: float = 0.0
    executed_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )

    portfolio: SimulationPortfolio | None = Relationship(back_populates="trades")


# ---------------------------------------------------------------------------
# Pure PnL helpers (no DB, no network — fully unit-testable, RULE 3 compliant)
# ---------------------------------------------------------------------------


def derivative_pnl(
    entry_price: float,
    exit_price: float,
    quantity: int,
    side: str = PositionSide.LONG,
    multiplier: int = DERIVATIVE_MULTIPLIER,
) -> float:
    """Gross PnL for an index-futures position.

    VN30F1M contract value = index_point * multiplier (100,000 VND/point).
    Gross PnL = (exit - entry) * quantity * multiplier, sign-flipped for SHORT.
    Fees/tax are applied separately by the caller.
    """
    gross = (exit_price - entry_price) * quantity * multiplier
    if str(side).upper() == PositionSide.SHORT:
        gross = -gross
    return float(gross)


def round_money(value: float) -> float:
    """Round a monetary amount to the nearest VND (no fractional dong)."""
    return float(Decimal(str(value)).quantize(Decimal("1")))
