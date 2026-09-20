"""Các đối tượng truyền tải dữ liệu (DTO) cho dữ liệu chứng khoán và báo cáo tài chính."""

from datetime import datetime

from sqlmodel import SQLModel

# =============================================================================
# RESPONSE DTOs
# =============================================================================


class StockSymbolPublic(SQLModel):
    """Thông tin tham chiếu mã chứng khoán trả về cho API."""

    symbol: str
    organ_name: str | None = None
    exchange: str | None = None
    asset_type: str
    is_active: bool


class StockSymbolsPublic(SQLModel):
    """Danh sách các mã chứng khoán kèm số lượng."""

    data: list[StockSymbolPublic]
    count: int


class OHLCVRecord(SQLModel):
    """Bản ghi nến giá đơn lẻ trong chuỗi thời gian."""

    trading_date: str  # Định dạng ngày ISO YYYY-MM-DD
    open: float
    high: float
    low: float
    close: float
    volume: int
    value: float | None = None


class PriceHistoryResponse(SQLModel):
    """Phản hồi lịch sử giá nến của một mã chứng khoán."""

    symbol: str
    interval: str
    count: int
    data: list[OHLCVRecord]


class CompanyOverviewPublic(SQLModel):
    """Thông tin tổng quan hồ sơ doanh nghiệp."""

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
    """Bản ghi báo cáo tài chính trả về cho API."""

    report_type: str
    period: str
    year: int
    quarter: int | None = None
    data: dict


class FinancialReportsResponse(SQLModel):
    """Danh sách các kỳ báo cáo tài chính của doanh nghiệp."""

    symbol: str
    count: int
    data: list[FinancialReportPublic]


class SyncStatusPublic(SQLModel):
    """Trạng thái đồng bộ dữ liệu thị trường."""

    sync_type: str
    symbol: str | None = None
    source: str
    status: str
    rows_synced: int
    error_message: str | None = None
    started_at: datetime
    completed_at: datetime | None = None
