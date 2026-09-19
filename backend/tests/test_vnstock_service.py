"""Bộ kiểm thử đơn vị toàn diện cho VnstockService.

Kiểm tra:
- Khởi tạo và danh sách nguồn ưu tiên (fallback source orchestration)
- Phân hệ Tham chiếu (Reference: symbols, exchanges, industries, groups, indices, derivatives, funds, search)
- Phân hệ Hồ sơ Doanh nghiệp (Company: overview, shareholders, officers, subsidiaries, insider trading, capital history, news, events)
- Phân hệ Thị trường & Giao dịch (Market: price history, intraday, tick orderflow, market quote, index ohlcv, futures quote)
- Phân hệ Báo cáo Tài chính & Định giá (Fundamental: financials, ratios)
- Phân hệ Hàng hóa & Ngoại tệ (Retail: gold SJC/BTMC, exchange rate)
- Xử lý ngoại lệ VnstockServiceError khi tất cả các nguồn thất bại
"""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from app.services.rate_limit import RateLimiter
from app.services.vnstock_service import VnstockService, VnstockServiceError


@pytest.fixture
def mock_limiter():
    """Tạo bộ điều tiết tần suất giả lập không chờ độ trễ."""
    limiter = MagicMock(spec=RateLimiter)
    limiter.wait.return_value = None
    return limiter


@pytest.fixture
def service(mock_limiter):
    """Khởi tạo thể hiện VnstockService với cấu hình kiểm thử."""
    return VnstockService(
        source="vci",
        fallback_source="kbs",
        tertiary_source="msn",
        limiter=mock_limiter,
    )


# =============================================================================
# 1. KIỂM THỬ KHỞI TẠO VÀ ĐIỀU PHỐI NGUỒN
# =============================================================================


def test_sources_ordering_and_deduplication(mock_limiter):
    """Kiểm tra danh sách nguồn được chuẩn hóa, khử trùng lặp và sắp xếp theo ưu tiên."""
    svc = VnstockService(
        source="kbs",
        fallback_source="vci",
        tertiary_source="kbs",
        limiter=mock_limiter,
    )
    sources = svc.sources
    assert sources[0] == "kbs"
    assert sources[1] == "vci"
    assert "msn" in sources
    assert "dnse" in sources
    # Đảm bảo không có phần tử trùng lặp
    assert len(sources) == len(set(sources))


def test_get_valid_sources(service):
    """Kiểm tra bộ lọc nguồn hợp lệ theo từng adapter."""
    valid_quote = service._get_valid_sources(service.VALID_SOURCES_QUOTE)
    for s in valid_quote:
        assert s in service.VALID_SOURCES_QUOTE


# =============================================================================
# 2. KIỂM THỬ PHÂN HỆ THAM CHIẾU (REFERENCE)
# =============================================================================


@patch("app.services.vnstock_service.Listing")
def test_fetch_all_symbols_success(mock_listing_cls, service):
    """Kiểm tra tải toàn bộ danh sách mã cổ phiếu thành công."""
    mock_inst = MagicMock()
    mock_df = pd.DataFrame({"symbol": ["VNM", "FPT"], "exchange": ["HOSE", "HOSE"]})
    mock_inst.all_symbols.return_value = mock_df
    mock_listing_cls.return_value = mock_inst

    df = service.fetch_all_symbols()
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2
    assert "VNM" in df["symbol"].values


@patch("app.services.vnstock_service.Listing")
def test_fetch_all_symbols_all_fail(mock_listing_cls, service):
    """Kiểm tra ném ngoại lệ khi tất cả nguồn đều không tải được danh sách mã."""
    mock_inst = MagicMock()
    mock_inst.all_symbols.side_effect = RuntimeError("Mạng lỗi")
    mock_listing_cls.return_value = mock_inst

    with pytest.raises(VnstockServiceError, match="Không thể tải danh sách mã"):
        service.fetch_all_symbols()


@patch("app.services.vnstock_service.Listing")
def test_fetch_symbols_by_exchange(mock_listing_cls, service):
    """Kiểm tra lọc danh sách mã theo sàn niêm yết."""
    mock_inst = MagicMock()
    mock_df = pd.DataFrame(
        {
            "symbol": ["VNM", "SHB"],
            "exchange": ["HOSE", "HNX"],
        }
    )
    mock_inst.symbols_by_exchange.return_value = mock_df
    mock_listing_cls.return_value = mock_inst

    df_hose = service.fetch_symbols_by_exchange("HOSE")
    assert len(df_hose) == 1
    assert df_hose.iloc[0]["symbol"] == "VNM"


