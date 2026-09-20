"""Các đối tượng truyền tải dữ liệu (DTO) cho dữ liệu thị trường vnstock."""

from __future__ import annotations

from pydantic import BaseModel

# ==============================================================================
# RESPONSE DTOs
# ==============================================================================


class VnstockSymbolResponse(BaseModel):
    """Thông tin mã cổ phiếu, tên tổ chức và sàn niêm yết từ vnstock."""

    symbol: str
    organ_name: str | None = None
    exchange: str | None = None
