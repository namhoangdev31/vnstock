from pydantic import BaseModel


class VnstockSymbolItem(BaseModel):
    """Thông tin mã cổ phiếu, tên tổ chức và sàn niêm yết từ vnstock."""

    symbol: str
    organ_name: str | None = None
    exchange: str | None = None
