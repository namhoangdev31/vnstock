"""Unit tests for DNSEStreamManager lifecycle and reconnect logic."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from dnse.websocket.exceptions import AuthenticationError
from dnse.websocket.exceptions import ConnectionError as DNSEConnectionError

from app.domains.dnse.config import DNSEStreamConfig
from app.domains.dnse.stream_manager import (
    DNSEStreamManager,
)
from app.domains.dnse.tick_handler import TickNormalizer


def test_config_from_settings(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("app.core.config.settings.DNSE_API_KEY", "test_key")
    monkeypatch.setattr("app.core.config.settings.DNSE_API_SECRET", "test_secret")
    monkeypatch.setattr(
        "app.core.config.settings.DNSE_WS_SYMBOLS", "VN30F1M, FPT , VCB "
    )
    monkeypatch.setattr("app.core.config.settings.DNSE_WS_MARKET_INDICES", "HOSE, HNX")

    cfg = DNSEStreamConfig.from_settings()
    assert cfg.api_key == "test_key"
    assert cfg.api_secret == "test_secret"
    assert cfg.symbols == ["VN30F1M", "FPT", "VCB"]
    assert cfg.market_indices == ["HOSE", "HNX"]
    assert cfg.is_configured is True


def test_config_is_configured_empty():
    cfg = DNSEStreamConfig(api_key="", api_secret="")
    assert cfg.is_configured is False

    cfg2 = DNSEStreamConfig(api_key="key", api_secret="")
    assert cfg2.is_configured is False


@pytest.mark.anyio
async def test_start_skips_when_not_configured():
    cfg = DNSEStreamConfig(api_key="", api_secret="")
    mgr = DNSEStreamManager(config=cfg)

    await mgr.start()
    assert mgr.is_running is False
    assert mgr.is_connected is False


@pytest.mark.anyio
async def test_start_and_stop_lifecycle():
    cfg = DNSEStreamConfig(
        api_key="mock_key",
        api_secret="mock_secret",
        symbols=["VN30F1M"],
        market_indices=["HOSE"],
    )
    normalizer = TickNormalizer()
    mgr = DNSEStreamManager(config=cfg, normalizer=normalizer)

    mock_client = AsyncMock()
    mock_client.connect = AsyncMock()
    mock_client.disconnect = AsyncMock()
    mock_client.subscribe_trades = AsyncMock()
    mock_client.subscribe_quotes = AsyncMock()
    mock_client.subscribe_ohlc = AsyncMock()
    mock_client.subscribe_foreign_trading = AsyncMock()
    mock_client.subscribe_expected_price = AsyncMock()
    mock_client.subscribe_market_index = AsyncMock()
    mock_client._is_running = True

    with patch(
        "app.domains.dnse.stream_manager.TradingClient",
        return_value=mock_client,
    ):
        await mgr.start()
        assert mgr.is_running is True

        # Let the loop execute connect and subscribe
        await asyncio.sleep(0.05)

        assert mock_client.connect.called
        assert mock_client.subscribe_trades.called
        assert mock_client.subscribe_market_index.called

        await mgr.stop()
        assert mgr.is_running is False
        assert mock_client.disconnect.called


@pytest.mark.anyio
async def test_auth_error_aborts_without_reconnect():
    cfg = DNSEStreamConfig(
        api_key="bad_key",
        api_secret="bad_secret",
        max_retries=5,
    )
    mgr = DNSEStreamManager(config=cfg)

    mock_client = AsyncMock()
    mock_client.connect = AsyncMock(side_effect=AuthenticationError("Invalid API key"))

    with patch(
        "app.domains.dnse.stream_manager.TradingClient",
        return_value=mock_client,
    ):
        await mgr.start()
        # Wait a short moment for loop to execute and abort
        await asyncio.sleep(0.1)

        # Loop should terminate cleanly without looping 5 times
        assert mgr.is_running is False
        assert mock_client.connect.call_count == 1

        await mgr.stop()


@pytest.mark.anyio
async def test_reconnect_on_connection_error():
    cfg = DNSEStreamConfig(
        api_key="key",
        api_secret="secret",
        reconnect_delay=0.01,
        max_retries=2,
    )
    mgr = DNSEStreamManager(config=cfg)

    mock_client = AsyncMock()
    mock_client.connect = AsyncMock(side_effect=DNSEConnectionError("Network drop"))

    with patch(
        "app.domains.dnse.stream_manager.TradingClient",
        return_value=mock_client,
    ):
        await mgr.start()
        # Let retry attempts exhaust (max_retries=2 -> attempt 1, attempt 2, then break)
        await asyncio.sleep(0.2)

        # Should have stopped after exceeding max retries
        assert mgr.is_running is False
        assert mock_client.connect.call_count >= 2

        await mgr.stop()
