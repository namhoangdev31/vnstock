"""Application DTOs (Schemas) for Fundamental & Corporate Analysis and Screener."""

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel
from sqlmodel import SQLModel

from app.domains.fundamental.domain.models import ScreenerSnapshot

# ===========================================================================
# 1. SCREENER SCHEMAS
# ===========================================================================


class ScreenerCursor(BaseModel):
    """Thông tin con trỏ Keyset Pagination."""

    roe: float | None = None
    instrument_id: uuid.UUID | None = None


class ScreenerResponse(BaseModel):
    """Kết quả phân trang của Screener."""

    items: list[ScreenerSnapshot]
    total_count: int
    has_next: bool
    next_cursor: ScreenerCursor | None = None


class ScreenerResultItem(SQLModel):
    """Bản ghi kết quả lọc cổ phiếu theo chỉ số tài chính & tăng trưởng."""

    symbol: str
    organ_name: str | None = None
    exchange: str | None = None
    industry: str | None = None
    fiscal_year: int
    fiscal_quarter: int | None = None
    pe: float | None = None
    pb: float | None = None
    roe: float | None = None
    roa: float | None = None
    debt_to_equity: float | None = None
    ev_to_ebitda: float | None = None
    net_profit_margin: float | None = None
    revenue_growth_yoy: float | None = None
    net_profit_growth_yoy: float | None = None
    market_cap: float | None = None


class StockScreenerResponse(SQLModel):
    """Phản hồi kết quả bộ lọc cổ phiếu định lượng."""

    count: int
    data: list[ScreenerResultItem]
    has_next: bool | None = None
    next_cursor_roe: float | None = None
    next_cursor_instrument_id: uuid.UUID | None = None


# ===========================================================================
# 2. CORPORATE OVERVIEW SCHEMAS
# ===========================================================================


class CompanyOverviewPublic(SQLModel):
    """Thông tin tổng quan hồ sơ doanh nghiệp."""

    id: uuid.UUID | None = None
    symbol: str
    company_name: str | None = None
    short_name: str | None = None
    industry_name: str | None = None
    established_date: str | None = None
    listed_date: str | None = None
    charter_capital: float | None = None
    outstanding_shares: float | None = None
    market_cap: float | None = None
    free_float_pct: float | None = None
    foreign_ownership_pct: float | None = None
    max_foreign_ownership_pct: float | None = None
    employee_count: int | None = None
    website: str | None = None
    address: str | None = None
    ceo_name: str | None = None
    auditor: str | None = None
    description: str | None = None


# ===========================================================================
# 3. FINANCIAL STATEMENTS & RATIOS SCHEMAS
# ===========================================================================


class FinancialReportPublic(SQLModel):
    """Bản ghi báo cáo tài chính trả về cho API."""

    report_type: str
    report_scope: str = "consolidated"
    period: str
    year: int
    quarter: int | None = None
    is_audited: bool = False

    # Các chỉ tiêu tài chính cốt lõi
    revenue: float | None = None
    gross_profit: float | None = None
    operating_profit: float | None = None
    net_profit_parent: float | None = None
    total_assets: float | None = None
    short_term_assets: float | None = None
    cash_and_equivalents: float | None = None
    total_liabilities: float | None = None
    short_term_debt: float | None = None
    long_term_debt: float | None = None
    owners_equity: float | None = None
    operating_cash_flow: float | None = None
    investing_cash_flow: float | None = None
    financing_cash_flow: float | None = None

    data: dict[str, Any] | None = None


class FinancialReportsResponse(SQLModel):
    """Danh sách các kỳ báo cáo tài chính của doanh nghiệp."""

    symbol: str
    count: int
    data: list[FinancialReportPublic]


class FinancialRatioPublic(SQLModel):
    """Chỉ số tài chính định lượng & định giá (P/E, P/B, ROE, ROA, EPS, BVPS...)."""

    id: uuid.UUID | None = None
    symbol: str
    period: str
    year: int
    quarter: int | None = None
    pe: float | None = None
    pb: float | None = None
    ps: float | None = None
    roe: float | None = None
    roa: float | None = None
    roic: float | None = None
    eps: float | None = None
    bvps: float | None = None
    gross_margin: float | None = None
    net_margin: float | None = None
    debt_to_equity: float | None = None
    quick_ratio: float | None = None
    current_ratio: float | None = None
    dividend_yield: float | None = None

    # Định giá & Dòng tiền bổ sung
    ev_to_ebitda: float | None = None
    ev_to_ebit: float | None = None
    p_to_fcf: float | None = None
    p_to_ocf: float | None = None
    fcf: float | None = None

    # Hiệu quả hoạt động & Lợi nhuận bổ sung
    ebit_margin: float | None = None
    ebitda_margin: float | None = None
    asset_turnover: float | None = None
    inventory_turnover: float | None = None
    receivables_turnover: float | None = None

    # Cơ cấu vốn & Khả năng thanh toán bổ sung
    debt_to_assets: float | None = None
    interest_coverage: float | None = None
    cash_ratio: float | None = None

    # Tăng trưởng (Growth)
    revenue_growth_yoy: float | None = None
    net_profit_growth_yoy: float | None = None
    revenue_growth_qoq: float | None = None
    net_profit_growth_qoq: float | None = None

    data: dict[str, Any] | None = None


