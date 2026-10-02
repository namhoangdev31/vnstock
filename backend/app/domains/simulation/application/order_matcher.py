"""Order Matcher - tick-driven filling for pending LIMIT/STOP orders.

Matches PENDING orders against incoming tick prices with realistic slippage
constraints. Supports:
- LIMIT orders: fill when tick_price crosses order.price
- STOP orders: trigger on stop_price cross, fill at market
- Trailing stops: adjust stop_price via ATR (optional)

RULE 1 & 2: paper-only simulation, isolated to simulation_* tables.
RULE 3: prices come from real market data (tick_price parameter); matcher
never fabricates fill prices - it only applies documented slippage.
"""

from __future__ import annotations

from datetime import datetime

from sqlmodel import Session, col, select

from app.core.enums import OrderSide, OrderStatus, OrderType
from app.core.models_base import VN_TZ
from app.domains.simulation.application.engine import SimulationEngine
from app.domains.simulation.domain.exceptions import SimulationError
from app.domains.simulation.domain.models import Order, Portfolio, Trade

SLIPPAGE_DERIVATIVE_PT = 0.1
SLIPPAGE_EQUITY_PCT = 0.001
TRAIL_K_DEFAULT = 1.0


def _apply_slippage(
    tick_price: float, side: str, _symbol: str, is_derivative: bool
) -> float:
    """Apply adverse slippage to market fill price.

    Derivatives: BUY +0.1 pt / SELL -0.1 pt
    Equities: BUY * 1.001 / SELL * 0.999
    """
    if is_derivative:
        if side in ("BUY", "LONG", "B"):
            return tick_price + SLIPPAGE_DERIVATIVE_PT
        else:
            return tick_price - SLIPPAGE_DERIVATIVE_PT
    else:
        if side in ("BUY", "LONG", "B"):
            return tick_price * (1.0 + SLIPPAGE_EQUITY_PCT)
        else:
            return tick_price * (1.0 - SLIPPAGE_EQUITY_PCT)


def _is_derivative(symbol: str) -> bool:
    """Check if symbol is a derivative (VN30F1M contract)."""
    return "F1M" in symbol.upper() or "VN30F" in symbol.upper()


def match_pending_orders(
    session: Session,
    symbol: str,
    tick_price: float,
    tick_volume: int,
    tick_time: datetime,
    *,
    atr14: float | None = None,
    trail_k: float = TRAIL_K_DEFAULT,
) -> list[Trade]:
    """Match pending orders against market tick for symbol.

    Matching logic:
    - LIMIT BUY: fill if tick_price <= order.price
    - LIMIT SELL: fill if tick_price >= order.price
    - STOP: trigger on stop_price cross, fill at market +/- slippage
    - Trailing STOP (SELL + atr14): raise stop_price = tick_price - k*atr14
    - MARKET: always fill at tick_price +/- slippage

    Liquidity constraint: fill_qty = min(order_remaining, tick_volume).
    Partial fills supported; order stays PENDING until fully filled.

    Returns list of created Trade rows (may be empty).
    """
    if tick_time.tzinfo is None:
        tick_time = tick_time.replace(tzinfo=VN_TZ)

    engine = SimulationEngine(session)
    is_deriv = _is_derivative(symbol)

    orders = session.exec(
        select(Order)
        .where(Order.symbol == symbol)
        .where(col(Order.status) == OrderStatus.PENDING)
        .order_by(col(Order.created_at).asc())
    ).all()

    trades: list[Trade] = []

    for order in orders:
        remaining = order.quantity - order.filled_quantity
        fill_qty = min(remaining, max(tick_volume, 0))
        if fill_qty <= 0:
            continue

        fill_price: float | None = None

        if order.order_type == OrderType.LIMIT:
            if order.side in (OrderSide.BUY, OrderSide.LONG):
                if tick_price <= order.price:
                    fill_price = min(tick_price, order.price)
            else:
                if tick_price >= order.price:
                    fill_price = max(tick_price, order.price)

        elif order.order_type == OrderType.STOP:
            stop_price = order.stop_price
            if stop_price is None:
                continue

            if (
                order.side in (OrderSide.SELL, OrderSide.SHORT)
                and atr14 is not None
                and atr14 > 0
            ):
                new_stop = tick_price - trail_k * atr14
                if new_stop > stop_price:
                    order.stop_price = new_stop
                    session.add(order)
                    stop_price = new_stop

            if order.side in (OrderSide.BUY, OrderSide.LONG):
                if tick_price >= stop_price:
                    fill_price = _apply_slippage(
                        tick_price, order.side, symbol, is_deriv
                    )
            else:
                if tick_price <= stop_price:
                    fill_price = _apply_slippage(
                        tick_price, order.side, symbol, is_deriv
                    )

        elif order.order_type == OrderType.MARKET:
            fill_price = _apply_slippage(tick_price, order.side, symbol, is_deriv)

        if fill_price is None:
            continue

        portfolio = session.get(Portfolio, order.portfolio_id)
        if portfolio is None:
            order.status = OrderStatus.REJECTED
            order.reject_reason = f"Portfolio {order.portfolio_id} not found"
            session.add(order)
            continue

        try:
            trade = engine._fill(
                order,
                portfolio,
                fill_price=fill_price,
                deriv=is_deriv,
                intent=engine._classify(portfolio.id, order.symbol, order.side),
                quantity=fill_qty,
                executed_at=tick_time,
            )
            if trade is not None:
                trades.append(trade)
        except SimulationError as exc:
            order.status = OrderStatus.REJECTED
            order.reject_reason = str(exc)
            session.add(order)
        except Exception as exc:
            order.status = OrderStatus.REJECTED
            order.reject_reason = f"Fill error: {exc}"
            session.add(order)

    session.commit()
    return trades
