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

        from app.domains.simulation.domain.models import PaperOrder
        from app.domains.simulation.domain.settlement import (
            SettlementService,
            SettlementStatus,
        )

        now = datetime.now(VN_TZ)

        with session_factory() as session:
            # Find EQUITY paper orders in PENDING_SETTLEMENT status
            pending_orders = session.exec(
                select(PaperOrder).where(
                    col(PaperOrder.settlement_status) == "PENDING_SETTLEMENT"
                )
            ).all()

            for order in pending_orders:
                try:
                    trade_time = order.filled_at or order.created_at
                    if trade_time is None:
                        continue

                    # Only equity orders have T+2 settlement
                    asset_type = getattr(order, "asset_type", "EQUITY")
                    status = SettlementService.evaluate_settlement_status(
                        trade_time=trade_time,
                        current_time=now,
                        asset_type=asset_type,
                    )
                    if status == SettlementStatus.SETTLED:
                        order.settlement_status = "SETTLED"
                        order.settled_at = now
                        session.add(order)
                        settled += 1
                except Exception as exc:
                    errors.append(f"order {getattr(order, 'id', '?')}: {exc}")
                    logger.warning("Settlement hook: error processing order: %s", exc)

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
                        if inst.asset_class == "EQUITY"
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

    Returns combined summary: {"settlement": ..., "screener": ..., "equity_universe": ...}.
    """
    run_date = today or datetime.now(VN_TZ).date()
    results: dict[str, Any] = {}

    if phase in _SETTLEMENT_PHASES:
        results["settlement"] = run_settlement_hook(session_factory, run_date)

    if phase in _SCREENER_PHASES:
        results["screener"] = run_screener_snapshot_hook(session_factory, run_date)

    if phase in _EQUITY_REFRESH_PHASES:
        results["equity_universe"] = run_equity_universe_refresh(
            session_factory, symbol_registry, run_date
        )

    return results
