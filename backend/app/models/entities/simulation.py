"""Mô hình dữ liệu thực thể giao dịch mô phỏng Paper Trading (Database Tables).

TUÂN THỦ NGHIÊM NGẶT RULE 1 & RULE 2 (AGENTS.md §5):
- Toàn bộ dữ liệu nằm trong schema simulation/paper_trading, hoàn toàn cách ly với vốn thật.
- Không lưu trữ mật khẩu, OTP, mã PIN hay token tài khoản chứng khoán thật.
- Tên trường chuẩn hóa sạch sẽ (balance, price, volume, pnl, status).
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import DateTime, UniqueConstraint
from sqlmodel import Field, Relationship

from app.models.base import AwareSQLModel, get_datetime_utc
from app.models.enums import (
    DEFAULT_INITIAL_BALANCE,
    DERIVATIVE_MULTIPLIER,
    OrderSide,
    OrderStatus,
    OrderType,
    PositionSide,
    PositionStatus,
)


class Portfolio(AwareSQLModel, table=True):
    """Bảng lưu trữ danh mục đầu tư mô phỏng của người dùng."""

    __tablename__ = "simulation_portfolio"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", index=True)
    name: str = Field(default="Default Portfolio", max_length=100)
    initial_balance: float = Field(default=DEFAULT_INITIAL_BALANCE)
    cash_balance: float = Field(default=DEFAULT_INITIAL_BALANCE)
    margin_used: float = Field(default=0.0)
    equity: float = Field(default=DEFAULT_INITIAL_BALANCE)
    created_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    updated_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )

    orders: list["Order"] = Relationship(
        back_populates="portfolio", cascade_delete=True
    )
    positions: list["Position"] = Relationship(
        back_populates="portfolio", cascade_delete=True
    )
    trades: list["Trade"] = Relationship(
        back_populates="portfolio", cascade_delete=True
    )


class Order(AwareSQLModel, table=True):
    """Bảng lưu trữ lệnh đặt mô phỏng (Paper Order)."""

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

    portfolio: Portfolio | None = Relationship(back_populates="orders")


class Position(AwareSQLModel, table=True):
    """Bảng trạng thái vị thế mở/đóng trong tài khoản mô phỏng (Paper Position)."""

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
    # Chu kỳ thanh toán: T+2 cho cổ phiếu cơ sở, T+0 cho phái sinh VN30F1M
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

    portfolio: Portfolio | None = Relationship(back_populates="positions")


class Trade(AwareSQLModel, table=True):
    """Bảng sổ cái khớp lệnh giao dịch mô phỏng (Paper Trade Execution Ledger)."""

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

    portfolio: Portfolio | None = Relationship(back_populates="trades")


def derivative_pnl(
    entry_price: float,
    exit_price: float,
    quantity: int,
    side: str = PositionSide.LONG,
    multiplier: int = DERIVATIVE_MULTIPLIER,
) -> float:
    """Tính toán lợi nhuận/thua lỗ gộp cho vị thế phái sinh hợp đồng tương lai chỉ số VN30F1M.

    Giá trị 1 điểm phái sinh = 100,000 VND (hệ số nhân 100,000).
    Lãi/lỗ gộp = (Giá đóng - Giá mở) * Khối lượng * Hệ số nhân (đảo dấu với vị thế SHORT).
    """
    gross = (exit_price - entry_price) * quantity * multiplier
    if str(side).upper() == PositionSide.SHORT:
        gross = -gross
    return float(gross)


def round_money(value: float) -> float:
    """Làm tròn số tiền đến đơn vị đồng (VND) gần nhất, không có số thập phân lẻ."""
    return float(Decimal(str(value)).quantize(Decimal("1")))