@patch("app.services.vnstock_service.Listing")
def test_fetch_symbols_by_industry(mock_listing_cls, service):
    """Kiểm tra lấy danh mục phân loại ngành."""
    mock_inst = MagicMock()
    mock_df = pd.DataFrame(
        {"symbol": ["VNM", "MSN"], "industry": ["Thực phẩm", "Tiêu dùng"]}
    )
    mock_inst.symbols_by_industries.return_value = mock_df
    mock_listing_cls.return_value = mock_inst

    df = service.fetch_symbols_by_industry()
    assert len(df) == 2


@patch("app.services.vnstock_service.Listing")
def test_fetch_group_symbols(mock_listing_cls, service):
    """Kiểm tra lấy danh sách thành viên rổ chỉ số VN30."""
    mock_inst = MagicMock()
    mock_inst.symbols_by_group.return_value = pd.Series(["VNM", "VCB", "FPT"])
    mock_listing_cls.return_value = mock_inst

    symbols = service.fetch_group_symbols("VN30")
    assert isinstance(symbols, list)
    assert symbols == ["VNM", "VCB", "FPT"]


@patch("app.services.vnstock_service.Reference")
def test_fetch_index_list(mock_ref_cls, service):
    """Kiểm tra lấy danh sách các chỉ số thị trường."""
    mock_ref = MagicMock()
    mock_ref.index.list.return_value = pd.DataFrame({"index_code": ["VNINDEX", "VN30"]})
    mock_ref_cls.return_value = mock_ref

    df = service.fetch_index_list()
    assert len(df) == 2
    assert "VNINDEX" in df["index_code"].values


@patch("app.services.vnstock_service.Listing")
def test_fetch_derivatives_list(mock_listing_cls, service):
    """Kiểm tra lấy danh sách hợp đồng phái sinh."""
    mock_inst = MagicMock()
    mock_inst.all_future_indices.return_value = pd.DataFrame(
        {"symbol": ["VN30F1M", "VN30F2M"]}
    )
    mock_listing_cls.return_value = mock_inst

    df = service.fetch_derivatives_list()
    assert len(df) == 2


@patch("app.services.vnstock_service.Reference")
def test_fetch_funds_list(mock_ref_cls, service):
    """Kiểm tra lấy danh sách quỹ mở FMarket và ETF."""
    mock_ref = MagicMock()
    mock_ref.fund.list.return_value = pd.DataFrame({"fund_code": ["VESAF", "DCDS"]})
    mock_ref_cls.return_value = mock_ref

    df = service.fetch_funds_list()
    assert len(df) == 2


@patch("app.services.vnstock_service.Reference")
def test_search_symbols(mock_ref_cls, service):
    """Kiểm tra tìm kiếm mã chứng khoán theo từ khóa."""
    mock_ref = MagicMock()
    mock_ref.search.symbol.return_value = pd.DataFrame(
        {"symbol": ["VNM"], "organ_name": ["Vinamilk"]}
    )
    mock_ref_cls.return_value = mock_ref

    df = service.search_symbols("Vinamilk", limit=5)
    assert len(df) == 1
    assert df.iloc[0]["symbol"] == "VNM"


# =============================================================================
# 3. KIỂM THỬ PHÂN HỆ HỒ SƠ DOANH NGHIỆP (COMPANY)
# =============================================================================


@patch("app.services.vnstock_service.Company")
def test_fetch_company_overview(mock_comp_cls, service):
    """Kiểm tra lấy thông tin tổng quan doanh nghiệp."""
    mock_inst = MagicMock()
    mock_inst.overview.return_value = pd.DataFrame(
        [{"symbol": "VNM", "industry": "Sữa", "market_cap": 150000}]
    )
    mock_comp_cls.return_value = mock_inst

    info = service.fetch_company_overview("VNM")
    assert isinstance(info, dict)
    assert info["symbol"] == "VNM"


