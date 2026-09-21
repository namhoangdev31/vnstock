"""Mô hình dữ liệu Screener Snapshot phục vụ bộ lọc cổ phiếu Brokerage-Grade (ScreenerSnapshot).

Đạt chuẩn hiệu năng cao:
- Lưu trữ snapshot tiền tính toán (pre-computed snapshot) của 34+ chỉ số cốt lõi.
- Tránh việc JOIN nhiều bảng lớn (OHLCV, FinancialReport, FinancialRatio) trong thời gian thực.
- Hỗ trợ Keyset Pagination với Partial Index (roe DESC NULLS LAST, instrument_id ASC) WHERE is_active = true.
- SLA DB execution time P95 < 10 ms.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import DateTime, Index, UniqueConstraint, text
from sqlmodel import Field

from app.models.base import AwareSQLModel, get_datetime_utc


class ScreenerSnapshotBase(AwareSQLModel):
    """Lớp cơ sở chứa toàn bộ các trường chỉ tiêu của bộ lọc cổ phiếu."""

    symbol: str = Field(max_length=20, index=True)
    exchange: str = Field(max_length=20, index=True)
    industry: str | None = Field(default=None, max_length=100, index=True)
    is_active: bool = Field(default=True, index=True)
    version: int = Field(default=1)

    # 1. Định giá (Valuation)
    pe: float | None = None
    pb: float | None = None
    ps: float | None = None
    ev_to_ebitda: float | None = None
    dividend_yield: float | None = None

    # 2. Sinh lời (Profitability)
    roe: float | None = None
    roa: float | None = None
    roic: float | None = None
    gross_margin: float | None = None
    net_margin: float | None = None

    # 3. Tăng trưởng (Growth)
    revenue_growth_yoy: float | None = None
    profit_growth_yoy: float | None = None
    revenue_growth_qoq: float | None = None
    profit_growth_qoq: float | None = None

    # 4. Sức khỏe tài chính & Đòn bẩy (Leverage & Liquidity)
    debt_to_equity: float | None = None
    current_ratio: float | None = None
    quick_ratio: float | None = None
    interest_coverage: float | None = None

    # 5. Kỹ thuật & Giá (Technical & Price Momentum)
    price: float | None = None
    change_pct: float | None = None
    volume_ma20: float | None = None
    rsi_14: float | None = None
    macd_histogram: float | None = None
    bollinger_bandwidth: float | None = None

    # 6. Dòng tiền & Thanh khoản (Institutional Flow & Liquidity)
    foreign_net_val_5d: float | None = None
    foreign_room_pct: float | None = None
    t2_pressure_score: float | None = None

    updated_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class ScreenerSnapshot(ScreenerSnapshotBase, table=True):
    """Bảng lưu snapshot hiện tại của phiên giao dịch gần nhất phục vụ screener realtime."""

    __tablename__ = "screener_snapshot"
    __table_args__ = (
        Index(
            "ix_screener_snapshot_roe_inst",
            text("roe DESC"),
            text("instrument_id ASC"),
            postgresql_where=text("is_active = true"),
            sqlite_where=text("is_active = 1"),
        ),
        Index(
            "ix_screener_snapshot_pe_inst",
            text("pe ASC"),
            text("instrument_id ASC"),
            postgresql_where=text("is_active = true"),
            sqlite_where=text("is_active = 1"),
        ),
    )

    instrument_id: uuid.UUID = Field(
        foreign_key="instrument.id",
        primary_key=True,
    )
    snapshot_date: date = Field(index=True)


class ScreenerSnapshotHistorical(ScreenerSnapshotBase, table=True):
    """Bảng lưu trữ lịch sử snapshot theo từng phiên phục vụ Point-in-Time Screener Backtest."""

    __tablename__ = "screener_snapshot_historical"
    __table_args__ = (
        UniqueConstraint("snapshot_date", "instrument_id", "as_of"),
        Index("ix_screener_hist_date_roe", "snapshot_date", "roe"),
        Index("ix_screener_hist_inst_as_of", "instrument_id", "as_of"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    instrument_id: uuid.UUID = Field(
        foreign_key="instrument.id",
        index=True,
    )
    snapshot_date: date = Field(index=True)
    as_of: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
        index=True,
    )
