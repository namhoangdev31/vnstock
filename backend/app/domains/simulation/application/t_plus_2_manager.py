"""T+2 Settlement Manager (paper-only).

Tracks the lifecycle of equity settlement via the ``EquitySettlementLedger``.
Provides ledger-row helpers, available-quantity queries, and a settlement
processor that flips due rows to ``SETTLED_AVAILABLE`` and credits sale cash.

This module ONLY operates on the isolated ``simulation_*`` tables (RULE 2).
No real brokerage API is called; no credentials are stored or accepted
(RULE 1). All timestamps are timezone-aware (AwareSQLModel enforces this).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlmodel import Session, col, select

from app.core.models_base import VN_TZ
from app.domains.simulation.domain.models import (
    SETTLEMENT_AVAILABLE,
    SETTLEMENT_PENDING,
    EquitySettlementLedger,
    Position,
    round_money,
)
from app.domains.simulation.domain.settlement import SettlementService


def compute_settlement_due(trade_dt: datetime) -> datetime:
    """Return the exact settlement moment (13:00 VN) for T+2 from ``trade_dt``."""
    return SettlementService.get_settlement_exact_time(trade_dt.date(), cycle_days=2)


def create_ledger_row(
    session: Session,
    *,
    portfolio_id: uuid.UUID,
    symbol: str,
    side: str,
    quantity: int,
    price: float,
    trade_dt: datetime | None = None,
) -> EquitySettlementLedger:
    """Insert a ``PENDING_T2`` ledger row for an equity fill.

    Caller is responsible for committing. ``side`` is ``"BUY"`` or ``"SELL"``
    (OrderSide). The ``settlement_due`` is set to 13:00 VN on T+2 (D3, D4).
    """
    trade_dt = trade_dt or datetime.now(VN_TZ)
    due = compute_settlement_due(trade_dt)
    row = EquitySettlementLedger(
        portfolio_id=portfolio_id,
        symbol=symbol,
        side=side,
        quantity=quantity,
        price=price,
        bought_at=trade_dt,
        settlement_due=due,
        status=SETTLEMENT_PENDING,
    )
    session.add(row)
    return row


def available_quantity(session: Session, portfolio_id: uuid.UUID, symbol: str) -> int:
    """Return the currently sellable equity quantity for ``portfolio_id``+``symbol``.

    Available = open LONG quantity − Σ PENDING_T2 BUY ledger quantity.
    If **no ledger rows** exist for that portfolio+symbol → fully available
    (back-compat for pre-Phase-4 positions) (D5).
    """
    pos = session.exec(
        select(Position)
        .where(Position.portfolio_id == portfolio_id)
        .where(Position.symbol == symbol)
        .where(Position.side == "LONG")
        .where(Position.status == "OPEN")
    ).first()
    position_qty = pos.quantity if pos is not None else 0

    pending_rows = session.exec(
        select(EquitySettlementLedger)
        .where(EquitySettlementLedger.portfolio_id == portfolio_id)
        .where(EquitySettlementLedger.symbol == symbol)
        .where(EquitySettlementLedger.side == "BUY")
        .where(col(EquitySettlementLedger.status) == SETTLEMENT_PENDING)
    ).all()
    if not pending_rows:
        return position_qty
    pending_qty = sum(r.quantity for r in pending_rows)
    return max(0, position_qty - pending_qty)


def process_due_settlements(session: Session, as_of: datetime | None = None) -> int:
    """Flip all ``PENDING_T2`` ledger rows whose due time has passed.

    For each settled row:
    - ``status`` → ``SETTLED_AVAILABLE``
    - If ``side == "SELL"``: credit ``portfolio.cash_balance`` by ``qty*price``
      (sale cash credits at settlement, D4)

    This is a **global** operation across all portfolios (paper-only, daemon
    semantics). Commits once; returns the number of rows settled.
    """
    as_of = as_of or datetime.now(VN_TZ)
    if as_of.tzinfo is None:
        as_of = as_of.replace(tzinfo=VN_TZ)

    rows = session.exec(
        select(EquitySettlementLedger)
        .where(col(EquitySettlementLedger.status) == SETTLEMENT_PENDING)
        .where(col(EquitySettlementLedger.settlement_due) <= as_of)
    ).all()

    from app.domains.simulation.domain.models import Portfolio

    settled_count = 0
    for row in rows:
        row.status = SETTLEMENT_AVAILABLE
        session.add(row)
        if row.side == "SELL":
            portfolio = session.get(Portfolio, row.portfolio_id)
            if portfolio is not None:
                proceeds = row.quantity * row.price
                portfolio.cash_balance = round_money(portfolio.cash_balance + proceeds)
                session.add(portfolio)
        settled_count += 1

    if settled_count > 0:
        session.commit()
    return settled_count
