# ruff: noqa: UP045
"""Mô hình dữ liệu thực thể chứng khoán, hồ sơ doanh nghiệp & báo cáo tài chính (Database Tables).

Hệ thống bảng dữ liệu chuyên sâu cho hệ sinh thái vnstock v4, phục vụ 3 Động cơ Định lượng (Tri-Engine),
dự báo phiên ATC, hợp đồng tương lai phái sinh VN30F1M và danh mục cổ phiếu Alpha đa khung thời gian.
"""

import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import DateTime, Index, UniqueConstraint
from sqlmodel import Field, Relationship

from app.models.base import AwareSQLModel, JSONBVariant, get_datetime_utc


class StockSymbol(AwareSQLModel, table=True):
    """Bảng lưu trữ thông tin tham chiếu mã chứng khoán (HOSE, HNX, UPCOM, Phái sinh, Index, ETF)."""

    __tablename__ = "stock_symbol"
    __table_args__ = (
        Index("ix_stock_symbol_active_exchange", "is_active", "exchange", "asset_type"),
        Index("ix_stock_symbol_active_group", "index_group", "is_active"),
    )

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        unique=True,
        index=True,
        nullable=False,
    )
    symbol: str = Field(primary_key=True, max_length=20)
    organ_name: str | None = Field(default=None, max_length=255)
    exchange: str | None = Field(default=None, max_length=10)  # HOSE, HNX, UPCOM, DERIV
    industry: str | None = Field(default=None, max_length=100)
    icb_code: str | None = Field(default=None, max_length=20)  # Mã ngành ICB cấp 1-4
    icb_name: str | None = Field(
        default=None, max_length=255
    )  # Tên ngành theo chuẩn ICB
    index_group: str | None = Field(
        default=None, max_length=50
    )  # Rổ chỉ số: VN30, VN100, VNFINLEAD
    asset_type: str = Field(
        default="stock",
        max_length=20,
    )  # stock, etf, derivative, index, covered_warrant, corporate_bond, government_bond
    lot_size: int = Field(default=100)  # Quy mô lô chuẩn (100 cp cơ sở, 1 HĐ phái sinh)
    is_active: bool = Field(default=True)
    updated_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )

    # Relationships hai chiều phục vụ truy xuất thông tin chéo
    profile: Optional["CompanyProfile"] = Relationship(
        back_populates="symbol_rel",
        sa_relationship_kwargs={"uselist": False},
    )
    financial_reports: list["FinancialReport"] = Relationship(
        back_populates="symbol_rel"
    )
    financial_ratios: list["FinancialRatio"] = Relationship(back_populates="symbol_rel")
    corporate_events: list["CorporateEvent"] = Relationship(back_populates="symbol_rel")
    shareholders: list["CompanyShareholder"] = Relationship(back_populates="symbol_rel")
    officers: list["CompanyOfficer"] = Relationship(back_populates="symbol_rel")
    # Chứng quyền có tài sản cơ sở là mã này (e.g. FPT -> [CFPT2501, CFPT2502])
    covered_warrants: list["CoveredWarrant"] = Relationship(
        back_populates="underlying_rel",
        sa_relationship_kwargs={"foreign_keys": "CoveredWarrant.underlying_symbol"},
    )
    # Trái phiếu do công ty này phát hành (e.g. MSN -> [MSN123009])
    issued_bonds: list["BondSpecification"] = Relationship(
        back_populates="issuer_rel",
        sa_relationship_kwargs={"foreign_keys": "BondSpecification.issuer_symbol"},
    )
    # Hợp đồng phái sinh dựa trên chỉ số này (e.g. VN30 -> [VN30F1M, VN30F2M])
    derivative_contracts: list["DerivativeContract"] = Relationship(
        back_populates="underlying_rel",
        sa_relationship_kwargs={"foreign_keys": "DerivativeContract.underlying_symbol"},
    )
    # Danh sách công ty con & liên kết (Company.subsidiaries())
    subsidiaries: list["CompanySubsidiary"] = Relationship(back_populates="symbol_rel")
    # Nhật ký giao dịch nội bộ (Company.insider_trading())
    insider_tradings: list["InsiderTrading"] = Relationship(back_populates="symbol_rel")
    # Lịch sử tăng vốn điều lệ (Company.capital_history())
    capital_histories: list["CapitalHistory"] = Relationship(
        back_populates="symbol_rel"
    )


