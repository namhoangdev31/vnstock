"""Unit & Regression Test Suite for IBoardService (Bảng giá v2).

Đảm bảo:
- Cấu trúc module hoá sạch sẽ, ngăn ngừa lỗi tái phát khi cập nhật về sau.
- Chuẩn hoá đơn vị giá: Cổ phiếu hiển thị đơn vị nghìn đồng (thang 1/1000), phái sinh giữ nguyên điểm số (1.0).
- Chuỗi nến 100 phiên có thứ tự thời gian tăng dần (chronological), khớp chuẩn định dạng biểu đồ kỹ thuật TradingView của DNSE.
- Không tồn tại số giả lập (Rule 3) và tuân thủ Database-First (Rule 7.2).
"""

from datetime import date, timedelta

import pytest
from sqlmodel import Session, SQLModel, create_engine

from app.domains.market_data.application.iboard_schemas import (
    IBoardCandleBar,
    IBoardMarketPulse,
    IBoardStockDetail,
    IBoardStockRow,
)
from app.domains.market_data.application.iboard_service import (
    IBoardService,
    _build_order_book,
    _eod_price_block,
    _live_price_block,
    _price_status,
    _safe_num,
)
from app.domains.market_data.domain.models import (
    DerivativeContract,
    StockOHLCVDaily,
    StockSymbol,
)


@pytest.fixture
def memory_session():
    """In-memory SQLite session isolated for testing IBoardService."""
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


# ---------------------------------------------------------------------------
# 1. Pure Helper Unit Tests
# ---------------------------------------------------------------------------


def test_safe_num_conversion():
    """Kiểm tra helper _safe_num xử lý an toàn các kiểu dữ liệu."""
    assert _safe_num(100) == 100.0
    assert _safe_num("62.5") == 62.5
    assert _safe_num(None) == 0.0
    assert _safe_num("invalid") == 0.0
    assert _safe_num({}) == 0.0


def test_price_status_classification():
    """Kiểm tra phân loại trạng thái giá: ceiling, floor, up, down, ref."""
    assert _price_status(67.0, ceil_p=67.0, flr_p=58.4, chg=4.3) == "ceiling"
    assert _price_status(58.4, ceil_p=67.0, flr_p=58.4, chg=-4.3) == "floor"
    assert _price_status(63.5, ceil_p=67.0, flr_p=58.4, chg=0.8) == "up"
    assert _price_status(61.0, ceil_p=67.0, flr_p=58.4, chg=-1.7) == "down"
    assert _price_status(62.7, ceil_p=67.0, flr_p=58.4, chg=0.0) == "ref"


def test_build_order_book_unit_scaling():
    """Kiểm tra trích xuất sổ lệnh 3 cấp và chuẩn hoá thang giá nghìn đồng vs điểm số."""
    # Giả lập dữ liệu live quote của cổ phiếu (VND nguyên tệ)
    stock_quote = {
        "bid_price_1": "62100.0",
        "bid_vol_1": 105100,
        "bid_price_2": 62000,
        "bid_vol_2": 309100,
        "bid_price_3": 61900,
        "bid_vol_3": 10400,
    }
    bids_stock = _build_order_book(stock_quote, side="bid", scale=0.001)
    assert len(bids_stock) == 3
    assert bids_stock[0].price == 62.1
    assert bids_stock[0].volume == 105100
    assert bids_stock[1].price == 62.0
    assert bids_stock[2].price == 61.9

    # Giả lập phái sinh (điểm số)
    deriv_quote = {
        "ask_price_1": "1885.0",
        "ask_vol_1": 831,
        "ask_price_2": 1885.1,
        "ask_vol_2": 5,
        "ask_price_3": 0.0,  # Không có cấp 3
        "ask_vol_3": 0,
    }
    asks_deriv = _build_order_book(deriv_quote, side="ask", scale=1.0)
    assert len(asks_deriv) == 2
    assert asks_deriv[0].price == 1885.0
    assert asks_deriv[0].volume == 831
    assert asks_deriv[1].price == 1885.1


