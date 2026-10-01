"""Market data ingestion service — nạp dữ liệu thực tế vào 3 bảng Engine 2.

Bảng cần nạp:
  • macro_indicator    — tỷ giá USD/VND và giá vàng SJC (từ Retail)
  • market_breadth     — số mã tăng/giảm/không đổi trên HOSE (từ Market.equity.quote)
  • institutional_flow — dòng tiền ngoại (khối ngoại) theo từng mã VN30

Tất cả hàm đều idempotent (UPSERT dựa trên unique constraint).
Được gọi bởi scheduled_hooks.py trong POST_MARKET / OVERNIGHT.
Cũng có thể chạy trực tiếp:
    uv run python -m app.domains.quant.application.market_data_ingest [backfill_days]
"""

import logging
import time
from collections.abc import Callable
from datetime import date, datetime, timedelta
from typing import Any

from sqlmodel import Session, col, select

from app.core.enums import MacroIndicatorCode
from app.core.models_base import VN_TZ
from app.domains.quant.domain.models import (
    InstitutionalFlow,
    MacroIndicator,
    MarketBreadth,
)

logger = logging.getLogger(__name__)

# Community tier: 60 req/min → keep below 50 req/min with safety margin
_API_DELAY_S = 1.2  # live ingest: ~45 calls/min max for Community tier safety
_BACKFILL_DELAY_S = 1.5  # backfill: ~40 calls/min — safe for 30-day history


def _safe_call(fn: Callable, label: str, delay: float = _API_DELAY_S) -> Any:
    """Gọi fn() 1 lần, log lỗi nhưng không raise."""
    time.sleep(delay)
    try:
        return fn()
    except (Exception, SystemExit) as exc:  # noqa: BLE001
        logger.warning("[ingest] %s failed: %s", label, exc)
        return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _upsert_macro(
    session: Session,
    recorded_date: date,
    indicator_code: str,
    value: float,
    change_pct: float | None,
    source: str,
) -> None:
    existing = session.exec(
        select(MacroIndicator).where(
            MacroIndicator.indicator_code == indicator_code,
            MacroIndicator.recorded_date == recorded_date,
            MacroIndicator.source == source,
        )
    ).first()
    if existing:
        existing.value = value
        existing.change_pct = change_pct
        session.add(existing)
    else:
        session.add(
            MacroIndicator(
                recorded_date=recorded_date,
                indicator_code=indicator_code,
                value=value,
                change_pct=change_pct,
                source=source,
            )
        )


def _recalculate_change_pct(session: Session, indicator_code: str) -> None:
    rows = session.exec(
        select(MacroIndicator)
        .where(MacroIndicator.indicator_code == indicator_code)
        .order_by(col(MacroIndicator.recorded_date).asc())
    ).all()
    prev_val: float | None = None
    for row in rows:
        if prev_val is not None and prev_val > 0:
            row.change_pct = round((row.value - prev_val) / prev_val * 100, 4)
        prev_val = row.value
        session.add(row)


def _get_col(df_cols: list[str], candidates: list[str]) -> str | None:
    df_lower = [c.lower().strip() for c in df_cols]
    for cand in candidates:
        if cand in df_lower:
            return df_cols[df_lower.index(cand)]
    return None


# ---------------------------------------------------------------------------
# 1. macro_indicator
# ---------------------------------------------------------------------------


