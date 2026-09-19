from pydantic import BaseModel


class VnstockSymbolItem(BaseModel):
    """Thông tin mã cổ phiếu và tên tổ chức niêm yết từ vnstock."""

    symbol: str
    organ_name: str | None = None