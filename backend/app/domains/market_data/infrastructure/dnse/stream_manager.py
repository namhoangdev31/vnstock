"""DNSEStreamManager — Lifecycle and stream manager for DNSE WebSocket.

Manages persistent WebSocket connection, channel subscriptions, and automated
reconnection with exponential backoff. Injects incoming data into `realtime_cache`
via `TickNormalizer` callbacks.

STRICT COMPLIANCE:
- RULE 1: Strictly no live order execution. Real-time data streaming only.
- RULE 2: Does not touch or modify live brokerage accounts or simulation state.
- RULE 3: Pure data pipeline without hallucinated or hardcoded numbers.
"""

from __future__ import annotations

import asyncio
import logging

from dnse.websocket.client import TradingClient
from dnse.websocket.exceptions import (
    AuthenticationError,
    ConnectionClosed,
)
from dnse.websocket.exceptions import (
    ConnectionError as DNSEConnectionError,
)

from app.domains.market_data.infrastructure.dnse.config import DNSEStreamConfig
from app.domains.market_data.infrastructure.dnse.tick_handler import TickNormalizer

logger = logging.getLogger(__name__)


class DNSEStreamManager:
    """Manages the lifecycle of DNSE real-time market data WebSocket streaming."""

    def __init__(
        self,
        config: DNSEStreamConfig,
        normalizer: TickNormalizer | None = None,
    ) -> None:
        self.config = config
        self.normalizer = normalizer or TickNormalizer()
        self._client: TradingClient | None = None
        self._task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()
        self._is_connected: bool = False
        self._subscribed_symbols: set[str] = {
            s.strip().upper() for s in self.config.symbols if s.strip()
        }

    @property
    def is_running(self) -> bool:
        """Return True if background streaming task is active and running."""
        return self._task is not None and not self._task.done()

    @property
    def is_connected(self) -> bool:
        """Return True if WebSocket connection is established and authenticated."""
        return self._is_connected

    async def start(self) -> None:
        """Start the background streaming worker. Safe to invoke in application lifespan."""
        if not self.config.is_configured:
            logger.info(
                "[DNSE] API credentials not provided — WebSocket streaming remains disabled."
            )
            return

        if self.is_running:
            logger.warning("[DNSE] Stream manager is already running.")
            return

        self._stop_event.clear()
        self._task = asyncio.create_task(self._run_loop(), name="dnse_ws_stream")
        logger.info(
            "[DNSE] Stream manager started. Tracking symbols=%s, indices=%s",
            list(self._subscribed_symbols),
            self.config.market_indices,
        )

    async def stop(self) -> None:
        """Gracefully stop background streaming and close connection."""
        self._stop_event.set()
        self._is_connected = False

        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await asyncio.wait_for(self._task, timeout=5.0)
            except (TimeoutError, asyncio.CancelledError):
                pass
            self._task = None

        if self._client:
            try:
                await self._client.disconnect()
            except Exception as e:
                logger.debug("[DNSE] Error during client disconnect: %s", e)
            finally:
                self._client = None

        logger.info("[DNSE] Stream manager stopped.")

    async def subscribe_symbols(self, symbols: list[str]) -> None:
        """Dynamically subscribe additional symbols to the running DNSE stream."""
        clean = [
            s.strip().upper() for s in symbols if s and isinstance(s, str) and s.strip()
        ]
        new_symbols = [s for s in clean if s not in self._subscribed_symbols]
        if not new_symbols:
            return

        self._subscribed_symbols.update(new_symbols)
        self.config.symbols = list(self._subscribed_symbols)

        if self.is_connected and self._client:
            try:
                logger.info("[DNSE] Dynamically subscribing to: %s", new_symbols)
                await self._client.subscribe_trades(
                    new_symbols, on_trade=self.normalizer.on_trade
                )
                await self._client.subscribe_trade_extra(
                    new_symbols, on_trade_extra=self.normalizer.on_trade_extra
                )
                await self._client.subscribe_quotes(
                    new_symbols, on_quote=self.normalizer.on_quote
                )
                await self._client.subscribe_sec_def(
                    new_symbols, on_sec_def=self.normalizer.on_sec_def
                )
                await self._client.subscribe_foreign_trading(
                    new_symbols, on_trade=self.normalizer.on_foreign
                )
                await self._client.subscribe_ohlc(
                    new_symbols,
                    resolution="1",
                    on_ohlc=self.normalizer.on_ohlc,
                )
                await self._client.subscribe_expected_price(
                    new_symbols,
                    on_expected_price=self.normalizer.on_expected_price,
                )
            except Exception as e:
                logger.warning(
                    "[DNSE] Dynamic subscription error for %s: %s", new_symbols, e
                )

    def subscribe_symbols_background(self, symbols: list[str]) -> None:
        """Fire-and-forget dynamic subscription safe to invoke from synchronous contexts."""
        clean = [
            s.strip().upper() for s in symbols if s and isinstance(s, str) and s.strip()
        ]
        new_symbols = [s for s in clean if s not in self._subscribed_symbols]
        if not new_symbols:
            return

        self._subscribed_symbols.update(new_symbols)
        self.config.symbols = list(self._subscribed_symbols)

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.subscribe_symbols(new_symbols))
        except RuntimeError:
            pass

    async def _run_loop(self) -> None:
        """Continuous reconnection loop with exponential backoff."""
        attempt = 0
        while not self._stop_event.is_set():
            try:
                await self._connect_and_stream()
                attempt = 0  # Reset counter after successful connection cycle
            except asyncio.CancelledError:
                break
            except AuthenticationError as e:
                logger.error(
                    "[DNSE] Authentication error: %s. Aborting reconnect loop.", e
                )
                break
            except (DNSEConnectionError, ConnectionClosed, Exception) as e:
                self._is_connected = False
                attempt += 1
                if attempt > self.config.max_retries:
                    logger.error(
                        "[DNSE] Maximum retry attempts (%d) reached. Stopping stream.",
                        self.config.max_retries,
                    )
                    break

                backoff = min(self.config.reconnect_delay * (2 ** (attempt - 1)), 120.0)
                logger.warning(
                    "[DNSE] Stream disconnected: %s. Reconnecting in %.1fs (attempt %d/%d)...",
                    e,
                    backoff,
                    attempt,
                    self.config.max_retries,
                )
                try:
                    await asyncio.sleep(backoff)
                except asyncio.CancelledError:
                    break

    async def _connect_and_stream(self) -> None:
        """Perform a single connection, subscribe to feeds, and wait until disconnected."""
        client = TradingClient(
            api_key=self.config.api_key,
            api_secret=self.config.api_secret,
            base_url=self.config.ws_url,
            auto_reconnect=False,  # Reconnection is handled cleanly by _run_loop
            max_retries=1,
            heartbeat_interval=self.config.heartbeat_interval,
        )
        self._client = client

        logger.info("[DNSE] Connecting to %s...", self.config.ws_url)
        await client.connect()
        self._is_connected = True
        logger.info("[DNSE] WebSocket connected and authenticated successfully.")

        # 1. Subscribe to Symbol-level Market Data
        active_symbols = list(self._subscribed_symbols)
        if active_symbols:
            logger.info("[DNSE] Subscribing to symbols: %s", active_symbols)
            await client.subscribe_trades(
                active_symbols, on_trade=self.normalizer.on_trade
            )
            await client.subscribe_trade_extra(
                active_symbols, on_trade_extra=self.normalizer.on_trade_extra
            )
            await client.subscribe_quotes(
                active_symbols, on_quote=self.normalizer.on_quote
            )
            await client.subscribe_sec_def(
                active_symbols, on_sec_def=self.normalizer.on_sec_def
            )
            await client.subscribe_ohlc(
                active_symbols,
                resolution="1",
                on_ohlc=self.normalizer.on_ohlc,
            )
            await client.subscribe_foreign_trading(
                active_symbols, on_trade=self.normalizer.on_foreign
            )
            await client.subscribe_expected_price(
                active_symbols,
                on_expected_price=self.normalizer.on_expected_price,
            )

        # 2. Subscribe to Market Indices
        for idx in self.config.market_indices:
            logger.info("[DNSE] Subscribing to market index: %s", idx)
            await client.subscribe_market_index(
                idx, on_market_index=self.normalizer.on_market_index
            )

        # 3. Stream loop until stop requested or internal connection dropped
        while not self._stop_event.is_set():
            if not getattr(client, "_is_running", False):
                logger.warning("[DNSE] Client reported not running; restarting stream.")
                break
            await asyncio.sleep(1.0)

        # Clean disconnection
        self._is_connected = False
        await client.disconnect()
        self._client = None
