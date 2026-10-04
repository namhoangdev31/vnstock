"""Domain Policies and Pure Calculation Rules for iBoard Trading Board.

Tuân thủ Domain-Driven Design (DDD):
- Không phụ thuộc vào tầng Application, I/O hay database framework.
- Định nghĩa các business rule thuần túy: chuẩn hoá giá (Price Scaling),
  phân loại trạng thái giá (Price Status), trích xuất sổ lệnh (Order Book),
  và tính toán độ rộng thị trường (Market Breadth).
"""

from __future__ import annotations

from typing import Any

from app.domains.market_data.application.iboard_schemas import (
    IBoardIndexBreadth,
    IBoardStockRow,
    OrderBookLevel,
)
from app.domains.market_data.domain.models import StockOHLCVDaily


def safe_num(v: Any) -> float:
    """Chuyển đổi an toàn sang float; trả về 0.0 nếu giá trị không hợp lệ."""
    try:
        return float(v) if v is not None else 0.0
    except (ValueError, TypeError):
        return 0.0


def classify_price_status(last: float, ceil_p: float, flr_p: float, chg: float) -> str:
    """Domain Policy: Phân loại trạng thái giá: ceiling / floor / up / down / ref."""
    if last >= ceil_p and ceil_p > 0:
        return "ceiling"
    if last <= flr_p and flr_p > 0:
        return "floor"
    if chg > 0:
        return "up"
    if chg < 0:
        return "down"
    return "ref"


def build_order_book_levels(
    quote_row: Any, side: str, scale: float = 1.0
) -> list[OrderBookLevel]:
    """Domain Policy: Trích xuất và chuẩn hoá sổ lệnh 3 cấp từ live quote."""
    levels: list[OrderBookLevel] = []
    for i in range(1, 4):
        raw_p = safe_num(quote_row.get(f"{side}_price_{i}"))
        if raw_p > 0:
            price = round(raw_p * scale, 2 if scale == 0.001 else 1)
            vol = int(quote_row.get(f"{side}_vol_{i}") or 0)
            levels.append(OrderBookLevel(price=price, volume=vol))
    return levels


def parse_live_price_block(
    quote_row: Any, is_derivatives: bool = False
) -> dict[str, Any]:
    """Domain Policy: Chuẩn hoá đơn vị giá cho cổ phiếu/ETF/chứng quyền (scale 0.001)

    và giữ nguyên thang điểm số cho phái sinh (scale 1.0).
    """
    raw_close = safe_num(quote_row.get("close_price"))
    raw_ref = safe_num(quote_row.get("reference_price"))
    scale = (
        0.001
        if (not is_derivatives and (raw_close >= 1000 or raw_ref >= 1000))
        else 1.0
    )

    bid_book = build_order_book_levels(quote_row, "bid", scale=scale)
    ask_book = build_order_book_levels(quote_row, "ask", scale=scale)

    total_bid = sum(int(quote_row.get(f"bid_vol_{i}") or 0) for i in range(1, 4))
    total_ask = sum(int(quote_row.get(f"ask_vol_{i}") or 0) for i in range(1, 4))
    total_ba = total_bid + total_ask
    buy_r = int(total_bid / total_ba * 100) if total_ba else 0

    decimals = 2 if scale == 0.001 else 1
    last_p = round(raw_close * scale, decimals)
    ref_p = round(raw_ref * scale, decimals)
    ceil_p = round(safe_num(quote_row.get("ceiling_price")) * scale, decimals)
    flr_p = round(safe_num(quote_row.get("floor_price")) * scale, decimals)
    high_p = round(safe_num(quote_row.get("high_price")) * scale, decimals)
    low_p = round(safe_num(quote_row.get("low_price")) * scale, decimals)
    chg = round(safe_num(quote_row.get("price_change")) * scale, decimals)
    pct = round(safe_num(quote_row.get("percent_change")), 2)

    return {
        "last_p": last_p,
        "ref_p": ref_p,
        "ceil_p": ceil_p,
        "flr_p": flr_p,
        "high_p": high_p,
        "low_p": low_p,
        "chg": chg,
        "pct": pct,
        "vol": int(quote_row.get("volume_accumulated") or 0),
        "val_bil": round(safe_num(quote_row.get("total_value")) / 1e9, 2),
        "buy_r": buy_r,
        "sell_r": 100 - buy_r,
        "foreign_buy": int(quote_row.get("foreign_buy_volume") or 0),
        "foreign_sell": int(quote_row.get("foreign_sell_volume") or 0),
        "foreign_room": int(quote_row.get("foreign_room") or 0),
        "bid_book": bid_book,
        "ask_book": ask_book,
    }


