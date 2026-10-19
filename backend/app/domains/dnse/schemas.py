"""Pydantic / SQLModel Schemas for DNSE Domain.

Defines schemas for DNSE market data feeds including Market Breadth series,
symbol breakdown by status, and real-time tick/depth structures.
"""

from __future__ import annotations

from sqlmodel import Field, SQLModel


class DNSEIndexBreadth(SQLModel):
    """Snapshot phân bổ trạng thái độ rộng thị trường của chỉ số."""

    advance: int = Field(default=0, description="Số mã tăng giá")
    ceiling: int = Field(default=0, description="Số mã tăng trần")
    unchanged: int = Field(default=0, description="Số mã đứng giá (tham chiếu)")
    decline: int = Field(default=0, description="Số mã giảm giá")
    floor: int = Field(default=0, description="Số mã giảm sàn")


class MarketBreadthPoint(SQLModel):
    """Điểm dữ liệu độ rộng thị trường tại một mốc thời gian trong phiên."""

    time: str = Field(description="Thời gian nến dạng HH:mm")
    timestamp: int = Field(description="Unix timestamp (giây)")
    advance: int = Field(description="Số mã tăng (bao gồm trần)")
    decline: int = Field(description="Số mã giảm (bao gồm sàn)")
    unchanged: int = Field(description="Số mã tham chiếu")
    ceiling: int = Field(description="Số mã giá trần")
    floor: int = Field(description="Số mã giá sàn")
    total: int = Field(description="Tổng số mã có dữ liệu")
    ceiling_pct: float = Field(description="Tỷ lệ % mã trần")
    advance_pure_pct: float = Field(description="Tỷ lệ % mã tăng (trừ trần)")
    unchanged_pct: float = Field(description="Tỷ lệ % mã đứng giá")
    decline_pure_pct: float = Field(description="Tỷ lệ % mã giảm (trừ sàn)")
    floor_pct: float = Field(description="Tỷ lệ % mã sàn")


class MarketBreadthSeriesResponse(SQLModel):
    """Chuỗi thời gian phân bổ tỷ lệ độ rộng thị trường trong phiên."""

    index_code: str = Field(description="Mã chỉ số chuẩn hoá (VNINDEX, VN30, ...)")
    data: list[MarketBreadthPoint] = Field(
        default_factory=list, description="Danh sách các điểm 100% stacked"
    )
    latest: MarketBreadthPoint | None = Field(
        default=None, description="Điểm độ rộng mới nhất"
    )


class MarketBreadthDetailResponse(SQLModel):
    """Chi tiết danh sách mã cổ phiếu phân theo 5 trạng thái biến động."""

    index_code: str = Field(description="Mã chỉ số (VNINDEX, VN30, ...)")
    ceiling: list[str] = Field(default_factory=list, description="Danh sách mã trần")
    advance: list[str] = Field(default_factory=list, description="Danh sách mã tăng")
    no_change: list[str] = Field(
        default_factory=list, description="Danh sách mã tham chiếu"
    )
    decline: list[str] = Field(default_factory=list, description="Danh sách mã giảm")
    floor: list[str] = Field(default_factory=list, description="Danh sách mã sàn")
    total: int = Field(default=0, description="Tổng số mã trong rổ")
