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

# ===========================================================================
# 1. SCREENER AGGREGATE
# ===========================================================================


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


# ===========================================================================
# 2. CORPORATE PROFILE AGGREGATE
# ===========================================================================


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
    charter_capital: float | None = None  # Vốn điều lệ (VND)
    outstanding_shares: float | None = None  # Số lượng cổ phiếu đang lưu hành
    market_cap: float | None = None  # Vốn hóa thị trường (VND)
    free_float_pct: float | None = None  # Tỷ lệ cổ phiếu tự do chuyển nhượng (%)
    foreign_ownership_pct: float | None = None  # Tỷ lệ sở hữu nước ngoài hiện tại (%)
    max_foreign_ownership_pct: float | None = (
        None  # Tỷ lệ sở hữu nước ngoài tối đa (Room ngoại %)
    )
    employee_count: int | None = None  # Số lượng nhân viên
    website: str | None = Field(default=None, max_length=500)
    address: str | None = Field(default=None, max_length=500)
    ceo_name: str | None = Field(default=None, max_length=255)
    auditor: str | None = Field(default=None, max_length=255)
    description: str | None = None
    updated_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


# ===========================================================================
# 3. FINANCIAL STATEMENTS & REVISIONS AGGREGATE
# ===========================================================================


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
    )  # income_statement, balance_sheet, cash_flow
    report_scope: str = Field(
        default="consolidated", max_length=20, index=True
    )  # consolidated (hợp nhất), parent (công ty mẹ)
    period: str = Field(max_length=10)  # quarter, year
    year: int
    quarter: int | None = None  # 1-4 cho quý, None cho năm
    is_audited: bool = Field(default=False)  # Đã kiểm toán

    # Cột tóm tắt tài chính cốt lõi (Top-line & Bottom-line) dạng số học tường minh
    revenue: float | None = None  # Doanh thu thuần
    gross_profit: float | None = None  # Lợi nhuận gộp
    operating_profit: float | None = None  # Lợi nhuận từ HĐKD
    net_profit_parent: float | None = None  # LNST của CĐ công ty mẹ
    total_assets: float | None = None  # Tổng tài sản
    short_term_assets: float | None = None  # Tài sản ngắn hạn
    cash_and_equivalents: float | None = None  # Tiền & tương đương tiền
    total_liabilities: float | None = None  # Tổng nợ phải trả
    short_term_debt: float | None = None  # Vay nợ ngắn hạn
    long_term_debt: float | None = None  # Vay nợ dài hạn
    owners_equity: float | None = None  # Vốn chủ sở hữu
    operating_cash_flow: float | None = None  # Lưu chuyển tiền thuần từ HĐKD
    investing_cash_flow: float | None = None  # Lưu chuyển tiền thuần từ HĐĐT
    financing_cash_flow: float | None = None  # Lưu chuyển tiền thuần từ HĐTC

    data: dict[str, Any] = Field(
        default_factory=dict,
        sa_type=JSONBVariant,  # type: ignore
    )  # Lưu trữ payload gốc vnstock làm fallback thứ cấp
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
    )  # 1: bản đầu, 2: bản soát xét/kiểm toán, 3+: sửa đổi sau kiểm toán
    payload_hash: str = Field(max_length=64, index=True)  # SHA-256 canonical JSON
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
    )  # Mã chỉ tiêu: REVENUE, NET_PROFIT, ASSETS,...
    item_name: str = Field(max_length=255)  # Tên chỉ tiêu tiếng Việt
    value: float | None = None  # Giá trị số học (VND)
    order_index: int = Field(default=0)  # Thứ tự sắp xếp trên báo cáo tài chính

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
    period: str = Field(max_length=10)  # quarter, year
    year: int
    quarter: int | None = None  # 1-4 cho quý, None cho năm

    # Định giá & Sinh lời cơ bản
    pe: float | None = None  # Tỷ số P/E
    pb: float | None = None  # Tỷ số P/B
    ps: float | None = None  # Tỷ số P/S
    roe: float | None = None  # Lợi nhuận trên vốn chủ sở hữu ROE (%)
    roa: float | None = None  # Lợi nhuận trên tổng tài sản ROA (%)
    roic: float | None = None  # Hiệu quả sử dụng vốn đầu tư ROIC (%)
    eps: float | None = None  # Lãi cơ bản trên mỗi cổ phiếu EPS (VND)
    bvps: float | None = None  # Giá trị sổ sách mỗi cổ phiếu BVPS (VND)
    gross_margin: float | None = None  # Biên lợi nhuận gộp (%)
    net_margin: float | None = None  # Biên lợi nhuận ròng (%)
    debt_to_equity: float | None = None  # Tỷ lệ Nợ / Vốn chủ sở hữu
    quick_ratio: float | None = None  # Hệ số thanh toán nhanh
    current_ratio: float | None = None  # Hệ số thanh toán hiện hành
    dividend_yield: float | None = None  # Tỷ suất cổ tức (%)

    # Định giá & Dòng tiền bổ sung (Explicit Columns thay cho JSONB)
    ev_to_ebitda: float | None = None  # Tỷ số EV/EBITDA
    ev_to_ebit: float | None = None  # Tỷ số EV/EBIT
    p_to_fcf: float | None = None  # Giá trên Dòng tiền tự do (P/FCF)
    p_to_ocf: float | None = None  # Giá trên Dòng tiền HĐKD (P/OCF)
    fcf: float | None = None  # Dòng tiền tự do FCF (VND)

    # Hiệu quả hoạt động & Lợi nhuận bổ sung
    ebit_margin: float | None = None  # Biên EBIT (%)
    ebitda_margin: float | None = None  # Biên EBITDA (%)
    asset_turnover: float | None = None  # Vòng quay tổng tài sản
    inventory_turnover: float | None = None  # Vòng quay hàng tồn kho
    receivables_turnover: float | None = None  # Vòng quay các khoản phải thu

    # Cơ cấu vốn & Khả năng thanh toán bổ sung
    debt_to_assets: float | None = None  # Tỷ lệ Tổng nợ / Tổng tài sản
    interest_coverage: float | None = None  # Hệ số chi trả lãi vay (EBIT / Lãi vay)
    cash_ratio: float | None = None  # Tỷ số thanh toán tiền mặt

    # Tăng trưởng (Growth)
    revenue_growth_yoy: float | None = None  # Tăng trưởng doanh thu cùng kỳ (%)
    net_profit_growth_yoy: float | None = None  # Tăng trưởng lợi nhuận cùng kỳ (%)
    revenue_growth_qoq: float | None = (
        None  # Tăng trưởng doanh thu so với quý trước (%)
    )
    net_profit_growth_qoq: float | None = (
        None  # Tăng trưởng lợi nhuận so với quý trước (%)
    )

    data: dict[str, Any] = Field(
        default_factory=dict,
        sa_type=JSONBVariant,  # type: ignore
    )  # Lưu trữ trọn vẹn toàn bộ 58 chỉ số tài chính gốc từ vnstock làm fallback
    source: str = Field(max_length=10)
    updated_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


