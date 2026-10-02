"""Tests for Phase 4: Realistic Paper Trading & Multi-Horizon Equity Screener (T+2).

Covers:
1. Tick-driven order matcher (LIMIT partial fills, price improvement, PENDING->FILLED)
2. VSDC margin calculator (IM 17%, MM 13%, multiplier 100k, SAFE / CALL_MARGIN / FORCE_LIQUIDATION)
3. T+2 settlement timing (Friday -> Tuesday 13:00 VN, sell-lock enforcement and release)
4. Multi-horizon equity alpha screener (Weekly, Monthly, Quarterly + Piotroski F-Score)
5. Router endpoints smoke test (margin-status, settlement process, alpha baskets)
"""

from datetime import date, datetime, timedelta

import pytest
from sqlmodel import Session

from app.core.config import settings
from app.core.enums import (
    Exchange,
    ForecastDirection,
    ForecastHorizon,
    ForecastStatus,
    OrderSide,
    OrderStatus,
    OrderType,
    PositionSide,
    PositionStatus,
)
from app.core.models_base import VN_TZ
from app.domains.fundamental.domain.models import FinancialRatio, FinancialReport
from app.domains.market_data.domain.models import (
    StockOHLCVDaily,
    StockSymbol,
)
from app.domains.quant.application.forecast_journal_service import (
    ForecastJournalService,
)
from app.domains.quant.domain.models import ForecastJournal, InstitutionalFlow
from app.domains.simulation.application.alpha_screener import screen
from app.domains.simulation.application.engine import SimulationEngine
from app.domains.simulation.application.margin_calculator import (
    STATUS_CALL_MARGIN,
    STATUS_FORCE_LIQUIDATION,
    STATUS_SAFE,
    calculate_required_margin,
    calculate_unrealized_pnl,
    check_margin_status,
)
from app.domains.simulation.application.order_matcher import match_pending_orders
from app.domains.simulation.application.t_plus_2_manager import (
    available_quantity,
    create_ledger_row,
    process_due_settlements,
)
from app.domains.simulation.domain.exceptions import SimulationError
from app.domains.simulation.domain.models import (
    SETTLEMENT_AVAILABLE,
    SETTLEMENT_PENDING,
    Order,
    Position,
)
from app.domains.simulation.domain.settlement import SettlementService
from tests.utils.phase1 import (  # noqa: F401
    api_client,
    as_utc,
    session,
    sqlite_engine,
    user,
)

# ---------------------------------------------------------------------------
# 1. Order Matcher Tests
# ---------------------------------------------------------------------------


def test_order_matcher_limit_order(session: Session, user) -> None:  # noqa: F811
    """Test tick-driven matcher: LIMIT order partial fill, price improvement, FILLED transition."""
    engine = SimulationEngine(session)
    portfolio = engine.create_portfolio(
        user_id=user.id, name="Matcher Test", initial_balance=50_000_000.0
    )

    # Insert a LIMIT BUY order directly in PENDING status (bypassing MARKET instant fill)
    order = Order(
        portfolio_id=portfolio.id,
        symbol="HPG",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        price=25000.0,
        quantity=100,
        filled_quantity=0,
        status=OrderStatus.PENDING,
    )
    session.add(order)
    session.commit()
    session.refresh(order)

    tick_time = datetime(2026, 9, 18, 9, 30, tzinfo=VN_TZ)

    # 1. Tick above limit price (26,000 > 25,000) -> no fill, stays PENDING
    trades = match_pending_orders(
        session, "HPG", tick_price=26000.0, tick_volume=100, tick_time=tick_time
    )
    assert len(trades) == 0
    session.refresh(order)
    assert order.status == OrderStatus.PENDING
    assert order.filled_quantity == 0

    # 2. Tick below limit price with partial volume (24,000 <= 25,000, volume 60 < 100)
    # Price improvement: fills at tick_price (24,000)
    trades = match_pending_orders(
        session, "HPG", tick_price=24000.0, tick_volume=60, tick_time=tick_time
    )
    assert len(trades) == 1
    assert trades[0].quantity == 60
    assert trades[0].price == 24000.0
    session.refresh(order)
    assert order.status == OrderStatus.PENDING
    assert order.filled_quantity == 60
    assert order.filled_price == 24000.0

    # 3. Next tick completes the order (24,500 <= 25,000, volume 50 >= remaining 40)
    trades = match_pending_orders(
        session, "HPG", tick_price=24500.0, tick_volume=50, tick_time=tick_time
    )
    assert len(trades) == 1
    assert trades[0].quantity == 40
    assert trades[0].price == 24500.0
    session.refresh(order)
    assert order.status == OrderStatus.FILLED
    assert order.filled_quantity == 100
    # Weighted average filled price: (60*24000 + 40*24500) / 100 = 24200.0
    assert order.filled_price == pytest.approx(24200.0)


