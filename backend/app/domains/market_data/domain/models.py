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
    exchange: str | None = Field(default=None, max_length=10)
    industry: str | None = Field(default=None, max_length=100)
    icb_code: str | None = Field(default=None, max_length=20)
    icb_name: str | None = Field(default=None, max_length=255)
    index_group: str | None = Field(default=None, max_length=50)
    asset_type: str = Field(
        default="stock",
        max_length=20,
    )
    lot_size: int = Field(default=100)
    is_active: bool = Field(default=True)
    updated_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )

    covered_warrants: list["CoveredWarrant"] = Relationship(
        back_populates="underlying_rel",
        sa_relationship_kwargs={"foreign_keys": "CoveredWarrant.underlying_symbol"},
    )
    issued_bonds: list["BondSpecification"] = Relationship(
        back_populates="issuer_rel",
        sa_relationship_kwargs={"foreign_keys": "BondSpecification.issuer_symbol"},
    )
    derivative_contracts: list["DerivativeContract"] = Relationship(
        back_populates="underlying_rel",
        sa_relationship_kwargs={"foreign_keys": "DerivativeContract.underlying_symbol"},
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
    value: float | None = None
    change: float | None = None
    change_pct: float | None = None
    reference_price: float | None = None
    ceiling_price: float | None = None
    floor_price: float | None = None
    adjusted_close: float | None = None
    buy_volume: int | None = None
    sell_volume: int | None = None
    foreign_buy_volume: int | None = None
    foreign_sell_volume: int | None = None
    foreign_net_volume: int | None = None
    open_interest: int | None = None
    basis: float | None = None
    source: str = Field(max_length=10)


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
    interval: str = Field(max_length=5)
    open: float
    high: float
    low: float
    close: float
    volume: int
    value: float | None = None
    buy_volume: int | None = None
    sell_volume: int | None = None
    volume_delta: int | None = None
    vwap: float | None = None
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
    match_type: str = Field(max_length=10)
    accumulated_volume: int | None = None
    accumulated_value: float | None = None
    sequence_number: int = Field(default=0)
    source: str = Field(max_length=10)


class IndexConstituent(AwareSQLModel, table=True):
    """Bảng lưu trữ thành phần & tỷ trọng rổ chỉ số (VN30, VN100, VNFINLEAD) phục vụ tính toán Basis & ATC."""

    __tablename__ = "index_constituent"
    __table_args__ = (
        UniqueConstraint("index_code", "symbol", "effective_date"),
        Index("ix_index_constituent_code_eff", "index_code", "effective_date"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    index_code: str = Field(max_length=20, index=True)
    symbol: str = Field(max_length=20, foreign_key="stock_symbol.symbol", index=True)
    weight: float = Field(default=0.0)
    free_float_shares: float | None = None
    effective_date: date = Field(index=True)
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
    sync_type: str = Field(max_length=30)
    symbol: str | None = Field(default=None, max_length=20)
    source: str = Field(max_length=10)
    status: str = Field(max_length=15)
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
    )
    underlying_symbol: str = Field(
        default="VN30", max_length=20, foreign_key="stock_symbol.symbol", index=True
    )
    multiplier: float = Field(default=100_000.0)
    first_trading_date: date | None = None
    last_trading_date: date | None = None
    expiration_date: date = Field(index=True)
    settlement_price: float | None = None
    is_active: bool = Field(default=True)
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
    )
    underlying_symbol: str = Field(
        max_length=20,
        foreign_key="stock_symbol.symbol",
        index=True,
    )
    issuer_name: str | None = Field(default=None, max_length=255)
    warrant_type: str = Field(default="call", max_length=10)
    exercise_price: float | None = None
    conversion_ratio: str | None = Field(default=None, max_length=20)
    exercise_ratio: float | None = None
    issue_date: date | None = None
    maturity_date: date | None = Field(default=None, index=True)
    last_trading_date: date | None = None
    settlement_type: str | None = Field(default="cash", max_length=20)
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
    )
    bond_type: str = Field(
        max_length=20,
        index=True,
    )
    issuer_symbol: str | None = Field(
        default=None,
        max_length=20,
        foreign_key="stock_symbol.symbol",
        index=True,
        nullable=True,
    )
    issuer_name: str | None = Field(default=None, max_length=255)
    par_value: float = Field(default=100_000.0)
    coupon_rate: float | None = None
    coupon_type: str | None = Field(default="fixed", max_length=20)
    tenor_years: float | None = None
    issue_date: date | None = None
    maturity_date: date | None = Field(default=None, index=True)
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