def test_live_price_block_stock_scaling():
    """Kiểm tra _live_price_block tự động chia 1000 cho cổ phiếu khi raw_price >= 1000."""
    raw_stock_quote = {
        "close_price": 62100,
        "reference_price": 62700,
        "ceiling_price": 67000,
        "floor_price": 58400,
        "high_price": 63200,
        "low_price": 62100,
        "price_change": -600,
        "percent_change": -0.9569,
        "volume_accumulated": 3199600,
        "total_value": 200301440000,
        "bid_price_1": "62100",
        "bid_vol_1": 1000,
        "ask_price_1": "62200",
        "ask_vol_1": 2000,
        "foreign_buy_volume": 474146,
        "foreign_sell_volume": 522297,
        "foreign_room": 351900724,
    }
    blk = _live_price_block(raw_stock_quote, is_derivatives=False)
    assert blk["last_p"] == 62.1
    assert blk["ref_p"] == 62.7
    assert blk["ceil_p"] == 67.0
    assert blk["flr_p"] == 58.4
    assert blk["high_p"] == 63.2
    assert blk["low_p"] == 62.1
    assert blk["chg"] == -0.6
    assert blk["pct"] == -0.96
    assert blk["vol"] == 3199600
    assert blk["val_bil"] == 200.3
    assert len(blk["bid_book"]) == 1
    assert blk["bid_book"][0].price == 62.1


def test_live_price_block_derivatives_retention():
    """Kiểm tra _live_price_block giữ nguyên thang điểm số cho phái sinh VN30F1M."""
    raw_deriv_quote = {
        "close_price": 1885.0,
        "reference_price": 1895.0,
        "ceiling_price": 2027.6,
        "floor_price": 1762.4,
        "high_price": 1899.4,
        "low_price": 1874.8,
        "price_change": -10.0,
        "percent_change": -0.53,
        "volume_accumulated": 253004,
        "total_value": 47738996360000,
        "bid_price_1": "1884.7",
        "bid_vol_1": 108,
        "ask_price_1": "1885.0",
        "ask_vol_1": 831,
        "foreign_buy_volume": 7360,
        "foreign_sell_volume": 7284,
        "foreign_room": 0,
    }
    blk = _live_price_block(raw_deriv_quote, is_derivatives=True)
    assert blk["last_p"] == 1885.0
    assert blk["ref_p"] == 1895.0
    assert blk["ceil_p"] == 2027.6
    assert blk["flr_p"] == 1762.4
    assert blk["chg"] == -10.0
    assert blk["vol"] == 253004


def test_eod_price_block_calculation():
    """Kiểm tra tính toán eod block từ các bản ghi lịch sử StockOHLCVDaily."""
    t_today = date(2026, 10, 2)
    t_prev = date(2026, 10, 1)
    bar1 = StockOHLCVDaily(
        symbol="FPT",
        trading_date=t_today,
        open=62.7,
        high=63.2,
        low=62.1,
        close=62.1,
        volume=3199600,
        value=200301440000,
        buy_volume=1600000,
        sell_volume=1599600,
        source="vci",
    )
    bar2 = StockOHLCVDaily(
        symbol="FPT",
        trading_date=t_prev,
        open=63.0,
        high=63.1,
        low=62.6,
        close=62.7,
        volume=3434926,
        source="vci",
    )
    blk = _eod_price_block([bar1, bar2], exchange="HOSE")
    assert blk["last_p"] == 62.1
    assert blk["ref_p"] == 62.7
    assert blk["chg"] == -0.6
    assert blk["ceil_p"] == round(62.7 * 1.07, 2)
    assert blk["flr_p"] == round(62.7 * 0.93, 2)
    assert blk["vol"] == 3199600
    assert blk["buy_r"] == 50
    assert blk["sell_r"] == 50


# ---------------------------------------------------------------------------
# 2. IBoardService Integration & Candle/Chart Tests (Matching DNSE Standards)
# ---------------------------------------------------------------------------


def test_get_candles_chronological_and_limit(memory_session: Session):
    """Kiểm tra get_candles đảm bảo thứ tự tăng dần thời gian (tương thích TradingView/DNSE)."""
    base_date = date(2026, 6, 1)
    for i in range(120):
        t_date = base_date + timedelta(days=i)
        memory_session.add(
            StockOHLCVDaily(
                symbol="FPT",
                trading_date=t_date,
                open=60.0 + (i * 0.1),
                high=61.0 + (i * 0.1),
                low=59.5 + (i * 0.1),
                close=60.5 + (i * 0.1),
                volume=1000000 + (i * 1000),
                source="vci",
            )
        )
    memory_session.commit()

    candles = IBoardService.get_candles(
        session=memory_session, symbol="FPT", timeframe="1D", limit=100
    )
    assert len(candles) == 100
    assert isinstance(candles[0], IBoardCandleBar)

    # Đảm bảo thứ tự thời gian tăng dần từ quá khứ đến hiện tại (chronological order)
    for idx in range(len(candles) - 1):
        assert candles[idx].time < candles[idx + 1].time

    # Nến mới nhất là nến ở cuối mảng
    last_candle = candles[-1]
    assert last_candle.time == str(base_date + timedelta(days=119))


