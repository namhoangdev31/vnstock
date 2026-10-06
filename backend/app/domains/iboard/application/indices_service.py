"""Application Service / Use Case: Market Indices retrieval for iBoard.

Quản lý dải chỉ số thị trường: VN30, VNINDEX, HNX30, VN30F1M, HNX-INDEX, và DOW JONES FUTURES.
"""

from __future__ import annotations

from typing import Any

from sqlmodel import Session, col, select

from app.core.cache import realtime_cache
from app.domains.iboard.application.schemas import (
    IBoardIndexBreadth,
    IBoardIndexItem,
)
from app.domains.iboard.domain.policy import compute_market_breadth
from app.domains.iboard.infrastructure.external_indices import (
    DowJonesGateway,
    IBoardDataGateway,
    IndexSparklineGateway,
)
from app.domains.market_data.domain.models import StockOHLCVDaily, StockSymbol
from app.domains.vnstock import VnstockService


class IBoardIndicesService:
    """Use Case: Truy xuất dải chỉ số thị trường tính toán động từ DB & live API."""

    @classmethod
    def get_indices(cls, session: Session) -> list[IBoardIndexItem]:
        latest_bar = session.exec(
            select(StockOHLCVDaily)
            .order_by(col(StockOHLCVDaily.trading_date).desc())
            .limit(1)
        ).first()
        latest_date = latest_bar.trading_date if latest_bar else None

        prev_bar = (
            session.exec(
                select(StockOHLCVDaily)
                .where(col(StockOHLCVDaily.trading_date) < latest_date)
                .order_by(col(StockOHLCVDaily.trading_date).desc())
                .limit(1)
            ).first()
            if latest_date
            else None
        )
        prev_date = prev_bar.trading_date if prev_bar else None

        today_bars: dict[str, StockOHLCVDaily] = {}
        prev_bars: dict[str, StockOHLCVDaily] = {}
        if latest_date and prev_date:
            for b in session.exec(
                select(StockOHLCVDaily).where(
                    StockOHLCVDaily.trading_date == latest_date
                )
            ).all():
                today_bars[b.symbol] = b
            for b in session.exec(
                select(StockOHLCVDaily).where(StockOHLCVDaily.trading_date == prev_date)
            ).all():
                prev_bars[b.symbol] = b

        def _sym_set(col_attr: Any, val: str) -> set[str]:
            return {
                s.symbol
                for s in session.exec(select(StockSymbol).where(col_attr == val)).all()
            }

        vn30_symbols = _sym_set(StockSymbol.index_group, "VN30")
        hose_symbols = _sym_set(StockSymbol.exchange, "HOSE")
        hnx_symbols = _sym_set(StockSymbol.exchange, "HNX")
        hnx30_symbols = _sym_set(StockSymbol.index_group, "HNX30")

        vn = VnstockService(db_session=session)
        items: list[IBoardIndexItem] = []

        target_indices = [
            ("VN30", "vn30", "VN30", vn30_symbols),
            ("VNINDEX", "vnindex", "VNINDEX", hose_symbols),
            ("HNX30", "hnx30", "HNX30", hnx30_symbols),
            ("VN30F1M", "vn30f1m", "VN30F1M", set()),
            ("HNXINDEX", "hnx", "HNX-INDEX", hnx_symbols),
        ]

        basket_map: dict[str, set[str]] = {
            "VN30": vn30_symbols,
            "VNINDEX": hose_symbols,
            "HNX30": hnx30_symbols,
            "HNXINDEX": hnx_symbols,
        }

        for code, idx_id, display_name, subset in target_indices:
            daily_rows = IBoardDataGateway.backfill_ohlcv_daily(
                session, vn, code, target_count=100
            )
            if not daily_rows:
                continue

            latest = daily_rows[0]
            prev = daily_rows[1] if len(daily_rows) > 1 else latest
            cur_close = float(latest.close)
            prev_close = float(prev.close) if len(daily_rows) > 1 else cur_close
            chg = cur_close - prev_close
            pct = (chg / prev_close * 100) if prev_close else 0.0

            is_deriv = code == "VN30F1M"

            raw_vol = float(latest.volume)
            raw_val = float(latest.value or 0)

            # Check realtime DNSE cache for market index updates
            cached_idx = realtime_cache.get(f"index:{code}")
            if not cached_idx and code == "HNXINDEX":
                cached_idx = realtime_cache.get("index:HNX")
            elif not cached_idx and code == "VNINDEX":
                cached_idx = realtime_cache.get("index:HOSE")

            breadth: IBoardIndexBreadth
            if (
                cached_idx
                and isinstance(cached_idx, dict)
                and cached_idx.get("value") is not None
            ):
                cur_close = float(cached_idx["value"])
                if cached_idx.get("change") is not None:
                    chg = float(cached_idx["change"])
                if cached_idx.get("pct_change") is not None:
                    pct = float(cached_idx["pct_change"])
                if cached_idx.get("total_volume") is not None:
                    raw_vol = float(cached_idx["total_volume"])
                if cached_idx.get("total_value") is not None:
                    raw_val = float(cached_idx["total_value"])
                if cached_idx.get("advance") is not None:
                    breadth = IBoardIndexBreadth(
                        advance=int(cached_idx.get("advance") or 0),
                        ceiling=int(cached_idx.get("ceiling") or 0),
                        unchanged=int(cached_idx.get("no_change") or 0),
                        decline=int(cached_idx.get("decline") or 0),
                        floor=int(cached_idx.get("floor") or 0),
                    )
                else:
                    breadth = compute_market_breadth(
                        today_bars=today_bars,
                        prev_bars=prev_bars,
                        subset=subset,
                        is_hnx="HNX" in code,
                    )
            elif is_deriv:
                cached_rt = realtime_cache.get(
                    "realtime:VN30F1M"
                ) or realtime_cache.get("iboard_quote:VN30F1M")
                if cached_rt and isinstance(cached_rt, dict):
                    c_p = cached_rt.get("close") or cached_rt.get("close_price")
                    if c_p is not None:
                        cur_close = float(c_p)
                        chg = cur_close - prev_close
                        pct = (chg / prev_close * 100) if prev_close else 0.0
                        if cached_rt.get("volume") is not None:
                            raw_vol = float(cached_rt["volume"])
                        elif cached_rt.get("volume_accumulated") is not None:
                            raw_vol = float(cached_rt["volume_accumulated"])
                breadth = IBoardIndexBreadth(
                    advance=1 if chg > 0 else 0,
                    ceiling=0,
                    unchanged=1 if chg == 0 else 0,
                    decline=1 if chg < 0 else 0,
                    floor=0,
                )
            else:
                breadth = compute_market_breadth(
                    today_bars=today_bars,
                    prev_bars=prev_bars,
                    subset=subset,
                    is_hnx="HNX" in code,
                )

            price_str = f"{cur_close:,.1f}" if is_deriv else f"{cur_close:,.2f}"

            if raw_val <= 0 and code in basket_map:
                basket_sum = sum(
                    float(
                        today_bars[s].value
                        or (today_bars[s].close * today_bars[s].volume * 1000)
                    )
                    for s in basket_map[code]
                    if s in today_bars
                )
                if basket_sum > 0:
                    raw_val = basket_sum
            elif code == "VN30F1M" and raw_val <= 0 and raw_vol > 0:
                raw_val = cur_close * raw_vol * 100000

            if raw_val > 0:
                val_num = raw_val / 1e9
                if not is_deriv and val_num > 100_000:
                    val_num /= 1000
                val_str = f"{val_num:,.2f} Tỷ"
            else:
                val_str = "-"

            vol_str = (
                f"{int(raw_vol):,} HĐ"
                if is_deriv
                else f"{raw_vol / 1e6:,.2f} Triệu CP"
                if raw_vol > 0
                else "-"
            )

            fallback_spark = [float(r.close) for r in reversed(daily_rows)]
            sparkline = IndexSparklineGateway.get_sparkline(
                code=code,
                vn=vn,
                fallback_daily=fallback_spark,
                cur_close=cur_close,
            )

            items.append(
                IBoardIndexItem(
                    id=idx_id,
                    name=display_name,
                    price=price_str,
                    change=f"{chg:+,.2f}",
                    change_percent=f"{pct:+,.2f}%",
                    is_positive=chg >= 0,
                    is_unchanged=chg == 0,
                    volume=vol_str,
                    value=val_str,
                    breadth=breadth,
                    sparkline=sparkline,
                )
            )

        # Chèn Dow Jones Futures thực
        dji_item = DowJonesGateway.get_futures_item()
        if dji_item is not None:
            vnindex_pos = next(
                (i for i, it in enumerate(items) if it.id == "vnindex"), -1
            )
            if vnindex_pos >= 0:
                items.insert(vnindex_pos + 1, dji_item)
            else:
                items.append(dji_item)

        return items


__all__ = ["IBoardIndicesService"]