def ingest_macro_indicators(
    session: Session,
    trading_date: date | None = None,
) -> dict[str, int]:
    """Nạp tỷ giá USD/VND và giá vàng SJC cho ngày trading_date (mặc định hôm nay)."""
    from app.domains.market_data.infrastructure.vnstock_adapter import vnstock_service

    today = trading_date or datetime.now(VN_TZ).date()
    counts: dict[str, int] = {"usd_vnd": 0, "sjc_buy": 0, "sjc_sell": 0}

    # USD/VND
    df_fx = _safe_call(
        lambda: vnstock_service.fetch_retail_exchange_rate(),
        "fetch_retail_exchange_rate",
    )
    if df_fx is not None and not df_fx.empty:
        df_fx.columns = [c.lower().strip() for c in df_fx.columns]
        id_col = _get_col(
            list(df_fx.columns),
            ["currency_code", "currency", "code", "name", "currency_name"],
        )
        if id_col:
            mask = df_fx[id_col].astype(str).str.upper().str.contains("USD")
            if mask.any():
                row = df_fx[mask].iloc[0]
                val_col = _get_col(
                    list(row.index),
                    ["sell", "sell_cash", "sell_transfer", "buy_transfer", "buy"],
                )
                if val_col:
                    try:
                        raw_val = str(row[val_col]).replace(",", "").strip()
                        usd_val = float(raw_val)
                        if usd_val > 0:
                            prev = session.exec(
                                select(MacroIndicator)
                                .where(
                                    MacroIndicator.indicator_code
                                    == MacroIndicatorCode.USD_VND
                                )
                                .order_by(col(MacroIndicator.recorded_date).desc())
                                .limit(1)
                            ).first()
                            chg = (
                                round((usd_val - prev.value) / prev.value * 100, 4)
                                if prev and prev.value > 0
                                else None
                            )
                            _upsert_macro(
                                session,
                                today,
                                MacroIndicatorCode.USD_VND,
                                usd_val,
                                chg,
                                "vcb",
                            )
                            counts["usd_vnd"] += 1
                    except (ValueError, TypeError):
                        pass

    # SJC gold
    df_gold = _safe_call(
        lambda: vnstock_service.fetch_retail_gold(source="sjc"),
        "fetch_retail_gold(sjc)",
    )
    if df_gold is not None and not df_gold.empty:
        df_gold.columns = [c.lower().strip() for c in df_gold.columns]
        buy_col = _get_col(
            list(df_gold.columns), ["buy", "buy_price", "gia_mua", "mua"]
        )
        sell_col = _get_col(
            list(df_gold.columns), ["sell", "sell_price", "gia_ban", "ban"]
        )

        for code, col_name, count_key in [
            (MacroIndicatorCode.SJC_GOLD_BUY, buy_col, "sjc_buy"),
            (MacroIndicatorCode.SJC_GOLD_SELL, sell_col, "sjc_sell"),
        ]:
            if col_name is None:
                continue
            try:
                gold_val = float(df_gold[col_name].iloc[0])
                if gold_val > 0:
                    prev = session.exec(
                        select(MacroIndicator)
                        .where(MacroIndicator.indicator_code == code)
                        .order_by(col(MacroIndicator.recorded_date).desc())
                        .limit(1)
                    ).first()
                    chg = (
                        round((gold_val - prev.value) / prev.value * 100, 4)
                        if prev and prev.value > 0
                        else None
                    )
                    _upsert_macro(session, today, code, gold_val, chg, "sjc")
                    counts[count_key] += 1
            except (ValueError, TypeError):
                pass

    if counts["sjc_buy"] == 0 and counts["sjc_sell"] == 0:
        logger.info(
            "[ingest] SJC gold feed unavailable (upstream 403 or timeout); existing DB indicators retained"
        )
    session.commit()
    logger.info("[ingest] macro_indicator: %s for %s", counts, today)
    return counts


# ---------------------------------------------------------------------------
# 2. market_breadth
# ---------------------------------------------------------------------------


def ingest_market_breadth(
    session: Session,
    trading_date: date | None = None,
    exchange: str = "HOSE",
) -> int:
    """Nạp độ rộng thị trường từ bảng giá VN30 hôm nay."""
    from app.domains.market_data.infrastructure.vnstock_adapter import vnstock_service

    today = trading_date or datetime.now(VN_TZ).date()

    symbols = _safe_call(
        lambda: vnstock_service.fetch_group_symbols("VN30"),
        "fetch_group_symbols(VN30)",
    )
    if not symbols:
        logger.warning("[ingest] market_breadth: no symbols")
        return 0

    advancers = decliners = unchanged = ceiling = floor_ = 0
    total_vol = 0
    total_val = 0.0

    for sym in list(symbols):
        df_q = _safe_call(
            lambda s=sym: vnstock_service.fetch_market_equity_quote(s),
            f"breadth_quote:{sym}",
        )
        if df_q is None or df_q.empty:
            continue
        df_q.columns = [c.lower().strip() for c in df_q.columns]

        chg_col = _get_col(
            list(df_q.columns),
            # actual vnstock column is 'percent_change'
            ["percent_change", "change_percent", "change_pct", "pct_change", "change"],
        )
        if chg_col is None:
            continue

        try:
            chg = float(df_q[chg_col].iloc[0])
        except (ValueError, TypeError):
            continue

        if chg >= 6.9:
            ceiling += 1
            advancers += 1
        elif chg <= -6.9:
            floor_ += 1
            decliners += 1
        elif chg > 0:
            advancers += 1
        elif chg < 0:
            decliners += 1
        else:
            unchanged += 1

        vol_col = _get_col(
            list(df_q.columns), ["volume_accumulated", "volume", "vol", "match_volume"]
        )
        val_col = _get_col(list(df_q.columns), ["total_value", "value", "match_value"])
        try:
            if vol_col:
                total_vol += int(float(df_q[vol_col].iloc[0]))
        except (ValueError, TypeError):
            pass
        try:
            if val_col:
                total_val += float(df_q[val_col].iloc[0])
        except (ValueError, TypeError):
            pass

    if advancers + decliners + unchanged == 0:
        logger.warning("[ingest] market_breadth: no quote data for %s", today)
        return 0

    existing = session.exec(
        select(MarketBreadth).where(
            MarketBreadth.trading_date == today,
            MarketBreadth.exchange == exchange,
        )
    ).first()

    if existing:
        existing.advancers = advancers
        existing.decliners = decliners
        existing.unchanged = unchanged
        existing.ceiling_count = ceiling
        existing.floor_count = floor_
        existing.total_volume = total_vol
        existing.total_value = total_val
        session.add(existing)
    else:
        session.add(
            MarketBreadth(
                trading_date=today,
                exchange=exchange,
                advancers=advancers,
                decliners=decliners,
                unchanged=unchanged,
                ceiling_count=ceiling,
                floor_count=floor_,
                total_volume=total_vol,
                total_value=total_val,
            )
        )

    session.commit()
    logger.info(
        "[ingest] market_breadth %s: adv=%d dec=%d unch=%d ceil=%d floor=%d",
        today,
        advancers,
        decliners,
        unchanged,
        ceiling,
        floor_,
    )
    return 1


