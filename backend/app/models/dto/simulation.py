"""Các đối tượng truyền tải dữ liệu (DTO) cho giao dịch và quản lý danh mục.

Phân định rõ ràng:
- REQUEST DTOs: dữ liệu client gửi lên
- RESPONSE DTOs: dữ liệu API phản hồi
"""

import uuid
from datetime import date, datetime

from sqlmodel import Field, SQLModel

from app.models.enums import DEFAULT_INITIAL_BALANCE, OrderType

# ==============================================================================
# REQUEST DTOs
# ==============================================================================


class PortfolioCreateRequest(SQLModel):
    """Payload tạo mới một danh mục giao dịch."""

    name: str = Field(max_length=255)
    initial_balance: float = DEFAULT_INITIAL_BALANCE


class OrderCreateRequest(SQLModel):
    """Payload đặt lệnh giao dịch mới."""

    symbol: str = Field(max_length=20)
    side: str = Field(max_length=10)
    quantity: int = Field(gt=0)
    price: float = Field(gt=0)
    order_type: str = Field(default=OrderType.MARKET, max_length=10)
    stop_price: float | None = None


class PositionCloseRequest(SQLModel):
    """Payload yêu cầu đóng vị thế theo khối lượng và giá xác định."""

    quantity: int = Field(gt=0)
    price: float = Field(gt=0)


class MarkToMarketRequest(SQLModel):
    """Payload định giá lại danh mục theo giá thị trường (Mark-to-Market)."""

    prices: dict[str, float] = Field(default_factory=dict)


# ==============================================================================
# RESPONSE DTOs
# ==============================================================================


class PortfolioResponse(SQLModel):
    """Thông tin số dư và trạng thái danh mục đầu tư."""

    id: uuid.UUID
    name: str
    initial_balance: float
    cash_balance: float
    equity: float
    margin_used: float
    created_at: datetime
    updated_at: datetime


class PortfoliosResponse(SQLModel):
    """Danh sách các danh mục kèm số lượng."""

    data: list[PortfolioResponse]
    count: int


class OrderResponse(SQLModel):
    """Chi tiết lệnh giao dịch trả về cho API."""

    id: uuid.UUID
    symbol: str
    side: str
    order_type: str
    price: float
    stop_price: float | None = None
    quantity: int
    filled_quantity: int
    filled_price: float | None = None
    fee: float
    tax: float
    status: str
    reject_reason: str | None = None
    created_at: datetime
    updated_at: datetime


class PositionResponse(SQLModel):
    """Chi tiết vị thế đang nắm giữ trong danh mục."""

    id: uuid.UUID
    symbol: str
    side: str
    quantity: int
    entry_price: float
    current_price: float
    unrealized_pnl: float
    realized_pnl: float
    margin_required: float
    settlement_date: date | None = None
    status: str


class TradeResponse(SQLModel):
    """Chi tiết lượt khớp lệnh giao dịch."""

    id: uuid.UUID
    symbol: str
    side: str
    quantity: int
    price: float
    fee: float
    tax: float
    realized_pnl: float
    executed_at: datetime
