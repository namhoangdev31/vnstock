"""WebSocket connection manager and broadcaster for iBoard Real-time Trading Board.

Handles real-time WebSocket subscriptions from frontend clients for:
- Market Indices (`indices`)
- Full / Multi-Category Trading Board (`board`)
- Stock-specific deep ticks and 3-level orderbook (`stock:{symbol}`)
- Bidirectional Ping/Pong heartbeat and snapshot synchronization

Integrates directly with DNSE `TickNormalizer` events to broadcast zero-latency updates.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import Any

from fastapi import WebSocket

from app.core.cache import realtime_cache
from app.core.models_base import VN_TZ
from app.domains.market_data.infrastructure.dnse import (
    dnse_stream_manager,
    get_dnse_stream_manager,
)

logger = logging.getLogger(__name__)


class IBoardWSManager:
    """Manages WebSocket connections and channel broadcasts for iBoard."""

    def __init__(self) -> None:
        self.active_connections: set[WebSocket] = set()
        self.subscriptions: dict[WebSocket, set[str]] = {}
        self._listener_registered: bool = False
        self._loop: asyncio.AbstractEventLoop | None = None

    def _ensure_listener(self) -> None:
        """Register listener with TickNormalizer once."""
        if not self._listener_registered:
            try:
                mgr = get_dnse_stream_manager()
                mgr.normalizer.add_listener(self._on_normalizer_event)
                self._listener_registered = True
                logger.info(
                    "[IBoardWS] Registered event listener with DNSE TickNormalizer."
                )
            except Exception as e:
                logger.warning(
                    "[IBoardWS] Failed to register TickNormalizer listener: %s", e
                )

    def _on_normalizer_event(
        self, event_type: str, key: str, payload: dict[str, Any]
    ) -> None:
        """Callback invoked by TickNormalizer when market data updates arrive."""
        if not self.active_connections:
            return

        msg: dict[str, Any]
        channels_to_target: set[str] = set()

        if event_type == "index":
            msg = {"type": "index", "index": key, "data": payload}
            channels_to_target.add("indices")
            channels_to_target.add("all")
        elif event_type in ("quote", "trade", "sec_def", "foreign"):
            msg = {"type": event_type, "symbol": key, "data": payload}
            channels_to_target.add("board")
            channels_to_target.add(f"stock:{key.upper()}")
            channels_to_target.add("all")
        else:
            msg = {"type": event_type, "key": key, "data": payload}
            channels_to_target.add("all")

        # Broadcast via async event loop
        try:
            loop = self._loop or asyncio.get_running_loop()
            loop.create_task(self._broadcast_to_channels(msg, channels_to_target))
        except RuntimeError:
            if self._loop and self._loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    self._broadcast_to_channels(msg, channels_to_target), self._loop
                )

    async def _broadcast_to_channels(
        self, message: dict[str, Any], target_channels: set[str]
    ) -> None:
        """Deliver message to all active WebSockets subscribed to any target channel."""
        text_data = json.dumps(message, ensure_ascii=False)
        dead_connections: list[WebSocket] = []

        for ws, subbed_channels in list(self.subscriptions.items()):
            if ws not in self.active_connections:
                continue
            if not target_channels.isdisjoint(subbed_channels):
                try:
                    await ws.send_text(text_data)
                except Exception as e:
                    logger.debug(
                        "[IBoardWS] Socket send failed, disconnecting client: %s", e
                    )
                    dead_connections.append(ws)

        for ws in dead_connections:
            await self.disconnect(ws)

    async def connect(self, websocket: WebSocket) -> None:
        """Accept new WebSocket connection and track channels."""
        await websocket.accept()
        self.active_connections.add(websocket)
        self.subscriptions[websocket] = {
            "indices",
            "board",
        }  # Default baseline channels
        self._ensure_listener()

        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            pass

        logger.info(
            "[IBoardWS] Client connected. Total active connections: %d",
            len(self.active_connections),
        )

        # Send initial connection acknowledgment & baseline snapshot
        await websocket.send_text(
            json.dumps(
                {
                    "type": "welcome",
                    "channels": list(self.subscriptions[websocket]),
                    "server_time": datetime.now(VN_TZ).isoformat(),
                }
            )
        )
        await self._send_indices_snapshot(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        """Cleanly remove disconnected WebSocket."""
        self.active_connections.discard(websocket)
        self.subscriptions.pop(websocket, None)
        logger.info(
            "[IBoardWS] Client disconnected. Remaining connections: %d",
            len(self.active_connections),
        )

    async def handle_client_message(
        self, websocket: WebSocket, raw_message: str
    ) -> None:
        """Parse incoming JSON frame from frontend client and process actions."""
        try:
            payload = json.loads(raw_message)
        except Exception:
            await websocket.send_text(
                json.dumps({"type": "error", "message": "Invalid JSON frame"})
            )
            return

        action = str(payload.get("action", "")).lower()

        if action == "ping":
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "pong",
                        "time": datetime.now(VN_TZ).isoformat(),
                    }
                )
            )
            return

        if action == "subscribe":
            raw_channels = payload.get("channels") or []
            if isinstance(raw_channels, str):
                raw_channels = [raw_channels]

            new_channels: set[str] = set()
            stock_symbols: list[str] = []
            for c in raw_channels:
                if not c or not isinstance(c, str):
                    continue
                c_str = c.strip()
                if c_str.lower().startswith("stock:"):
                    sym = c_str.split(":", 1)[1].strip().upper()
                    new_channels.add(f"stock:{sym}")
                    stock_symbols.append(sym)
                else:
                    new_channels.add(c_str.lower())

            client_subs = self.subscriptions.setdefault(websocket, set())
            client_subs.update(new_channels)

            # Trigger background DNSE subscription for stock-specific feeds
            if stock_symbols:
                dnse_stream_manager.subscribe_symbols_background(stock_symbols)

            await websocket.send_text(
                json.dumps(
                    {
                        "type": "subscribed",
                        "channels": list(client_subs),
                    }
                )
            )

            # Immediate snapshots
            if "indices" in new_channels:
                await self._send_indices_snapshot(websocket)
            for sym in stock_symbols:
                await self._send_stock_snapshot(websocket, sym)
            return

        if action == "unsubscribe":
            raw_channels = payload.get("channels") or []
            if isinstance(raw_channels, str):
                raw_channels = [raw_channels]

            remove_channels: set[str] = set()
            for c in raw_channels:
                if not c or not isinstance(c, str):
                    continue
                c_str = c.strip()
                if c_str.lower().startswith("stock:"):
                    sym = c_str.split(":", 1)[1].strip().upper()
                    remove_channels.add(f"stock:{sym}")
                else:
                    remove_channels.add(c_str.lower())

            client_subs = self.subscriptions.setdefault(websocket, set())
            client_subs.difference_update(remove_channels)
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "unsubscribed",
                        "channels": list(client_subs),
                    }
                )
            )
            return

    async def _send_indices_snapshot(self, websocket: WebSocket) -> None:
        """Send cached snapshot of major market indices."""
        indices_keys = ["VNINDEX", "VN30", "HNX", "HNX30", "UPCOM"]
        snapshot: list[dict[str, Any]] = []
        for name in indices_keys:
            data = realtime_cache.get(f"index:{name}")
            if data and isinstance(data, dict):
                snapshot.append(data)
        if snapshot:
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "snapshot_indices",
                        "data": snapshot,
                    }
                )
            )

    async def _send_stock_snapshot(self, websocket: WebSocket, symbol: str) -> None:
        """Send cached quote and recent ticks snapshot for a stock."""
        sym = symbol.strip().upper()
        quote_data = realtime_cache.get(f"iboard_quote:{sym}")
        recent_ticks = get_dnse_stream_manager().normalizer.get_recent_ticks(
            sym, limit=20
        )
        await websocket.send_text(
            json.dumps(
                {
                    "type": "snapshot_stock",
                    "symbol": sym,
                    "quote": quote_data,
                    "ticks": recent_ticks,
                }
            )
        )


iboard_ws_manager = IBoardWSManager()

__all__ = ["IBoardWSManager", "iboard_ws_manager"]