# ---------------------------------------------------------------------------
# 3. institutional_flow
# ---------------------------------------------------------------------------


def ingest_institutional_flows(
    session: Session,
    trading_date: date | None = None,
    symbols: list[str] | None = None,
) -> int:
    """Nạp dòng tiền khối ngoại từ Market.equity.quote() cho từng mã VN30."""
    from app.domains.market_data.infrastructure.vnstock_adapter import vnstock_service

    today = trading_date or datetime.now(VN_TZ).date()
    upserted = 0

    if symbols is None:
        raw = _safe_call(
            lambda: vnstock_service.fetch_group_symbols("VN30"),
            "fetch_group_symbols(VN30) flows",
        )
        symbols = list(raw) if raw else []

    if not symbols:
        return 0

    for sym in symbols:
        df_q = _safe_call(
            lambda s=sym: vnstock_service.fetch_market_equity_quote(s),
            f"flow_quote:{sym}",
        )
        if df_q is None or df_q.empty:
            continue
        df_q.columns = [c.lower().strip() for c in df_q.columns]

        def _g(names: list[str], df: Any = df_q) -> float | None:
            c = _get_col(list(df.columns), names)
            if c is None:
                return None
            try:
                return float(df[c].iloc[0])
            except (ValueError, TypeError):
                return None

        fb_vol = _g(["foreign_buy_volume", "buy_foreign_vol", "fb_vol", "nn_mua"])
        fs_vol = _g(["foreign_sell_volume", "sell_foreign_vol", "fs_vol", "nn_ban"])
        fb_val = _g(["foreign_buy_value", "buy_foreign_val"])
        fs_val = _g(["foreign_sell_value", "sell_foreign_val"])
        # 'foreign_room' in per-symbol quote = remaining (current) room
        fr_current = _g(
            ["foreign_room", "room_current", "foreign_room_current", "con_room"]
        )
        fr_total: float | None = None  # not returned by per-symbol quote API

        if all(v is None for v in (fb_vol, fs_vol, fb_val, fs_val)):
            continue

        fn_vol = (
            int(fb_vol - fs_vol) if fb_vol is not None and fs_vol is not None else None
        )
        fn_val = (
            round(fb_val - fs_val, 2)
            if fb_val is not None and fs_val is not None
            else None
        )
        fr_pct: float | None = None

        existing = session.exec(
            select(InstitutionalFlow).where(
                InstitutionalFlow.trading_date == today,
                InstitutionalFlow.symbol == sym,
                InstitutionalFlow.source == "vci",
            )
        ).first()

        kwargs: dict = {
            "foreign_buy_volume": int(fb_vol) if fb_vol is not None else None,
            "foreign_sell_volume": int(fs_vol) if fs_vol is not None else None,
            "foreign_net_volume": fn_vol,
            "foreign_buy_value": fb_val,
            "foreign_sell_value": fs_val,
            "foreign_net_value": fn_val,
            "foreign_room_total": fr_total,
            "foreign_room_current": fr_current,
            "foreign_room_pct": fr_pct,
        }
        if existing:
            for k, v in kwargs.items():
                setattr(existing, k, v)
            session.add(existing)
        else:
            session.add(
                InstitutionalFlow(
                    trading_date=today, symbol=sym, source="vci", **kwargs
                )
            )
        upserted += 1

    session.commit()
    logger.info(
        "[ingest] institutional_flow: %d/%d upserted for %s",
        upserted,
        len(symbols),
        today,
    )
    return upserted


