"""Normalise DNSE WebSocket messages into in-memory TTL cache entries.

Ensures incoming real-time streaming data from DNSE WebSocket (Trades,
Quotes, Market Indices, OHLC, Foreign Flows, Expected Prices) is normalized
and injected directly into `realtime_cache` with strict schema adherence
and zero hardcoded default overrides (Rule 3).
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.cache import realtime_cache

logger = logging.getLogger(__name__)


class TickNormalizer:
    """Converts DNSE SDK WebSocket model objects into cached real-time dicts."""

    TRADE_TTL: int = 5
    QUOTE_TTL: int = 5
    INDEX_TTL: int = 5
    FOREIGN_TTL: int = 30
    OHLC_TTL: int = 60
    EXPECTED_PRICE_TTL: int = 15
    IBOARD_QUOTE_TTL: int = 10
    MAX_RECENT_TICKS: int = 50

    def __init__(self) -> None:
        self._listeners: list[Any] = []
        self._recent_ticks: dict[str, list[dict[str, Any]]] = {}

    def add_listener(self, listener: Any) -> None:
        """Register a callback listener for realtime market events.

        Callback signature: listener(event_type: str, key: str, payload: dict[str, Any])
        """
        if listener not in self._listeners:
            self._listeners.append(listener)

    def remove_listener(self, listener: Any) -> None:
        """Unregister an event listener."""
        if listener in self._listeners:
            self._listeners.remove(listener)

    def _notify_listeners(
        self, event_type: str, key: str, payload: dict[str, Any]
    ) -> None:
        """Dispatch event to all registered listeners safely."""
        for listener in list(self._listeners):
            try:
                listener(event_type, key, payload)
            except Exception as e:
                logger.debug(
                    "[TickNormalizer] Listener error on event %s: %s", event_type, e
                )

    def get_recent_ticks(self, symbol: str, limit: int = 20) -> list[dict[str, Any]]:
        """Return the most recent matched ticks for a symbol."""
        sym = symbol.strip().upper()
        ticks = self._recent_ticks.get(sym, [])
        return ticks[:limit]

    def _get_or_create_iboard_quote(self, sym: str) -> dict[str, Any]:
        """Fetch existing iboard_quote or initialize clean schema dictionary."""
        cached = realtime_cache.get(f"iboard_quote:{sym}")
        if isinstance(cached, dict):
            return dict(cached)
        return {
            "symbol": sym,
            "close_price": None,
            "reference_price": None,
            "ceiling_price": None,
            "floor_price": None,
            "high_price": None,
            "low_price": None,
            "open_price": None,
            "price_change": None,
            "percent_change": None,
            "volume_accumulated": 0,
            "total_value": 0.0,
            "bid_price_1": None,
            "bid_vol_1": None,
            "bid_price_2": None,
            "bid_vol_2": None,
            "bid_price_3": None,
            "bid_vol_3": None,
            "ask_price_1": None,
            "ask_vol_1": None,
            "ask_price_2": None,
            "ask_vol_2": None,
            "ask_price_3": None,
            "ask_vol_3": None,
            "foreign_buy_volume": None,
            "foreign_sell_volume": None,
            "foreign_room": None,
            "source": "dnse_ws",
        }

    def on_trade(self, trade: Any) -> None:
        """Handle matched Trade tick and update realtime price cache."""
        symbol_raw = getattr(trade, "symbol", None)
        if not symbol_raw or not isinstance(symbol_raw, str):
            return

        sym = symbol_raw.strip().upper()
        existing = realtime_cache.get(f"realtime:{sym}") or {}

        open_val = getattr(trade, "openPrice", None)
        if open_val is None:
            open_val = existing.get("open")

        high_val = getattr(trade, "highestPrice", None)
        if high_val is None:
            high_val = existing.get("high")

        low_val = getattr(trade, "lowestPrice", None)
        if low_val is None:
            low_val = existing.get("low")

        close_val = getattr(trade, "price", None)
        if close_val is None:
            close_val = existing.get("close")

        vol_val = getattr(trade, "totalVolumeTraded", None)
        if vol_val is None:
            vol_val = existing.get("volume", 0)

        trade_qty = getattr(trade, "quantity", None)
        gross_val = getattr(trade, "grossTradeAmount", None)
        time_val = getattr(trade, "time", None)
        if time_val is None:
            time_val = existing.get("time", "")

        payload: dict[str, Any] = {
            "symbol": sym,
            "open": float(open_val) if open_val is not None else None,
            "high": float(high_val) if high_val is not None else None,
            "low": float(low_val) if low_val is not None else None,
            "close": float(close_val) if close_val is not None else None,
            "volume": int(vol_val) if vol_val is not None else 0,
            "trade_quantity": int(trade_qty) if trade_qty is not None else None,
            "gross_amount": float(gross_val) if gross_val is not None else None,
            "time": str(time_val),
            "source": "dnse_ws",
        }
        realtime_cache.set(f"realtime:{sym}", payload, ttl=self.TRADE_TTL)

        # Update iboard_quote composite cache
        ib_quote = self._get_or_create_iboard_quote(sym)
        if close_val is not None:
            ib_quote["close_price"] = float(close_val)
        if open_val is not None:
            ib_quote["open_price"] = float(open_val)
        if high_val is not None:
            ib_quote["high_price"] = float(high_val)
        if low_val is not None:
            ib_quote["low_price"] = float(low_val)
        if vol_val is not None:
            ib_quote["volume_accumulated"] = int(vol_val)
        if gross_val is not None:
            ib_quote["total_value"] = float(gross_val)

        ref_p = ib_quote.get("reference_price")
        if (
            close_val is not None
            and ref_p is not None
            and isinstance(ref_p, (int, float))
            and ref_p > 0
        ):
            c_val = float(close_val)
            ib_quote["price_change"] = round(c_val - ref_p, 2)
            ib_quote["percent_change"] = round((c_val - ref_p) / ref_p * 100, 2)

        realtime_cache.set(f"iboard_quote:{sym}", ib_quote, ttl=self.IBOARD_QUOTE_TTL)

        # Record recent tick for Time & Sales
        if close_val is not None and trade_qty is not None:
            time_str = str(time_val)
            if " " in time_str:
                time_str = time_str.split(" ")[1][:8]
            else:
                time_str = time_str[:8]

            # Side detection (default to Buy/Sell neutral if side not explicit)
            side_raw = getattr(trade, "side", None)
            if side_raw is not None:
                side_str = "B" if side_raw == 1 else "S"
            else:
                # Compare to best bid/ask in ib_quote
                bid_1 = ib_quote.get("bid_price_1")
                ask_1 = ib_quote.get("ask_price_1")
                c_val = float(close_val)
                if ask_1 is not None and c_val >= float(ask_1):
                    side_str = "B"
                elif bid_1 is not None and c_val <= float(bid_1):
                    side_str = "S"
                else:
                    side_str = "B"

            tick_item = {
                "time": time_str,
                "price": float(close_val),
                "volume": int(trade_qty),
                "side": side_str,
            }
            sym_ticks = self._recent_ticks.setdefault(sym, [])
            sym_ticks.insert(0, tick_item)
            if len(sym_ticks) > self.MAX_RECENT_TICKS:
                self._recent_ticks[sym] = sym_ticks[: self.MAX_RECENT_TICKS]

        self._notify_listeners("trade", sym, payload)
        logger.debug("[TickNormalizer] trade %s price=%s", sym, close_val)

    def on_trade_extra(self, trade_extra: Any) -> None:
        """Handle TradeExtra tick containing aggressive order side."""
        self.on_trade(trade_extra)

    def on_quote(self, quote: Any) -> None:
        """Handle top-of-book and 3-level order book Quote tick."""
        symbol_raw = getattr(quote, "symbol", None)
        if not symbol_raw or not isinstance(symbol_raw, str):
            return

        sym = symbol_raw.strip().upper()
        bids = getattr(quote, "bid", None) or []
        offers = getattr(quote, "offer", None) or []
        tot_bid_qtty = getattr(quote, "totalBidQtty", None)
        tot_offer_qtty = getattr(quote, "totalOfferQtty", None)
        time_val = getattr(quote, "time", None)

        def _get_level(lst: list[Any], idx: int) -> tuple[float | None, int | None]:
            if len(lst) > idx:
                item = lst[idx]
                p = getattr(item, "price", None)
                q = getattr(item, "quantity", None)
                return (
                    float(p) if p is not None else None,
                    int(q) if q is not None else None,
                )
            return (None, None)

        b_p_1, b_v_1 = _get_level(bids, 0)
        b_p_2, b_v_2 = _get_level(bids, 1)
        b_p_3, b_v_3 = _get_level(bids, 2)

        a_p_1, a_v_1 = _get_level(offers, 0)
        a_p_2, a_v_2 = _get_level(offers, 1)
        a_p_3, a_v_3 = _get_level(offers, 2)

        # Standard top-of-book cache (quote:{sym})
        spread = (
            round(a_p_1 - b_p_1, 2)
            if (a_p_1 is not None and b_p_1 is not None)
            else None
        )
        payload: dict[str, Any] = {
            "symbol": sym,
            "bid": b_p_1,
            "bid_vol": b_v_1,
            "ask": a_p_1,
            "ask_vol": a_v_1,
            "spread": spread,
            "time": str(time_val) if time_val is not None else None,
            "source": "dnse_ws_quote",
        }
        realtime_cache.set(f"quote:{sym}", payload, ttl=self.QUOTE_TTL)

        # Update iboard_quote composite cache with full 3-level orderbook
        ib_quote = self._get_or_create_iboard_quote(sym)
        ib_quote["bid_price_1"] = b_p_1
        ib_quote["bid_vol_1"] = b_v_1
        ib_quote["bid_price_2"] = b_p_2
        ib_quote["bid_vol_2"] = b_v_2
        ib_quote["bid_price_3"] = b_p_3
        ib_quote["bid_vol_3"] = b_v_3

        ib_quote["ask_price_1"] = a_p_1
        ib_quote["ask_vol_1"] = a_v_1
        ib_quote["ask_price_2"] = a_p_2
        ib_quote["ask_vol_2"] = a_v_2
        ib_quote["ask_price_3"] = a_p_3
        ib_quote["ask_vol_3"] = a_v_3

        if tot_bid_qtty is not None:
            ib_quote["total_bid_qty"] = int(tot_bid_qtty)
        if tot_offer_qtty is not None:
            ib_quote["total_offer_qty"] = int(tot_offer_qtty)

        realtime_cache.set(f"iboard_quote:{sym}", ib_quote, ttl=self.IBOARD_QUOTE_TTL)

        self._notify_listeners("quote", sym, ib_quote)

    def on_sec_def(self, sec_def: Any) -> None:
        """Handle SecurityDefinition (reference, ceiling, floor prices)."""
        symbol_raw = getattr(sec_def, "symbol", None)
        if not symbol_raw or not isinstance(symbol_raw, str):
            return

        sym = symbol_raw.strip().upper()
        basic_p = getattr(sec_def, "basicPrice", None)
        ceil_p = getattr(sec_def, "ceilingPrice", None)
        floor_p = getattr(sec_def, "floorPrice", None)

        ib_quote = self._get_or_create_iboard_quote(sym)
        if basic_p is not None:
            ib_quote["reference_price"] = float(basic_p)
        if ceil_p is not None:
            ib_quote["ceiling_price"] = float(ceil_p)
        if floor_p is not None:
            ib_quote["floor_price"] = float(floor_p)

        close_p = ib_quote.get("close_price")
        if (
            close_p is not None
            and basic_p is not None
            and isinstance(basic_p, (int, float))
            and basic_p > 0
        ):
            c_val = float(close_p)
            b_val = float(basic_p)
            ib_quote["price_change"] = round(c_val - b_val, 2)
            ib_quote["percent_change"] = round((c_val - b_val) / b_val * 100, 2)

        realtime_cache.set(f"iboard_quote:{sym}", ib_quote, ttl=self.IBOARD_QUOTE_TTL)
        self._notify_listeners("sec_def", sym, ib_quote)

    def on_market_index(self, idx: Any) -> None:
        """Handle MarketIndex tick (VNINDEX, VN30, HNX, HNX30, etc.)."""
        name_raw = (
            getattr(idx, "indexName", None)
            or getattr(idx, "indexId", None)
            or getattr(idx, "marketId", None)
        )
        if not name_raw:
            return

        name = str(name_raw).strip().upper()
        val_idx = getattr(idx, "valueIndexes", None)
        chg_val = getattr(idx, "changedValue", None)
        chg_ratio = getattr(idx, "changedRatio", None)
        adv = getattr(idx, "fluctuationUpIssueCount", None)
        dec = getattr(idx, "fluctuationDownIssueCount", None)
        no_chg = getattr(idx, "fluctuationSteadinessIssueCount", None)
        ceil = getattr(idx, "fluctuationUpperLimitIssueCount", None)
        flr = getattr(idx, "fluctuationLowerLimitIssueCount", None)
        tot_vol = getattr(idx, "totalVolumeTraded", None)
        tot_val = getattr(idx, "grossTradeAmount", None)
        tx_time = getattr(idx, "transactTime", None) or getattr(idx, "time", None)

        payload: dict[str, Any] = {
            "index": name,
            "value": float(val_idx) if val_idx is not None else None,
            "change": float(chg_val) if chg_val is not None else None,
            "pct_change": float(chg_ratio) if chg_ratio is not None else None,
            "advance": int(adv) if adv is not None else None,
            "decline": int(dec) if dec is not None else None,
            "no_change": int(no_chg) if no_chg is not None else None,
            "ceiling": int(ceil) if ceil is not None else 0,
            "floor": int(flr) if flr is not None else 0,
            "total_volume": int(tot_vol) if tot_vol is not None else None,
            "total_value": float(tot_val) if tot_val is not None else None,
            "time": str(tx_time) if tx_time is not None else None,
            "source": "dnse_ws",
        }
        realtime_cache.set(f"index:{name}", payload, ttl=self.INDEX_TTL)
        self._notify_listeners("index", name, payload)

    def on_foreign(self, fi: Any) -> None:
        """Handle ForeignInvestor volume/value flow tick."""
        symbol_raw = getattr(fi, "symbol", None)
        if not symbol_raw or not isinstance(symbol_raw, str):
            return

        sym = symbol_raw.strip().upper()
        tot_buy_vol = getattr(fi, "totalBuyVolume", None)
        tot_sell_vol = getattr(fi, "totalSellVolume", None)
        payload: dict[str, Any] = {
            "symbol": sym,
            "buy_volume": getattr(fi, "buyVolume", None),
            "sell_volume": getattr(fi, "sellVolume", None),
            "buy_value": getattr(fi, "buyTradedAmount", None),
            "sell_value": getattr(fi, "sellTradedAmount", None),
            "total_buy_volume": tot_buy_vol,
            "total_sell_volume": tot_sell_vol,
            "time": getattr(fi, "transactTime", None),
            "source": "dnse_ws",
        }
        realtime_cache.set(f"foreign:{sym}", payload, ttl=self.FOREIGN_TTL)

        # Update iboard_quote composite cache
        ib_quote = self._get_or_create_iboard_quote(sym)
        if tot_buy_vol is not None:
            ib_quote["foreign_buy_volume"] = int(tot_buy_vol)
        if tot_sell_vol is not None:
            ib_quote["foreign_sell_volume"] = int(tot_sell_vol)
        realtime_cache.set(f"iboard_quote:{sym}", ib_quote, ttl=self.IBOARD_QUOTE_TTL)

        self._notify_listeners("foreign", sym, payload)

    def on_ohlc(self, ohlc: Any) -> None:
        """Handle OHLC candle update."""
        symbol_raw = getattr(ohlc, "symbol", None)
        if not symbol_raw or not isinstance(symbol_raw, str):
            return

        sym = symbol_raw.strip().upper()
        res = str(getattr(ohlc, "resolution", "1"))
        o = getattr(ohlc, "open", None)
        h = getattr(ohlc, "high", None)
        low = getattr(ohlc, "low", None)
        c = getattr(ohlc, "close", None)
        v = getattr(ohlc, "volume", None)
        t = getattr(ohlc, "time", None)

        payload: dict[str, Any] = {
            "symbol": sym,
            "resolution": res,
            "open": float(o) if o is not None else None,
            "high": float(h) if h is not None else None,
            "low": float(low) if low is not None else None,
            "close": float(c) if c is not None else None,
            "volume": int(v) if v is not None else 0,
            "time": str(t) if t is not None else "",
            "source": "dnse_ws_ohlc",
        }
        realtime_cache.set(f"ohlc:{res}:{sym}", payload, ttl=self.OHLC_TTL)

        if res in ("1", "1m"):
            realtime_cache.set(f"realtime:{sym}", payload, ttl=self.TRADE_TTL)

        self._notify_listeners("ohlc", sym, payload)

    def on_expected_price(self, ep: Any) -> None:
        """Handle estimated/expected match price during call auction (ATO/ATC)."""
        symbol_raw = getattr(ep, "symbol", None)
        if not symbol_raw or not isinstance(symbol_raw, str):
            return

        sym = symbol_raw.strip().upper()
        exp_price = getattr(ep, "expectedTradePrice", None)
        exp_qty = getattr(ep, "expectedTradeQuantity", None)
        close_p = getattr(ep, "closePrice", None)
        time_val = getattr(ep, "time", None)

        payload: dict[str, Any] = {
            "symbol": sym,
            "expected_price": float(exp_price) if exp_price is not None else None,
            "expected_volume": int(exp_qty) if exp_qty is not None else None,
            "close_price": float(close_p) if close_p is not None else None,
            "time": str(time_val) if time_val is not None else None,
            "source": "dnse_ws_expected_price",
        }
        realtime_cache.set(
            f"expected_price:{sym}", payload, ttl=self.EXPECTED_PRICE_TTL
        )
        self._notify_listeners("expected_price", sym, payload)