class StockOHLCVDaily(AwareSQLModel, table=True):
    """Bảng lưu trữ nến lịch sử giao dịch hàng ngày (OHLCV Daily) kèm phân rã dòng tiền & biên độ."""

    __tablename__ = "stock_ohlcv_daily"
    __table_args__ = (
        UniqueConstraint("symbol", "trading_date"),
        Index("ix_stock_ohlcv_daily_sym_date", "symbol", "trading_date"),
        Index("ix_stock_ohlcv_daily_date_val", "trading_date", "value"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    symbol: str = Field(max_length=20, foreign_key="stock_symbol.symbol", index=True)
    trading_date: date = Field(index=True)
    open: float
    high: float
    low: float
    close: float
    volume: int
    value: float | None = None  # Giá trị giao dịch khớp lệnh (VND)
    change: float | None = None  # Biến động giá tuyệt đối (VND)
    change_pct: float | None = None  # Phần trăm thay đổi giá (%)
    reference_price: float | None = None  # Giá tham chiếu trong ngày
    ceiling_price: float | None = None  # Giá trần (HOSE: +7%, HNX: +10%, UPCOM: +15%)
    floor_price: float | None = None  # Giá sàn (HOSE: -7%, HNX: -10%, UPCOM: -15%)
    adjusted_close: float | None = None  # Giá đóng cửa điều chỉnh sau chia cổ tức
    buy_volume: int | None = None  # Khối lượng khớp lệnh mua chủ động
    sell_volume: int | None = None  # Khối lượng khớp lệnh bán chủ động
    foreign_buy_volume: int | None = None  # Khối lượng mua của Khối ngoại
    foreign_sell_volume: int | None = None  # Khối lượng bán của Khối ngoại
    foreign_net_volume: int | None = None  # Mua/Bán ròng của Khối ngoại
    open_interest: int | None = None  # Khối lượng vị thế mở qua đêm (phái sinh VN30F1M)
    basis: float | None = (
        None  # Độ lệch giá đóng cửa phái sinh so với VN30 (VN30F1M - VN30)
    )
    source: str = Field(max_length=10)  # VCI, KBS, TCBS


class StockOHLCVIntraday(AwareSQLModel, table=True):
    """Bảng lưu trữ nến giao dịch trong ngày đa khung (1m, 5m, 15m) tích hợp Volume Delta & VWAP."""

    __tablename__ = "stock_ohlcv_intraday"
    __table_args__ = (
        UniqueConstraint("symbol", "timestamp", "interval"),
        Index(
            "ix_stock_ohlcv_intraday_sym_int_time",
            "symbol",
            "interval",
            "timestamp",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    symbol: str = Field(max_length=20, foreign_key="stock_symbol.symbol", index=True)
    timestamp: datetime = Field(sa_type=DateTime(timezone=True), index=True)  # type: ignore
    interval: str = Field(max_length=5)  # 1m, 5m, 15m, 1h
    open: float
    high: float
    low: float
    close: float
    volume: int
    value: float | None = None  # Giá trị giao dịch cây nến
    buy_volume: int | None = None  # Khối lượng mua chủ động
    sell_volume: int | None = None  # Khối lượng bán chủ động
    volume_delta: int | None = None  # Delta luồng lệnh (Buy Vol - Sell Vol)
    vwap: float | None = None  # Giá bình quân gia quyền theo khối lượng (VWAP)
    source: str = Field(max_length=10)


class StockTickIntraday(AwareSQLModel, table=True):
    """Bảng lưu trữ từng tick khớp lệnh thời gian thực Quote.intraday() (Chiến lược lưu trữ 30 ngày)."""

    __tablename__ = "stock_tick_intraday"
    __table_args__ = (
        UniqueConstraint("symbol", "timestamp", "sequence_number"),
        Index("ix_stock_tick_intraday_sym_time", "symbol", "timestamp"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    symbol: str = Field(max_length=20, foreign_key="stock_symbol.symbol", index=True)
    timestamp: datetime = Field(sa_type=DateTime(timezone=True), index=True)  # type: ignore
    price: float
    volume: int
    match_type: str = Field(
        max_length=10
    )  # BU (Mua chủ động), SD (Bán chủ động), ATO, ATC
    accumulated_volume: int | None = None  # Khối lượng tích lũy đến thời điểm tick
    accumulated_value: float | None = None  # Giá trị tích lũy đến thời điểm tick
    sequence_number: int = Field(
        default=0
    )  # Thứ tự tick trong cùng một timestamp mili-giây
    source: str = Field(max_length=10)


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

    symbol_rel: Optional[StockSymbol] = Relationship(back_populates="profile")


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

    data: dict = Field(
        default_factory=dict,
        sa_type=JSONBVariant,  # type: ignore
    )  # Lưu trữ payload gốc vnstock làm fallback thứ cấp
    source: str = Field(max_length=10)
    updated_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )

    symbol_rel: Optional[StockSymbol] = Relationship(back_populates="financial_reports")
    items: list["FinancialReportItem"] = Relationship(back_populates="report")


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

    data: dict = Field(
        default_factory=dict,
        sa_type=JSONBVariant,  # type: ignore
    )  # Lưu trữ trọn vẹn toàn bộ 58 chỉ số tài chính gốc từ vnstock làm fallback
    source: str = Field(max_length=10)
    updated_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )

    symbol_rel: Optional[StockSymbol] = Relationship(back_populates="financial_ratios")


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
    details: dict = Field(
        default_factory=dict,
        sa_type=JSONBVariant,  # type: ignore
    )  # Payload gốc linh hoạt
    source: str = Field(max_length=10)
    created_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )

    symbol_rel: Optional[StockSymbol] = Relationship(back_populates="corporate_events")


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

    symbol_rel: Optional[StockSymbol] = Relationship(back_populates="shareholders")


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

    symbol_rel: Optional[StockSymbol] = Relationship(back_populates="officers")


class IndexConstituent(AwareSQLModel, table=True):
    """Bảng lưu trữ thành phần & tỷ trọng rổ chỉ số (VN30, VN100, VNFINLEAD) phục vụ tính toán Basis & ATC."""

    __tablename__ = "index_constituent"
    __table_args__ = (
        UniqueConstraint("index_code", "symbol", "effective_date"),
        Index("ix_index_constituent_code_eff", "index_code", "effective_date"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    index_code: str = Field(
        max_length=20, index=True
    )  # VN30, VN100, VNFINLEAD, VNMID, VNSML
    symbol: str = Field(max_length=20, foreign_key="stock_symbol.symbol", index=True)
    weight: float = Field(default=0.0)  # Tỷ trọng trong rổ chỉ số (%)
    free_float_shares: float | None = None  # Số lượng cổ phiếu tự do lưu hành
    effective_date: date = Field(index=True)  # Ngày áp dụng hiệu lực của kỳ cơ cấu
    updated_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class DataSyncLog(AwareSQLModel, table=True):
    """Bảng nhật ký kiểm toán và theo dõi tiến trình đồng bộ dữ liệu thị trường."""

    __tablename__ = "data_sync_log"
    __table_args__ = (
        Index("ix_data_sync_log_type_date", "sync_type", "started_at"),
        Index("ix_data_sync_log_symbol_date", "symbol", "started_at"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    sync_type: str = Field(
        max_length=30
    )  # symbols, daily_ohlcv, intraday, ticks, profile, financials, ratios, events, constituents
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


class DerivativeContract(AwareSQLModel, table=True):
    """Bảng lưu trữ đặc tả hợp đồng tương lai phái sinh (VN30F1M, VN30F2M, VN30F1Q, VN30F2Q)."""

    __tablename__ = "derivative_contract"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        unique=True,
        index=True,
        nullable=False,
    )
    symbol: str = Field(
        primary_key=True, max_length=20, foreign_key="stock_symbol.symbol"
    )  # Mã HĐ: VN30F1M, VN30F2609
    underlying_symbol: str = Field(
        default="VN30", max_length=20, foreign_key="stock_symbol.symbol", index=True
    )  # Tài sản cơ sở VN30
    multiplier: float = Field(default=100_000.0)  # Hệ số nhân: 100,000 VND / điểm
    first_trading_date: date | None = None  # Ngày niêm yết chào sàn
    last_trading_date: date | None = None  # Ngày giao dịch cuối cùng
    expiration_date: date = Field(index=True)  # Ngày đáo hạn hợp đồng (Thứ 5 tuần 3)
    settlement_price: float | None = None  # Giá thanh toán cuối cùng ngày đáo hạn
    is_active: bool = Field(default=True)  # Đang trong chu kỳ giao dịch
    updated_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )

    underlying_rel: Optional[StockSymbol] = Relationship(
        back_populates="derivative_contracts",
        sa_relationship_kwargs={"foreign_keys": "DerivativeContract.underlying_symbol"},
    )


class CoveredWarrant(AwareSQLModel, table=True):
    """Bảng lưu trữ đặc tả chứng quyền có bảo đảm (Covered Warrant - CW) niêm yết trên HOSE."""

    __tablename__ = "covered_warrant"
    __table_args__ = (
        Index(
            "ix_covered_warrant_underlying_active",
            "underlying_symbol",
            "is_active",
        ),
    )

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
    )
    symbol: str = Field(
        max_length=20,
        unique=True,
        index=True,
        foreign_key="stock_symbol.symbol",
    )  # Mã chứng quyền ví dụ CACB2511, CFPT2501
    underlying_symbol: str = Field(
        max_length=20,
        foreign_key="stock_symbol.symbol",
        index=True,
    )  # Mã cổ phiếu cơ sở ví dụ ACB, FPT, HPG
    issuer_name: str | None = Field(
        default=None, max_length=255
    )  # Tên tổ chức phát hành (CTCK: SSI, VND, HSC...)
    warrant_type: str = Field(default="call", max_length=10)  # call / put
    exercise_price: float | None = None  # Giá thực hiện (VND)
    conversion_ratio: str | None = Field(
        default=None, max_length=20
    )  # Tỷ lệ chuyển đổi ví dụ "4:1", "2:1"
    exercise_ratio: float | None = None  # Tỷ lệ thực hiện dạng số thập phân (e.g. 0.25)
    issue_date: date | None = None  # Ngày phát hành
    maturity_date: date | None = Field(
        default=None, index=True
    )  # Ngày đáo hạn chứng quyền
    last_trading_date: date | None = None  # Ngày giao dịch cuối cùng
    settlement_type: str | None = Field(
        default="cash", max_length=20
    )  # Hình thức thanh toán: cash (tiền mặt)
    is_active: bool = Field(default=True)
    updated_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )

    underlying_rel: Optional[StockSymbol] = Relationship(
        back_populates="covered_warrants",
        sa_relationship_kwargs={"foreign_keys": "CoveredWarrant.underlying_symbol"},
    )


class BondSpecification(AwareSQLModel, table=True):
    """Bảng lưu trữ đặc tả trái phiếu doanh nghiệp & trái phiếu chính phủ niêm yết trên HNX."""

    __tablename__ = "bond_specification"
    __table_args__ = (
        Index("ix_bond_spec_issuer_active", "issuer_symbol", "is_active"),
        Index("ix_bond_spec_type_active", "bond_type", "is_active"),
    )

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
    )
    symbol: str = Field(
        max_length=20,
        unique=True,
        index=True,
        foreign_key="stock_symbol.symbol",
    )  # Mã trái phiếu ví dụ BAB123032, 41B5GC000
    bond_type: str = Field(
        max_length=20,
        index=True,
    )  # corporate (doanh nghiệp) / government (chính phủ)
    issuer_symbol: str | None = Field(
        default=None,
        max_length=20,
        foreign_key="stock_symbol.symbol",
        index=True,
        nullable=True,
    )  # Mã doanh nghiệp phát hành nếu niêm yết (ví dụ BAB, MSN, VIC)
    issuer_name: str | None = Field(
        default=None, max_length=255
    )  # Tên tổ chức phát hành
    par_value: float = Field(default=100_000.0)  # Mệnh giá chuẩn (VND)
    coupon_rate: float | None = None  # Lãi suất danh nghĩa (%/năm)
    coupon_type: str | None = Field(
        default="fixed", max_length=20
    )  # fixed (cố định) / floating (thả nổi)
    tenor_years: float | None = None  # Kỳ hạn trái phiếu (năm)
    issue_date: date | None = None  # Ngày phát hành
    maturity_date: date | None = Field(
        default=None, index=True
    )  # Ngày đáo hạn trái phiếu
    is_active: bool = Field(default=True)
    updated_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )

    issuer_rel: Optional[StockSymbol] = Relationship(
        back_populates="issued_bonds",
        sa_relationship_kwargs={"foreign_keys": "BondSpecification.issuer_symbol"},
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

    symbol_rel: Optional[StockSymbol] = Relationship(back_populates="subsidiaries")


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

    symbol_rel: Optional[StockSymbol] = Relationship(back_populates="insider_tradings")


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

    symbol_rel: Optional[StockSymbol] = Relationship(back_populates="capital_histories")
