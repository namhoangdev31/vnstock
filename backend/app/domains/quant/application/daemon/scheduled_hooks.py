"""Scheduled periodic hooks for the quant daemon.

Hooks are called by the DaemonController at the end of each cycle when the
current session phase matches the hook's trigger window.

Registered hooks:
1. T+2 Settlement hook  -- runs once in AFTERNOON_CONTINUOUS (around 13:00)
2. EOD Screener hook    -- runs once in POST_MARKET (around 15:30)
3. Equity Universe hook -- runs once in OVERNIGHT_SIMULATION to refresh symbols

Rules (AGENTS.md §6, §7):
- Blocking DB work MUST be wrapped with asyncio.to_thread() by the caller.
- Each hook is idempotent; running it twice for the same date is a no-op.
- Hooks must NOT place real orders or touch real-money systems (RULE 1).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import date, datetime
from typing import Any

from app.core.enums import SessionPhase
from app.core.models_base import VN_TZ

logger = logging.getLogger(__name__)


class _HookTracker:
    """Tracks which hooks have already run for the current trading date."""

    def __init__(self) -> None:
        self._ran: dict[str, date] = {}

    def should_run(self, name: str, today: date) -> bool:
        """Return True if hook *name* has not yet run for *today*."""
        return self._ran.get(name) != today

    def mark_ran(self, name: str, today: date) -> None:
        self._ran[name] = today

    def reset(self) -> None:
        self._ran.clear()


_tracker = _HookTracker()


# ---------------------------------------------------------------------------
# Hook 1 — T+2 Settlement update
# ---------------------------------------------------------------------------


def run_settlement_hook(
    session_factory: Callable[[], Any] | None,
    today: date | None = None,
) -> dict[str, Any]:
    """Resolve PENDING paper orders that have reached their T+2 settlement time.

    This hook fires once per trading day during AFTERNOON_CONTINUOUS (13:00+).
    It is a no-op if no DB session factory is provided or if already run today.

    Returns a summary dict: {"settled": int, "errors": list[str]}.
    """
    run_date = today or datetime.now(VN_TZ).date()
    hook_name = f"settlement_{run_date}"

    if not _tracker.should_run(hook_name, run_date):
        logger.debug("Settlement hook already ran for %s, skipping", run_date)
        return {"settled": 0, "errors": [], "skipped": True}

    if session_factory is None:
        logger.debug("Settlement hook: no session_factory, skipping")
        return {"settled": 0, "errors": [], "skipped": True}

    settled = 0
    errors: list[str] = []

    try:
        from sqlmodel import col, select

        from app.core.enums import PositionStatus
        from app.domains.simulation.domain.models import Portfolio, Position, Trade

        now = datetime.now(VN_TZ)
        today = now.date()

        with session_factory() as session:
            # Find EQUITY positions with settlement_date reached (T+2 settled)
            pending_positions = session.exec(
                select(Position).where(
                    col(Position.status) == PositionStatus.OPEN,
                    col(Position.settlement_date) <= today,
                    col(Position.settlement_date).is_not(None),
                )
            ).all()

            for pos in pending_positions:
                try:
                    # 1. Fetch the owning portfolio
                    portfolio = session.get(Portfolio, pos.portfolio_id)
                    if portfolio is None:
                        errors.append(f"position {pos.id}: portfolio not found")
                        continue

                    # 2. Calculate settlement proceeds
                    settlement_price = (
                        pos.current_price if pos.current_price > 0 else pos.entry_price
                    )
                    proceeds = abs(pos.quantity) * settlement_price

                    # 3. Credit cash balance (sale proceeds or buy settlement completed)
                    portfolio.cash_balance += proceeds
                    portfolio.margin_used = max(
                        0.0, portfolio.margin_used - pos.margin_required
                    )
                    portfolio.updated_at = now

                    # 4. Create settlement trade record for audit trail
                    settlement_trade = Trade(
                        portfolio_id=portfolio.id,
                        symbol=pos.symbol,
                        side=pos.side,
                        quantity=pos.quantity,
                        price=settlement_price,
                        realized_pnl=pos.realized_pnl,
                        executed_at=now,
                    )
                    session.add(settlement_trade)

                    # 5. Close position
                    pos.status = PositionStatus.CLOSED
                    pos.updated_at = now
                    session.add(pos)
                    session.add(portfolio)

                    settled += 1
                except Exception as exc:
                    errors.append(f"position {getattr(pos, 'id', '?')}: {exc}")
                    logger.warning(
                        "Settlement hook: error processing position: %s", exc
                    )

            if settled > 0:
                session.commit()

        _tracker.mark_ran(hook_name, run_date)
        logger.info(
            "Settlement hook completed: settled=%d errors=%d date=%s",
            settled,
            len(errors),
            run_date,
        )
    except Exception as exc:
        errors.append(str(exc))
        logger.error("Settlement hook failed: %s", exc, exc_info=True)

    return {"settled": settled, "errors": errors, "skipped": False}


# ---------------------------------------------------------------------------
# Hook 2 — EOD Screener Snapshot
# ---------------------------------------------------------------------------


def run_screener_snapshot_hook(
    session_factory: Callable[[], Any] | None,
    today: date | None = None,
) -> dict[str, Any]:
    """Generate daily screener snapshot for all active instruments.

    This hook fires once per trading day during POST_MARKET (15:30).
    Idempotent: ScreenerService.generate_daily_snapshot() already handles
    duplicate detection, so running it twice for the same date is safe.

    Returns a summary dict: {"created": int, "errors": list[str]}.
    """
    run_date = today or datetime.now(VN_TZ).date()
    hook_name = f"screener_{run_date}"

    if not _tracker.should_run(hook_name, run_date):
        logger.debug("Screener snapshot hook already ran for %s, skipping", run_date)
        return {"created": 0, "errors": [], "skipped": True}

    if session_factory is None:
        logger.debug("Screener hook: no session_factory, skipping")
        return {"created": 0, "errors": [], "skipped": True}

    created = 0
    errors: list[str] = []

    try:
        from app.domains.fundamental.application.screener_service import ScreenerService

        with session_factory() as session:
            created = ScreenerService.generate_daily_snapshot(
                session=session,
                snapshot_date=run_date,
            )

        _tracker.mark_ran(hook_name, run_date)
        logger.info(
            "Screener snapshot hook completed: created=%d date=%s",
            created,
            run_date,
        )
    except Exception as exc:
        errors.append(str(exc))
        logger.error("Screener snapshot hook failed: %s", exc, exc_info=True)

    return {"created": created, "errors": errors, "skipped": False}


# ---------------------------------------------------------------------------
# Hook 3 — Equity Universe Refresh
# ---------------------------------------------------------------------------


def run_equity_universe_refresh(
    session_factory: Callable[[], Any] | None,
    symbol_registry: Any | None,
    today: date | None = None,
) -> dict[str, Any]:
    """Refresh equity universe from VN30 index constituents via vnstock.

    Runs once per day during OVERNIGHT_SIMULATION. Updates the SymbolRegistry
    so the next cycle polls the current index members.

    Returns a summary dict: {"symbols": int, "errors": list[str]}.
    """
    run_date = today or datetime.now(VN_TZ).date()
    hook_name = f"equity_universe_{run_date}"

    if not _tracker.should_run(hook_name, run_date):
        logger.debug("Equity universe refresh already ran for %s, skipping", run_date)
        return {"symbols": 0, "errors": [], "skipped": True}

    if symbol_registry is None:
        return {"symbols": 0, "errors": [], "skipped": True}

    symbols: list[str] = []
    errors: list[str] = []

    try:
        # Try vnstock Listing first
        from vnstock import Listing  # type: ignore[import]

        listing = Listing()
        df = listing.symbols_by_group(group="VN30")
        if df is not None and not df.empty:
            col_candidates = ["ticker", "symbol", "code"]
            sym_col = next((c for c in col_candidates if c in df.columns), None)
            if sym_col:
                symbols = df[sym_col].dropna().str.upper().tolist()

        if not symbols:
            raise ValueError("Empty symbol list from vnstock Listing")

        symbol_registry.set_equity_universe(symbols, source="vn30_index")
        _tracker.mark_ran(hook_name, run_date)
        logger.info(
            "Equity universe refreshed: %d symbols from VN30 index", len(symbols)
        )
    except Exception as exc:
        errors.append(str(exc))
        # Fall back to DB-persisted instruments if vnstock fails
        if session_factory is not None:
            try:
                from sqlmodel import col, select

                from app.domains.market_data.domain.asset_master import Instrument

                with session_factory() as session:
                    instruments = session.exec(
                        select(Instrument)
                        .where(col(Instrument.is_active).is_(True))
                        .limit(50)
                    ).all()
                    symbols = [
                        inst.canonical_code.split(":")[-1]
                        for inst in instruments
                        if inst.instrument_type == "EQUITY"
                    ]

                if symbols:
                    symbol_registry.set_equity_universe(symbols, source="db_fallback")
                    _tracker.mark_ran(hook_name, run_date)
                    logger.info(
                        "Equity universe refreshed from DB fallback: %d symbols",
                        len(symbols),
                    )
            except Exception as db_exc:
                errors.append(f"db_fallback: {db_exc}")
                logger.error(
                    "Equity universe refresh DB fallback also failed: %s", db_exc
                )

    return {"symbols": len(symbols), "errors": errors, "skipped": False}


# ---------------------------------------------------------------------------
# Phase-based hook dispatcher
# ---------------------------------------------------------------------------

_SETTLEMENT_PHASES = {
    SessionPhase.AFTERNOON_CONTINUOUS,
}

_SCREENER_PHASES = {
    SessionPhase.POST_MARKET,
}

_EQUITY_REFRESH_PHASES = {
    SessionPhase.OVERNIGHT_SIMULATION,
}

_INGEST_PHASES = {
    SessionPhase.POST_MARKET,
    SessionPhase.OVERNIGHT_SIMULATION,
}


# ---------------------------------------------------------------------------
# Hook 4 — Market Data Ingestion (macro + breadth + flows)
# ---------------------------------------------------------------------------


def run_market_data_ingest_hook(
    session_factory: Callable[[], Any] | None,
    run_date: date,
) -> dict[str, Any]:
    """Nạp macro_indicator, market_breadth, institutional_flow vào DB.

    Chạy 1 lần mỗi ngày trong POST_MARKET / OVERNIGHT_SIMULATION.
    Idempotent — gọi nhiều lần cho cùng ngày là safe.
    """
    hook_name = "market_data_ingest"
    if not _tracker.should_run(hook_name, run_date):
        logger.debug("[hook] %s already ran for %s — skip", hook_name, run_date)
        return {"skipped": True, "date": str(run_date)}

    if session_factory is None:
        logger.warning("[hook] %s: no session_factory — skip", hook_name)
        return {"skipped": True, "reason": "no_session_factory"}

    try:
        from app.domains.quant.application.market_data_ingest import (
            ingest_institutional_flows,
            ingest_macro_indicators,
            ingest_market_breadth,
        )

        with session_factory() as session:
            macro_counts = ingest_macro_indicators(session, trading_date=run_date)
            breadth_count = ingest_market_breadth(session, trading_date=run_date)
            flow_count = ingest_institutional_flows(session, trading_date=run_date)

        _tracker.mark_ran(hook_name, run_date)
        result: dict[str, Any] = {
            "date": str(run_date),
            "macro": macro_counts,
            "breadth": breadth_count,
            "flows": flow_count,
        }
        logger.info("[hook] %s completed: %s", hook_name, result)
        return result
    except (Exception, SystemExit) as exc:  # noqa: BLE001
        logger.error("[hook] %s failed: %s", hook_name, exc, exc_info=True)
        return {"error": str(exc), "date": str(run_date)}


# ---------------------------------------------------------------------------
# Hook 5 — Forecast Resolution & Scoring (§9.1 Layer A Self-Learning)
# ---------------------------------------------------------------------------


def run_forecast_resolution_hook(
    session_factory: Callable[[], Any] | None,
    today: date | None = None,
) -> dict[str, Any]:
    """Auto-resolve and score pending forecasts against realized market prices.

    Runs once per trading day during POST_MARKET (around 15:15+).
    Idempotent.
    """
    run_date = today or datetime.now(VN_TZ).date()
    hook_name = f"forecast_resolution_{run_date}"

    if not _tracker.should_run(hook_name, run_date):
        logger.debug("[hook] %s already ran for %s — skip", hook_name, run_date)
        return {"resolved": 0, "skipped": True}

    if session_factory is None:
        return {"resolved": 0, "skipped": True, "reason": "no_session_factory"}

    try:
        from app.domains.quant.application.forecast_journal_service import (
            ForecastJournalService,
        )

        with session_factory() as session:
            svc = ForecastJournalService(session)
            result = svc.resolve_and_score_due_forecasts(as_of=run_date)

        _tracker.mark_ran(hook_name, run_date)
        logger.info("[hook] %s completed: %s", hook_name, result)
        return result
    except Exception as exc:
        logger.error("[hook] %s failed: %s", hook_name, exc, exc_info=True)
        return {"error": str(exc), "skipped": False}


def dispatch_phase_hooks(
    phase: SessionPhase,
    session_factory: Callable[[], Any] | None,
    symbol_registry: Any | None = None,
    today: date | None = None,
) -> dict[str, Any]:
    """Dispatch scheduled hooks based on the current session phase.

    This is designed to be called synchronously from within
    ``asyncio.to_thread()`` in the daemon's main loop, keeping blocking
    DB/API work off the event loop.

    Returns combined summary: {"settlement": ..., "screener": ...,
    "equity_universe": ..., "market_data_ingest": ..., "forecast_resolution": ...}.
    """
    run_date = today or datetime.now(VN_TZ).date()
    results: dict[str, Any] = {}

    if phase in _SETTLEMENT_PHASES:
        results["settlement"] = run_settlement_hook(session_factory, run_date)

    if phase in _SCREENER_PHASES:
        results["screener"] = run_screener_snapshot_hook(session_factory, run_date)
        results["forecast_resolution"] = run_forecast_resolution_hook(
            session_factory, run_date
        )

    if phase in _EQUITY_REFRESH_PHASES:
        results["equity_universe"] = run_equity_universe_refresh(
            session_factory, symbol_registry, run_date
        )

    if phase in _INGEST_PHASES:
        results["market_data_ingest"] = run_market_data_ingest_hook(
            session_factory, run_date
        )

    return results
