"""Infrastructure Adapters for External Market Indices & Intraday Sparklines.

Sử dụng độc quyền VnstockService từ app.domains.vnstock (tuân thủ Rule 4, 7 & kiến trúc miền).
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta
from math import isfinite
from typing import Any
from zoneinfo import ZoneInfo

from sqlmodel import Session, col, select

from app.core.cache import realtime_cache
from app.core.enums import MarketIndex
from app.domains.market_data.domain.models import StockOHLCVDaily
from app.domains.vnstock import VnstockService

logger = logging.getLogger(__name__)
VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")


class IndexSparklineGateway:
    """Gateway quản lý nến 1m sparkline qua VnstockService độc quyền."""

    _mem_cache: dict[str, Any] = {}

    @staticmethod
    def _build_360_slots(
        time_value_pairs: list[tuple[datetime, float]],
    ) -> list[float | None]:
        """Xây dựng dải 360 phút (09:00 -> 15:00, slots 0..359).

        Quy chuẩn phiên giao dịch Việt Nam:
        - 09:00 đến 11:30 (slots 0..150 · 151 slots): Nến 1m phiên sáng.
        - 11:31 đến 12:59 (slots 151..239 · 89 slots): Giờ nghỉ trưa giữ nguyên giá trị
          ở slot 150 (chốt 11:30) xuyên suốt tới 239 tạo thành đường thẳng nằm ngang.
        - 13:00 đến 14:45 (slots 240..345 · 106 slots): Nến 1m phiên chiều + ATC.
        - 14:46 đến 14:59 (slots 346..359 · 14 slots): Giữ giá chốt ATC sau 14:45 đến hết ngày.
        - Nếu nến sau không đổi / không có giao dịch thì giữ nguyên giá trị nến trước đó (forward-fill).
        """
        slots: list[float | None] = [None] * 360

        for dt, val in time_value_pairs:
            if dt.tzinfo is None:
                dt_vn = dt.replace(tzinfo=VN_TZ)
            else:
                dt_vn = dt.astimezone(VN_TZ)
            m = (dt_vn.hour - 9) * 60 + dt_vn.minute

            if 0 <= m < 360 and not (151 <= m <= 239):
                slots[m] = round(float(val), 2)

        first_known_morning = next(
            (slots[m] for m in range(0, 151) if slots[m] is not None), None
        )
        if first_known_morning is not None:
            for m in range(0, 151):
                if slots[m] is None:
                    slots[m] = first_known_morning
                else:
                    break

        last_val: float | None = None
        for m in range(0, 151):
            if slots[m] is not None:
                last_val = slots[m]
            elif last_val is not None:
                slots[m] = last_val

            val_150 = slots[150]
        if val_150 is not None:
            for m in range(151, 240):
                slots[m] = val_150
            last_val = val_150

        has_afternoon = any(slots[m] is not None for m in range(240, 360))
        if has_afternoon:
            first_afternoon = next(
                (slots[m] for m in range(240, 346) if slots[m] is not None),
                last_val,
            )
            if first_afternoon is not None:
                for m in range(240, 346):
                    if slots[m] is None:
                        slots[m] = first_afternoon
                    else:
                        break

            for m in range(240, 346):
                if slots[m] is not None:
                    last_val = slots[m]
                elif last_val is not None:
                    slots[m] = last_val

            if last_val is not None:
                for m in range(346, 360):
                    if slots[m] is None:
                        slots[m] = last_val

        return slots

    @classmethod
    def get_sparkline(
        cls,
        code: str,
        vn: VnstockService,
        fallback_daily: list[float] | None = None,
        cur_close: float | None = None,
    ) -> list[float | None]:
        """Lấy chuỗi giá 1m intraday 360 slots cho mã chỉ số hoặc phái sinh qua VnstockService."""
        now = time.time()
        cached = cls._mem_cache.get(code)
        if cached and (now - cached["timestamp"] < 60):
            return cached["sparkline"]

        today = datetime.now(VN_TZ).date()
        start_date = today - timedelta(days=2)

        if code == MarketIndex.VN30F1M:
            try:
                df = vn.fetch_price_history(
                    symbol=code,
                    start=start_date,
                    end=today,
                    count=380,
                    interval="1m",
                )
                if (
                    df is not None
                    and not df.empty
                    and "close" in df.columns
                    and "time" in df.columns
                ):
                    pairs: list[tuple[datetime, float]] = []
                    for _, row in df.iterrows():
                        t_val = row.get("time")
                        c_val = row.get("close")
                        if t_val is None or c_val is None:
                            continue
                        try:
                            close = float(c_val)
                        except (TypeError, ValueError):
                            continue
                        if not isfinite(close):
                            continue
                        try:
                            dt = (
                                t_val
                                if isinstance(t_val, datetime)
                                else datetime.fromisoformat(str(t_val))
                            )
                        except (TypeError, ValueError):
                            continue
                        pairs.append((dt, close))

                    if pairs:
                        latest_date = max(p[0].date() for p in pairs)
                        session_pairs = [p for p in pairs if p[0].date() == latest_date]
                        session_pairs.sort(key=lambda x: x[0])
                        slots = cls._build_360_slots(session_pairs)
                        cls._mem_cache[code] = {
                            "timestamp": now,
                            "sparkline": slots,
                        }
                        return slots
            except Exception as e:
                logger.debug("Không thể tải nến 1m cho VN30F1M: %s", e)

        try:
            df = vn.fetch_index_ohlcv(
                symbol=code,
                interval="1m",
                count=380,
            )
            if (
                df is not None
                and not df.empty
                and "close" in df.columns
                and "time" in df.columns
            ):
                pairs = []
                for _, row in df.iterrows():
                    t_val = row.get("time")
                    c_val = row.get("close")
                    if t_val is None or c_val is None:
                        continue
                    try:
                        close = float(c_val)
                    except (TypeError, ValueError):
                        continue
                    if not isfinite(close):
                        continue
                    try:
                        dt = (
                            t_val
                            if isinstance(t_val, datetime)
                            else datetime.fromisoformat(str(t_val))
                        )
                    except (TypeError, ValueError):
                        continue
                    pairs.append((dt, close))

                if pairs:
                    latest_date = max(p[0].date() for p in pairs)
                    session_pairs = [p for p in pairs if p[0].date() == latest_date]
                    session_pairs.sort(key=lambda x: x[0])
                    slots = cls._build_360_slots(session_pairs)
                    cls._mem_cache[code] = {
                        "timestamp": now,
                        "sparkline": slots,
                    }
                    return slots
        except Exception as e:
            logger.debug("Không thể tải nến 1m cho %s: %s", code, e)

        cls._mem_cache[code] = {
            "timestamp": now - 45,
            "sparkline": [],
        }
        return []


class IBoardDataGateway:
    """Gateway truy vấn dữ liệu kết hợp DB PostgreSQL và VnstockService (Rule 7.2)."""

    @classmethod
    def backfill_ohlcv_daily(
        cls,
        session: Session,
        vn: VnstockService,
        symbol: str,
        target_count: int = 100,
    ) -> list[StockOHLCVDaily]:
        """Truy xuất nến ngày từ PostgreSQL; chỉ gọi vnstock nếu DB hoàn toàn rỗng."""
        rows: list[StockOHLCVDaily] = list(
            session.exec(
                select(StockOHLCVDaily)
                .where(StockOHLCVDaily.symbol == symbol)
                .order_by(col(StockOHLCVDaily.trading_date).desc())
                .limit(target_count)
            ).all()
        )

        today = datetime.now(VN_TZ).date()
        needs_fetch = len(rows) == 0

        if needs_fetch:
            try:
                fetch_sym = (
                    MarketIndex.UPCOMINDEX
                    if symbol.upper() in (MarketIndex.UPCOM, MarketIndex.UPCOMINDEX)
                    else (
                        MarketIndex.HNXINDEX
                        if symbol.upper() == MarketIndex.HNX
                        else symbol
                    )
                )
                start_date = today - timedelta(days=max(target_count * 2, 220))
                df = vn.fetch_price_history(
                    fetch_sym,
                    start=start_date,
                    end=today,
                    count=target_count,
                    interval="1D",
                )
                if df is not None and not df.empty:
                    existing = {r.trading_date for r in rows}
                    new_entities = []
                    for _, r in df.iterrows():
                        t_str = str(r["time"])[:10]
                        try:
                            t_date = datetime.strptime(t_str, "%Y-%m-%d").date()
                        except ValueError:
                            continue
                        if t_date not in existing:
                            new_row = StockOHLCVDaily(
                                symbol=symbol,
                                trading_date=t_date,
                                open=float(r["open"]),
                                high=float(r["high"]),
                                low=float(r["low"]),
                                close=float(r["close"]),
                                volume=int(r["volume"]),
                                value=float(r.get("value", 0) or 0),
                                source=vn.last_successful_source or "vci",
                            )
                            rows.append(new_row)
                            new_entities.append(new_row)
                            existing.add(t_date)
                    if new_entities:
                        try:
                            session.add_all(new_entities)
                            session.commit()
                        except Exception as ce:
                            session.rollback()
                            logger.debug("Không thể commit nến mới vào DB: %s", ce)

                    rows.sort(key=lambda x: x.trading_date, reverse=True)
                    rows = rows[:target_count]
            except Exception as e:
                logger.debug("Không thể đọc thêm nến EOD cho %s: %s", symbol, e)

        return rows

    @staticmethod
    def fetch_batch_quotes(
        vn: VnstockService | None, symbols: list[str]
    ) -> dict[str, Any]:
        """Tải bảng giá realtime snapshot hàng loạt ưu tiên DNSE realtime stream."""
        if not symbols:
            return {}

        results: dict[str, Any] = {}
        missing: list[str] = []

        for s in symbols:
            sym = s.strip().upper()
            cached = realtime_cache.get(f"iboard_quote:{sym}")
            if (
                cached
                and isinstance(cached, dict)
                and cached.get("close_price") is not None
            ):
                results[sym] = cached
            else:
                missing.append(sym)

        if missing and vn is not None:
            try:
                quotes_df = vn.fetch_market_quote(missing)
                if quotes_df is not None and not quotes_df.empty:
                    for _, row in quotes_df.iterrows():
                        sym = str(row.get("symbol") or row.get("ticker") or "").upper()
                        if sym:
                            q_dict = row.to_dict()
                            results[sym] = q_dict
                            realtime_cache.set(f"iboard_quote:{sym}", q_dict, ttl=5)
            except Exception as e:
                logger.debug("Lỗi tải snapshot hàng loạt qua VnstockService: %s", e)

        return results


__all__ = [
    "IBoardDataGateway",
    "IndexSparklineGateway",
]