@patch("app.services.vnstock_service.Company")
def test_fetch_company_details(mock_comp_cls, service):
    """Kiểm tra các phương thức chi tiết về doanh nghiệp."""
    mock_inst = MagicMock()
    mock_inst.shareholders.return_value = pd.DataFrame(
        {"name": ["SCIC"], "ratio": [0.36]}
    )
    mock_inst.officers.return_value = pd.DataFrame(
        {"name": ["Mai Kiều Liên"], "position": ["CEO"]}
    )
    mock_inst.subsidiaries.return_value = pd.DataFrame({"name": ["Công ty Bò sữa VN"]})
    mock_inst.insider_trading.return_value = pd.DataFrame({"trader": ["Nguyễn Văn A"]})
    mock_inst.capital_history.return_value = pd.DataFrame({"year": [2020]})
    mock_inst.news.return_value = pd.DataFrame({"title": ["Doanh thu tăng mạnh"]})
    mock_inst.events.return_value = pd.DataFrame({"event": ["Chi trả cổ tức"]})
    mock_comp_cls.return_value = mock_inst

    assert len(service.fetch_company_shareholders("VNM")) == 1
    assert len(service.fetch_company_officers("VNM")) == 1
    assert len(service.fetch_company_subsidiaries("VNM")) == 1
    assert len(service.fetch_company_insider_trading("VNM")) == 1
    assert len(service.fetch_company_capital_history("VNM")) == 1
    assert len(service.fetch_company_news("VNM")) == 1
    assert len(service.fetch_company_events("VNM")) == 1


# =============================================================================
# 4. KIỂM THỬ PHÂN HỆ THỊ TRƯỜNG & GIAO DỊCH (MARKET)
# =============================================================================


@patch("app.services.vnstock_service.Quote")
def test_fetch_price_history_with_count(mock_quote_cls, service):
    """Kiểm tra tải nến lịch sử hỗ trợ tham số count."""
    mock_inst = MagicMock()
    mock_inst.history.return_value = pd.DataFrame(
        {
            "time": ["2026-09-18", "2026-09-19"],
            "open": [60.0, 61.0],
            "high": [61.5, 62.0],
            "low": [59.8, 60.5],
            "close": [61.0, 61.8],
            "volume": [1000000, 1200000],
        }
    )
    mock_quote_cls.return_value = mock_inst

    df = service.fetch_price_history("VNM", count=50, interval="1D")
    assert len(df) == 2
    mock_inst.history.assert_called_once_with(interval="1D", count_back=50)


@patch("app.services.vnstock_service.Quote")
def test_fetch_intraday(mock_quote_cls, service):
    """Kiểm tra tải nến intraday."""
    mock_inst = MagicMock()
    mock_inst.history.return_value = pd.DataFrame(
        {"time": ["09:15:00"], "close": [60.5]}
    )
    mock_quote_cls.return_value = mock_inst

    df = service.fetch_intraday("VNM", interval="1m", count_back=100)
    assert len(df) == 1


@patch("app.services.vnstock_service.Quote")
def test_fetch_tick_orderflow(mock_quote_cls, service):
    """Kiểm tra tải sổ lệnh khớp lệnh tick."""
    mock_inst = MagicMock()
    mock_inst.intraday.return_value = pd.DataFrame(
        {
            "time": ["09:15:00", "09:15:02"],
            "price": [60.5, 60.6],
            "volume": [5000, 10000],
            "match_type": ["Buy", "Sell"],
        }
    )
    mock_quote_cls.return_value = mock_inst

    df = service.fetch_tick_orderflow("VNM", page_size=50)
    assert len(df) == 2


@patch("app.services.vnstock_service.Market")
def test_fetch_market_quote(mock_mkt_cls, service):
    """Kiểm tra tải bảng giá snapshot realtime."""
    mock_mkt = MagicMock()
    mock_mkt.quote.return_value = pd.DataFrame(
        {
            "symbol": ["VNM"],
            "price": [61.2],
            "ceiling_price": [64.0],
            "floor_price": [56.0],
            "bid_price_1": [61.1],
            "ask_price_1": [61.3],
        }
    )
    mock_mkt_cls.return_value = mock_mkt

    df = service.fetch_market_quote("VNM")
    assert len(df) == 1
    assert df.iloc[0]["price"] == 61.2


