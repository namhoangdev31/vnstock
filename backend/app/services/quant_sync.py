"""QuantSyncManager — persists macro & order-flow data (Engine 1 & 2 inputs).

Only data with a real, verifiable vnstock source is synced here (RULE 3):

- Macro indicators: SJC gold (buy/sell) and USD/VND from the ``Retail`` layer.
  WORLD_GOLD has no vnstock source in v4, so it is intentionally NOT fabricated.
- Tick order-flow: ``Quote.intraday`` matched prints, classified by aggressor
  side and aggregated to 1-minute delta bars (``TickFlowAggregated``).

``InstitutionalFlow`` and ``MarketBreadth`` are deliberately absent — vnstock v4
exposes no proprietary-desk values and no breadth endpoint. Their tables exist
for a future verified source; populating them now would violate RULE 3.

The tick→minute aggregation is a pure function (``aggregate_tick_orderflow``)
so it can be unit-tested without network access.
"""

import logging
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pandas as pd
from sqlmodel import Session, select

from app.models.enums import MacroIndicatorCode
from app.models.models_quant import MacroIndicator, TickFlowAggregated
from app.models.models_stock import DataSyncLog
from app.services.vnstock_service import VnstockService, VnstockServiceError

logger = logging.getLogger(__name__)

# vnstock returns intraday timestamps in Vietnam local time (naive).
_VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")


def _to_utc_aware(value: object) -> datetime | None:
    """Normalize a naive VN-local timestamp (or pandas Timestamp) to aware UTC."""
    ts: datetime | None = None
    if isinstance(value, pd.Timestamp):
        ts = value.to_pydatetime()
    elif isinstance(value, datetime):
        ts = value
    if ts is None:
        return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=_VN_TZ)
    return ts.astimezone(UTC)


def aggregate_tick_orderflow(
    df: pd.DataFrame, *, source: str
) -> list[TickFlowAggregated]:
    """Aggregate raw tick prints into 1-minute order-flow delta bars.

    Classification (from vnstock's normalized ``match_type``):
    - ``Buy``  → aggressive_buy_volume (matched at the ask)
    - ``Sell`` → aggressive_sell_volume (matched at the bid)
    - ``ATO`` / ``ATC`` / ``unknown`` → auction/unlabeled prints; counted in
      ``trade_count`` and VWAP but not in either aggressive side.

    Returns a list of unsaved ``TickFlowAggregated`` rows (one per minute).
    """
    rows: list[TickFlowAggregated] = []
    if df is None or df.empty or "match_type" not in df.columns:
        return rows

    work = df.copy()
    if "time" not in work.columns:
        return rows
    work["_ts"] = work["time"].map(_to_utc_aware)
    work = work.dropna(subset=["_ts", "price", "volume"])
    if work.empty:
        return rows

    work["_minute"] = work["_ts"].map(lambda t: t.replace(second=0, microsecond=0))
    work["_notional"] = work["price"] * work["volume"]
    mt = work["match_type"].astype(str).str.upper()
    work["_buy"] = work["volume"].where(mt == "BUY", 0)
    work["_sell"] = work["volume"].where(mt == "SELL", 0)

    for minute, grp in work.groupby("_minute"):
        buy_vol = int(grp["_buy"].sum())
        sell_vol = int(grp["_sell"].sum())
        total_vol = int(grp["volume"].sum())
        notional = float(grp["_notional"].sum())
        vwap = round(notional / total_vol, 4) if total_vol else None
        rows.append(
            TickFlowAggregated(
                symbol=str(grp["symbol"].iloc[0]) if "symbol" in grp.columns else "",
                timestamp=minute,
                aggressive_buy_volume=buy_vol,
                aggressive_sell_volume=sell_vol,
                volume_delta=buy_vol - sell_vol,
                trade_count=int(len(grp)),
                vwap=vwap,
                source=source,
            )
        )
    rows.sort(key=lambda r: r.timestamp)
    return rows


