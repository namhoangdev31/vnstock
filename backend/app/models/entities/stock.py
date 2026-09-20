"""Mô hình dữ liệu thực thể chứng khoán và báo cáo tài chính (Database Tables)."""

import uuid
from datetime import date, datetime

from sqlalchemy import JSON, DateTime, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.models.base import get_datetime_utc


class StockSymbol(SQLModel, table=True):
    """Bảng lưu trữ thông tin tham chiếu mã chứng khoán (HOSE, HNX, UPCOM, Phái sinh)."""

    __tablename__ = "stock_symbol"

    symbol: str = Field(primary_key=True, max_length=20)
    organ_name: str | None = Field(default=None, max_length=255)
    exchange: str | None = Field(default=None, max_length=10)  # HOSE, HNX, UPCOM, DERIV
    industry: str | None = Field(default=None, max_length=100)
    asset_type: str = Field(max_length=20)  # stock, etf, derivative, index
    is_active: bool = True
    updated_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class StockOHLCVDaily(SQLModel, table=True):
    """Bảng lưu trữ nến lịch sử giao dịch hàng ngày (OHLCV Daily)."""

    __tablename__ = "stock_ohlcv_daily"
    __table_args__ = (UniqueConstraint("symbol", "trading_date"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    symbol: str = Field(max_length=20, foreign_key="stock_symbol.symbol", index=True)
    trading_date: date = Field(index=True)
    open: float
    high: float
    low: float
    close: float
    volume: int
    value: float | None = None  # Giá trị giao dịch (VND)
    source: str = Field(max_length=10)  # VCI, KBS


class StockOHLCVIntraday(SQLModel, table=True):
    """Bảng lưu trữ nến giao dịch trong ngày đa khung thời gian (1m, 5m, 15m)."""

    __tablename__ = "stock_ohlcv_intraday"
    __table_args__ = (UniqueConstraint("symbol", "timestamp", "interval"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    symbol: str = Field(max_length=20, foreign_key="stock_symbol.symbol", index=True)
    timestamp: datetime = Field(sa_type=DateTime(timezone=True), index=True)  # type: ignore
    interval: str = Field(max_length=5)  # 1m, 5m, 15m
    open: float
    high: float
    low: float
    close: float
    volume: int
    source: str = Field(max_length=10)


class CompanyProfile(SQLModel, table=True):
    """Bảng lưu trữ hồ sơ doanh nghiệp niêm yết."""

    __tablename__ = "company_profile"

    symbol: str = Field(
        primary_key=True, max_length=20, foreign_key="stock_symbol.symbol"
    )
    company_name: str | None = Field(default=None, max_length=500)
    short_name: str | None = Field(default=None, max_length=255)
    industry_name: str | None = Field(default=None, max_length=255)
    established_date: str | None = None
    listed_date: str | None = None
    charter_capital: float | None = None
    outstanding_shares: float | None = None
    market_cap: float | None = None
    website: str | None = Field(default=None, max_length=500)
    description: str | None = None
    updated_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class FinancialReport(SQLModel, table=True):
    """Bảng lưu trữ báo cáo tài chính của doanh nghiệp dạng cấu trúc linh hoạt JSONB."""

    __tablename__ = "financial_report"
    __table_args__ = (
        UniqueConstraint("symbol", "report_type", "period", "year", "quarter"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    symbol: str = Field(max_length=20, foreign_key="stock_symbol.symbol", index=True)
    report_type: str = Field(
        max_length=20
    )  # income_statement, balance_sheet, cash_flow
    period: str = Field(max_length=10)  # quarter, year
    year: int
    quarter: int | None = None  # 1-4 cho quý, None cho năm
    data: dict = Field(sa_type=JSON)  # Lưu trữ cấu trúc JSON báo cáo
    source: str = Field(max_length=10)
    updated_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class DataSyncLog(SQLModel, table=True):
    """Bảng nhật ký kiểm toán và theo dõi tiến trình đồng bộ dữ liệu thị trường."""

    __tablename__ = "data_sync_log"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    sync_type: str = Field(
        max_length=30
    )  # symbols, daily_ohlcv, intraday, profile, financials
    symbol: str | None = Field(default=None, max_length=20)
    source: str = Field(max_length=10)
    status: str = Field(max_length=15)  # started, success, failed, partial
    rows_synced: int = 0
    error_message: str | None = None
    started_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    completed_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
