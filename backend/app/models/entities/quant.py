"""Mô hình dữ liệu thực thể nghiên cứu định lượng & kịch bản dự phóng (Database Tables)."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import DateTime, Index, UniqueConstraint
from sqlmodel import Field

from app.models.base import AwareSQLModel, JSONBVariant, get_datetime_utc
from app.models.enums import (
    ForecastDirection,
    ForecastHorizon,
    ForecastStatus,
)


class ForecastJournal(AwareSQLModel, table=True):
    """Bảng sổ cái dự phóng bắt buộc (RULE 3): Lưu vết mọi tín hiệu và kết quả tự học."""

    __tablename__ = "forecast_journal"
    __table_args__ = (
        UniqueConstraint("symbol", "horizon", "predicted_at"),
        Index("ix_forecast_journal_status_pred", "status", "predicted_at"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    symbol: str = Field(max_length=20, index=True)
    horizon: str = Field(default=ForecastHorizon.T_PLUS_1, max_length=20)
    # Mốc thời gian neo dự phóng (đảm bảo cam kết không rò rỉ dữ liệu tương lai No-Look-Ahead)
    predicted_at: datetime = Field(
        sa_type=DateTime(timezone=True),  # type: ignore
        index=True,
    )
    predicted_value: float | None = None
    predicted_direction: str = Field(default=ForecastDirection.NEUTRAL, max_length=10)
    engine_weights: dict = Field(default_factory=dict, sa_type=JSONBVariant)  # type: ignore
    model_version: str = Field(max_length=40)
    parameter_snapshot: dict = Field(default_factory=dict, sa_type=JSONBVariant)  # type: ignore

    # Kết quả thực tế được ghi ngược lại khi phiên giao dịch kết thúc
    actual_value: float | None = None
    actual_direction: str | None = Field(default=None, max_length=10)
    realized_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    error: float | None = None
    score: float | None = None
    status: ForecastStatus = Field(default=ForecastStatus.PENDING, index=True)
    updated_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class MacroIndicator(AwareSQLModel, table=True):
    """Bảng lưu trữ các chỉ số vĩ mô: Giá vàng SJC/thế giới và tỷ giá USD/VND (Bối cảnh Động cơ 2)."""

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


class TickFlowAggregated(AwareSQLModel, table=True):
    """Bảng nén tick-by-tick thành nến 1 phút kèm volume delta (Động cơ 1: Khớp lệnh chủ động)."""

    __tablename__ = "tick_flow_aggregated"
    __table_args__ = (UniqueConstraint("symbol", "interval_start"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    symbol: str = Field(max_length=20, index=True)
    interval_start: datetime = Field(sa_type=DateTime(timezone=True), index=True)  # type: ignore
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    volume: int = 0
    aggressive_buy_volume: int = 0
    aggressive_sell_volume: int = 0
    volume_delta: int = 0
    trade_count: int = 0
    vwap: float | None = None
    source: str = Field(max_length=20)


class InstitutionalFlow(AwareSQLModel, table=True):
    """Bảng theo dõi dòng tiền tổ chức: Khối ngoại & Tự doanh (Động cơ 2: Thanh khoản)."""

    __tablename__ = "institutional_flow"
    __table_args__ = (
        UniqueConstraint("trading_date", "symbol", "source"),
        Index("ix_inst_flow_symbol_date", "symbol", "trading_date"),
        Index("ix_inst_flow_date_net_val", "trading_date", "foreign_net_value"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    trading_date: date = Field(index=True)
    symbol: str = Field(max_length=20, index=True)

    # Khối ngoại (Foreign Trading)
    foreign_buy_volume: int | None = None
    foreign_sell_volume: int | None = None
    foreign_net_volume: int | None = None
    foreign_buy_value: float | None = None
    foreign_sell_value: float | None = None
    foreign_net_value: float | None = None
    foreign_room_total: float | None = None
    foreign_room_current: float | None = None
    foreign_room_pct: float | None = None

    # Tự doanh (Proprietary Trading)
    prop_buy_volume: int | None = None
    prop_sell_volume: int | None = None
    prop_net_volume: int | None = None
    prop_buy_value: float | None = None
    prop_sell_value: float | None = None
    prop_net_value: float | None = None

    source: str = Field(max_length=20)


class MarketBreadth(AwareSQLModel, table=True):
    """Bảng đo lường độ rộng thị trường: Số mã tăng, giảm, trần, sàn theo sàn giao dịch."""

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


class SignalLog(AwareSQLModel, table=True):
    """Bảng lưu vết tín hiệu giao dịch định lượng sinh ra từ các chiến lược (Động cơ 1, 2, 3)."""

    __tablename__ = "signal_log"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    strategy_name: str = Field(
        max_length=50, index=True
    )  # vd: basis_arbitrage, atc_breakout, vwap_pullback
    symbol: str = Field(max_length=20, index=True)
    signal_type: str = Field(max_length=10)  # BUY, SELL, CLOSE, HOLD
    action_price: float  # Mức giá kích hoạt tín hiệu
    stop_loss: float | None = None  # Ngưỡng dừng lỗ kỹ thuật (Dynamic ATR)
    take_profit: float | None = None  # Ngưỡng chốt lời kỳ vọng
    timeframe: str = Field(
        default="1m", max_length=10
    )  # Khung thời gian: 1m, 5m, 15m, 1D
    strength: float = Field(default=1.0)  # Độ mạnh của tín hiệu (0.0 - 1.0)
    metadata_info: dict = Field(
        default_factory=dict,
        sa_type=JSONBVariant,  # type: ignore
    )  # Snapshot các chỉ báo (RSI, VWAP, Basis...)
    created_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
        index=True,
    )
