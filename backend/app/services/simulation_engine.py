"""SimulationEngine — isolated paper-trading order matching (RULE 1 & RULE 2).

This engine NEVER touches a real brokerage. It models an isolated simulated
account: portfolios, orders, positions and trades. No credential, API key,
password, PIN, OTP or session secret is accepted, stored or referenced anywhere
in this module or its models (TEST-ISO-01).

Accounting model
----------------
A portfolio holds ``cash_balance`` (free cash) and ``margin_used`` (locked
collateral). Equity is conserved as::

    equity = cash_balance + margin_used + sum(unrealized_pnl)

- Opening a derivative LONG/SHORT debits ``margin + fee`` from cash and adds the
  margin to ``margin_used``. Closing releases the margin back and credits the
  realized PnL. Derivative PnL uses the VN30F1M multiplier of 100,000 VND per
  index point (TEST-ISO-03).
- Opening an equity BUY debits the full notional + fee (cash market, no
  leverage). SELL reduces an existing LONG, crediting proceeds less fee and the
  0.1% transfer tax. Equities cannot be shorted — a SELL with no shares is
  rejected.
- Insufficient buying power / shares → the order is ``REJECTED`` and balances are
  left untouched (TEST-ISO-02).

Phase 1 does not model position flipping (reducing beyond an open quantity),
LIMIT/STOP fills, or a trading calendar; settlement_date is weekday-approximate.
"""

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from uuid import UUID

from sqlmodel import Session, select

from app.models import VN_TZ
from app.models.entities.simulation import (
    Order,
    Portfolio,
    Position,
    Trade,
    derivative_pnl,
    round_money,
)
from app.models.enums import (
    DERIVATIVE_MULTIPLIER,
    EQUITY_SETTLEMENT_DAYS,
    OrderSide,
    OrderStatus,
    OrderType,
    PositionSide,
    PositionStatus,
)

logger = logging.getLogger(__name__)

# Sides that open/increase a LONG vs. a SHORT.
_BULLISH_SIDES = {OrderSide.BUY, OrderSide.LONG}
_BEARISH_SIDES = {OrderSide.SELL, OrderSide.SHORT}

# Futures contract codes look like VN30F1M / VN30F2M / VN30F1Y ...
_DERIVATIVE_PREFIXES = ("VN30F",)


class SimulationError(Exception):
    """Raised on invalid simulation operations."""


@dataclass(frozen=True)
class SimulationConfig:
    """Fee / tax / margin parameters for the paper account.

    Defaults approximate typical Vietnamese retail terms. Injected so tests can
    pin exact values for PnL assertions (TEST-ISO-03).
    """

    equity_fee_rate: float = 0.0015  # 0.15% per side
    equity_tax_rate: float = 0.001  # 0.1% on equity sells
    derivative_fee_rate: float = 0.00025  # 0.025% per side
    derivative_margin_rate: float = 0.135  # ~13.5% initial margin


def is_derivative(symbol: str) -> bool:
    """True for VN30 index-futures contracts (T+0, 100k multiplier)."""
    return str(symbol).upper().startswith(_DERIVATIVE_PREFIXES)


def _business_days_after(start: date, days: int) -> date:
    """Add ``days`` weekdays to ``start`` (public holidays not excluded in P1)."""
    if days <= 0:
        return start
    added = 0
    cursor = start
    while added < days:
        cursor += timedelta(days=1)
        if cursor.weekday() < 5:  # Mon–Fri
            added += 1
    return cursor