class FinancialRatiosResponse(SQLModel):
    """Danh sách các chỉ số tài chính theo kỳ của một doanh nghiệp."""

    symbol: str
    count: int
    data: list[FinancialRatioPublic]


class FinancialReportRevisionPublic(SQLModel):
    """Bản ghi thông tin phiên bản / sửa đổi của Báo cáo tài chính."""

    id: uuid.UUID
    report_id: uuid.UUID
    revision_number: int
    payload_hash: str
    published_at: datetime | None = None
    is_provisional: bool = False
    restated_reason: str | None = None
    data: dict[str, Any] = {}
    created_at: datetime


class FinancialReportRevisionsResponse(SQLModel):
    """Danh sách lịch sử các phiên bản sửa đổi BCTC."""

    symbol: str
    report_id: uuid.UUID
    count: int
    revisions: list[FinancialReportRevisionPublic]


# ===========================================================================
# 4. CORPORATE GOVERNANCE SCHEMAS
# ===========================================================================


class CompanyShareholderPublic(SQLModel):
    """Thông tin cơ cấu cổ đông lớn / cổ đông nội bộ."""

    id: uuid.UUID | None = None
    symbol: str
    shareholder_name: str
    share_count: float = 0.0
    ownership_pct: float = 0.0
    is_institutional: bool = False
    is_foreign: bool = False
    is_state: bool = False


class CompanyShareholdersResponse(SQLModel):
    """Danh sách cổ đông của một doanh nghiệp."""

    symbol: str
    count: int
    data: list[CompanyShareholderPublic]


class CompanyOfficerPublic(SQLModel):
    """Thông tin thành viên ban lãnh đạo / Hội đồng quản trị."""

    id: uuid.UUID | None = None
    symbol: str
    officer_name: str
    position: str
    share_count: float | None = None
    ownership_pct: float | None = None


class CompanyOfficersResponse(SQLModel):
    """Danh sách thành viên ban điều hành & HĐQT của một doanh nghiệp."""

    symbol: str
    count: int
    data: list[CompanyOfficerPublic]


class CorporateEventPublic(SQLModel):
    """Sự kiện doanh nghiệp & lịch chi trả cổ tức."""

    id: uuid.UUID | None = None
    symbol: str
    event_type: str
    event_title: str
    ex_date: date | None = None
    record_date: date | None = None
    effective_date: date | None = None
    cash_rate: float | None = None
    stock_rate: float | None = None
    ratio_string: str | None = None
    notes: str | None = None


class CorporateEventsResponse(SQLModel):
    """Danh sách sự kiện doanh nghiệp & lịch cổ tức."""

    symbol: str
    count: int
    data: list[CorporateEventPublic]


class CompanySubsidiaryPublic(SQLModel):
    """Thông tin công ty con / công ty liên kết."""

    id: uuid.UUID | None = None
    symbol: str
    sub_organ_code: str
    organ_name: str
    ownership_percent: float = 0.0


class CompanySubsidiariesResponse(SQLModel):
    """Danh sách công ty con & liên kết của một doanh nghiệp."""

    symbol: str
    count: int
    data: list[CompanySubsidiaryPublic]


class InsiderTradingPublic(SQLModel):
    """Nhật ký giao dịch nội bộ của lãnh đạo và cổ đông lớn."""

    id: uuid.UUID | None = None
    symbol: str
    officer_name: str
    officer_position: str | None = None
    deal_action: str
    deal_quantity: float | None = None
    deal_price: float | None = None
    deal_ratio: float | None = None
    deal_announce_date: date | None = None


class InsiderTradingResponse(SQLModel):
    """Danh sách giao dịch nội bộ của doanh nghiệp."""

    symbol: str
    count: int
    data: list[InsiderTradingPublic]


class CapitalHistoryPublic(SQLModel):
    """Lịch sử tăng vốn điều lệ và phát hành cổ phiếu."""

    id: uuid.UUID | None = None
    symbol: str
    issue_date: date | None = None
    charter_capital: float | None = None
    shares_issued: float | None = None
    description: str | None = None


class CapitalHistoryResponse(SQLModel):
    """Danh sách các đợt tăng vốn điều lệ của doanh nghiệp."""

    symbol: str
    count: int
    data: list[CapitalHistoryPublic]
