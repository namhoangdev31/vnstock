"""Unit & Integration tests for iBoard DNSE Real-time WebSocket and Caching pipeline."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.testclient import TestClient

from app.core.cache import realtime_cache
from app.domains.dnse.tick_handler import TickNormalizer
from app.domains.iboard.application.ws_manager import IBoardWSManager
from app.domains.iboard.infrastructure.external_indices import IBoardDataGateway
from app.main import app


@dataclass
class MockPriceLevel:
    price: float
    quantity: int


@dataclass
class MockDNSEQuote:
    symbol: str
    bid: list[MockPriceLevel]
    offer: list[MockPriceLevel]
    totalBidQtty: float = 150000.0
    totalOfferQtty: float = 120000.0
    time: str = "14:35:10"


@dataclass
class MockDNSETrade:
    symbol: str
    price: float
    quantity: int
    totalVolumeTraded: int
    grossTradeAmount: float
    highestPrice: float
    lowestPrice: float
    openPrice: float
    time: str = "14:35:10"
    side: int = 1


@dataclass
class MockDNSESecDef:
    symbol: str
    basicPrice: float
    ceilingPrice: float
    floorPrice: float


@dataclass
class MockDNSEMarketIndex:
    indexName: str
    valueIndexes: float
    changedValue: float
    changedRatio: float
    fluctuationUpIssueCount: int
    fluctuationDownIssueCount: int
    fluctuationSteadinessIssueCount: int
    fluctuationUpperLimitIssueCount: int = 5
    fluctuationLowerLimitIssueCount: int = 2
    totalVolumeTraded: int = 450000000
    grossTradeAmount: float = 12500000000000.0
    transactTime: str = "14:35:10"


def test_tick_normalizer_quote_and_trade():
    """Verify TickNormalizer properly computes 3-level orderbook, recent ticks, and iboard_quote."""
    normalizer = TickNormalizer()
    events_received: list[tuple[str, str, dict[str, Any]]] = []

    def mock_listener(evt: str, key: str, payload: dict[str, Any]):
        events_received.append((evt, key, payload))

    normalizer.add_listener(mock_listener)

    # 1. Test Security Definition (Reference prices)
    sec_def = MockDNSESecDef(
        symbol="HPG",
        basicPrice=28000.0,
        ceilingPrice=29950.0,
        floorPrice=26050.0,
    )
    normalizer.on_sec_def(sec_def)
    ib_quote = normalizer._get_or_create_iboard_quote("HPG")
    assert ib_quote["reference_price"] == 28000.0
    assert ib_quote["ceiling_price"] == 29950.0
    assert ib_quote["floor_price"] == 26050.0

    # 2. Test 3-Level Orderbook Quote
    quote = MockDNSEQuote(
        symbol="HPG",
        bid=[
            MockPriceLevel(price=28400.0, quantity=50000),
            MockPriceLevel(price=28350.0, quantity=70000),
            MockPriceLevel(price=28300.0, quantity=90000),
        ],
        offer=[
            MockPriceLevel(price=28450.0, quantity=40000),
            MockPriceLevel(price=28500.0, quantity=60000),
            MockPriceLevel(price=28550.0, quantity=80000),
        ],
    )
    normalizer.on_quote(quote)

    ib_quote = normalizer._get_or_create_iboard_quote("HPG")
    assert ib_quote["bid_price_1"] == 28400.0
    assert ib_quote["bid_vol_1"] == 50000
    assert ib_quote["bid_price_2"] == 28350.0
    assert ib_quote["bid_vol_2"] == 70000
    assert ib_quote["bid_price_3"] == 28300.0
    assert ib_quote["bid_vol_3"] == 90000
    assert ib_quote["ask_price_1"] == 28450.0
    assert ib_quote["ask_vol_1"] == 40000

    # 3. Test Matched Trade Tick and Recent Ticks Buffer
    trade = MockDNSETrade(
        symbol="HPG",
        price=28450.0,
        quantity=5000,
        totalVolumeTraded=12000000,
        grossTradeAmount=340000000000.0,
        highestPrice=28600.0,
        lowestPrice=28100.0,
        openPrice=28200.0,
        side=1,
    )
    normalizer.on_trade(trade)

    ib_quote = normalizer._get_or_create_iboard_quote("HPG")
    assert ib_quote["close_price"] == 28450.0
    assert ib_quote["price_change"] == 450.0
    assert ib_quote["percent_change"] == round(450.0 / 28000.0 * 100, 2)
    assert ib_quote["volume_accumulated"] == 12000000

    recent_ticks = normalizer.get_recent_ticks("HPG", limit=10)
    assert len(recent_ticks) == 1
    assert recent_ticks[0]["price"] == 28450.0
    assert recent_ticks[0]["volume"] == 5000
    assert recent_ticks[0]["side"] == "B"

    # Verify listeners notified
    event_types = [e[0] for e in events_received]
    assert "sec_def" in event_types
    assert "quote" in event_types
    assert "trade" in event_types


def test_tick_normalizer_market_index():
    """Verify MarketIndex tick normalization."""
    normalizer = TickNormalizer()
    idx = MockDNSEMarketIndex(
        indexName="VNINDEX",
        valueIndexes=1285.6,
        changedValue=10.5,
        changedRatio=0.82,
        fluctuationUpIssueCount=245,
        fluctuationDownIssueCount=120,
        fluctuationSteadinessIssueCount=65,
    )
    normalizer.on_market_index(idx)

    cached = realtime_cache.get("index:VNINDEX")
    assert cached is not None
    assert cached["value"] == 1285.6
    assert cached["change"] == 10.5
    assert cached["pct_change"] == 0.82
    assert cached["advance"] == 245
    assert cached["decline"] == 120
    assert cached["no_change"] == 65


def test_fetch_batch_quotes_reads_dnse_cache_first():
    """Ensure IBoardDataGateway.fetch_batch_quotes serves DNSE cached quotes without calling vnstock."""
    realtime_cache.set(
        "iboard_quote:SSI",
        {
            "symbol": "SSI",
            "close_price": 35500.0,
            "reference_price": 35000.0,
            "bid_price_1": 35450.0,
            "bid_vol_1": 10000,
            "ask_price_1": 35500.0,
            "ask_vol_1": 20000,
        },
        ttl=10,
    )

    mock_vn = MagicMock()
    quotes = IBoardDataGateway.fetch_batch_quotes(mock_vn, ["SSI"])
    assert "SSI" in quotes
    assert quotes["SSI"]["close_price"] == 35500.0
    # mock_vn should not be called because SSI was found in cache
    mock_vn.fetch_market_quote.assert_not_called()


@pytest.mark.anyio
async def test_iboard_ws_manager_lifecycle():
    """Test IBoardWSManager connection and message handling."""
    manager = IBoardWSManager()
    mock_ws = AsyncMock()
    sent_frames: list[dict[str, Any]] = []

    async def async_send(msg: str):
        sent_frames.append(json.loads(msg))

    mock_ws.send_text = async_send

    await manager.connect(mock_ws)
    assert mock_ws in manager.active_connections
    assert "indices" in manager.subscriptions[mock_ws]
    assert "board" in manager.subscriptions[mock_ws]

    # Handle ping action
    await manager.handle_client_message(mock_ws, json.dumps({"action": "ping"}))
    assert any(m.get("type") == "pong" for m in sent_frames)

    # Handle subscribe action
    await manager.handle_client_message(
        mock_ws, json.dumps({"action": "subscribe", "channels": ["stock:HPG"]})
    )
    assert (
        "STOCK:HPG" in manager.subscriptions[mock_ws]
        or "stock:HPG" in manager.subscriptions[mock_ws]
    )

    # Handle disconnect
    await manager.disconnect(mock_ws)
    assert mock_ws not in manager.active_connections


def test_fastapi_websocket_endpoint():
    """Integration test connecting to /api/v1/stock/iboard/ws."""
    client = TestClient(app)
    with client.websocket_connect("/api/v1/stock/iboard/ws") as websocket:
        first_frame = websocket.receive_json()
        assert first_frame.get("type") == "welcome"

        # Drain any initial indices snapshot if present
        websocket.send_json({"action": "ping"})
        msg = websocket.receive_json()
        if msg.get("type") == "snapshot_indices":
            msg = websocket.receive_json()

        assert msg.get("type") == "pong"

        # Subscribe to specific stock
        websocket.send_json({"action": "subscribe", "channels": ["stock:HPG"]})
        sub_resp = websocket.receive_json()
        assert sub_resp.get("type") == "subscribed"

        snap_resp = websocket.receive_json()
        assert snap_resp.get("type") == "snapshot_stock"
        assert snap_resp.get("symbol") == "HPG"

        # Trigger live quote on TickNormalizer and verify broadcast arrives on websocket
        from app.domains.dnse import (
            get_dnse_stream_manager,
        )

        normalizer = get_dnse_stream_manager().normalizer
        live_quote = MockDNSEQuote(
            symbol="HPG",
            bid=[MockPriceLevel(price=28900.0, quantity=10000)],
            offer=[MockPriceLevel(price=28950.0, quantity=20000)],
        )
        normalizer.on_quote(live_quote)

        ws_event = websocket.receive_json()
        assert ws_event.get("type") == "quote"
        assert ws_event.get("symbol") == "HPG"
        assert ws_event.get("data", {}).get("bid_price_1") == 28900.0