def parse_eod_price_block(
    rows: list[StockOHLCVDaily],
    exchange: str = "HOSE",
) -> dict[str, Any]:
    """Domain Policy: Tính toán khối giá và biên độ trần/sàn từ nến ngày EOD."""
    if not rows:
        return {
            "last_p": 0.0,
            "ref_p": 0.0,
            "chg": 0.0,
            "pct": 0.0,
            "ceil_p": 0.0,
            "flr_p": 0.0,
            "high_p": 0.0,
            "low_p": 0.0,
            "vol": 0,
            "val_bil": 0.0,
            "buy_r": 0,
            "sell_r": 0,
            "foreign_buy": 0,
            "foreign_sell": 0,
            "foreign_room": 0,
            "bid_book": [],
            "ask_book": [],
        }

    latest = rows[0]
    prev = rows[1] if len(rows) > 1 else latest

    last_p = float(latest.close)
    ref_p = float(prev.close) if len(rows) > 1 else float(latest.open)
    chg = round(last_p - ref_p, 2)
    pct = round((chg / ref_p) * 100, 2) if ref_p else 0.0

    ratio = 0.07 if exchange == "HOSE" else 0.10 if exchange == "HNX" else 0.15
    ceil_p = round(ref_p * (1 + ratio), 2)
    flr_p = round(ref_p * (1 - ratio), 2)

    vol = int(latest.volume)
    val_bil = round(
        latest.value / 1e9 if latest.value else (last_p * vol * 1000 / 1e9), 2
    )

    if latest.buy_volume and latest.sell_volume:
        tot = latest.buy_volume + latest.sell_volume
        buy_r = int(latest.buy_volume / tot * 100) if tot else 0
        sell_r = 100 - buy_r
    else:
        buy_r, sell_r = 0, 0

    return {
        "last_p": last_p,
        "ref_p": ref_p,
        "chg": chg,
        "pct": pct,
        "ceil_p": ceil_p,
        "flr_p": flr_p,
        "high_p": float(latest.high),
        "low_p": float(latest.low),
        "vol": vol,
        "val_bil": val_bil,
        "buy_r": buy_r,
        "sell_r": sell_r,
        "foreign_buy": int(latest.foreign_buy_volume or 0),
        "foreign_sell": int(latest.foreign_sell_volume or 0),
        "foreign_room": 0,
        "bid_book": [],
        "ask_book": [],
    }


def make_stock_row(
    symbol: str,
    name: str,
    exchange: str,
    blk: dict[str, Any],
    sparkline: list[float],
    category: str = "listed",
    sector: str | None = None,
    expiry_date: str | None = None,
) -> IBoardStockRow:
    """Domain Factory: Khởi tạo IBoardStockRow theo format chuẩn, loại bỏ trùng lặp."""
    last_p = blk["last_p"]
    ceil_p = blk["ceil_p"]
    flr_p = blk["flr_p"]
    high_p = blk["high_p"]
    low_p = blk["low_p"]
    chg = blk["chg"]

    return IBoardStockRow(
        symbol=symbol,
        name=name,
        exchange=exchange,
        last_price=last_p,
        ref_price=blk["ref_p"],
        ceiling_price=ceil_p,
        floor_price=flr_p,
        high_price=high_p,
        low_price=low_p,
        avg_price=round((high_p + low_p) / 2, 2 if category != "derivatives" else 1),
        change=chg,
        change_percent=blk["pct"],
        volume=blk["vol"],
        value_billion=blk["val_bil"],
        buy_ratio=blk.get("buy_r", 0),
        sell_ratio=blk.get("sell_r", 0),
        foreign_buy=blk.get("foreign_buy", 0),
        foreign_sell=blk.get("foreign_sell", 0),
        foreign_room=blk.get("foreign_room", 0),
        status=classify_price_status(last_p, ceil_p, flr_p, chg),
        sparkline=sparkline,
        bid_book=blk.get("bid_book", []),
        ask_book=blk.get("ask_book", []),
        category=category,
        sector=sector,
        expiry_date=expiry_date,
    )


def compute_market_breadth(
    today_bars: dict[str, StockOHLCVDaily],
    prev_bars: dict[str, StockOHLCVDaily],
    subset: set[str],
    is_hnx: bool = False,
) -> IBoardIndexBreadth:
    """Domain Calculation: Tính toán độ rộng thị trường (tăng/giảm/trần/sàn/tham chiếu)."""
    adv = ceil = unch = dec = flr = 0
    ceil_mult = 1.10 if is_hnx else 1.07
    flr_mult = 0.90 if is_hnx else 0.93

    for s in subset:
        if s in today_bars and s in prev_bars:
            cur_p = today_bars[s].close
            pre_p = prev_bars[s].close
            if pre_p <= 0:
                continue
            chg_s = cur_p - pre_p
            c_ceil = round(pre_p * ceil_mult, 2)
            c_flr = round(pre_p * flr_mult, 2)
            if cur_p >= c_ceil:
                ceil += 1
                adv += 1
            elif cur_p <= c_flr:
                flr += 1
                dec += 1
            elif chg_s > 0:
                adv += 1
            elif chg_s < 0:
                dec += 1
            else:
                unch += 1

    return IBoardIndexBreadth(
        advance=adv, ceiling=ceil, unchanged=unch, decline=dec, floor=flr
    )
