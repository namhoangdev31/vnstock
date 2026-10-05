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
            "time": str(time_val),
            "source": "dnse_ws",
        }
        realtime_cache.set(f"realtime:{sym}", payload, ttl=self.TRADE_TTL)
        logger.debug("[TickNormalizer] trade %s price=%s", sym, close_val)

    def on_quote(self, quote: Any) -> None:
        """Handle top-of-book Quote tick (best bids/offers)."""
        symbol_raw = getattr(quote, "symbol", None)
        if not symbol_raw or not isinstance(symbol_raw, str):
            return

        sym = symbol_raw.strip().upper()
        best_bid = getattr(quote, "best_bid", None)
        best_ask = getattr(quote, "best_ask", None)
        spread = getattr(quote, "spread", None)
        time_val = getattr(quote, "time", None)

        payload: dict[str, Any] = {
            "symbol": sym,
            "bid": float(best_bid[0]) if best_bid else None,
            "bid_vol": int(best_bid[1]) if best_bid else None,
            "ask": float(best_ask[0]) if best_ask else None,
            "ask_vol": int(best_ask[1]) if best_ask else None,
            "spread": float(spread) if spread is not None else None,
            "time": str(time_val) if time_val is not None else None,
            "source": "dnse_ws_quote",
        }
        realtime_cache.set(f"quote:{sym}", payload, ttl=self.QUOTE_TTL)

    def on_market_index(self, idx: Any) -> None:
        """Handle MarketIndex tick (VNINDEX, VN30, etc.)."""
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
            "total_volume": int(tot_vol) if tot_vol is not None else None,
            "total_value": float(tot_val) if tot_val is not None else None,
            "time": str(tx_time) if tx_time is not None else None,
            "source": "dnse_ws",
        }
        realtime_cache.set(f"index:{name}", payload, ttl=self.INDEX_TTL)

    def on_foreign(self, fi: Any) -> None:
        """Handle ForeignInvestor volume/value flow tick."""
        symbol_raw = getattr(fi, "symbol", None)
        if not symbol_raw or not isinstance(symbol_raw, str):
            return

        sym = symbol_raw.strip().upper()
        payload: dict[str, Any] = {
            "symbol": sym,
            "buy_volume": getattr(fi, "buyVolume", None),
            "sell_volume": getattr(fi, "sellVolume", None),
            "buy_value": getattr(fi, "buyTradedAmount", None),
            "sell_value": getattr(fi, "sellTradedAmount", None),
            "total_buy_volume": getattr(fi, "totalBuyVolume", None),
            "total_sell_volume": getattr(fi, "totalSellVolume", None),
            "time": getattr(fi, "transactTime", None),
            "source": "dnse_ws",
        }
        realtime_cache.set(f"foreign:{sym}", payload, ttl=self.FOREIGN_TTL)

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
