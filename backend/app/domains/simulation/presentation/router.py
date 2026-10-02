"""Simulation (paper-trading) API — RULE 1 & RULE 2 isolated accounts.

Every endpoint is scoped to the authenticated user's own portfolios. No real
brokerage credential is ever accepted or stored, and no order leaves this
process (RULE 1: no real-money execution).

Endpoints:
- POST /simulation/portfolios create a paper account
- GET /simulation/portfolios list their own portfolios
- GET /simulation/portfolios/{id} fetch one (ownership-checked)
- GET    /simulation/portfolios/{id}/positions   open positions
- POST   /simulation/portfolios/{id}/mark        mark-to-market from a price map
- POST   /simulation/orders                      place a paper order
- POST   /simulation/orders/{id}/cancel          cancel a pending order
- POST   /simulation/positions/{id}/close        close (part of) a position
- GET    /simulation/portfolios/{id}/margin-status VSDC margin status and safety ratio
- POST   /simulation/settlement/process          trigger T+2 settlements for due paper rows
- GET    /simulation/alpha/baskets               multi-horizon equity alpha baskets
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import Session, col, select

from app.api.deps import CurrentUser, SessionDep
from app.domains.simulation.application.alpha_screener import screen
from app.domains.simulation.application.engine import SimulationEngine, is_derivative
from app.domains.simulation.application.margin_calculator import (
    STATUS_SAFE,
    check_margin_status,
    compute_margin_ratio,
    total_derivative_position_value,
)
from app.domains.simulation.application.schemas import (
    AlphaBasketsResponse,
    AlphaCriteria,
    AlphaTicker,
    MarginStatusResponse,
    MarkToMarketRequest,
    OrderCreateRequest,
    OrderResponse,
    PortfolioCreateRequest,
    PortfolioResponse,
    PortfoliosResponse,
    PositionCloseRequest,
    PositionResponse,
    SettlementProcessResponse,
    TradeResponse,
)
from app.domains.simulation.application.t_plus_2_manager import (
    process_due_settlements,
)
from app.domains.simulation.domain.exceptions import SimulationError
from app.domains.simulation.domain.models import (
    Order,
    Portfolio,
    Position,
)

router = APIRouter(prefix="/simulation", tags=["simulation"])


def _engine(session: Session) -> SimulationEngine:
    return SimulationEngine(session)


def _owned_portfolio(
    engine: SimulationEngine, portfolio_id: UUID, user_id: UUID
) -> Portfolio:
    try:
        return engine.get_portfolio(portfolio_id, user_id=user_id)
    except SimulationError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ---------------------------------------------------------------------------
# Portfolios
# ---------------------------------------------------------------------------


@router.post("/portfolios", response_model=PortfolioResponse)
def create_portfolio(
    session: SessionDep,
    current_user: CurrentUser,
    payload: PortfolioCreateRequest,
) -> Any:
    """Create an isolated paper-trading portfolio for the current user."""
    engine = _engine(session)
    portfolio = engine.create_portfolio(
        user_id=current_user.id,
        name=payload.name,
        initial_balance=payload.initial_balance,
    )
    return PortfolioResponse.model_validate(portfolio)


@router.get("/portfolios", response_model=PortfoliosResponse)
def list_portfolios(session: SessionDep, current_user: CurrentUser) -> Any:
    """List the current user's portfolios."""
    engine = _engine(session)
    rows = engine.list_portfolios(user_id=current_user.id)
    return PortfoliosResponse(
        data=[PortfolioResponse.model_validate(r) for r in rows],
        count=len(rows),
    )


@router.get("/portfolios/{portfolio_id}", response_model=PortfolioResponse)
def get_portfolio(
    session: SessionDep,
    current_user: CurrentUser,
    portfolio_id: UUID,
) -> Any:
    """Fetch one portfolio (ownership-checked)."""
    engine = _engine(session)
    portfolio = _owned_portfolio(engine, portfolio_id, current_user.id)
    return PortfolioResponse.model_validate(portfolio)