# ---------------------------------------------------------------------------
# 4. Backfill macro lịch sử
# ---------------------------------------------------------------------------


def backfill_macro_indicators(session: Session, days: int = 30) -> int:
    """Nạp macro history N ngày gần nhất (bỏ qua cuối tuần)."""
    from app.domains.market_data.infrastructure.vnstock_adapter import vnstock_service

    today = datetime.now(VN_TZ).date()
    total = 0

    for i in range(days - 1, -1, -1):
        d = today - timedelta(days=i)
        if d.weekday() >= 5:
            continue

        df_fx = _safe_call(
            lambda dt=d: vnstock_service.fetch_retail_exchange_rate(date=str(dt)),
            f"fx_hist:{d}",
            delay=_BACKFILL_DELAY_S,
        )
        if df_fx is not None and not df_fx.empty:
            df_fx.columns = [c.lower().strip() for c in df_fx.columns]
            id_col = _get_col(
                list(df_fx.columns),
                ["currency_code", "currency", "code", "name", "currency_name"],
            )
            if id_col:
                mask = df_fx[id_col].astype(str).str.upper().str.contains("USD")
                if mask.any():
                    row = df_fx[mask].iloc[0]
                    val_col = _get_col(
                        list(row.index), ["sell", "sell_cash", "buy_transfer", "buy"]
                    )
                    if val_col:
                        try:
                            raw = str(row[val_col]).replace(",", "").strip()
                            v = float(raw)
                            if v > 0:
                                _upsert_macro(
                                    session,
                                    d,
                                    MacroIndicatorCode.USD_VND,
                                    v,
                                    None,
                                    "vcb",
                                )
                                total += 1
                        except (ValueError, TypeError):
                            pass

        df_gold = _safe_call(
            lambda dt=d: vnstock_service.fetch_retail_gold(source="sjc", date=str(dt)),
            f"gold_hist:{d}",
            delay=_BACKFILL_DELAY_S,
        )
        if df_gold is not None and not df_gold.empty:
            df_gold.columns = [c.lower().strip() for c in df_gold.columns]
            buy_col = _get_col(
                list(df_gold.columns), ["buy", "buy_price", "gia_mua", "mua"]
            )
            sell_col = _get_col(
                list(df_gold.columns), ["sell", "sell_price", "gia_ban", "ban"]
            )
            for code, c in [
                (MacroIndicatorCode.SJC_GOLD_BUY, buy_col),
                (MacroIndicatorCode.SJC_GOLD_SELL, sell_col),
            ]:
                if c:
                    try:
                        v = float(df_gold[c].iloc[0])
                        if v > 0:
                            _upsert_macro(session, d, code, v, None, "sjc")
                            total += 1
                    except (ValueError, TypeError):
                        pass

    _recalculate_change_pct(session, MacroIndicatorCode.USD_VND)
    _recalculate_change_pct(session, MacroIndicatorCode.SJC_GOLD_BUY)
    _recalculate_change_pct(session, MacroIndicatorCode.SJC_GOLD_SELL)
    session.commit()
    logger.info(
        "[ingest] backfill_macro_indicators: %d records for %d days", total, days
    )
    return total


# ---------------------------------------------------------------------------
# 5. run_all — chạy toàn bộ pipeline
# ---------------------------------------------------------------------------


def run_all(session: Session, backfill_days: int = 30) -> None:
    logger.info("=== market_data_ingest START ===")
    logger.info("Step 1: Backfill macro (%d days)...", backfill_days)
    n1 = backfill_macro_indicators(session, days=backfill_days)
    logger.info("  macro backfill: %d records", n1)

    logger.info("Step 2: Today macro (live)...")
    ingest_macro_indicators(session)

    logger.info("Step 3: Market breadth (today)...")
    n3 = ingest_market_breadth(session)
    logger.info("  breadth: %d record", n3)

    logger.info("Step 4: Institutional flows VN30 (today)...")
    n4 = ingest_institutional_flows(session)
    logger.info("  flows: %d symbols", n4)

    logger.info("=== market_data_ingest DONE ===")


if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    from sqlmodel import Session as _Session

    from app.core.db import engine as _engine

    backfill = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    with _Session(_engine) as s:
        run_all(s, backfill_days=backfill)