def test_order_matcher_trailing_stop_with_atr(session: Session, user) -> None:  # noqa: F811
    """Test Trailing STOP order with dynamic ATR adjustment and fill on downward reversal."""
    engine = SimulationEngine(session)
    portfolio = engine.create_portfolio(
        user_id=user.id, name="Trailing Stop Test", initial_balance=100_000_000.0
    )

    # 1. Establish an open position of 100 shares of FPT at 100,000
    pos = Position(
        portfolio_id=portfolio.id,
        symbol="FPT",
        side=PositionSide.LONG,
        quantity=100,
        entry_price=100_000.0,
        current_price=100_000.0,
        status=PositionStatus.OPEN,
    )
    session.add(pos)
    session.commit()

    # 2. Place a trailing stop SELL order with initial stop at 95,000
    stop_order = Order(
        portfolio_id=portfolio.id,
        symbol="FPT",
        side=OrderSide.SELL,
        order_type=OrderType.STOP,
        price=95000.0,
        stop_price=95000.0,
        quantity=100,
        filled_quantity=0,
        status=OrderStatus.PENDING,
    )
    session.add(stop_order)
    session.commit()
    session.refresh(stop_order)

    tick_time = datetime(2026, 9, 18, 10, 0, tzinfo=VN_TZ)
    atr = 2000.0  # ATR14 = 2,000 VND
    trail_k = 1.5  # Trail distance = 1.5 * 2000 = 3,000 VND

    # Tick 1: Price climbs to 105,000.
    # New stop = 105,000 - 3,000 = 102,000 > 95,000 -> Stop price ratchets to 102,000.
    # Since tick_price 105,000 > 102,000, no fill.
    trades = match_pending_orders(
        session,
        "FPT",
        tick_price=105000.0,
        tick_volume=200,
        tick_time=tick_time,
        atr14=atr,
        trail_k=trail_k,
    )
    assert len(trades) == 0
    session.refresh(stop_order)
    assert stop_order.status == OrderStatus.PENDING
    assert stop_order.stop_price == pytest.approx(102000.0)

    # Tick 2: Price climbs further to 110,000.
    # New stop = 110,000 - 3,000 = 107,000 > 102,000 -> Stop price ratchets to 107,000.
    trades = match_pending_orders(
        session,
        "FPT",
        tick_price=110000.0,
        tick_volume=200,
        tick_time=tick_time,
        atr14=atr,
        trail_k=trail_k,
    )
    assert len(trades) == 0
    session.refresh(stop_order)
    assert stop_order.stop_price == pytest.approx(107000.0)

    # Tick 3: Price drops slightly to 108,000.
    # New stop would be 108,000 - 3,000 = 105,000 < 107,000 -> Stop price does NOT decrease!
    trades = match_pending_orders(
        session,
        "FPT",
        tick_price=108000.0,
        tick_volume=200,
        tick_time=tick_time,
        atr14=atr,
        trail_k=trail_k,
    )
    assert len(trades) == 0
    session.refresh(stop_order)
    assert stop_order.stop_price == pytest.approx(107000.0)

    # Tick 4: Sharp drop to 106,000 <= stop_price (107,000) -> TRIGGERS STOP!
    # Equity SELL fill price has 0.1% slippage: 106,000 * 0.999 = 105,894.0
    trades = match_pending_orders(
        session,
        "FPT",
        tick_price=106000.0,
        tick_volume=200,
        tick_time=tick_time,
        atr14=atr,
        trail_k=trail_k,
    )
    assert len(trades) == 1
    assert trades[0].quantity == 100
    assert trades[0].price == pytest.approx(106000.0 * 0.999)
    session.refresh(stop_order)
    assert stop_order.status == OrderStatus.FILLED
    assert stop_order.filled_quantity == 100


