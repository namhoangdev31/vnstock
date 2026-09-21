"""Các đối tượng truyền tải dữ liệu (DTO) cho dữ liệu chứng khoán và báo cáo tài chính."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlmodel import SQLModel

# =============================================================================
# RESPONSE DTOs
# =============================================================================


class StockSymbolPublic(SQLModel):
    """Thông tin tham chiếu mã chứng khoán trả về cho API."""

    id: uuid.UUID | None = None
    symbol: str
    organ_name: str | None = None
    exchange: str | None = None
    industry: str | None = None
    icb_code: str | None = None
    icb_name: str | None = None
    index_group: str | None = None
    asset_type: str
    lot_size: int = 100
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
    open_interest: int | None = None
    basis: float | None = None


class PriceHistoryResponse(SQLModel):
    """Phản hồi lịch sử giá nến của một mã chứng khoán."""

    symbol: str
    interval: str
    count: int
    data: list[OHLCVRecord]


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

    data: dict | None = None


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


class CoveredWarrantPublic(SQLModel):
    """Đặc tả chứng quyền có bảo đảm (Covered Warrant) trả về cho API."""

    id: uuid.UUID
    symbol: str
    underlying_symbol: str
    issuer_name: str | None = None
    warrant_type: str = "call"
    exercise_price: float | None = None
    conversion_ratio: str | None = None
    exercise_ratio: float | None = None
    issue_date: date | None = None
    maturity_date: date | None = None
    last_trading_date: date | None = None
    settlement_type: str | None = None
    is_active: bool = True


class BondSpecificationPublic(SQLModel):
    """Đặc tả trái phiếu doanh nghiệp & trái phiếu chính phủ trả về cho API."""

    id: uuid.UUID
    symbol: str
    bond_type: str  # corporate / government
    issuer_symbol: str | None = None
    issuer_name: str | None = None
    par_value: float = 100_000.0
    coupon_rate: float | None = None
    coupon_type: str | None = None
    tenor_years: float | None = None
    issue_date: date | None = None
    maturity_date: date | None = None
    is_active: bool = True


class DerivativeContractPublic(SQLModel):
    """Đặc tả hợp đồng tương lai phái sinh trả về cho API."""

    id: uuid.UUID
    symbol: str
    underlying_symbol: str
    multiplier: float = 100_000.0
    first_trading_date: date | None = None
    last_trading_date: date | None = None
    expiration_date: date
    settlement_price: float | None = None
    is_active: bool = True


class RelatedAssetsResponse(SQLModel):
    """Mạng lưới tài sản liên kết đa tầng của một mã chứng khoán bất kỳ."""

    symbol: str
    asset_type: str
    organ_name: str | None = None
    exchange: str | None = None
    profile: CompanyOverviewPublic | None = None
    covered_warrants: list[CoveredWarrantPublic] = []
    issued_bonds: list[BondSpecificationPublic] = []
    derivative_contracts: list[DerivativeContractPublic] = []
    underlying_asset: StockSymbolPublic | None = None
    issuer_asset: StockSymbolPublic | None = None


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


class IndexConstituentPublic(SQLModel):
    """Thành phần và tỷ trọng rổ chỉ số (VN30, VN100, VNFINLEAD)."""

    id: uuid.UUID | None = None
    index_code: str
    symbol: str
    weight: float = 0.0
    free_float_shares: float | None = None
    effective_date: date


class IndexConstituentsResponse(SQLModel):
    """Danh sách thành phần rổ chỉ số."""

    index_code: str
    count: int
    data: list[IndexConstituentPublic]


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
