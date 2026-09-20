"""SimulationEngine tests — TEST-ISO-01/02/03 (RULE 1 & RULE 2 isolation).

TEST-ISO-01 (no brokerage secrets in schema) is asserted structurally against
the column metadata, so it cannot regress silently.
"""

import uuid

import pytest
from sqlmodel import select

from app.models.entities.simulation import (
    Order,
    Portfolio,
    Position,
    Trade,
    derivative_pnl,
)
from app.models.enums import OrderSide, OrderStatus, PositionSide, PositionStatus
from app.services.simulation_engine import SimulationEngine, SimulationError
from tests.utils.phase1 import session, sqlite_engine  # noqa: F401

# Any of these substrings in a simulation_* column name would breach RULE 1/2.
_FORBIDDEN_COLUMN_TOKENS = (
    "api_key",
    "apikey",
    "secret",
    "password",
    "passwd",
    "token",
    "pin",
    "otp",
    "credential",
    "private_key",
    "session_key",
)
_SIM_TABLES = (
    Portfolio,
    Order,
    Position,
    Trade,
)


def test_iso_01_no_brokerage_secrets_in_schema() -> None:
    """TEST-ISO-01: simulation_* tables carry no credential-bearing columns."""
    for model in _SIM_TABLES:
        columns = {c.name.lower() for c in model.__table__.columns}
        for col_name in columns:
            for token in _FORBIDDEN_COLUMN_TOKENS:
                assert token not in col_name, (
                    f"{model.__tablename__}.{col_name} looks like a secret "
                    f"({token}) — violates RULE 1/2 isolation"
                )


def _new_portfolio(s, balance=100_000_000.0) -> Portfolio:
    engine = SimulationEngine(s)
    return engine.create_portfolio(
        user_id=uuid.uuid4(), name="VN30F1M Intraday", initial_balance=balance
    )


def test_iso_03_derivative_pnl_formula() -> None:
    """TEST-ISO-03: (close - entry) * qty * 100_000, sign-flipped for SHORT."""
    assert derivative_pnl(1000, 1010, 10) == pytest.approx(10_000_000.0)
    assert derivative_pnl(1000, 1010, 10, side=PositionSide.SHORT) == pytest.approx(
        -10_000_000.0
    )
    assert derivative_pnl(1010, 1000, 10, side=PositionSide.SHORT) == pytest.approx(
        10_000_000.0
    )


def test_iso_02_insufficient_buying_power_rejected(session) -> None:  # noqa: F811
    """TEST-ISO-02: order exceeding buying power → REJECTED; balance unchanged."""
    engine = SimulationEngine(session)
    portfolio = _new_portfolio(session, balance=1_000_000.0)
    before = portfolio.cash_balance

    # 1000 contracts of an equity at 100k each = 100M >> 1M balance.
    order = engine.place_order(
        portfolio=portfolio,
        symbol="VNM",
        side=OrderSide.BUY,
        quantity=1000,
        price=100_000.0,
    )
    assert order.status == OrderStatus.REJECTED
    assert order.reject_reason is not None
    # Balance untouched.
    session.refresh(portfolio)
    assert portfolio.cash_balance == before


def test_buy_then_close_realizes_pnl(session) -> None:  # noqa: F811
    """A filled long position closed at a higher price realizes positive PnL."""
    engine = SimulationEngine(session)
    portfolio = _new_portfolio(session, balance=200_000_000.0)

    order = engine.place_order(
        portfolio=portfolio,
        symbol="VN30F1M",
        side=OrderSide.LONG,
        quantity=10,
        price=1000.0,
    )
    assert order.status == OrderStatus.FILLED
    positions = engine.open_positions(portfolio.id)
    assert len(positions) == 1
    pos = positions[0]
    assert pos.side == PositionSide.LONG
    assert pos.quantity == 10

    trade = engine.close_position(
        portfolio=portfolio, position=pos, quantity=10, price=1010.0
    )
    # Gross = (1010-1000)*10*100_000 = 10,000,000 minus fees/tax.
    assert trade.realized_pnl > 0
    assert trade.realized_pnl < 10_000_000.0  # fees + tax deducted


def test_position_closed_status(session) -> None:  # noqa: F811
    """Fully closing a position flips it to CLOSED."""
    engine = SimulationEngine(session)
    portfolio = _new_portfolio(session, balance=200_000_000.0)
    _ = engine.place_order(
        portfolio=portfolio,
        symbol="VN30F1M",
        side=OrderSide.LONG,
        quantity=5,
        price=1000.0,
    )
    pos = engine.open_positions(portfolio.id)[0]
    engine.close_position(portfolio=portfolio, position=pos, quantity=5, price=1005.0)
    session.refresh(pos)
    assert pos.status == PositionStatus.CLOSED
    assert engine.open_positions(portfolio.id) == []


def test_cancel_pending_order(session) -> None:  # noqa: F811
    """A LIMIT order far from market stays PENDING and can be cancelled."""
    engine = SimulationEngine(session)
    portfolio = _new_portfolio(session, balance=200_000_000.0)
    from app.models.enums import OrderType

    order = engine.place_order(
        portfolio=portfolio,
        symbol="VNM",
        side=OrderSide.BUY,
        quantity=10,
        price=50_000.0,
        order_type=OrderType.LIMIT,
    )
    # A limit buy may fill or pend depending on engine policy; either way it
    # must be a known status, and cancel of a non-pending order must error.
    if order.status == OrderStatus.PENDING:
        cancelled = engine.cancel_order(order.id)
        assert cancelled.status == OrderStatus.CANCELLED
    else:
        with pytest.raises(SimulationError):
            engine.cancel_order(order.id)


def test_get_portfolio_ownership_enforced(session) -> None:  # noqa: F811
    """get_portfolio raises for a portfolio not owned by the requesting user."""
    engine = SimulationEngine(session)
    owner = uuid.uuid4()
    p = engine.create_portfolio(user_id=owner, name="mine")
    # Correct owner resolves.
    assert engine.get_portfolio(p.id, user_id=owner).id == p.id
    # A different user must not access it.
    with pytest.raises(SimulationError):
        engine.get_portfolio(p.id, user_id=uuid.uuid4())


def test_equity_short_not_allowed_for_equity(session) -> None:  # noqa: F811
    """SHORT on a cash equity symbol is rejected (no borrow book in Phase 1)."""
    engine = SimulationEngine(session)
    portfolio = _new_portfolio(session, balance=200_000_000.0)
    with pytest.raises(SimulationError):
        engine.place_order(
            portfolio=portfolio,
            symbol="VNM",
            side=OrderSide.SHORT,
            quantity=10,
            price=100_000.0,
        )


def test_trade_history_persisted(session) -> None:  # noqa: F811
    """Every fill writes a Trade ledger row."""
    engine = SimulationEngine(session)
    portfolio = _new_portfolio(session, balance=200_000_000.0)
    engine.place_order(
        portfolio=portfolio,
        symbol="VN30F1M",
        side=OrderSide.LONG,
        quantity=5,
        price=1000.0,
    )
    pos = engine.open_positions(portfolio.id)[0]
    engine.close_position(portfolio=portfolio, position=pos, quantity=5, price=1008.0)
    trades = session.exec(select(Trade).where(Trade.portfolio_id == portfolio.id)).all()
    # One open fill + one close fill.
    assert len(trades) >= 2
