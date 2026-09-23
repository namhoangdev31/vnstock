# ruff: noqa: UP045
"""Mô hình thực thể Dữ liệu thị trường & Ingestion (Domain Models).

Bao gồm 9 thực thể SQLModel cốt lõi:
- StockSymbol: Thông tin tham chiếu mã chứng khoán (HOSE, HNX, UPCOM, Phái sinh, Index, ETF)
- StockOHLCVDaily: Nến lịch sử ngày, phân rã dòng tiền & biên độ giá
- StockOHLCVIntraday: Nến trong ngày đa khung (1m, 5m, 15m, 1h), Volume Delta, VWAP
- StockTickIntraday: Từng tick khớp lệnh quan sát thời gian thực (Quote.intraday)
- IndexConstituent: Thành phần và tỷ trọng rổ chỉ số (VN30, VN100, VNFINLEAD)
- DataSyncLog: Nhật ký kiểm toán và theo dõi tiến trình đồng bộ dữ liệu
- DerivativeContract: Đặc tả hợp đồng tương lai phái sinh (VN30F1M)
- CoveredWarrant: Đặc tả chứng quyền có bảo đảm (HOSE)
- BondSpecification: Đặc tả trái phiếu doanh nghiệp & chính phủ (HNX)
"""

import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import DateTime, Index, UniqueConstraint
from sqlmodel import Field, Relationship

from app.core.models_base import AwareSQLModel, get_datetime_utc
from app.domains.fundamental.domain.models import (
    CapitalHistory,
    CompanyOfficer,
    CompanyProfile,
    CompanyShareholder,
    CompanySubsidiary,
    CorporateEvent,
    FinancialRatio,
    FinancialReport,
    InsiderTrading,
)


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
    instrument_id: uuid.UUID | None = Field(
        default=None, foreign_key="instrument.id", index=True
    )
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


__all__ = [
    "BondSpecification",
    "CoveredWarrant",
    "DataSyncLog",
    "DerivativeContract",
    "IndexConstituent",
    "StockOHLCVDaily",
    "StockOHLCVIntraday",
    "StockSymbol",
    "StockTickIntraday",
]