def test_get_board_listed_and_derivatives(memory_session: Session):
    """Kiểm tra get_board cho cả hai nhóm cổ phiếu niêm yết và phái sinh."""
    # 1. Thêm symbol và nến cho FPT
    fpt_sym = StockSymbol(
        symbol="FPT",
        organ_name="Công ty Cổ phần FPT",
        exchange="HOSE",
        asset_type="stock",
        index_group="VN30",
        industry="Công nghệ Thông tin",
    )
    memory_session.add(fpt_sym)
    memory_session.add(
        StockOHLCVDaily(
            symbol="FPT",
            trading_date=date(2026, 10, 2),
            open=62.7,
            high=63.2,
            low=62.1,
            close=62.1,
            volume=3199600,
            source="vci",
        )
    )

    # 2. Thêm hợp đồng phái sinh VN30F1M
    f1m = DerivativeContract(
        symbol="VN30F1M",
        underlying_symbol="VN30",
        contract_type="futures",
        multiplier=100000,
        expiration_date=date(2026, 10, 15),
        is_active=True,
    )
    memory_session.add(f1m)
    memory_session.add(
        StockOHLCVDaily(
            symbol="VN30F1M",
            trading_date=date(2026, 10, 2),
            open=1897.0,
            high=1899.4,
            low=1874.8,
            close=1885.0,
            volume=253004,
            source="vci",
        )
    )
    memory_session.commit()

    # Query listed board
    board_listed = IBoardService.get_board(
        session=memory_session, category="listed", group="VN30"
    )
    assert len(board_listed) >= 1
    fpt_row = next((r for r in board_listed if r.symbol == "FPT"), None)
    assert fpt_row is not None
    assert isinstance(fpt_row, IBoardStockRow)
    assert fpt_row.last_price == 62.1
    assert fpt_row.category == "listed"

    # Query derivatives board
    board_deriv = IBoardService.get_board(
        session=memory_session, category="derivatives"
    )
    assert len(board_deriv) >= 1
    f1m_row = next((r for r in board_deriv if r.symbol == "VN30F1M"), None)
    assert f1m_row is not None
    assert f1m_row.last_price == 1885.0
    assert f1m_row.category == "derivatives"


def test_get_stock_detail(memory_session: Session):
    """Kiểm tra get_stock_detail trả về đầy đủ các trường DTO hợp lệ."""
    fpt_sym = StockSymbol(
        symbol="FPT",
        organ_name="Công ty Cổ phần FPT",
        exchange="HOSE",
        asset_type="stock",
        index_group="VN30",
    )
    memory_session.add(fpt_sym)
    memory_session.add(
        StockOHLCVDaily(
            symbol="FPT",
            trading_date=date(2026, 10, 2),
            open=62.7,
            high=63.2,
            low=62.1,
            close=62.1,
            volume=3199600,
            source="vci",
        )
    )
    memory_session.commit()

    detail = IBoardService.get_stock_detail(
        session=memory_session, symbol="FPT", timeframe="1D"
    )
    assert isinstance(detail, IBoardStockDetail)
    assert detail.stock.symbol == "FPT"
    assert detail.stock.last_price == 62.1
    assert isinstance(detail.candles, list)
    assert isinstance(detail.matched_ticks, list)
    assert detail.overview is not None


def test_get_market_pulse(memory_session: Session):
    """Kiểm tra get_market_pulse tạo nhận định insight động không hardcode."""
    memory_session.add(
        StockOHLCVDaily(
            symbol="VNINDEX",
            trading_date=date(2026, 10, 2),
            open=1740.0,
            high=1750.0,
            low=1735.0,
            close=1737.71,
            volume=829390000,
            source="vci",
        )
    )
    memory_session.add(
        StockOHLCVDaily(
            symbol="VNINDEX",
            trading_date=date(2026, 10, 1),
            open=1745.0,
            high=1752.0,
            low=1742.0,
            close=1749.30,
            volume=810000000,
            source="vci",
        )
    )
    memory_session.commit()

    pulse = IBoardService.get_market_pulse(session=memory_session)
    assert isinstance(pulse, IBoardMarketPulse)
    assert "1,737.71" in pulse.ai_insight
    assert "829.39" in pulse.ai_insight
    assert isinstance(pulse.top_gainers, list)
    assert isinstance(pulse.top_losers, list)