class QuantSyncManager:
    """Sync macro indicators and tick order-flow into PostgreSQL."""

    def __init__(
        self, session: Session, vnstock_svc: VnstockService | None = None
    ) -> None:
        self.session = session
        self.svc = vnstock_svc or VnstockService()

    # ------------------------------------------------------------------
    # Macro indicators
    # ------------------------------------------------------------------

    def sync_macro(self, *, date_str: str | None = None) -> DataSyncLog:
        """Sync SJC gold + USD/VND for a date (default today)."""
        log = self._create_log("macro")
        recorded_date = (
            datetime.strptime(date_str, "%Y-%m-%d").date()
            if date_str
            else datetime.now(_VN_TZ).date()
        )
        try:
            count = 0
            count += self._sync_gold(recorded_date, date_str)
            count += self._sync_fx(recorded_date, date_str)
            status = "success" if count > 0 else "partial"
            return self._finish_log(log, status, rows_synced=count)
        except VnstockServiceError as exc:
            return self._finish_log(log, "failed", error_message=str(exc))
        except Exception as exc:  # noqa: BLE001 — surface any sync error to the log
            self.session.rollback()
            logger.exception("Macro sync failed")
            return self._finish_log(log, "failed", error_message=str(exc))

    def _sync_gold(self, recorded_date, date_str: str | None) -> int:
        df = self.svc.fetch_gold_prices(date_str)
        if df is None or df.empty:
            return 0
        # SJC standard bar (loại 1 lượng) is the headline price series.
        row = self._select_gold_row(df)
        if row is None:
            return 0
        n = 0
        n += self._upsert_macro(
            MacroIndicatorCode.SJC_GOLD_BUY,
            recorded_date,
            float(row["buy_price"]),
            source="SJC",
        )
        n += self._upsert_macro(
            MacroIndicatorCode.SJC_GOLD_SELL,
            recorded_date,
            float(row["sell_price"]),
            source="SJC",
        )
        return n

    @staticmethod
    def _select_gold_row(df: pd.DataFrame) -> dict | None:
        """Pick the SJC standard-bar row; fall back to the first row."""
        if "name" in df.columns:
            named = df[df["name"].astype(str).str.contains("SJC", case=False, na=False)]
            if not named.empty:
                return named.iloc[0].to_dict()
        if "buy_price" in df.columns and "sell_price" in df.columns:
            return df.iloc[0].to_dict()
        return None

    def _sync_fx(self, recorded_date, date_str: str | None) -> int:
        df = self.svc.fetch_exchange_rate(date_str or "")
        if df is None or df.empty:
            return 0
        code_col = "currency_code" if "currency_code" in df.columns else None
        sell_col = "sell" if "sell" in df.columns else None
        if code_col is None or sell_col is None:
            return 0
        usd = df[df[code_col].astype(str).str.upper() == "USD"]
        if usd.empty:
            return 0
        value = pd.to_numeric(usd.iloc[0][sell_col], errors="coerce")
        if pd.isna(value):
            return 0
        return self._upsert_macro(
            MacroIndicatorCode.USD_VND, recorded_date, float(value), source="VCB"
        )

    def _upsert_macro(
        self, code: str, recorded_date, value: float, *, source: str
    ) -> int:
        existing = self.session.exec(
            select(MacroIndicator)
            .where(MacroIndicator.indicator_code == code)
            .where(MacroIndicator.recorded_date == recorded_date)
            .where(MacroIndicator.source == source)
        ).first()
        prev = None
        if existing:
            prev = existing.value
            existing.value = value
            existing.change_pct = (
                round((value - prev) / prev * 100, 4) if prev else None
            )
            self.session.add(existing)
        else:
            self.session.add(
                MacroIndicator(
                    recorded_date=recorded_date,
                    indicator_code=code,
                    value=value,
                    change_pct=None,
                    source=source,
                )
            )
        self.session.commit()
        return 1

    # ------------------------------------------------------------------
    # Tick order-flow → 1-minute aggregated delta
    # ------------------------------------------------------------------

    def sync_tick_orderflow(
        self, symbol: str, *, page_size: int = 100
    ) -> DataSyncLog:
        """Fetch matched ticks and persist aggregated 1-minute delta bars."""
        log = self._create_log("tick_orderflow", symbol=symbol)
        try:
            df = self.svc.fetch_tick_orderflow(symbol, page_size=page_size)
            if df is None or df.empty:
                return self._finish_log(log, "partial", rows_synced=0)
            if "symbol" not in df.columns:
                df = df.assign(symbol=symbol)

            bars = aggregate_tick_orderflow(df, source=self.svc.source)
            count = 0
            for bar in bars:
                bar.symbol = bar.symbol or symbol
                existing = self.session.exec(
                    select(TickFlowAggregated)
                    .where(TickFlowAggregated.symbol == bar.symbol)
                    .where(TickFlowAggregated.timestamp == bar.timestamp)
                ).first()
                if existing:
                    existing.aggressive_buy_volume = bar.aggressive_buy_volume
                    existing.aggressive_sell_volume = bar.aggressive_sell_volume
                    existing.volume_delta = bar.volume_delta
                    existing.trade_count = bar.trade_count
                    existing.vwap = bar.vwap
                    existing.source = bar.source
                    self.session.add(existing)
                else:
                    self.session.add(bar)
                count += 1
            self.session.commit()
            logger.info("Aggregated %d tick-flow bars for %s", count, symbol)
            return self._finish_log(log, "success", rows_synced=count)
        except VnstockServiceError as exc:
            return self._finish_log(log, "failed", error_message=str(exc))
        except Exception as exc:  # noqa: BLE001
            self.session.rollback()
            logger.exception("Tick order-flow sync failed for %s", symbol)
            return self._finish_log(log, "failed", error_message=str(exc))

    # ------------------------------------------------------------------
    # Log helpers (mirror DataSyncManager)
    # ------------------------------------------------------------------

    def _create_log(self, sync_type: str, symbol: str | None = None) -> DataSyncLog:
        log = DataSyncLog(
            sync_type=sync_type,
            symbol=symbol,
            source=self.svc.source,
            status="started",
        )
        self.session.add(log)
        self.session.commit()
        self.session.refresh(log)
        return log

    def _finish_log(
        self,
        log: DataSyncLog,
        status: str,
        rows_synced: int = 0,
        error_message: str | None = None,
    ) -> DataSyncLog:
        log.status = status
        log.rows_synced = rows_synced
        log.error_message = error_message
        log.completed_at = datetime.now(UTC)
        self.session.add(log)
        self.session.commit()
        self.session.refresh(log)
        return log
