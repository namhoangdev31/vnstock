"""Stock data models for the Quant Trading system.

6 tables: stock_symbol, stock_ohlcv_daily, stock_ohlcv_intraday,
company_profile, financial_report, data_sync_log.
"""

import uuid
from datetime import UTC, date, datetime

from sqlalchemy import JSON, DateTime, UniqueConstraint
from sqlmodel import Field, SQLModel


def get_datetime_utc() -> datetime:
    return datetime.now(UTC)


# ---------------------------------------------------------------------------
# Table 1: stock_symbol — Metadata mã chứng khoán
# ---------------------------------------------------------------------------


class StockSymbol(SQLModel, table=True):
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


# ---------------------------------------------------------------------------
# Table 2: stock_ohlcv_daily — Nến ngày
# ---------------------------------------------------------------------------


class StockOHLCVDaily(SQLModel, table=True):
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
    source: str = Field(max_length=10)  # TCBS, VCI


# ---------------------------------------------------------------------------
# Table 3: stock_ohlcv_intraday — Nến phút (1m, 5m, 15m)
# ---------------------------------------------------------------------------


class StockOHLCVIntraday(SQLModel, table=True):
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


# ---------------------------------------------------------------------------
# Table 4: company_profile — Thông tin công ty
# ---------------------------------------------------------------------------


class CompanyProfile(SQLModel, table=True):
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


# ---------------------------------------------------------------------------
# Table 5: financial_report — Báo cáo tài chính (JSONB for flexible schema)
# ---------------------------------------------------------------------------


class FinancialReport(SQLModel, table=True):
    __tablename__ = "financial_report"
    __table_args__ = (
        UniqueConstraint("symbol", "report_type", "period", "year", "quarter"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    symbol: str = Field(max_length=20, foreign_key="stock_symbol.symbol", index=True)
    report_type: str = Field(
        max_length=20
    )  # income_statement, balance_sheet, cash_flow
    period: str = Field(max_length=10)  # quarterly, annual
    year: int
    quarter: int | None = None  # 1-4 for quarterly, None for annual
    data: dict = Field(sa_type=JSON)  # JSONB flexible schema
    source: str = Field(max_length=10)
    updated_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


# ---------------------------------------------------------------------------
# Table 6: data_sync_log — Audit trail cho data sync
# ---------------------------------------------------------------------------


class DataSyncLog(SQLModel, table=True):
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


# ---------------------------------------------------------------------------
# Response / Request models (non-table, for API use)
# ---------------------------------------------------------------------------


class StockSymbolPublic(SQLModel):
    symbol: str
    organ_name: str | None = None
    exchange: str | None = None
    asset_type: str
    is_active: bool


class StockSymbolsPublic(SQLModel):
    data: list[StockSymbolPublic]
    count: int


class OHLCVRecord(SQLModel):
    trading_date: str  # ISO date string for JSON
    open: float
    high: float
    low: float
    close: float
    volume: int
    value: float | None = None


class PriceHistoryResponse(SQLModel):
    symbol: str
    interval: str
    count: int
    data: list[OHLCVRecord]


class CompanyOverviewPublic(SQLModel):
    symbol: str
    company_name: str | None = None
    short_name: str | None = None
    industry_name: str | None = None
    established_date: str | None = None
    listed_date: str | None = None
    charter_capital: float | None = None
    outstanding_shares: float | None = None
    market_cap: float | None = None
    website: str | None = None
    description: str | None = None


class FinancialReportPublic(SQLModel):
    report_type: str
    period: str
    year: int
    quarter: int | None = None
    data: dict


class FinancialReportsResponse(SQLModel):
    symbol: str
    count: int
    data: list[FinancialReportPublic]


class SyncStatusPublic(SQLModel):
    sync_type: str
    symbol: str | None = None
    source: str
    status: str
    rows_synced: int
    error_message: str | None = None
    started_at: datetime
    completed_at: datetime | None = None
