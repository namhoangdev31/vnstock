"""Domain exceptions for Market Data & Ingestion."""


class MarketDataError(Exception):
    """Ngoại lệ cơ sở cho phân hệ dữ liệu thị trường."""


class SymbolNotFoundError(MarketDataError):
    """Ngoại lệ ném ra khi không tìm thấy mã chứng khoán trong hệ thống."""

    def __init__(self, symbol: str) -> None:
        self.symbol = symbol
        super().__init__(f"Symbol '{symbol}' was not found in stock symbol registry.")


class IngestionError(MarketDataError):
    """Ngoại lệ ném ra khi tiến trình thu thập / đồng bộ dữ liệu thất bại."""


class SafePurgeGateError(MarketDataError):
    """Ngoại lệ phát sinh khi Safe Purge Gate chặn việc xóa dữ liệu do chưa có bản tổng hợp thay thế."""


class VnstockServiceError(MarketDataError):
    """Ngoại lệ phát sinh khi tất cả các nguồn dữ liệu vnstock đều thất bại."""


__all__ = [
    "IngestionError",
    "MarketDataError",
    "SafePurgeGateError",
    "SymbolNotFoundError",
    "VnstockServiceError",
]