@router.get(
    "/portfolios/{portfolio_id}/positions",
    response_model=list[PositionResponse],
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
    return [PositionResponse.model_validate(r) for r in rows]


@router.post("/portfolios/{portfolio_id}/mark", response_model=PortfolioResponse)
def mark_to_market(
    session: SessionDep,
    current_user: CurrentUser,
    portfolio_id: UUID,
    payload: MarkToMarketRequest,
) -> Any:
    """Mark a portfolio to market from a symbol→price map.

    Symbols absent from the map keep their last price — never fabricated
    (RULE 3).
    """
    engine = _engine(session)
    portfolio = _owned_portfolio(engine, portfolio_id, current_user.id)
    updated = engine.mark_to_market(portfolio, payload.prices)
    return PortfolioResponse.model_validate(updated)


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------


@router.post("/portfolios/{portfolio_id}/orders", response_model=OrderResponse)
def place_order(
    session: SessionDep,
    current_user: CurrentUser,
    portfolio_id: UUID,
    payload: OrderCreateRequest,
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
    return OrderResponse.model_validate(order)


@router.post("/orders/{order_id}/cancel", response_model=OrderResponse)
def cancel_order(
    session: SessionDep,
    current_user: CurrentUser,
    order_id: UUID,
) -> Any:
    """Cancel a PENDING paper order."""
    engine = _engine(session)
    order = session.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    # Ownership: the order's portfolio must belong to the user.
    _owned_portfolio(engine, order.portfolio_id, current_user.id)
    try:
        cancelled = engine.cancel_order(order_id)
    except SimulationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return OrderResponse.model_validate(cancelled)


# ---------------------------------------------------------------------------
# Positions
# ---------------------------------------------------------------------------


@router.post("/positions/{position_id}/close", response_model=TradeResponse)
def close_position(
    session: SessionDep,
    current_user: CurrentUser,
    position_id: UUID,
    payload: PositionCloseRequest,
) -> Any:
    """Close (part of) an open position, realizing PnL (TEST-ISO-03)."""
    engine = _engine(session)
    position = session.get(Position, position_id)
    if position is None:
        raise HTTPException(status_code=404, detail="Position not found")
    portfolio = _owned_portfolio(engine, position.portfolio_id, current_user.id)
    try:
        trade = engine.close_position(
            portfolio=portfolio,
            position=position,
            quantity=payload.quantity,
            price=payload.price,
        )
    except SimulationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return TradeResponse.model_validate(trade)


@router.get("/orders", response_model=list[OrderResponse])
def list_orders(
    session: SessionDep,
    current_user: CurrentUser,
    portfolio_id: UUID | None = None,
    limit: int = 100,
) -> Any:
    """List the user's paper orders, optionally scoped to one portfolio."""
    engine = _engine(session)
    query = select(Order)
    if portfolio_id is not None:
        _owned_portfolio(engine, portfolio_id, current_user.id)
        query = query.where(Order.portfolio_id == portfolio_id)
    else:
        owned = engine.list_portfolios(user_id=current_user.id)
        ids = [p.id for p in owned]
        if not ids:
            return []
        query = query.where(col(Order.portfolio_id).in_(ids))
    rows = session.exec(query.order_by(col(Order.created_at).desc()).limit(limit)).all()
    return [OrderResponse.model_validate(r) for r in rows]


# ---------------------------------------------------------------------------
# Phase 4: Margin Status, T+2 Settlement, and Alpha Screener Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/portfolios/{portfolio_id}/margin-status",
    response_model=MarginStatusResponse,
)
def get_margin_status(
    session: SessionDep,
    current_user: CurrentUser,
    portfolio_id: UUID,
) -> Any:
    """Trạng thái ký quỹ và tỷ lệ an toàn danh mục VSDC (RULE 1/2 paper only)."""
    engine = _engine(session)
    portfolio = _owned_portfolio(engine, portfolio_id, current_user.id)
    positions = engine.open_positions(portfolio_id)
    deriv_positions = [p for p in positions if is_derivative(p.symbol)]
    total_position_value = total_derivative_position_value(deriv_positions)

    if deriv_positions and total_position_value > 0:
        margin_ratio = compute_margin_ratio(portfolio.equity, total_position_value)
        status = check_margin_status(portfolio.equity, total_position_value)
    else:
        margin_ratio = None
        status = STATUS_SAFE

    return MarginStatusResponse(
        equity=portfolio.equity,
        margin_used=portfolio.margin_used,
        margin_ratio=margin_ratio,
        status=status,
    )


@router.post("/settlement/process", response_model=SettlementProcessResponse)
def process_settlement_batch(
    session: SessionDep,
    _current_user: CurrentUser,
) -> Any:
    """Process due T+2 settlements across paper portfolios.

    Unlocks pending equity buy shares at 13:00 on T+2 and credits deferred
    equity sale cash to portfolio cash balance.
    Note: Operates globally on all due paper settlements (RULE 1 & 2 paper-only).
    """
    settled_count = process_due_settlements(session)
    return SettlementProcessResponse(settled=settled_count)


@router.get("/alpha/baskets", response_model=AlphaBasketsResponse)
def get_alpha_baskets(
    session: SessionDep,
    _current_user: CurrentUser,
    horizon: str = Query(
        default="all", description="weekly, monthly, quarterly, or all"
    ),
    record_journal: bool = Query(
        default=False,
        description="Whether to record screened tickers to ForecastJournal (RULE 3 audit ledger)",
    ),
) -> Any:
    """Multi-horizon equity alpha screener baskets (RULE 1/2/4 simulation/research only)."""
    if horizon not in ("all", "weekly", "monthly", "quarterly"):
        raise HTTPException(
            status_code=422,
            detail=f"Invalid horizon: '{horizon}'. Must be one of: all, weekly, monthly, quarterly",
        )
    try:
        results = screen(session, horizon=horizon, record_journal=record_journal)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    baskets_dto: dict[str, list[AlphaTicker]] = {}
    for h_key, tickers in results.items():
        if horizon != "all" and h_key != horizon:
            continue
        baskets_dto[h_key] = [
            AlphaTicker(
                symbol=t.symbol,
                horizon=t.horizon,
                alpha_score=t.alpha_score,
                criteria=[
                    AlphaCriteria(
                        key=c.key,
                        label=c.label,
                        passed=c.passed,
                        value=c.value,
                        threshold=c.threshold,
                    )
                    for c in t.criteria
                ],
            )
            for t in tickers
        ]

    return AlphaBasketsResponse(horizon=horizon, baskets=baskets_dto)