# ---------------------------------------------------------------------------
# 2. VSDC Margin Calculator Tests
# ---------------------------------------------------------------------------


def test_margin_calculator_call_margin_and_liquidation() -> None:
    """Test IM/MM rates, PnL calculation, and VSDC margin safety statuses."""
    # 1. Initial Margin: 1 contract @ 1000.0 pts * 100,000 VND * 0.17 = 17,000,000 VND
    im = calculate_required_margin(1, 1000.0, im_rate=0.17)
    assert im == 17_000_000.0

    # 2. Unrealized PnL: LONG gain vs SHORT loss
    long_pnl = calculate_unrealized_pnl("LONG", 1, 1000.0, 1010.0)
    assert long_pnl == pytest.approx(1_000_000.0)

    short_pnl = calculate_unrealized_pnl("SHORT", 1, 1000.0, 1010.0)
    assert short_pnl == pytest.approx(-1_000_000.0)

    short_gain = calculate_unrealized_pnl("SHORT", 1, 1010.0, 1000.0)
    assert short_gain == pytest.approx(1_000_000.0)

    with pytest.raises(SimulationError):
        calculate_unrealized_pnl("INVALID", 1, 1000.0, 1010.0)

    # 3. Margin Status Thresholds (MM = 13%, Force Liquidation = 10%)
    pv = 100_000_000.0  # Total derivative position value
    assert check_margin_status(0.20 * pv, pv) == STATUS_SAFE
    assert check_margin_status(0.13 * pv, pv) == STATUS_SAFE
    assert check_margin_status(0.12 * pv, pv) == STATUS_CALL_MARGIN
    assert check_margin_status(0.09 * pv, pv) == STATUS_FORCE_LIQUIDATION
    assert check_margin_status(0.05 * pv, pv) == STATUS_FORCE_LIQUIDATION
    # No positions (pv = 0) -> always SAFE
    assert check_margin_status(50_000_000.0, 0.0) == STATUS_SAFE


# ---------------------------------------------------------------------------
# 3. T+2 Settlement Timing & Sell-Lock Tests
# ---------------------------------------------------------------------------


def test_t2_settlement_timing(session: Session, user) -> None:  # noqa: F811
    """Test Friday -> Tuesday 13:00 VN settlement exact time and sell-lock enforcement."""
    engine = SimulationEngine(session)
    portfolio = engine.create_portfolio(
        user_id=user.id, name="T+2 Portfolio", initial_balance=50_000_000.0
    )

    # Friday trade at 10:00 AM VN time (2026-09-18)
    fri_trade_dt = datetime(2026, 9, 18, 10, 0, tzinfo=VN_TZ)
    # Expected settlement is Tuesday 2026-09-22 at 13:00 VN time (cycle_days=2)
    expected_due = SettlementService.get_settlement_exact_time(
        fri_trade_dt.date(), cycle_days=2
    )
    assert expected_due == datetime(2026, 9, 22, 13, 0, tzinfo=VN_TZ)

    # Create a BUY ledger row representing 100 pending shares
    ledger_row = create_ledger_row(
        session,
        portfolio_id=portfolio.id,
        symbol="HPG",
        side="BUY",
        quantity=100,
        price=25000.0,
        trade_dt=fri_trade_dt,
    )
    session.commit()
    assert as_utc(ledger_row.settlement_due) == as_utc(expected_due)
    assert ledger_row.status == SETTLEMENT_PENDING

    # Create matching open position of 100 shares
    position = Position(
        portfolio_id=portfolio.id,
        symbol="HPG",
        side=PositionSide.LONG,
        quantity=100,
        entry_price=25000.0,
        current_price=25000.0,
        status=PositionStatus.OPEN,
    )
    session.add(position)
    session.commit()

    # 1. On Monday (2026-09-21 14:00 VN), settlement is not due yet
    mon_dt = datetime(2026, 9, 21, 14, 0, tzinfo=VN_TZ)
    settled = process_due_settlements(session, as_of=mon_dt)
    assert settled == 0
    assert available_quantity(session, portfolio.id, "HPG") == 0

    # Attempting to SELL before settlement MUST be rejected by engine sell-lock
    sell_order = engine.place_order(
        portfolio=portfolio,
        symbol="HPG",
        side=OrderSide.SELL,
        quantity=100,
        price=26000.0,
        order_type=OrderType.MARKET,
    )
    assert sell_order.status == OrderStatus.REJECTED
    assert "settled available" in str(sell_order.reject_reason)

    # 2. On Tuesday before 13:00 (12:59 VN), still 0 settled
    tue_before_dt = datetime(2026, 9, 22, 12, 59, tzinfo=VN_TZ)
    settled = process_due_settlements(session, as_of=tue_before_dt)
    assert settled == 0
    assert available_quantity(session, portfolio.id, "HPG") == 0

    # 3. On Tuesday at 13:01 VN, settlement unlocks!
    tue_after_dt = datetime(2026, 9, 22, 13, 1, tzinfo=VN_TZ)
    settled = process_due_settlements(session, as_of=tue_after_dt)
    assert settled == 1
    session.refresh(ledger_row)
    assert ledger_row.status == SETTLEMENT_AVAILABLE
    assert available_quantity(session, portfolio.id, "HPG") == 100

    # Now sell order succeeds without settlement lock rejection
    sell_order2 = engine.place_order(
        portfolio=portfolio,
        symbol="HPG",
        side=OrderSide.SELL,
        quantity=100,
        price=26000.0,
        order_type=OrderType.MARKET,
    )
    assert sell_order2.status == OrderStatus.FILLED


