"""Unit tests for DNSE WebSocket TickNormalizer (Rule 3 compliant)."""

from __future__ import annotations

from unittest.mock import MagicMock

from dnse.websocket.models import ExpectedPrice, Ohlc, PriceLevel, Quote, Trade

from app.core.cache import realtime_cache
from app.domains.dnse.tick_handler import TickNormalizer


def test_on_trade_sets_realtime_cache():
    normalizer = TickNormalizer()
    trade = Trade(
        marketId="HOSE",
        boardId="G1",
        isin="VN000000FPT0",
        symbol="FPT",
        price=62.5,
        quantity=5000,
        totalVolumeTraded=3500000,
        grossTradeAmount=218750000.0,
        highestPrice=63.0,
        lowestPrice=61.8,
        openPrice=62.0,
        tradingSessionId=1,
        time="2026-10-05 14:15:00.000",
    )

    normalizer.on_trade(trade)

    cached = realtime_cache.get("realtime:FPT")
    assert cached is not None
    assert cached["symbol"] == "FPT"
    assert cached["close"] == 62.5
    assert cached["open"] == 62.0
    assert cached["high"] == 63.0
    assert cached["low"] == 61.8
    assert cached["volume"] == 3500000
    assert cached["time"] == "2026-10-05 14:15:00.000"
    assert cached["source"] == "dnse_ws"


def test_on_trade_empty_symbol_ignored():
    normalizer = TickNormalizer()
    trade = MagicMock()
    trade.symbol = None

    normalizer.on_trade(trade)
    # Shouldn't raise and shouldn't set cache for None
    assert realtime_cache.get("realtime:NONE") is None


def test_on_quote_sets_quote_cache():
    normalizer = TickNormalizer()
    quote = Quote(
        marketId="HOSE",
        boardId="G1",
        symbol="VN30F1M",
        isin="",
        bid=[PriceLevel(price=1880.0, quantity=50)],
        offer=[PriceLevel(price=1880.5, quantity=70)],
        totalOfferQtty=500.0,
        totalBidQtty=400.0,
        time="2026-10-05 14:15:01.000",
    )

    normalizer.on_quote(quote)

    cached = realtime_cache.get("quote:VN30F1M")
    assert cached is not None
    assert cached["symbol"] == "VN30F1M"
    assert cached["bid"] == 1880.0
    assert cached["bid_vol"] == 50
    assert cached["ask"] == 1880.5
    assert cached["ask_vol"] == 70
    assert cached["spread"] == 0.5
    assert cached["source"] == "dnse_ws_quote"


def test_on_market_index_sets_index_cache():
    normalizer = TickNormalizer()
    idx = MagicMock()
    idx.indexName = "VNINDEX"
    idx.valueIndexes = 1285.5
    idx.changedValue = 4.2
    idx.changedRatio = 0.33
    idx.fluctuationUpIssueCount = 210
    idx.fluctuationDownIssueCount = 145
    idx.fluctuationSteadinessIssueCount = 60
    idx.totalVolumeTraded = 750000000
    idx.grossTradeAmount = 18500000000.0
    idx.transactTime = "2026-10-05 14:20:00"

    normalizer.on_market_index(idx)

    cached = realtime_cache.get("index:VNINDEX")
    assert cached is not None
    assert cached["index"] == "VNINDEX"
    assert cached["value"] == 1285.5
    assert cached["change"] == 4.2
    assert cached["pct_change"] == 0.33
    assert cached["advance"] == 210
    assert cached["decline"] == 145
    assert cached["no_change"] == 60
    assert cached["total_volume"] == 750000000
    assert cached["source"] == "dnse_ws"


def test_on_foreign_sets_foreign_cache():
    normalizer = TickNormalizer()
    fi = MagicMock()
    fi.symbol = "HPG"
    fi.buyVolume = 1200000
    fi.sellVolume = 800000
    fi.buyTradedAmount = 36000000
    fi.sellTradedAmount = 24000000
    fi.totalBuyVolume = 2500000
    fi.totalSellVolume = 1800000
    fi.transactTime = "2026-10-05 14:25:00"

    normalizer.on_foreign(fi)

    cached = realtime_cache.get("foreign:HPG")
    assert cached is not None
    assert cached["symbol"] == "HPG"
    assert cached["buy_volume"] == 1200000
    assert cached["sell_volume"] == 800000
    assert cached["source"] == "dnse_ws"


def test_on_ohlc_sets_ohlc_and_realtime():
    normalizer = TickNormalizer()
    ohlc = Ohlc(
        symbol="FPT",
        resolution="1",
        open=62.0,
        high=62.8,
        low=61.9,
        close=62.6,
        volume=25000,
        time=1728114600,
        lastUpdated=1728114660,
        type="stock",
    )

    normalizer.on_ohlc(ohlc)

    cached_ohlc = realtime_cache.get("ohlc:1:FPT")
    assert cached_ohlc is not None
    assert cached_ohlc["close"] == 62.6
    assert cached_ohlc["resolution"] == "1"

    cached_rt = realtime_cache.get("realtime:FPT")
    assert cached_rt is not None
    assert cached_rt["close"] == 62.6


def test_on_expected_price_sets_expected_price_cache():
    normalizer = TickNormalizer()
    ep = ExpectedPrice(
        marketId="HOSE",
        boardId="G1",
        isin="",
        symbol="VN30F1M",
        closePrice=1880.0,
        expectedTradePrice=1883.5,
        expectedTradeQuantity=1250,
        time="2026-10-05 14:40:00",
    )

    normalizer.on_expected_price(ep)

    cached = realtime_cache.get("expected_price:VN30F1M")
    assert cached is not None
    assert cached["expected_price"] == 1883.5
    assert cached["expected_volume"] == 1250
    assert cached["close_price"] == 1880.0
    assert cached["source"] == "dnse_ws_expected_price"


def test_no_hardcoded_defaults_on_missing_values():
    """Verify Rule 3: None values are preserved as None, never fabricated."""
    normalizer = TickNormalizer()
    trade = MagicMock()
    trade.symbol = "SSI"
    trade.openPrice = None
    trade.highestPrice = None
    trade.lowestPrice = None
    trade.price = None
    trade.totalVolumeTraded = None
    trade.time = None

    # Clear previous cache if any
    realtime_cache.invalidate("realtime:SSI")

    normalizer.on_trade(trade)

    cached = realtime_cache.get("realtime:SSI")
    assert cached is not None
    assert cached["open"] is None
    assert cached["high"] is None
    assert cached["low"] is None
    assert cached["close"] is None
