"""Vnstock v4 Capability Registry & Source Provenance Specification.

Định nghĩa rõ ràng ma trận năng lực theo Provider × Field, phân định:
- Mapped Capabilities: Các tính năng chính thức thuộc phạm vi TTCK Việt Nam.
- Unavailable Capabilities: Các chỉ báo (tự doanh, breadth) không có nguồn Vnstock xác minh.
- Out-of-Scope Capabilities: Crypto, hàng hóa quốc tế chủ động loại trừ theo AGENTS §1.1.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class CapabilityStatus(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    OUT_OF_SCOPE = "out_of_scope"


class DataAvailability(BaseModel):
    """Thông tin về tính khả dụng và nguồn gốc của một trường/chỉ báo dữ liệu."""

    status: CapabilityStatus = CapabilityStatus.AVAILABLE
    reason: str | None = None
    supported_sources: list[str] = Field(default_factory=list)
    is_fallback: bool = False
    actual_source: str | None = None


class CapabilityInfo(BaseModel):
    module: str
    action: str
    status: CapabilityStatus
    primary_source: str | None = None
    fallback_sources: list[str] = Field(default_factory=list)
    description: str = ""
    reason: str | None = None


class VnstockCapabilityRegistry:
    """Registry trung tâm quản lý ma trận năng lực của toàn bộ hệ sinh thái dữ liệu vnstock."""

    # Provider fallback order chuẩn theo AGENTS §7.1 (loại bỏ DNSE không tương thích)
    FALLBACK_ORDER: list[str] = ["vci", "kbs", "msn"]

    CAPABILITIES: dict[str, CapabilityInfo] = {
        # 1. Quote Module
        "quote.history_daily": CapabilityInfo(
            module="Quote",
            action="history(interval='1D')",
            status=CapabilityStatus.AVAILABLE,
            primary_source="vci",
            fallback_sources=["kbs", "msn"],
            description="Nến lịch sử theo ngày (OHLCV, tham chiếu, trần/sàn, điều chỉnh, khối ngoại)",
        ),
        "quote.history_intraday": CapabilityInfo(
            module="Quote",
            action="history(interval='1m')",
            status=CapabilityStatus.AVAILABLE,
            primary_source="vci",
            fallback_sources=["kbs"],
            description="Nến lịch sử trong ngày 1 phút (OHLCV, giá trị)",
        ),
        "quote.intraday_ticks": CapabilityInfo(
            module="Quote",
            action="intraday()",
            status=CapabilityStatus.AVAILABLE,
            primary_source="vci",
            fallback_sources=["kbs"],
            description="Gói tick khớp lệnh quan sát (price, volume, match_type)",
        ),
        # 2. Listing Module
        "listing.all_symbols": CapabilityInfo(
            module="Listing",
            action="all_symbols()",
            status=CapabilityStatus.AVAILABLE,
            primary_source="kbs",
            fallback_sources=["vci", "msn"],
            description="Toàn bộ mã niêm yết HOSE, HNX, UPCOM",
        ),
        "listing.group_symbols": CapabilityInfo(
            module="Listing",
            action="symbols_by_group()",
            status=CapabilityStatus.AVAILABLE,
            primary_source="kbs",
            fallback_sources=["vci"],
            description="Danh mục mã theo rổ chỉ số (VN30, VN100, VNFINLEAD)",
        ),
        "listing.industries_icb": CapabilityInfo(
            module="Listing",
            action="industries_icb()",
            status=CapabilityStatus.AVAILABLE,
            primary_source="kbs",
            fallback_sources=["vci"],
            description="Phân loại ngành ICB 4 cấp",
        ),
        # 3. Company Module
        "company.overview": CapabilityInfo(
            module="Company",
            action="overview()",
            status=CapabilityStatus.AVAILABLE,
            primary_source="kbs",
            fallback_sources=["vci"],
            description="Tổng quan vốn điều lệ, vốn hóa, số CP lưu hành",
        ),
        "company.profile": CapabilityInfo(
            module="Company",
            action="profile()",
            status=CapabilityStatus.AVAILABLE,
            primary_source="kbs",
            fallback_sources=["vci"],
            description="Thông tin chi tiết doanh nghiệp, ban điều hành",
        ),
        "company.shareholders": CapabilityInfo(
            module="Company",
            action="shareholders()",
            status=CapabilityStatus.AVAILABLE,
            primary_source="kbs",
            fallback_sources=["vci"],
            description="Cơ cấu cổ đông lớn và tổ chức",
        ),
        "company.officers": CapabilityInfo(
            module="Company",
            action="officers()",
            status=CapabilityStatus.AVAILABLE,
            primary_source="kbs",
            fallback_sources=["vci"],
            description="Danh sách ban lãnh đạo và người đại diện pháp luật",
        ),
        "company.subsidiaries": CapabilityInfo(
            module="Company",
            action="subsidiaries()",
            status=CapabilityStatus.AVAILABLE,
            primary_source="kbs",
            fallback_sources=["vci"],
            description="Danh sách công ty con và công ty liên kết",
        ),
        "company.capital_history": CapabilityInfo(
            module="Company",
            action="capital_history()",
            status=CapabilityStatus.AVAILABLE,
            primary_source="kbs",
            fallback_sources=["vci"],
            description="Lịch sử các đợt phát hành và tăng vốn điều lệ",
        ),
        "company.insider_trading": CapabilityInfo(
            module="Company",
            action="insider_trading()",
            status=CapabilityStatus.AVAILABLE,
            primary_source="kbs",
            fallback_sources=["vci"],
            description="Lịch sử giao dịch của cổ đông nội bộ",
        ),
        # 4. Finance & Fundamental Module
        "finance.income_statement": CapabilityInfo(
            module="Finance",
            action="income_statement()",
            status=CapabilityStatus.AVAILABLE,
            primary_source="kbs",
            fallback_sources=["vci"],
            description="Báo cáo kết quả hoạt động kinh doanh (KQKD) Quý/Năm",
        ),
        "finance.balance_sheet": CapabilityInfo(
            module="Finance",
            action="balance_sheet()",
            status=CapabilityStatus.AVAILABLE,
            primary_source="kbs",
            fallback_sources=["vci"],
            description="Bảng cân đối kế toán (CĐKT) Quý/Năm",
        ),
        "finance.cash_flow": CapabilityInfo(
            module="Finance",
            action="cash_flow()",
            status=CapabilityStatus.AVAILABLE,
            primary_source="kbs",
            fallback_sources=["vci"],
            description="Báo cáo lưu chuyển tiền tệ (LCTT) Quý/Năm",
        ),
        "fundamental.ratios": CapabilityInfo(
            module="Fundamental",
            action="equity().ratio()",
            status=CapabilityStatus.AVAILABLE,
            primary_source="kbs",
            fallback_sources=["vci"],
            description="Hơn 50 chỉ số tài chính và tỷ số định giá cốt lõi (alias)",
        ),
        "fundamental.income_statement": CapabilityInfo(
            module="Fundamental",
            action="equity().income_statement()",
            status=CapabilityStatus.AVAILABLE,
            primary_source="kbs",
            fallback_sources=["vci"],
            description="Báo cáo kết quả hoạt động kinh doanh Quý/Năm qua Fundamental.equity",
        ),
        "fundamental.balance_sheet": CapabilityInfo(
            module="Fundamental",
            action="equity().balance_sheet()",
            status=CapabilityStatus.AVAILABLE,
            primary_source="kbs",
            fallback_sources=["vci"],
            description="Bảng cân đối kế toán Quý/Năm qua Fundamental.equity",
        ),
        "fundamental.cash_flow": CapabilityInfo(
            module="Fundamental",
            action="equity().cash_flow()",
            status=CapabilityStatus.AVAILABLE,
            primary_source="kbs",
            fallback_sources=["vci"],
            description="Báo cáo lưu chuyển tiền tệ Quý/Năm qua Fundamental.equity",
        ),
        "fundamental.ratio": CapabilityInfo(
            module="Fundamental",
            action="equity().ratio()",
            status=CapabilityStatus.AVAILABLE,
            primary_source="kbs",
            fallback_sources=["vci"],
            description="Hơn 50 chỉ số tài chính và định giá định lượng qua Fundamental.equity",
        ),
        # 5. Retail Module
        "retail.gold": CapabilityInfo(
            module="Retail",
            action="gold()",
            status=CapabilityStatus.AVAILABLE,
            primary_source="retail",
            fallback_sources=[],
            description="Giá vàng miếng SJC và giá vàng quốc tế quy đổi",
        ),
        "retail.exchange_rate": CapabilityInfo(
            module="Retail",
            action="exchange_rate()",
            status=CapabilityStatus.AVAILABLE,
            primary_source="retail",
            fallback_sources=[],
            description="Tỷ giá USD/VND thị trường liên ngân hàng",
        ),
        # 6. Market Module (Đầy đủ 10 lớp tài sản v4.0.6)
        "market.quote": CapabilityInfo(
            module="Market",
            action="quote()",
            status=CapabilityStatus.AVAILABLE,
            primary_source="vci",
            fallback_sources=["kbs"],
            description="Bảng giá realtime cơ sở và khớp lệnh snapshot",
        ),
        "market.equity_ohlcv": CapabilityInfo(
            module="Market",
            action="equity().ohlcv()",
            status=CapabilityStatus.AVAILABLE,
            primary_source="kbs",
            fallback_sources=["vci"],
            description="Nến OHLCV cổ phiếu qua Market.equity",
        ),
        "market.equity_trades": CapabilityInfo(
            module="Market",
            action="equity().trades()",
            status=CapabilityStatus.AVAILABLE,
            primary_source="kbs",
            fallback_sources=["vci"],
            description="Dữ liệu khớp lệnh chi tiết cổ phiếu trong ngày (Tick-by-tick)",
        ),
        "market.equity_quote": CapabilityInfo(
            module="Market",
            action="equity().quote()",
            status=CapabilityStatus.AVAILABLE,
            primary_source="kbs",
            fallback_sources=["vci"],
            description="Bảng giá hiện tại của cổ phiếu qua Market.equity",
        ),
        "market.index_ohlcv": CapabilityInfo(
            module="Market",
            action="index().ohlcv()",
            status=CapabilityStatus.AVAILABLE,
            primary_source="kbs",
            fallback_sources=["vci"],
            description="Nến điểm số chỉ số thị trường (VNINDEX, VN30)",
        ),
        "market.futures": CapabilityInfo(
            module="Market",
            action="futures().quote()",
            status=CapabilityStatus.AVAILABLE,
            primary_source="vci",
            fallback_sources=["kbs"],
            description="Bảng giá phái sinh chỉ số VN30 và OI",
        ),
        "market.futures_ohlcv": CapabilityInfo(
            module="Market",
            action="futures().ohlcv()",
            status=CapabilityStatus.AVAILABLE,
            primary_source="vci",
            fallback_sources=["kbs"],
            description="Nến OHLCV hợp đồng phái sinh qua Market.futures",
        ),
        "market.futures_trades": CapabilityInfo(
            module="Market",
            action="futures().trades()",
            status=CapabilityStatus.AVAILABLE,
            primary_source="vci",
            fallback_sources=["kbs"],
            description="Khớp lệnh phái sinh chi tiết trong ngày",
        ),
        "market.warrant_ohlcv": CapabilityInfo(
            module="Market",
            action="warrant().ohlcv()",
            status=CapabilityStatus.AVAILABLE,
            primary_source="kbs",
            fallback_sources=[],
            description="Nến OHLCV chứng quyền có bảo đảm qua Market.warrant",
        ),
        "market.warrant_quote": CapabilityInfo(
            module="Market",
            action="warrant().quote()",
            status=CapabilityStatus.AVAILABLE,
            primary_source="kbs",
            fallback_sources=[],
            description="Bảng giá chứng quyền qua Market.warrant",
        ),
        "market.warrant_trades": CapabilityInfo(
            module="Market",
            action="warrant().trades()",
            status=CapabilityStatus.AVAILABLE,
            primary_source="kbs",
            fallback_sources=[],
            description="Khớp lệnh chi tiết chứng quyền trong ngày",
        ),
        "market.etf_ohlcv": CapabilityInfo(
            module="Market",
            action="etf().ohlcv()",
            status=CapabilityStatus.AVAILABLE,
            primary_source="kbs",
            fallback_sources=[],
            description="Nến OHLCV chứng chỉ quỹ ETF qua Market.etf",
        ),
        "market.etf_quote": CapabilityInfo(
            module="Market",
            action="etf().quote()",
            status=CapabilityStatus.AVAILABLE,
            primary_source="kbs",
            fallback_sources=[],
            description="Bảng giá chứng chỉ quỹ ETF",
        ),
        "market.etf_trades": CapabilityInfo(
            module="Market",
            action="etf().trades()",
            status=CapabilityStatus.AVAILABLE,
            primary_source="kbs",
            fallback_sources=[],
            description="Khớp lệnh chi tiết chứng chỉ quỹ ETF",
        ),
        "market.fund_nav": CapabilityInfo(
            module="Market",
            action="fund().nav()",
            status=CapabilityStatus.AVAILABLE,
            primary_source="fmarket",
            fallback_sources=[],
            description="Giá trị tài sản ròng NAV của quỹ mở qua Market.fund",
        ),
        "market.fund_history": CapabilityInfo(
            module="Market",
            action="fund().history()",
            status=CapabilityStatus.AVAILABLE,
            primary_source="fmarket",
            fallback_sources=[],
            description="Lịch sử giá NAV quỹ mở qua Market.fund",
        ),
        "market.fund_top_holding": CapabilityInfo(
            module="Market",
            action="fund().top_holding()",
            status=CapabilityStatus.AVAILABLE,
            primary_source="fmarket",
            fallback_sources=[],
            description="Danh mục top cổ phiếu nắm giữ của quỹ mở qua Market.fund",
        ),
        "market.fund_asset_holding": CapabilityInfo(
            module="Market",
            action="fund().asset_holding()",
            status=CapabilityStatus.AVAILABLE,
            primary_source="fmarket",
            fallback_sources=[],
            description="Cơ cấu phân bổ tài sản của quỹ mở qua Market.fund",
        ),
        "market.fund_industry_holding": CapabilityInfo(
            module="Market",
            action="fund().industry_holding()",
            status=CapabilityStatus.AVAILABLE,
            primary_source="fmarket",
            fallback_sources=[],
            description="Cơ cấu phân bổ ngành của quỹ mở qua Market.fund",
        ),
        "market.forex_ohlcv": CapabilityInfo(
            module="Market",
            action="forex().ohlcv()",
            status=CapabilityStatus.AVAILABLE,
            primary_source="msn",
            fallback_sources=[],
            description="Tỷ giá ngoại hối nến OHLCV qua Market.forex",
        ),
        "market.crypto_ohlcv": CapabilityInfo(
            module="Market",
            action="crypto().ohlcv()",
            status=CapabilityStatus.AVAILABLE,
            primary_source="msn",
            fallback_sources=[],
            description="Giá tiền điện tử nến OHLCV qua Market.crypto",
        ),
        "market.commodity_ohlcv": CapabilityInfo(
            module="Market",
            action="commodity().ohlcv()",
            status=CapabilityStatus.AVAILABLE,
            primary_source="msn",
            fallback_sources=[],
            description="Giá hàng hóa quốc tế nến OHLCV qua Market.commodity",
        ),
        "market.bond_ohlcv": CapabilityInfo(
            module="Market",
            action="bond().ohlcv()",
            status=CapabilityStatus.AVAILABLE,
            primary_source="kbs",
            fallback_sources=[],
            description="Nến giá giao dịch trái phiếu qua Market.bond",
        ),
        "market.bond_quote": CapabilityInfo(
            module="Market",
            action="bond().quote()",
            status=CapabilityStatus.AVAILABLE,
            primary_source="kbs",
            fallback_sources=[],
            description="Bảng giá trái phiếu qua Market.bond",
        ),
        "market.bond_trades": CapabilityInfo(
            module="Market",
            action="bond().trades()",
            status=CapabilityStatus.AVAILABLE,
            primary_source="kbs",
            fallback_sources=[],
            description="Khớp lệnh trái phiếu chi tiết trong ngày",
        ),
        # 7. Reference Module (Đầy đủ theo chuẩn v4.0.6)
        "reference.equity_list": CapabilityInfo(
            module="Reference",
            action="equity().list()",
            status=CapabilityStatus.AVAILABLE,
            primary_source="kbs",
            fallback_sources=[],
            description="Liệt kê toàn bộ mã cổ phiếu niêm yết qua Reference.equity",
        ),
        "reference.equity_list_by_industry": CapabilityInfo(
            module="Reference",
            action="equity().list_by_industry()",
            status=CapabilityStatus.AVAILABLE,
            primary_source="kbs",
            fallback_sources=["vci"],
            description="Liệt kê cổ phiếu theo ngành (chuẩn ICB) qua Reference.equity",
        ),
        "reference.equity_list_by_exchange": CapabilityInfo(
            module="Reference",
            action="equity().list_by_exchange()",
            status=CapabilityStatus.AVAILABLE,
            primary_source="kbs",
            fallback_sources=[],
            description="Liệt kê cổ phiếu theo sàn (HOSE, HNX, UPCOM) qua Reference.equity",
        ),
        "reference.equity_list_by_group": CapabilityInfo(
            module="Reference",
            action="equity().list_by_group()",
            status=CapabilityStatus.AVAILABLE,
            primary_source="kbs",
            fallback_sources=[],
            description="Liệt kê cổ phiếu theo nhóm chỉ số/sàn (VN30,...) qua Reference.equity",
        ),
        "reference.index_list": CapabilityInfo(
            module="Reference",
            action="index().list()",
            status=CapabilityStatus.AVAILABLE,
            primary_source="kbs",
            fallback_sources=[],
            description="Danh sách tất cả các chỉ số qua Reference.index",
        ),
        "reference.index_groups": CapabilityInfo(
            module="Reference",
            action="index().groups()",
            status=CapabilityStatus.AVAILABLE,
            primary_source="kbs",
            fallback_sources=[],
            description="Danh sách các nhóm chỉ số hỗ trợ qua Reference.index",
        ),
        "reference.index_members": CapabilityInfo(
            module="Reference",
            action="index().members()",
            status=CapabilityStatus.AVAILABLE,
            primary_source="kbs",
            fallback_sources=[],
            description="Danh sách các mã thành phần trong rổ chỉ số qua Reference.index",
        ),
        "reference.company_info": CapabilityInfo(
            module="Reference",
            action="company().info()",
            status=CapabilityStatus.AVAILABLE,
            primary_source="kbs",
            fallback_sources=[],
            description="Tổng quan về doanh nghiệp (ngành, vốn hóa...) qua Reference.company",
        ),
        "reference.company_shareholders": CapabilityInfo(
            module="Reference",
            action="company().shareholders()",
            status=CapabilityStatus.AVAILABLE,
            primary_source="kbs",
            fallback_sources=[],
            description="Danh sách cổ đông lớn qua Reference.company",
        ),
        "reference.company_officers": CapabilityInfo(
            module="Reference",
            action="company().officers()",
            status=CapabilityStatus.AVAILABLE,
            primary_source="kbs",
            fallback_sources=[],
            description="Ban lãnh đạo công ty qua Reference.company",
        ),
        "reference.company_subsidiaries": CapabilityInfo(
            module="Reference",
            action="company().subsidiaries()",
            status=CapabilityStatus.AVAILABLE,
            primary_source="kbs",
            fallback_sources=[],
            description="Các công ty con, công ty liên kết qua Reference.company",
        ),
        "reference.company_ownership": CapabilityInfo(
            module="Reference",
            action="company().ownership()",
            status=CapabilityStatus.AVAILABLE,
            primary_source="kbs",
            fallback_sources=[],
            description="Cơ cấu sở hữu doanh nghiệp qua Reference.company",
        ),
        "reference.company_insider_trading": CapabilityInfo(
            module="Reference",
            action="company().insider_trading()",
            status=CapabilityStatus.AVAILABLE,
            primary_source="kbs",
            fallback_sources=[],
            description="Lịch sử giao dịch nội bộ qua Reference.company",
        ),
        "reference.company_capital_history": CapabilityInfo(
            module="Reference",
            action="company().capital_history()",
            status=CapabilityStatus.AVAILABLE,
            primary_source="kbs",
            fallback_sources=[],
            description="Lịch sử thay đổi vốn điều lệ qua Reference.company",
        ),
        "reference.company_news": CapabilityInfo(
            module="Reference",
            action="company().news()",
            status=CapabilityStatus.AVAILABLE,
            primary_source="kbs",
            fallback_sources=[],
            description="Tin tức liên quan đến doanh nghiệp qua Reference.company",
        ),
        "reference.company_events": CapabilityInfo(
            module="Reference",
            action="company().events()",
            status=CapabilityStatus.AVAILABLE,
            primary_source="kbs",
            fallback_sources=[],
            description="Sự kiện doanh nghiệp (cổ tức, ĐHCĐ...) qua Reference.company",
        ),
        "reference.etf_list": CapabilityInfo(
            module="Reference",
            action="etf().list()",
            status=CapabilityStatus.AVAILABLE,
            primary_source="kbs",
            fallback_sources=[],
            description="Danh sách các chứng chỉ quỹ ETF qua Reference.etf",
        ),
        "reference.futures_list": CapabilityInfo(
            module="Reference",
            action="futures().list()",
            status=CapabilityStatus.AVAILABLE,
            primary_source="kbs",
            fallback_sources=[],
            description="Danh sách hợp đồng tương lai phái sinh qua Reference.futures",
        ),
        "reference.warrant_list": CapabilityInfo(
            module="Reference",
            action="warrant().list()",
            status=CapabilityStatus.AVAILABLE,
            primary_source="kbs",
            fallback_sources=[],
            description="Danh sách chứng quyền có bảo đảm qua Reference.warrant",
        ),
        "reference.bond_list": CapabilityInfo(
            module="Reference",
            action="bond().list()",
            status=CapabilityStatus.AVAILABLE,
            primary_source="kbs",
            fallback_sources=[],
            description="Danh sách trái phiếu doanh nghiệp & chính phủ qua Reference.bond",
        ),
        "reference.fund_list": CapabilityInfo(
            module="Reference",
            action="fund().list()",
            status=CapabilityStatus.AVAILABLE,
            primary_source="fmarket",
            fallback_sources=[],
            description="Danh sách các quỹ mở qua Reference.fund",
        ),
        "reference.search_symbol": CapabilityInfo(
            module="Reference",
            action="search.symbol()",
            status=CapabilityStatus.AVAILABLE,
            primary_source="kbs",
            fallback_sources=[],
            description="Tìm kiếm mã chứng khoán theo từ khóa qua Reference.search",
        ),
        "reference.search_info": CapabilityInfo(
            module="Reference",
            action="search.info()",
            status=CapabilityStatus.AVAILABLE,
            primary_source="kbs",
            fallback_sources=[],
            description="Tìm kiếm thông tin chi tiết tài sản qua Reference.search",
        ),
        "reference.events_calendar": CapabilityInfo(
            module="Reference",
            action="events.calendar()",
            status=CapabilityStatus.AVAILABLE,
            primary_source="kbs",
            fallback_sources=[],
            description="Lịch sự kiện thị trường (cổ tức, ĐHCĐ, phát hành) qua Reference.events",
        ),
        "reference.industry_list": CapabilityInfo(
            module="Reference",
            action="industry.list()",
            status=CapabilityStatus.AVAILABLE,
            primary_source="kbs",
            fallback_sources=[],
            description="Danh mục phân loại ngành qua Reference.industry",
        ),
        "reference.market_status": CapabilityInfo(
            module="Reference",
            action="market.status()",
            status=CapabilityStatus.AVAILABLE,
            primary_source="kbs",
            fallback_sources=[],
            description="Trạng thái phiên giao dịch hiện tại qua Reference.market",
        ),
        "reference.show_api": CapabilityInfo(
            module="Reference",
            action="show_api()",
            status=CapabilityStatus.AVAILABLE,
            primary_source="vnstock",
            fallback_sources=[],
            description="Hiển thị cấu trúc cây API của vnstock",
        ),
        "reference.show_doc": CapabilityInfo(
            module="Reference",
            action="show_doc()",
            status=CapabilityStatus.AVAILABLE,
            primary_source="vnstock",
            fallback_sources=[],
            description="Hiển thị tài liệu hướng dẫn cú pháp hàm qua show_doc",
        ),
        # 8. Unverified & Unavailable Flows
        "flow.proprietary": CapabilityInfo(
            module="Flow",
            action="fetch_prop_flow()",
            status=CapabilityStatus.UNAVAILABLE,
            primary_source=None,
            fallback_sources=[],
            description="Dòng tiền tự doanh giao dịch hàng ngày",
            reason="Vnstock v4 Community tier không hỗ trợ endpoint tự doanh chính thức",
        ),
        "flow.market_breadth_ad": CapabilityInfo(
            module="Flow",
            action="market_breadth()",
            status=CapabilityStatus.UNAVAILABLE,
            primary_source=None,
            fallback_sources=[],
            description="Độ rộng thị trường Advance/Decline toàn thị trường",
            reason="Vnstock v4 không cung cấp feed thống kê Advance/Decline chính thức",
        ),
        # 8. Out-of-Scope Declarations
        "external.crypto": CapabilityInfo(
            module="External",
            action="crypto()",
            status=CapabilityStatus.OUT_OF_SCOPE,
            primary_source=None,
            fallback_sources=[],
            description="Thị trường tiền mã hóa",
            reason="Tài sản tiền mã hóa nằm ngoài phạm vi thị trường tài chính Việt Nam (AGENTS §1.1)",
        ),
        "external.global_commodities": CapabilityInfo(
            module="External",
            action="global_commodities()",
            status=CapabilityStatus.OUT_OF_SCOPE,
            primary_source=None,
            fallback_sources=[],
            description="Hàng hóa quốc tế (dầu thô, lúa mì, nông sản ngoại)",
            reason="Hàng hóa quốc tế ngoài phạm vi trọng tâm TTCK Việt Nam (AGENTS §1.1)",
        ),
    }

    @classmethod
    def check_availability(cls, key: str) -> DataAvailability:
        """Kiểm tra tính khả dụng và chính sách nguồn dữ liệu của một tính năng."""
        info = cls.CAPABILITIES.get(key)
        if info is None:
            return DataAvailability(
                status=CapabilityStatus.UNAVAILABLE,
                reason=f"Capability '{key}' is not registered in VnstockCapabilityRegistry",
            )

        supported: list[str] = []
        if info.primary_source:
            supported.append(info.primary_source)
        supported.extend(info.fallback_sources)

        return DataAvailability(
            status=info.status,
            reason=info.reason,
            supported_sources=supported,
        )

    @classmethod
    def is_available(cls, key: str) -> bool:
        info = cls.CAPABILITIES.get(key)
        return bool(info and info.status == CapabilityStatus.AVAILABLE)


class ProviderResponse(BaseModel):
    """Container chuẩn cho mọi kết quả trả về từ VnstockService kèm metadata kiểm toán."""

    data: Any
    actual_source: str
    is_fallback: bool = False
    latency_ms: float = 0.0
    availability: DataAvailability
