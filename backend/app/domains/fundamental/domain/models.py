# ruff: noqa: UP045
"""Domain models for Fundamental & Corporate Analysis and Quantitative Screener.

Aggregates:
- ScreenerSnapshot & ScreenerSnapshotHistorical (Brokerage-Grade Keyset Screener)
- CompanyProfile (Corporate Profile & Metadata)
- FinancialReport, FinancialReportRevision, FinancialReportItem (Financial Statements & Audit Trail)
- FinancialRatio (Valuation, Profitability, Leverage, Growth Ratios)
- Corporate Governance: CorporateEvent, CompanyShareholder, CompanyOfficer, CompanySubsidiary, InsiderTrading, CapitalHistory
"""

import uuid
from datetime import date, datetime
from typing import Any, Optional

from sqlalchemy import DateTime, Index, UniqueConstraint, text
from sqlmodel import Field, Relationship

from app.core.models_base import AwareSQLModel, JSONBVariant, get_datetime_utc


class ScreenerSnapshotBase(AwareSQLModel):
    """Lớp cơ sở chứa toàn bộ các trường chỉ tiêu của bộ lọc cổ phiếu."""

    symbol: str = Field(max_length=20, index=True)
    exchange: str = Field(max_length=20, index=True)
    industry: str | None = Field(default=None, max_length=100, index=True)
    is_active: bool = Field(default=True, index=True)
    version: int = Field(default=1)

    pe: float | None = None
    pb: float | None = None
    ps: float | None = None
    ev_to_ebitda: float | None = None
    dividend_yield: float | None = None

    roe: float | None = None
    roa: float | None = None
    roic: float | None = None
    gross_margin: float | None = None
    net_margin: float | None = None

    revenue_growth_yoy: float | None = None
    profit_growth_yoy: float | None = None
    revenue_growth_qoq: float | None = None
    profit_growth_qoq: float | None = None

    debt_to_equity: float | None = None
    current_ratio: float | None = None
    quick_ratio: float | None = None
    interest_coverage: float | None = None

    price: float | None = None
    change_pct: float | None = None
    volume_ma20: float | None = None
    rsi_14: float | None = None
    macd_histogram: float | None = None
    bollinger_bandwidth: float | None = None

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