# ===========================================================================
# 4. CORPORATE GOVERNANCE AGGREGATES
# ===========================================================================


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
    )  # cash_dividend, stock_dividend, additional_issuance, agm, listing
    event_title: str = Field(max_length=500)
    ex_date: date | None = Field(
        default=None, index=True
    )  # Ngày giao dịch không hưởng quyền (GDKHQ)
    record_date: date | None = None  # Ngày đăng ký cuối cùng
    effective_date: date | None = None  # Ngày thực hiện / thanh toán cổ tức
    cash_rate: float | None = None  # Cổ tức tiền mặt (VND/cp)
    stock_rate: float | None = (
        None  # Tỷ lệ chia cổ phiếu thưởng / cổ tức (vd: 0.15 = 15%)
    )
    ratio_string: str | None = Field(
        default=None, max_length=50
    )  # Tỷ lệ thực hiện quyền (vd: "100:15", "10:1")
    notes: str | None = None  # Ghi chú / Điều kiện thực hiện quyền
    details: dict[str, Any] = Field(
        default_factory=dict,
        sa_type=JSONBVariant,  # type: ignore
    )  # Payload gốc linh hoạt
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
    share_count: float = Field(default=0.0)  # Số lượng cổ phiếu nắm giữ
    ownership_pct: float = Field(default=0.0)  # Tỷ lệ sở hữu (%)
    is_institutional: bool = Field(default=False)  # Cổ đông tổ chức
    is_foreign: bool = Field(default=False)  # Cổ đông nước ngoài
    is_state: bool = Field(default=False)  # Cổ đông đại diện vốn nhà nước
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
    )  # Chức vụ: Chủ tịch HĐQT, Tổng Giám đốc, Kế toán trưởng
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
    )  # Mã định danh công ty con / mã CK nếu có
    organ_name: str = Field(max_length=500)  # Tên công ty con/liên kết
    ownership_percent: float = Field(default=0.0)  # Tỷ lệ sở hữu (0.0 đến 1.0 hoặc %)
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
    )  # Tên cá nhân / tổ chức thực hiện giao dịch
    officer_position: str | None = Field(default=None, max_length=255)  # Chức vụ
    deal_action: str = Field(max_length=50)  # Mua / Bán / Đăng ký mua / Đăng ký bán
    deal_quantity: float | None = None  # Số lượng cổ phiếu giao dịch
    deal_price: float | None = None  # Giá giao dịch
    deal_ratio: float | None = None  # Tỷ lệ sau giao dịch
    deal_announce_date: date | None = Field(
        default=None, index=True
    )  # Ngày công bố thông tin
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
    )  # Ngày thực hiện tăng vốn / niêm yết bổ sung
    charter_capital: float | None = None  # Vốn điều lệ sau phát hành (VND)
    shares_issued: float | None = None  # Số lượng cổ phiếu phát hành thêm
    description: str | None = Field(default=None, max_length=500)  # Hình thức tăng vốn
    updated_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
