"""Unit tests for app.models package.

Tests timezone-awareness validation, model instantiation, enum values,
and pure PnL / financial calculation utilities without needing an active PostgreSQL DB.
"""

import uuid
from datetime import UTC, date, datetime

import pytest

from app.models.enums import (
    DEFAULT_INITIAL_BALANCE,
    Exchange,
    ForecastDirection,
    ForecastHorizon,
    ForecastStatus,
    MacroIndicatorCode,
    OrderSide,
    OrderStatus,
    OrderType,
    PositionSide,
    PositionStatus,
)
from app.models.models_base import AwareSQLModel, get_datetime_utc
from app.models.models_quant import (
    ForecastJournal,
    InstitutionalFlow,
    MacroIndicator,
    MarketBreadth,
    TickFlowAggregated,
)
from app.models.models_simulation import (
    SimulationOrder,
    SimulationPortfolio,
    SimulationPosition,
    SimulationTrade,
    derivative_pnl,
    round_money,
)


class DummyTimeModel(AwareSQLModel):
    timestamp: datetime


def test_aware_sqlmodel_rejects_naive_datetime() -> None:
    """AwareSQLModel must reject naive datetimes (RULE 3 compliance)."""
    naive_dt = datetime(2026, 9, 17, 10, 0, 0)
    with pytest.raises(ValueError, match="timezone-naive datetime is not allowed"):
        DummyTimeModel(timestamp=naive_dt)


def test_aware_sqlmodel_accepts_utc_datetime() -> None:
    """AwareSQLModel must accept UTC-aware datetimes."""
    utc_dt = datetime(2026, 9, 17, 10, 0, 0, tzinfo=UTC)
    m = DummyTimeModel(timestamp=utc_dt)
    assert m.timestamp == utc_dt


def test_forecast_journal_instantiation() -> None:
    """ForecastJournal must have proper defaults and audit fields."""
    now = get_datetime_utc()
    journal = ForecastJournal(
        symbol="VN30F1M",
        horizon=ForecastHorizon.ATC,
        predicted_at=now,
        predicted_value=1350.5,
        predicted_direction=ForecastDirection.BULLISH,
        engine_weights={"engine1": 0.4, "engine2": 0.3, "engine3": 0.3},
        model_version="v1.0.0",
        parameter_snapshot={"threshold": 0.02},
    )
    assert journal.symbol == "VN30F1M"
    assert journal.status == ForecastStatus.PENDING
    assert journal.actual_value is None
    assert journal.score is None


def test_simulation_models_instantiation() -> None:
    """Simulation models must initialize with clean domain fields."""
    user_id = uuid.uuid4()
    portfolio = SimulationPortfolio(
        user_id=user_id,
        name="Test Portfolio",
    )
    assert portfolio.initial_balance == DEFAULT_INITIAL_BALANCE
    assert portfolio.cash_balance == DEFAULT_INITIAL_BALANCE
    assert portfolio.equity == DEFAULT_INITIAL_BALANCE
    assert portfolio.margin_used == 0.0

    order = SimulationOrder(
        portfolio_id=portfolio.id,
        symbol="VN30F1M",
        side=OrderSide.LONG,
        order_type=OrderType.MARKET,
        price=1320.0,
        quantity=5,
    )
    assert order.status == OrderStatus.PENDING
    assert order.filled_quantity == 0

    position = SimulationPosition(
        portfolio_id=portfolio.id,
        symbol="VN30F1M",
        side=PositionSide.LONG,
        quantity=5,
        entry_price=1320.0,
        current_price=1325.0,
    )
    assert position.status == PositionStatus.OPEN


def test_derivative_pnl_calculation() -> None:
    """Verify standard VN30F1M derivative PnL formulas."""
    # Long 2 contracts: +5 points = +5 * 2 * 100,000 = +1,000,000 VND
    long_pnl = derivative_pnl(
        entry_price=1300.0, exit_price=1305.0, quantity=2, side=PositionSide.LONG
    )
    assert long_pnl == 1_000_000.0

    # Short 2 contracts: +5 points = -1,000,000 VND
    short_pnl = derivative_pnl(
        entry_price=1300.0, exit_price=1305.0, quantity=2, side=PositionSide.SHORT
    )
    assert short_pnl == -1_000_000.0

    # Short 2 contracts: -5 points = +1,000,000 VND
    short_gain = derivative_pnl(
        entry_price=1305.0, exit_price=1300.0, quantity=2, side=PositionSide.SHORT
    )
    assert short_gain == 1_000_000.0


def test_round_money() -> None:
    """Verify rounding VND amounts to the nearest integer VND."""
    assert round_money(100500.4) == 100500.0
    assert round_money(100500.6) == 100501.0


def test_macro_and_market_breadth_models() -> None:
    """Verify MacroIndicator and MarketBreadth models."""
    macro = MacroIndicator(
        recorded_date=date(2026, 9, 17),
        indicator_code=MacroIndicatorCode.USD_VND,
        value=25450.0,
        source="VCB",
    )
    assert macro.value == 25450.0

    breadth = MarketBreadth(
        trading_date=date(2026, 9, 17),
        exchange=Exchange.HOSE,
        advancers=210,
        decliners=180,
        unchanged=70,
        ceiling_count=12,
        floor_count=3,
        total_volume=750_000_000,
        total_value=18_500_000_000_000.0,
    )
    assert breadth.advancers == 210
    assert breadth.ceiling_count == 12

    flow = InstitutionalFlow(
        trading_date=date(2026, 9, 17),
        symbol="VN30F1M",
        foreign_buy_value=100_000_000.0,
        foreign_sell_value=80_000_000.0,
        foreign_net_value=20_000_000.0,
        prop_buy_value=50_000_000.0,
        prop_sell_value=40_000_000.0,
        prop_net_value=10_000_000.0,
        source="TCBS",
    )
    assert flow.foreign_net_value == 20_000_000.0

    tick = TickFlowAggregated(
        symbol="VN30F1M",
        timestamp=get_datetime_utc(),
        source="vci",
        aggressive_buy_volume=150,
        aggressive_sell_volume=90,
        volume_delta=60,
        trade_count=45,
        vwap=1322.5,
    )
    assert tick.volume_delta == 60

    trade = SimulationTrade(
        portfolio_id=uuid.uuid4(),
        symbol="VN30F1M",
        side=OrderSide.BUY,
        quantity=2,
        price=1320.0,
        fee=10000.0,
        tax=5000.0,
        realized_pnl=0.0,
    )
    assert trade.quantity == 2


if __name__ == "__main__":
    test_aware_sqlmodel_rejects_naive_datetime()
    test_aware_sqlmodel_accepts_utc_datetime()
    test_forecast_journal_instantiation()
    test_simulation_models_instantiation()
    test_derivative_pnl_calculation()
    test_round_money()
    test_macro_and_market_breadth_models()