class CompanyProfile(AwareSQLModel, table=True):
    """Bảng lưu trữ hồ sơ doanh nghiệp niêm yết, cơ cấu vốn và tỷ lệ sở hữu."""

    __tablename__ = "company_profile"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        unique=True,
        index=True,
        nullable=False,
    )
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
    free_float_pct: float | None = None
    foreign_ownership_pct: float | None = None
    max_foreign_ownership_pct: float | None = (
        None
    )
    employee_count: int | None = None
    website: str | None = Field(default=None, max_length=500)
    address: str | None = Field(default=None, max_length=500)
    ceo_name: str | None = Field(default=None, max_length=255)
    auditor: str | None = Field(default=None, max_length=255)
    description: str | None = None
    updated_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class FinancialReport(AwareSQLModel, table=True):
    """Bảng cha lưu thông tin chung của kỳ báo cáo tài chính (CĐKT, KQKD, LCTT)."""

    __tablename__ = "financial_report"
    __table_args__ = (
        UniqueConstraint(
            "symbol", "report_type", "report_scope", "period", "year", "quarter"
        ),
        Index(
            "ix_financial_report_lookup",
            "symbol",
            "report_type",
            "report_scope",
            "year",
            "quarter",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    symbol: str = Field(max_length=20, foreign_key="stock_symbol.symbol", index=True)
    instrument_id: uuid.UUID | None = Field(
        default=None, foreign_key="instrument.id", index=True
    )
    report_type: str = Field(
        max_length=20
    )
    report_scope: str = Field(
        default="consolidated", max_length=20, index=True
    )
    period: str = Field(max_length=10)
    year: int
    quarter: int | None = None
    is_audited: bool = Field(default=False)

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

    data: dict[str, Any] = Field(
        default_factory=dict,
        sa_type=JSONBVariant,  # type: ignore
    )
    source: str = Field(max_length=10)
    updated_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )

    items: list["FinancialReportItem"] = Relationship(back_populates="report")
    revisions: list["FinancialReportRevision"] = Relationship(back_populates="report")


class FinancialReportRevision(AwareSQLModel, table=True):
    """Bảng lưu trữ lịch sử các bản sửa đổi/bổ sung của BCTC (Restatements & Revisions).

    Bảo vệ tính toàn vẹn kiểm toán (Rule 3) và loại trừ Look-ahead bias:
    - payload_hash: SHA256 canonical JSON để nhận diện sửa đổi nội dung tất định.
    - is_provisional: Đánh dấu dữ liệu tạm nếu chưa xác thực được ngày công bố chính thức.
    """

    __tablename__ = "financial_report_revision"
    __table_args__ = (
        UniqueConstraint("report_id", "revision_number"),
        Index(
            "ix_financial_report_rev_pub", "report_id", "published_at", "is_provisional"
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    report_id: uuid.UUID = Field(foreign_key="financial_report.id", index=True)
    revision_number: int = Field(
        default=1
    )
    payload_hash: str = Field(max_length=64, index=True)
    published_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore
        index=True,
    )
    is_provisional: bool = Field(default=False, index=True)
    restated_reason: str | None = Field(default=None, max_length=500)
    data: dict[str, Any] = Field(
        default_factory=dict,
        sa_type=JSONBVariant,  # type: ignore
    )
    created_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )

    report: Optional["FinancialReport"] = Relationship(back_populates="revisions")


class FinancialReportItem(AwareSQLModel, table=True):
    """Bảng con lưu từng dòng chỉ tiêu tài chính chi tiết dạng quan hệ chuẩn hóa (Relational Normalization)."""

    __tablename__ = "financial_report_item"
    __table_args__ = (UniqueConstraint("report_id", "item_code"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    report_id: uuid.UUID = Field(foreign_key="financial_report.id", index=True)
    item_code: str = Field(
        max_length=100, index=True
    )
    item_name: str = Field(max_length=255)
    value: float | None = None
    order_index: int = Field(default=0)

    report: Optional["FinancialReport"] = Relationship(back_populates="items")


class FinancialRatio(AwareSQLModel, table=True):
    """Bảng lưu trữ các chỉ số tài chính định giá & tăng trưởng (Finance.ratio() & Fundamental)."""

    __tablename__ = "financial_ratio"
    __table_args__ = (
        UniqueConstraint("symbol", "period", "year", "quarter"),
        Index("ix_financial_ratio_screener", "year", "quarter", "pe", "roe"),
        Index(
            "ix_financial_ratio_growth",
            "year",
            "quarter",
            "revenue_growth_yoy",
            "net_profit_growth_yoy",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    symbol: str = Field(max_length=20, foreign_key="stock_symbol.symbol", index=True)
    instrument_id: uuid.UUID | None = Field(
        default=None, foreign_key="instrument.id", index=True
    )
    period: str = Field(max_length=10)
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

    ev_to_ebitda: float | None = None
    ev_to_ebit: float | None = None
    p_to_fcf: float | None = None
    p_to_ocf: float | None = None
    fcf: float | None = None

    ebit_margin: float | None = None
    ebitda_margin: float | None = None
    asset_turnover: float | None = None
    inventory_turnover: float | None = None
    receivables_turnover: float | None = None

    debt_to_assets: float | None = None
    interest_coverage: float | None = None
    cash_ratio: float | None = None

    revenue_growth_yoy: float | None = None
    net_profit_growth_yoy: float | None = None
    revenue_growth_qoq: float | None = (
        None
    )
    net_profit_growth_qoq: float | None = (
        None
    )

    data: dict[str, Any] = Field(
        default_factory=dict,
        sa_type=JSONBVariant,  # type: ignore
    )
    source: str = Field(max_length=10)
    updated_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class CorporateEvent(AwareSQLModel, table=True):
    """Bảng lưu trữ sự kiện doanh nghiệp & lịch chi trả cổ tức (Listing.events() & Company.events())."""

    __tablename__ = "corporate_event"
    __table_args__ = (
        UniqueConstraint("symbol", "event_type", "ex_date"),
        Index("ix_corporate_event_sym_exdate", "symbol", "ex_date"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    symbol: str = Field(max_length=20, foreign_key="stock_symbol.symbol", index=True)
    event_type: str = Field(
        max_length=30
    )
    event_title: str = Field(max_length=500)
    ex_date: date | None = Field(
        default=None, index=True
    )
    record_date: date | None = None
    effective_date: date | None = None
    cash_rate: float | None = None
    stock_rate: float | None = (
        None
    )
    ratio_string: str | None = Field(
        default=None, max_length=50
    )
    notes: str | None = None
    details: dict[str, Any] = Field(
        default_factory=dict,
        sa_type=JSONBVariant,  # type: ignore
    )
    source: str = Field(max_length=10)
    created_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class CompanyShareholder(AwareSQLModel, table=True):
    """Bảng lưu trữ cơ cấu cổ đông lớn và cổ đông nội bộ (Company.shareholders())."""

    __tablename__ = "company_shareholder"
    __table_args__ = (UniqueConstraint("symbol", "shareholder_name"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    symbol: str = Field(max_length=20, foreign_key="stock_symbol.symbol", index=True)
    shareholder_name: str = Field(max_length=255)
    share_count: float = Field(default=0.0)
    ownership_pct: float = Field(default=0.0)
    is_institutional: bool = Field(default=False)
    is_foreign: bool = Field(default=False)
    is_state: bool = Field(default=False)
    updated_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class CompanyOfficer(AwareSQLModel, table=True):
    """Bảng lưu trữ danh sách ban lãnh đạo & hội đồng quản trị doanh nghiệp (Company.officers())."""

    __tablename__ = "company_officer"
    __table_args__ = (UniqueConstraint("symbol", "officer_name", "position"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    symbol: str = Field(max_length=20, foreign_key="stock_symbol.symbol", index=True)
    officer_name: str = Field(max_length=255)
    position: str = Field(
        max_length=255
    )
    share_count: float | None = None
    ownership_pct: float | None = None
    updated_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class CompanySubsidiary(AwareSQLModel, table=True):
    """Bảng lưu trữ danh sách công ty con và công ty liên kết (Company.subsidiaries())."""

    __tablename__ = "company_subsidiary"
    __table_args__ = (UniqueConstraint("symbol", "sub_organ_code"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    symbol: str = Field(max_length=20, foreign_key="stock_symbol.symbol", index=True)
    sub_organ_code: str = Field(
        max_length=50, index=True
    )
    organ_name: str = Field(max_length=500)
    ownership_percent: float = Field(default=0.0)
    updated_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class InsiderTrading(AwareSQLModel, table=True):
    """Bảng lưu trữ nhật ký giao dịch người nội bộ và người có liên quan (Company.insider_trading())."""

    __tablename__ = "insider_trading"
    __table_args__ = (
        UniqueConstraint("symbol", "officer_name", "deal_action", "deal_announce_date"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    symbol: str = Field(max_length=20, foreign_key="stock_symbol.symbol", index=True)
    officer_name: str = Field(
        max_length=255, index=True
    )
    officer_position: str | None = Field(default=None, max_length=255)
    deal_action: str = Field(max_length=50)
    deal_quantity: float | None = None
    deal_price: float | None = None
    deal_ratio: float | None = None
    deal_announce_date: date | None = Field(
        default=None, index=True
    )
    updated_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class CapitalHistory(AwareSQLModel, table=True):
    """Bảng lưu trữ lịch sử tăng vốn điều lệ và phát hành cổ phiếu (Company.capital_history())."""

    __tablename__ = "capital_history"
    __table_args__ = (UniqueConstraint("symbol", "issue_date", "charter_capital"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    symbol: str = Field(max_length=20, foreign_key="stock_symbol.symbol", index=True)
    issue_date: date | None = Field(
        default=None, index=True
    )
    charter_capital: float | None = None
    shares_issued: float | None = None
    description: str | None = Field(default=None, max_length=500)
    updated_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