# ---------------------------------------------------------------------------
# 4. Multi-Horizon Equity Screener Tests
# ---------------------------------------------------------------------------


def test_alpha_screener_criteria(session: Session) -> None:  # noqa: F811
    """Test weekly, monthly, and quarterly alpha screening criteria."""
    # Seed active stock symbol AAA
    sym = StockSymbol(
        symbol="AAA",
        organ_name="An Phat Holdings",
        exchange=Exchange.HOSE,
        asset_type="stock",
        icb_code="5010",
        is_active=True,
    )
    session.add(sym)

    base_date = date(2026, 9, 30)

    # Seed 65 daily bars for AAA:
    # - Rising prices: 10,000 -> 16,400 (ROC ~64% > benchmark)
    # - Last volume surging: 2,000,000 (SMA20 ~ 800,000)
    # - High daily value: > 15 billion VND
    # - Tight range on last 5 bars: high-low / close ~ 3% < 8% (VCP)
    for i in range(65):
        d = base_date - timedelta(days=64 - i)
        close_p = 10000.0 + (i * 100.0)  # reaches 16,400.0
        high_p = close_p * 1.015
        low_p = close_p * 0.985
        vol = 2_000_000 if i == 64 else 800_000
        val = close_p * vol
        bar = StockOHLCVDaily(
            symbol="AAA",
            trading_date=d,
            open=close_p * 0.99,
            high=high_p,
            low=low_p,
            close=close_p,
            volume=vol,
            value=val,
            source="VCI",
        )
        session.add(bar)

    # Seed 65 flat bars for VNINDEX benchmark (1,200.0 pts flat)
    for i in range(65):
        d = base_date - timedelta(days=64 - i)
        session.add(
            StockOHLCVDaily(
                symbol="VNINDEX",
                trading_date=d,
                open=1200.0,
                high=1205.0,
                low=1195.0,
                close=1200.0,
                volume=500_000_000,
                value=15_000_000_000_000.0,
                source="VCI",
            )
        )

    # Seed InstitutionalFlow for AAA in top sector 5010 over last 10 dates
    for i in range(10):
        d = base_date - timedelta(days=9 - i)
        session.add(
            InstitutionalFlow(
                symbol="AAA",
                trading_date=d,
                foreign_net_value=10_000_000_000.0,
                prop_net_value=5_000_000_000.0,
                source="VCI",
            )
        )

    # Seed FinancialRatio for Quarterly horizon:
    # 5 quarters of PE history (pe=10.0 current, 4 prior quarters with pe=15.0)
    for q_idx in range(5):
        y = 2026 if q_idx == 4 else 2025
        q = (q_idx % 4) + 1
        is_current = q_idx == 4
        session.add(
            FinancialRatio(
                symbol="AAA",
                period="quarter",
                year=y,
                quarter=q,
                pe=10.0 if is_current else 15.0,
                roe=18.0 if is_current else 12.0,
                roa=8.0 if is_current else 6.0,
                debt_to_equity=0.8 if is_current else 1.2,
                current_ratio=2.0 if is_current else 1.5,
                gross_margin=25.0 if is_current else 20.0,
                asset_turnover=1.2 if is_current else 1.0,
                revenue_growth_yoy=25.0 if is_current else 10.0,
                net_profit_growth_yoy=30.0 if is_current else 10.0,
                source="VCI",
            )
        )

    # Seed FinancialReport for current year and prior year (Piotroski signals)
    session.add(
        FinancialReport(
            symbol="AAA",
            report_type="income_statement",
            period="quarter",
            year=2026,
            quarter=1,
            net_profit_parent=100_000_000_000.0,
            total_assets=1_000_000_000_000.0,
            long_term_debt=100_000_000_000.0,
            operating_cash_flow=150_000_000_000.0,
            source="VCI",
        )
    )
    session.add(
        FinancialReport(
            symbol="AAA",
            report_type="income_statement",
            period="quarter",
            year=2025,
            quarter=1,
            net_profit_parent=70_000_000_000.0,
            total_assets=900_000_000_000.0,
            long_term_debt=150_000_000_000.0,
            operating_cash_flow=100_000_000_000.0,
            source="VCI",
        )
    )

    session.commit()

    # Run multi-horizon screen
    baskets = screen(session, horizon="all", as_of=base_date)

    # 1. Weekly Basket
    weekly_symbols = [t.symbol for t in baskets["weekly"]]
    assert "AAA" in weekly_symbols
    aaa_weekly = next(t for t in baskets["weekly"] if t.symbol == "AAA")
    assert aaa_weekly.alpha_score >= 75.0

    # 2. Monthly Basket
    monthly_symbols = [t.symbol for t in baskets["monthly"]]
    assert "AAA" in monthly_symbols
    aaa_monthly = next(t for t in baskets["monthly"] if t.symbol == "AAA")
    rs_crit = next(c for c in aaa_monthly.criteria if c.key == "rs_rating")
    assert rs_crit.passed is True
    assert rs_crit.value is not None and rs_crit.value >= 80.0

    # 3. Quarterly Basket
    quarterly_symbols = [t.symbol for t in baskets["quarterly"]]
    assert "AAA" in quarterly_symbols
    aaa_quarterly = next(t for t in baskets["quarterly"] if t.symbol == "AAA")
    fscore_crit = next(c for c in aaa_quarterly.criteria if c.key == "piotroski_fscore")
    assert fscore_crit.value is not None and fscore_crit.value >= 7.0


