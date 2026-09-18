"""Simulation (paper-trading) API — RULE 1 & RULE 2 isolated accounts.

Every endpoint is scoped to the authenticated user's own portfolios. No real
brokerage credential is ever accepted or stored, and no order leaves this
process (RULE 1: no real-money execution).

Endpoints:
- POST   /simulation/portfolios                  create a paper account
- GET    /simulation/portfolios                  list own portfolios
- GET    /simulation/portfolios/{id}             fetch one (ownership-checked)
- GET    /simulation/portfolios/{id}/positions   open positions
- POST   /simulation/portfolios/{id}/mark        mark-to-market from a price map
- POST   /simulation/orders                      place a paper order
- POST   /simulation/orders/{id}/cancel          cancel a pending order
- POST   /simulation/positions/{id}/close        close (part of) a position
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException
from sqlmodel import Session, col, select

from app.api.deps import CurrentUser, SessionDep
from app.models.models_simulation import (
    SimulationMarkToMarket,
    SimulationOrder,
    SimulationOrderCreate,
    SimulationOrderPublic,
    SimulationPortfolio,
    SimulationPortfolioCreate,
    SimulationPortfolioPublic,
    SimulationPortfoliosPublic,
    SimulationPosition,
    SimulationPositionClose,
    SimulationPositionPublic,
    SimulationTradePublic,
)
from app.services.simulation_engine import SimulationEngine, SimulationError

router = APIRouter(prefix="/simulation", tags=["simulation"])


def _engine(session: Session) -> SimulationEngine:
    return SimulationEngine(session)


def _owned_portfolio(
    engine: SimulationEngine, portfolio_id: UUID, user_id: UUID
) -> SimulationPortfolio:
    try:
        return engine.get_portfolio(portfolio_id, user_id=user_id)
    except SimulationError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ---------------------------------------------------------------------------
# Portfolios
# ---------------------------------------------------------------------------


@router.post("/portfolios", response_model=SimulationPortfolioPublic)
def create_portfolio(
    session: SessionDep,
    current_user: CurrentUser,
    payload: SimulationPortfolioCreate,
) -> Any:
    """Create an isolated paper-trading portfolio for the current user."""
    engine = _engine(session)
    portfolio = engine.create_portfolio(
        user_id=current_user.id,
        name=payload.name,
        initial_balance=payload.initial_balance,
    )
    return SimulationPortfolioPublic.model_validate(portfolio)


@router.get("/portfolios", response_model=SimulationPortfoliosPublic)
def list_portfolios(session: SessionDep, current_user: CurrentUser) -> Any:
    """List the current user's portfolios."""
    engine = _engine(session)
    rows = engine.list_portfolios(user_id=current_user.id)
    return SimulationPortfoliosPublic(
        data=[SimulationPortfolioPublic.model_validate(r) for r in rows],
        count=len(rows),
    )


@router.get("/portfolios/{portfolio_id}", response_model=SimulationPortfolioPublic)
def get_portfolio(
    session: SessionDep,
    current_user: CurrentUser,
    portfolio_id: UUID,
) -> Any:
    """Fetch one portfolio (ownership-checked)."""
    engine = _engine(session)
    portfolio = _owned_portfolio(engine, portfolio_id, current_user.id)
    return SimulationPortfolioPublic.model_validate(portfolio)


@router.get(
    "/portfolios/{portfolio_id}/positions",
    response_model=list[SimulationPositionPublic],
)
def list_positions(
    session: SessionDep,
    current_user: CurrentUser,
    portfolio_id: UUID,
) -> Any:
    """Open positions for a portfolio."""
    engine = _engine(session)
    _owned_portfolio(engine, portfolio_id, current_user.id)
    rows = engine.open_positions(portfolio_id)
    return [SimulationPositionPublic.model_validate(r) for r in rows]


@router.post(
    "/portfolios/{portfolio_id}/mark", response_model=SimulationPortfolioPublic
)
def mark_to_market(
    session: SessionDep,
    current_user: CurrentUser,
    portfolio_id: UUID,
    payload: SimulationMarkToMarket,
) -> Any:
    """Mark a portfolio to market from a symbol→price map.

    Symbols absent from the map keep their last price — never fabricated
    (RULE 3).
    """
    engine = _engine(session)
    portfolio = _owned_portfolio(engine, portfolio_id, current_user.id)
    updated = engine.mark_to_market(portfolio, payload.prices)
    return SimulationPortfolioPublic.model_validate(updated)


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------


@router.post("/portfolios/{portfolio_id}/orders", response_model=SimulationOrderPublic)
def place_order(
    session: SessionDep,
    current_user: CurrentUser,
    portfolio_id: UUID,
    payload: SimulationOrderCreate,
) -> Any:
    """Place a paper order. Insufficient buying power → REJECTED (TEST-ISO-02)."""
    engine = _engine(session)
    portfolio = _owned_portfolio(engine, portfolio_id, current_user.id)
    try:
        order = engine.place_order(
            portfolio=portfolio,
            symbol=payload.symbol,
            side=payload.side,
            quantity=payload.quantity,
            price=payload.price,
            order_type=payload.order_type,
            stop_price=payload.stop_price,
        )
    except SimulationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return SimulationOrderPublic.model_validate(order)


@router.post("/orders/{order_id}/cancel", response_model=SimulationOrderPublic)
def cancel_order(
    session: SessionDep,
    current_user: CurrentUser,
    order_id: UUID,
) -> Any:
    """Cancel a PENDING paper order."""
    engine = _engine(session)
    order = session.get(SimulationOrder, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    # Ownership: the order's portfolio must belong to the user.
    _owned_portfolio(engine, order.portfolio_id, current_user.id)
    try:
        cancelled = engine.cancel_order(order_id)
    except SimulationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return SimulationOrderPublic.model_validate(cancelled)


# ---------------------------------------------------------------------------
# Positions
# ---------------------------------------------------------------------------


@router.post("/positions/{position_id}/close", response_model=SimulationTradePublic)
def close_position(
    session: SessionDep,
    current_user: CurrentUser,
    position_id: UUID,
    payload: SimulationPositionClose,
) -> Any:
    """Close (part of) an open position, realizing PnL (TEST-ISO-03)."""
    engine = _engine(session)
    position = session.get(SimulationPosition, position_id)
    if position is None:
        raise HTTPException(status_code=404, detail="Position not found")
    portfolio = _owned_portfolio(
        engine, position.portfolio_id, current_user.id
    )
    try:
        trade = engine.close_position(
            portfolio=portfolio,
            position=position,
            quantity=payload.quantity,
            price=payload.price,
        )
    except SimulationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return SimulationTradePublic.model_validate(trade)


@router.get("/orders", response_model=list[SimulationOrderPublic])
def list_orders(
    session: SessionDep,
    current_user: CurrentUser,
    portfolio_id: UUID | None = None,
    limit: int = 100,
) -> Any:
    """List the user's paper orders, optionally scoped to one portfolio."""
    engine = _engine(session)
    query = select(SimulationOrder)
    if portfolio_id is not None:
        _owned_portfolio(engine, portfolio_id, current_user.id)
        query = query.where(SimulationOrder.portfolio_id == portfolio_id)
    else:
        owned = engine.list_portfolios(user_id=current_user.id)
        ids = [p.id for p in owned]
        if not ids:
            return []
        query = query.where(col(SimulationOrder.portfolio_id).in_(ids))
    rows = session.exec(
        query.order_by(col(SimulationOrder.created_at).desc()).limit(limit)
    ).all()
    return [SimulationOrderPublic.model_validate(r) for r in rows]
