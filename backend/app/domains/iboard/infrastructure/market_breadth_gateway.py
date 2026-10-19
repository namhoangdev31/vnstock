"""Infrastructure Gateway: Market Breadth adapter delegating to DNSE domain.

iBoard tiêu thụ dữ liệu độ rộng thị trường từ domain `app.domains.dnse`.
File này đóng vai trò Facade Adapter để đảm bảo tính nhất quán kiến trúc DDD.
"""

from __future__ import annotations

from app.domains.dnse.market_breadth_gateway import DNSEMarketBreadthGateway

# Alias tương thích kiến trúc cho iBoard
MarketBreadthGateway = DNSEMarketBreadthGateway

__all__ = ["DNSEMarketBreadthGateway", "MarketBreadthGateway"]