# ---------------------------------------------------------------------------
# 5. Endpoint Smoke Tests
# ---------------------------------------------------------------------------


def test_phase4_api_endpoints(api_client) -> None:  # noqa: F811
    """Smoke test Phase 4 REST API endpoints."""
    # 1. Create portfolio
    create_resp = api_client.post(
        f"{settings.API_V1_STR}/simulation/portfolios",
        json={"name": "Endpoint Smoke Portfolio", "initial_balance": 100_000_000.0},
    )
    assert create_resp.status_code == 200
    portfolio_id = create_resp.json()["id"]

    # 2. GET margin-status
    margin_resp = api_client.get(
        f"{settings.API_V1_STR}/simulation/portfolios/{portfolio_id}/margin-status"
    )
    assert margin_resp.status_code == 200
    margin_data = margin_resp.json()
    assert margin_data["status"] == "SAFE"
    assert margin_data["margin_ratio"] is None
    assert margin_data["equity"] == 100_000_000.0

    # 3. POST /simulation/settlement/process
    settle_resp = api_client.post(
        f"{settings.API_V1_STR}/simulation/settlement/process"
    )
    assert settle_resp.status_code == 200
    assert "settled" in settle_resp.json()
    assert isinstance(settle_resp.json()["settled"], int)

    # 4. GET /simulation/alpha/baskets?horizon=weekly
    alpha_resp = api_client.get(
        f"{settings.API_V1_STR}/simulation/alpha/baskets?horizon=weekly"
    )
    assert alpha_resp.status_code == 200
    alpha_data = alpha_resp.json()
    assert alpha_data["horizon"] == "weekly"
    assert "weekly" in alpha_data["baskets"]

    # 5. GET /simulation/alpha/baskets with invalid horizon -> 422
    invalid_resp = api_client.get(
        f"{settings.API_V1_STR}/simulation/alpha/baskets?horizon=invalid_horizon"
    )
    assert invalid_resp.status_code == 422


