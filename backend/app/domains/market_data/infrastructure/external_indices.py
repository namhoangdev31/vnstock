"""Infrastructure Adapters for External Market Indices & Intraday Sparklines.

Tuân thủ Clean Architecture:
- Đóng gói toàn bộ các tác vụ I/O, network calls ra ngoài (Yahoo Finance, disk file cache).
- Cách ly Application Service khỏi các chi tiết giao thức HTTP và filesystem.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlmodel import Session, col, select

from app.domains.market_data.application.iboard_schemas import IBoardIndexItem
from app.domains.market_data.domain.models import StockOHLCVDaily
from app.domains.market_data.infrastructure.vnstock_adapter import VnstockService

logger = logging.getLogger(__name__)


class DowJonesGateway:
    """Gateway truy xuất dữ liệu Dow Jones Futures (YM=F) từ Yahoo Finance với in-memory TTL cache."""

    _cache: dict[str, Any] = {}

    @classmethod
    def get_futures_item(cls) -> IBoardIndexItem | None:
        """Truy xuất snapshot Dow Jones Futures thực; trả về None khi lỗi (không bịa số)."""
        now = time.time()
        cached = cls._cache.get("dji")
        if cached and (now - cached["timestamp"] < 60):
            return cached["item"]

        try:
            url = "https://query1.finance.yahoo.com/v8/finance/chart/YM=F?interval=1d&range=3mo"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode())["chart"]["result"][0]
                meta = data["meta"]
                price = float(meta.get("regularMarketPrice") or 0.0)
                raw_closes = [
                    round(float(c), 2)
                    for c in data["indicators"]["quote"][0]["close"]
                    if c is not None
                ]
                prev_close = (
                    raw_closes[-2]
                    if len(raw_closes) >= 2
                    else float(meta.get("chartPreviousClose") or price)
                )
                chg = price - prev_close
                pct = (chg / prev_close * 100) if prev_close else 0.0
                spark = raw_closes[-50:] if len(raw_closes) >= 50 else raw_closes

                item = IBoardIndexItem(
                    id="dji",
                    name="DOW JONES FUTURES",
                    price=f"{price:,.2f}",
                    change=f"{chg:+,.2f}",
                    change_percent=f"{pct:+,.2f}%",
                    is_positive=chg >= 0,
                    is_unchanged=chg == 0,
                    volume="-",
                    value="-",
                    breadth=None,
                    sparkline=spark,
                )
                cls._cache["dji"] = {"timestamp": now, "item": item}
                return item
        except Exception as e:
            logger.debug("Không thể tải Dow Jones Futures online: %s", e)

        return cached["item"] if cached else None

    get_dow_jones_futures = get_futures_item


class IndexSparklineGateway:
    """Gateway quản lý nến 1m sparkline cho dải chỉ số thị trường (disk cache + live API)."""

    _mem_cache: dict[str, Any] = {}

    @classmethod
    def get_sparkline(
        cls,
        code: str,
        vn: VnstockService,
        fallback_daily: list[float],
        cur_close: float,
    ) -> list[float]:
        now = time.time()
        cached = cls._mem_cache.get(code)
        if cached and (now - cached["timestamp"] < 300):
            return cached["sparkline"]

        # 1. Thử disk cache
        cache_file = Path("data/index_intraday_cache.json")
        if cache_file.exists():
            try:
                disk_cache = json.loads(cache_file.read_text())
                if code in disk_cache and len(disk_cache[code]) >= 5:
                    spark = disk_cache[code][-50:]
                    cls._mem_cache[code] = {
                        "timestamp": now,
                        "sparkline": spark,
                    }
                    return spark
            except Exception:
                pass

        # 2. Thử fetch qua VnstockService
        try:
            today = date.today()
            df = vn.fetch_index_ohlcv(
                symbol=code, start=today, end=today, interval="1m", count=80
            )
            if df is not None and not df.empty and "close" in df.columns:
                pts = [round(float(c), 2) for c in df["close"] if c is not None]
                if pts:
                    spark = pts[-50:] if len(pts) >= 50 else pts
                    cls._mem_cache[code] = {
                        "timestamp": now,
                        "sparkline": spark,
                    }
                    return spark
        except Exception as e:
            logger.debug("Không thể tải nến 1m cho %s: %s", code, e)

        return fallback_daily[-30:] if len(fallback_daily) >= 30 else fallback_daily


class IBoardDataGateway:
    """Gateway truy vấn dữ liệu kết hợp DB PostgreSQL và VnstockService (Rule 7.2)."""

    @staticmethod
    def backfill_ohlcv_daily(
        session: Session,
        vn: VnstockService,
        symbol: str,
        target_count: int = 100,
    ) -> list[StockOHLCVDaily]:
        """Truy xuất nến ngày từ PostgreSQL; tự động backfill từ VnstockService nếu thiếu."""
        rows: list[StockOHLCVDaily] = list(
            session.exec(
                select(StockOHLCVDaily)
                .where(StockOHLCVDaily.symbol == symbol)
                .order_by(col(StockOHLCVDaily.trading_date).desc())
                .limit(target_count)
            ).all()
        )

        if len(rows) < target_count:
            try:
                today = date.today()
                df = vn.fetch_price_history(
                    symbol,
                    start=today - timedelta(days=max(target_count * 2, 220)),
                    end=today,
                    count=target_count,
                    interval="1D",
                )
                if df is not None and not df.empty:
                    existing = {r.trading_date for r in rows}
                    for _, r in df.iterrows():
                        t_str = str(r["time"])[:10]
                        try:
                            t_date = datetime.strptime(t_str, "%Y-%m-%d").date()
                        except ValueError:
                            continue
                        if t_date not in existing:
                            session.add(
                                StockOHLCVDaily(
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
                            )
                            existing.add(t_date)
                    session.commit()
                    rows = list(
                        session.exec(
                            select(StockOHLCVDaily)
                            .where(StockOHLCVDaily.symbol == symbol)
                            .order_by(col(StockOHLCVDaily.trading_date).desc())
                            .limit(target_count)
                        ).all()
                    )
            except Exception as e:
                logger.warning("Không thể bổ sung nến EOD cho %s: %s", symbol, e)

        return rows

    @staticmethod
    def fetch_batch_quotes(vn: VnstockService, symbols: list[str]) -> dict[str, Any]:
        """Tải bảng giá realtime snapshot hàng loạt cho danh sách mã."""
        if not symbols:
            return {}
        try:
            df = vn.fetch_market_quote(symbols)
            if df is not None and not df.empty and "symbol" in df.columns:
                return {
                    str(row["symbol"]).strip().upper(): row for _, row in df.iterrows()
                }
        except Exception as e:
            logger.warning("fetch_market_quote batch thất bại: %s", e)
        return {}