@patch("app.services.vnstock_service.Market")
def test_fetch_index_ohlcv(mock_mkt_cls, service):
    """Kiểm tra tải nến chỉ số thị trường."""
    mock_mkt = MagicMock()
    mock_mkt.index.return_value.ohlcv.return_value = pd.DataFrame(
        {
            "time": ["2026-09-18"],
            "close": [1815.66],
        }
    )
    mock_mkt_cls.return_value = mock_mkt

    df = service.fetch_index_ohlcv("VNINDEX", count=10)
    assert len(df) == 1
    assert df.iloc[0]["close"] == 1815.66


@patch("app.services.vnstock_service.Market")
def test_fetch_futures_quote(mock_mkt_cls, service):
    """Kiểm tra tải bảng giá phái sinh kèm Open Interest (OI)."""
    mock_mkt = MagicMock()
    mock_mkt.futures.return_value.quote.return_value = pd.DataFrame(
        {
            "symbol": ["VN30F1M"],
            "price": [1900.5],
            "open_interest": [24816],
        }
    )
    mock_mkt_cls.return_value = mock_mkt

    df = service.fetch_futures_quote("VN30F1M")
    assert len(df) == 1
    assert df.iloc[0]["open_interest"] == 24816


# =============================================================================
# 5. KIỂM THỬ PHÂN HỆ BÁO CÁO TÀI CHÍNH & CHỈ SỐ (FUNDAMENTAL)
# =============================================================================


@patch("app.services.vnstock_service.Fundamental")
def test_fetch_financials_via_fundamental(mock_fnd_cls, service):
    """Kiểm tra tải BCTC qua lớp Fundamental hỗ trợ định dạng orient."""
    mock_fnd = MagicMock()
    mock_equity = MagicMock()
    mock_equity.income_statement.return_value = pd.DataFrame(
        {
            "item": ["Doanh thu thuần", "Lợi nhuận sau thuế"],
            "2026-Q1": [15000, 2500],
        }
    )
    mock_fnd.equity.return_value = mock_equity
    mock_fnd_cls.return_value = mock_fnd

    df = service.fetch_financials(
        "VNM", report_type="income_statement", period="quarter", orient="report"
    )
    assert len(df) == 2


@patch("app.services.vnstock_service.Fundamental")
def test_fetch_financial_ratios(mock_fnd_cls, service):
    """Kiểm tra tải bộ 58 chỉ số tài chính định lượng."""
    mock_fnd = MagicMock()
    mock_equity = MagicMock()
    mock_equity.ratio.return_value = pd.DataFrame(
        {
            "ratio_name": ["P/E", "P/B", "ROE"],
            "value": [15.2, 2.5, 0.28],
        }
    )
    mock_fnd.equity.return_value = mock_equity
    mock_fnd_cls.return_value = mock_fnd

    df = service.fetch_financial_ratios("VNM", orient="report")
    assert len(df) == 3


# =============================================================================
# 6. KIỂM THỬ PHÂN HỆ HÀNG HÓA & NGOẠI TỆ (RETAIL)
# =============================================================================


@patch("app.services.vnstock_service.Retail")
def test_fetch_gold_prices_sjc_and_btmc(mock_retail_cls, service):
    """Kiểm tra tải giá vàng hỗ trợ cả SJC và Bảo Tín Minh Châu (BTMC)."""
    mock_retail = MagicMock()
    mock_retail.gold.return_value = pd.DataFrame(
        {
            "name": ["Vàng SJC 1L"],
            "buy_price": [80.5],
            "sell_price": [82.5],
        }
    )
    mock_retail_cls.return_value = mock_retail

    df_sjc = service.fetch_gold_prices(source="sjc")
    assert len(df_sjc) == 1
    mock_retail.gold.assert_called_with(source="sjc", date=None)

    df_btmc = service.fetch_gold_prices(source="btmc", date_str="2026-09-18")
    assert len(df_btmc) == 1
    mock_retail.gold.assert_called_with(source="btmc", date="2026-09-18")


@patch("app.services.vnstock_service.Retail")
def test_fetch_exchange_rate(mock_retail_cls, service):
    """Kiểm tra tải tỷ giá Vietcombank."""
    mock_retail = MagicMock()
    mock_retail.exchange_rate.return_value = pd.DataFrame(
        {
            "currency_code": ["USD"],
            "buy_transfer": [25400],
            "sell": [25450],
        }
    )
    mock_retail_cls.return_value = mock_retail

    df = service.fetch_exchange_rate(date_str="2026-09-18")
    assert len(df) == 1
    assert df.iloc[0]["currency_code"] == "USD"