# ---------------------------------------------------------------------------
# 6. Forecast Journal & Self-Learning Tests (AGENTS.md §9)
# ---------------------------------------------------------------------------


def test_screener_forecast_journal_integration(session: Session) -> None:  # noqa: F811
    """Test that Alpha Screener baskets are persisted into ForecastJournal (RULE 3 / AGENTS §9.1)."""
    # 1. Seed active StockSymbol
    sym = StockSymbol(
        symbol="VNM",
        organ_name="Vinamilk",
        exchange=Exchange.HOSE,
        asset_type="stock",
        icb_code="3530",
        is_active=True,
    )
    session.add(sym)

    # 2. Seed 60 daily bars for VNM with rising prices and volume
    base_date = date(2026, 9, 18)
    for i in range(60):
        d = base_date - timedelta(days=60 - i)
        bar = StockOHLCVDaily(
            symbol="VNM",
            trading_date=d,
            open=70000.0 + i * 200,
            high=71000.0 + i * 200,
            low=69500.0 + i * 200,
            close=70500.0 + i * 200,
            volume=5_000_000 if i == 59 else 1_000_000,
            value=20_000_000_000.0,
            source="VCI",
        )
        session.add(bar)

    session.commit()

    # 3. Run screener with record_journal=True
    baskets = screen(session, horizon="weekly", as_of=base_date, record_journal=True)
    assert "weekly" in baskets
    assert len(baskets["weekly"]) >= 1

    # 4. Verify ForecastJournal entries were created in pending state
    from sqlmodel import select

    journals = session.exec(
        select(ForecastJournal).where(
            ForecastJournal.symbol == "VNM",
            ForecastJournal.horizon == ForecastHorizon.WEEKLY,
        )
    ).all()
    assert len(journals) == 1
    j = journals[0]
    assert j.status == ForecastStatus.PENDING
    assert j.predicted_direction == ForecastDirection.BULLISH
    assert j.predicted_value == pytest.approx(70500.0 + 59 * 200)
    assert j.engine_weights["technical"] == 0.35
    assert j.parameter_snapshot["alpha_score"] >= 75


def test_forecast_journal_auto_resolve_and_score(session: Session) -> None:  # noqa: F811
    """Test auto-resolution and scoring of due forecasts against realized market prices."""
    # 1. Create a pending forecast for T+1
    pred_date = date(2026, 9, 18)
    pred_time = datetime.combine(pred_date, datetime.min.time()).replace(
        hour=15, minute=0, tzinfo=VN_TZ
    )
    svc = ForecastJournalService(session)
    forecast = svc.record(
        symbol="FPT",
        predicted_at=pred_time,
        model_version="ensemble_v1",
        horizon=ForecastHorizon.T_PLUS_1,
        predicted_value=1000.0,
        predicted_direction=ForecastDirection.BULLISH,
    )
    assert forecast.status == ForecastStatus.PENDING

    # 2. Before next day arrives, resolving with as_of = 2026-09-18 should skip
    res_early = svc.resolve_and_score_due_forecasts(as_of=pred_date)
    assert res_early["resolved"] == 0

    # 3. Add realized market bar for next day: 2026-09-19 close = 1015.0
    bar_next = StockOHLCVDaily(
        symbol="FPT",
        trading_date=date(2026, 9, 19),
        open=1002.0,
        high=1020.0,
        low=1000.0,
        close=1015.0,
        volume=2_000_000,
        source="VCI",
    )
    session.add(bar_next)
    session.commit()

    # 4. Resolve on 2026-09-19
    res_due = svc.resolve_and_score_due_forecasts(as_of=date(2026, 9, 19))
    assert res_due["resolved"] == 1

    # 5. Verify status is SCORED with accurate error & directional score
    session.refresh(forecast)
    assert forecast.status == ForecastStatus.SCORED
    assert forecast.actual_value == 1015.0
    assert forecast.actual_direction == ForecastDirection.BULLISH
    assert forecast.error == pytest.approx(15.0)  # |1000 - 1015|
    assert forecast.score == 1.0  # Predicted BULLISH, Actual BULLISH -> 1.0
