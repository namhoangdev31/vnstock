"""Data Transfer Objects (DTOs) for Market Data & Ingestion."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlmodel import SQLModel

from app.domains.fundamental.application.schemas import CompanyOverviewPublic


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


class VnstockSymbolResponse(SQLModel):
    """Thông tin mã cổ phiếu, tên tổ chức và sàn niêm yết từ vnstock."""

    symbol: str
    organ_name: str | None = None
    exchange: str | None = None


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


__all__ = [
    "BondSpecificationPublic",
    "CoveredWarrantPublic",
    "DerivativeContractPublic",
    "IndexConstituentPublic",
    "IndexConstituentsResponse",
    "OHLCVRecord",
    "PriceHistoryResponse",
    "RelatedAssetsResponse",
    "StockSymbolPublic",
    "StockSymbolsPublic",
    "SyncStatusPublic",
    "VnstockSymbolResponse",
]