class SimulationEngine:
    """Match paper orders against an isolated simulated portfolio."""

    def __init__(
        self, session: Session, config: SimulationConfig | None = None
    ) -> None:
        self.session = session
        self.config = config or SimulationConfig()

    # ------------------------------------------------------------------
    # Portfolio lifecycle
    # ------------------------------------------------------------------

    def create_portfolio(
        self,
        *,
        user_id: UUID,
        name: str,
        initial_balance: float = 100_000_000.0,
    ) -> Portfolio:
        balance = round_money(initial_balance)
        portfolio = Portfolio(
            user_id=user_id,
            name=name,
            initial_balance=balance,
            cash_balance=balance,
            equity=balance,
            margin_used=0.0,
        )
        self.session.add(portfolio)
        self.session.commit()
        self.session.refresh(portfolio)
        logger.info(
            "Created simulation portfolio %s for user %s", portfolio.id, user_id
        )
        return portfolio

    def get_portfolio(self, portfolio_id: UUID, *, user_id: UUID) -> Portfolio:
        """Fetch a portfolio with an ownership check (RULE 2 isolation)."""
        portfolio = self.session.get(Portfolio, portfolio_id)
        if portfolio is None:
            raise SimulationError(f"Portfolio {portfolio_id} not found")
        if portfolio.user_id != user_id:
            raise SimulationError("Portfolio does not belong to this user")
        return portfolio

    def list_portfolios(self, *, user_id: UUID) -> list[Portfolio]:
        return list(
            self.session.exec(
                select(Portfolio).where(Portfolio.user_id == user_id)
            ).all()
        )

    # ------------------------------------------------------------------
    # Order placement
    # ------------------------------------------------------------------

    def place_order(
        self,
        *,
        portfolio: Portfolio,
        symbol: str,
        side: str,
        quantity: int,
        price: float,
        order_type: str = OrderType.MARKET,
        stop_price: float | None = None,
    ) -> Order:
        """Validate and (for MARKET orders) fill a paper order immediately.

        Rejection conditions leave balances untouched:
        - equity SELL/SHORT with no matching LONG position (equities can't short)
        - reducing more than the open quantity
        - insufficient buying power to open
        """
        side_norm = str(side).upper()
        if side_norm not in {s.value for s in OrderSide}:
            raise SimulationError(f"Invalid order side: {side}")
        if quantity <= 0:
            raise SimulationError("quantity must be positive")
        if price <= 0:
            raise SimulationError("price must be positive")

        deriv = is_derivative(symbol)
        if not deriv and side_norm in {OrderSide.SHORT, OrderSide.LONG}:
            raise SimulationError(
                f"{side_norm} orders are only valid for derivatives, not equities"
            )
        if order_type == OrderType.STOP and stop_price is None:
            raise SimulationError("STOP orders require a stop_price")

        intent = self._classify(portfolio.id, symbol, side_norm)

        order = Order(
            portfolio_id=portfolio.id,
            symbol=symbol,
            side=side_norm,
            order_type=order_type,
            price=price,
            stop_price=stop_price,
            quantity=quantity,
            status=OrderStatus.PENDING,
        )

        if order_type == OrderType.MARKET:
            reject_reason = self._precheck(portfolio, order, deriv=deriv, intent=intent)
            if reject_reason is not None:
                order.status = OrderStatus.REJECTED
                order.reject_reason = reject_reason[:255]
                self.session.add(order)
                self.session.commit()
                self.session.refresh(order)
                logger.info("Rejected order for %s: %s", symbol, reject_reason)
                return order

        self.session.add(order)
        self.session.commit()
        self.session.refresh(order)

        if order_type == OrderType.MARKET:
            self._fill(order, portfolio, fill_price=price, deriv=deriv, intent=intent)
        return order

    def cancel_order(self, order_id: UUID) -> Order:
        order = self.session.get(Order, order_id)
        if order is None:
            raise SimulationError(f"Order {order_id} not found")
        if order.status != OrderStatus.PENDING:
            raise SimulationError(
                f"Only PENDING orders can be cancelled (got {order.status})"
            )
        order.status = OrderStatus.CANCELLED
        order.updated_at = datetime.now(VN_TZ)
        self.session.add(order)
        self.session.commit()
        self.session.refresh(order)
        return order

    # ------------------------------------------------------------------
    # Intent classification
    # ------------------------------------------------------------------

    def _classify(
        self, portfolio_id: UUID, symbol: str, side: str
    ) -> tuple[str, Position | None]:
        """Decide whether ``side`` reduces an opposite position or opens one.

        Returns ``("reduce", opposite_position)`` or ``("open", same_direction_position_or_None)``.
        """
        target = PositionSide.LONG if side in _BULLISH_SIDES else PositionSide.SHORT
        opposite = (
            PositionSide.SHORT if target == PositionSide.LONG else PositionSide.LONG
        )

        opp_pos = self._open_position(portfolio_id, symbol, opposite)
        if opp_pos is not None:
            return ("reduce", opp_pos)

        same_pos = self._open_position(portfolio_id, symbol, target)
        return ("open", same_pos)

    def _precheck(
        self,
        portfolio: Portfolio,
        order: Order,
        *,
        deriv: bool,
        intent: tuple[str, Position | None],
    ) -> str | None:
        """Return a rejection reason, or None if the MARKET order may proceed."""
        kind, position = intent
        mult = DERIVATIVE_MULTIPLIER if deriv else 1
        notional = order.price * order.quantity * mult

        if kind == "reduce":
            assert position is not None
            if order.quantity > position.quantity:
                return (
                    f"Cannot reduce {order.quantity}; open position holds "
                    f"{position.quantity}"
                )
            return None

        # Opening.
        fee = self._fee(notional, deriv)
        if deriv:
            margin = notional * self.config.derivative_margin_rate
            required = margin + fee  # derivatives carry no transfer tax
        else:
            # Equity opens are always LONG (BUY); a SELL with no position is a
            # short attempt, which the cash market forbids.
            if order.side in _BEARISH_SIDES:
                return "No open position to sell; equities cannot be shorted"
            required = notional + fee

        if required > portfolio.cash_balance + 1e-6:
            return (
                f"Insufficient buying power: required {round_money(required)} > "
                f"available {round_money(portfolio.cash_balance)}"
            )
        return None

    # ------------------------------------------------------------------
    # Fill logic
    # ------------------------------------------------------------------

    def _fill(
        self,
        order: Order,
        portfolio: Portfolio,
        *,
        fill_price: float,
        deriv: bool,
        intent: tuple[str, Position | None],
    ) -> None:
        kind, position = intent
        mult = DERIVATIVE_MULTIPLIER if deriv else 1
        notional = fill_price * order.quantity * mult
        fee = self._fee(notional, deriv)

        if kind == "reduce":
            assert position is not None
            tax = 0.0 if deriv else round_money(notional * self.config.equity_tax_rate)
            realized = self._reduce_position(
                portfolio, position, order.quantity, fill_price, mult, fee, tax, deriv
            )
        else:
            tax = 0.0  # opening buys incur no transfer tax
            realized = 0.0
            self._apply_open_fill(
                portfolio, position, order, fill_price, mult, fee, tax, deriv
            )

        order.filled_quantity = order.quantity
        order.filled_price = fill_price
        order.fee = fee
        order.tax = tax
        order.status = OrderStatus.FILLED
        order.updated_at = datetime.now(VN_TZ)
        self.session.add(order)

        trade = Trade(
            portfolio_id=portfolio.id,
            order_id=order.id,
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            price=fill_price,
            fee=fee,
            tax=tax,
            realized_pnl=realized,
        )
        self.session.add(trade)

        self._refresh_equity(portfolio)
        portfolio.updated_at = datetime.now(VN_TZ)
        self.session.add(portfolio)
        self.session.commit()
        self.session.refresh(order)
        self.session.refresh(portfolio)

    def _apply_open_fill(
        self,
        portfolio: Portfolio,
        existing: Position | None,
        order: Order,
        fill_price: float,
        mult: int,
        fee: float,
        tax: float,
        deriv: bool,
    ) -> None:
        """Create or increase a position; debit cash (and margin for derivatives)."""
        notional = fill_price * order.quantity * mult
        target_side = (
            PositionSide.LONG if order.side in _BULLISH_SIDES else PositionSide.SHORT
        )
        margin_add = notional * self.config.derivative_margin_rate if deriv else 0.0

        if deriv:
            portfolio.cash_balance = round_money(
                portfolio.cash_balance - margin_add - fee - tax
            )
            portfolio.margin_used = round_money(portfolio.margin_used + margin_add)
        elif order.side in _BULLISH_SIDES:
            portfolio.cash_balance = round_money(
                portfolio.cash_balance - notional - fee - tax
            )
        # Equity SELL never reaches here (rejected in _precheck).

        if existing is None:
            settlement = (
                None
                if deriv
                else _business_days_after(date.today(), EQUITY_SETTLEMENT_DAYS)
            )
            position = Position(
                portfolio_id=portfolio.id,
                symbol=order.symbol,
                side=target_side,
                quantity=order.quantity,
                entry_price=fill_price,
                current_price=fill_price,
                unrealized_pnl=0.0,
                realized_pnl=0.0,
                margin_required=round_money(margin_add),
                settlement_date=settlement,
                status=PositionStatus.OPEN,
            )
            self.session.add(position)
            return

        # Increase an existing same-direction position (average the entry).
        new_qty = existing.quantity + order.quantity
        existing.entry_price = round(
            (existing.entry_price * existing.quantity + fill_price * order.quantity)
            / new_qty,
            4,
        )
        existing.quantity = new_qty
        existing.margin_required = round_money(existing.margin_required + margin_add)
        self._mark_position(existing, fill_price, mult)
        existing.updated_at = datetime.now(VN_TZ)
        self.session.add(existing)

    def _reduce_position(
        self,
        portfolio: Portfolio,
        position: Position,
        quantity: int,
        fill_price: float,
        mult: int,
        fee: float,
        tax: float,
        deriv: bool,
    ) -> float:
        """Close ``quantity`` of an open position; realize PnL; return realized."""
        if deriv:
            gross = derivative_pnl(
                entry_price=position.entry_price,
                exit_price=fill_price,
                quantity=quantity,
                side=position.side,
                multiplier=mult,
            )
        else:
            sign = 1 if position.side == PositionSide.LONG else -1
            gross = (fill_price - position.entry_price) * quantity * sign
        realized = round_money(gross - fee - tax)

        notional = fill_price * quantity * mult
        if deriv:
            released = round_money(
                position.margin_required * (quantity / position.quantity)
            )
            portfolio.margin_used = round_money(portfolio.margin_used - released)
            position.margin_required = round_money(position.margin_required - released)
            portfolio.cash_balance = round_money(
                portfolio.cash_balance + released + realized
            )
        else:
            # Equity long close: proceeds land in cash; realized PnL is implicit.
            portfolio.cash_balance = round_money(
                portfolio.cash_balance + notional - fee - tax
            )

        position.quantity -= quantity
        position.realized_pnl = round_money(position.realized_pnl + realized)
        if position.quantity == 0:
            position.status = PositionStatus.CLOSED
        else:
            self._mark_position(position, fill_price, mult)
        position.updated_at = datetime.now(VN_TZ)
        self.session.add(position)
        return realized

    def close_position(
        self,
        *,
        portfolio: Portfolio,
        position: Position,
        quantity: int,
        price: float,
    ) -> Trade:
        """Explicitly close (part of) an open position, realizing PnL."""
        if quantity <= 0 or quantity > position.quantity:
            raise SimulationError(
                f"Cannot close {quantity} of position holding {position.quantity}"
            )
        deriv = is_derivative(position.symbol)
        mult = DERIVATIVE_MULTIPLIER if deriv else 1
        notional = price * quantity * mult
        fee = self._fee(notional, deriv)
        tax = 0.0 if deriv else round_money(notional * self.config.equity_tax_rate)
        realized = self._reduce_position(
            portfolio, position, quantity, price, mult, fee, tax, deriv
        )

        trade = Trade(
            portfolio_id=portfolio.id,
            order_id=None,
            symbol=position.symbol,
            side=(
                OrderSide.SELL if position.side == PositionSide.LONG else OrderSide.BUY
            ),
            quantity=quantity,
            price=price,
            fee=fee,
            tax=tax,
            realized_pnl=realized,
        )
        self.session.add(trade)

        self._refresh_equity(portfolio)
        portfolio.updated_at = datetime.now(VN_TZ)
        self.session.add(portfolio)
        self.session.commit()
        self.session.refresh(trade)
        return trade

    # ------------------------------------------------------------------
    # Mark-to-market
    # ------------------------------------------------------------------

    def mark_to_market(
        self, portfolio: Portfolio, prices: dict[str, float]
    ) -> Portfolio:
        """Update prices, unrealized PnL and equity from a symbol→price map.

        Symbols absent from the map keep their last current_price (RULE 3: never
        fabricate a price).
        """
        for position in self.open_positions(portfolio.id):
            mult = DERIVATIVE_MULTIPLIER if is_derivative(position.symbol) else 1
            if position.symbol in prices:
                self._mark_position(position, prices[position.symbol], mult)
                self.session.add(position)
        self._refresh_equity(portfolio)
        portfolio.updated_at = datetime.now(VN_TZ)
        self.session.add(portfolio)
        self.session.commit()
        self.session.refresh(portfolio)
        return portfolio

    def _mark_position(self, position: Position, price: float, mult: int) -> None:
        sign = 1 if position.side == PositionSide.LONG else -1
        position.current_price = price
        position.unrealized_pnl = round_money(
            (price - position.entry_price) * position.quantity * mult * sign
        )

    def _refresh_equity(self, portfolio: Portfolio) -> None:
        unrealized = sum(p.unrealized_pnl for p in self.open_positions(portfolio.id))
        portfolio.equity = round_money(
            portfolio.cash_balance + portfolio.margin_used + unrealized
        )

    # ------------------------------------------------------------------
    # Queries & helpers
    # ------------------------------------------------------------------

    def open_positions(self, portfolio_id: UUID) -> list[Position]:
        return list(
            self.session.exec(
                select(Position)
                .where(Position.portfolio_id == portfolio_id)
                .where(Position.status == PositionStatus.OPEN)
            ).all()
        )

    def _open_position(
        self, portfolio_id: UUID, symbol: str, side: str
    ) -> Position | None:
        return self.session.exec(
            select(Position)
            .where(Position.portfolio_id == portfolio_id)
            .where(Position.symbol == symbol)
            .where(Position.side == side)
            .where(Position.status == PositionStatus.OPEN)
        ).first()

    def _fee(self, notional: float, deriv: bool) -> float:
        rate = self.config.derivative_fee_rate if deriv else self.config.equity_fee_rate
        return round_money(notional * rate)
