"""Unit tests for app.models package.

Tests timezone-awareness validation, model instantiation, enum values,
and pure PnL / financial calculation utilities without needing an active PostgreSQL DB.
"""

import uuid
from datetime import UTC, date, datetime

import pytest

from app.models.entities.simulation import (
    Order,
    Portfolio,
    Position,
    Trade,
    derivative_pnl,
    round_money,
)
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
    portfolio = Portfolio(
        user_id=user_id,
        name="Test Portfolio",
    )
    assert portfolio.initial_balance == DEFAULT_INITIAL_BALANCE
    assert portfolio.cash_balance == DEFAULT_INITIAL_BALANCE
    assert portfolio.equity == DEFAULT_INITIAL_BALANCE
    assert portfolio.margin_used == 0.0

    order = Order(
        portfolio_id=portfolio.id,
        symbol="VN30F1M",
        side=OrderSide.LONG,
        order_type=OrderType.MARKET,
        price=1320.0,
        quantity=5,
    )
    assert order.status == OrderStatus.PENDING
    assert order.filled_quantity == 0

    position = Position(
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

    trade = Trade(
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


def test_dto_models_instantiation() -> None:
    """Kiểm tra tính hợp lệ và khả năng khởi tạo của các DTOs (Data Transfer Objects)."""
    from app.models.dto import (
        CompanyOverviewPublic,
        EnsembleSignalRequest,
        EnsembleSignalResponse,
        EnsembleWeightsResponse,
        EnsembleWeightsUpdate,
        FinancialReportPublic,
        FinancialReportsResponse,
        FlowLiquidityEngineResponse,
        ForecastAggregateResponse,
        ForecastCreate,
        ForecastJournalPublic,
        ForecastResolve,
        ForecastScoredPublic,
        InstitutionalFlowPublic,
        ItemCreate,
        ItemPublic,
        ItemsPublic,
        ItemUpdate,
        MacroIndicatorPublic,
        MacroLatestResponse,
        MarkToMarketRequest,
        Message,
        NewPassword,
        OHLCVRecord,
        OrderCreateRequest,
        OrderResponse,
        PortfolioCreateRequest,
        PortfolioResponse,
        PortfoliosResponse,
        PositionCloseRequest,
        PositionResponse,
        PriceHistoryResponse,
        QuantMLEngineResponse,
        StockSymbolPublic,
        StockSymbolsPublic,
        SyncStatusPublic,
        TechnicalEngineResponse,
        Token,
        TokenPayload,
        TradeResponse,
        UpdatePassword,
        UserCreate,
        UserPublic,
        UserRegister,
        UsersPublic,
        UserUpdate,
        UserUpdateMe,
        VnstockSymbolResponse,
    )

    # Khởi tạo thử nghiệm Request DTO
    order_req = OrderCreateRequest(
        symbol="VN30F1M",
        side="BUY",
        quantity=2,
        price=1320.0,
    )
    assert order_req.quantity == 2

    # Khởi tạo thử nghiệm Response DTO
    msg_resp = Message(message="Success")
    assert msg_resp.message == "Success"

    # Kiểm tra tồn tại và hợp lệ của các class DTO chính
    assert ForecastCreate is not None
    assert ForecastResolve is not None
    assert ForecastJournalPublic is not None
    assert ForecastScoredPublic is not None
    assert ForecastAggregateResponse is not None
    assert MacroIndicatorPublic is not None
    assert MacroLatestResponse is not None
    assert InstitutionalFlowPublic is not None
    assert TechnicalEngineResponse is not None
    assert FlowLiquidityEngineResponse is not None
    assert QuantMLEngineResponse is not None
    assert EnsembleSignalRequest is not None
    assert EnsembleSignalResponse is not None
    assert EnsembleWeightsUpdate is not None
    assert EnsembleWeightsResponse is not None

    assert PortfolioCreateRequest is not None
    assert PortfolioResponse is not None
    assert PortfoliosResponse is not None
    assert PositionCloseRequest is not None
    assert PositionResponse is not None
    assert TradeResponse is not None
    assert MarkToMarketRequest is not None
    assert OrderCreateRequest is not None
    assert OrderResponse is not None

    assert StockSymbolPublic is not None
    assert StockSymbolsPublic is not None
    assert OHLCVRecord is not None
    assert PriceHistoryResponse is not None
    assert CompanyOverviewPublic is not None
    assert FinancialReportPublic is not None
    assert FinancialReportsResponse is not None
    assert SyncStatusPublic is not None

    assert UserCreate is not None
    assert UserPublic is not None
    assert UsersPublic is not None
    assert UserRegister is not None
    assert UserUpdate is not None
    assert UserUpdateMe is not None
    assert ItemCreate is not None
    assert ItemUpdate is not None
    assert ItemPublic is not None
    assert ItemsPublic is not None
    assert UpdatePassword is not None
    assert NewPassword is not None
    assert Token is not None
    assert TokenPayload is not None
    assert VnstockSymbolResponse is not None


def test_stock_entities_instantiation() -> None:
    """Kiểm tra tính toàn vẹn và khởi tạo của 12 bảng thực thể chứng khoán vnstock."""
    from app.models.entities import (
        CompanyOfficer,
        CompanyProfile,
        CompanyShareholder,
        CorporateEvent,
        DataSyncLog,
        FinancialRatio,
        FinancialReport,
        IndexConstituent,
        StockOHLCVDaily,
        StockOHLCVIntraday,
        StockSymbol,
        StockTickIntraday,
    )

    now = get_datetime_utc()
    today = date(2026, 9, 20)

    # 1. StockSymbol
    sym = StockSymbol(
        symbol="FPT",
        organ_name="Công ty Cổ phần FPT",
        exchange="HOSE",
        industry="Công nghệ",
        icb_code="9530",
        icb_name="Phần mềm & Dịch vụ Máy tính",
        index_group="VN30",
        asset_type="stock",
        lot_size=100,
    )
    assert sym.symbol == "FPT"
    assert sym.index_group == "VN30"

    # 2. StockOHLCVDaily
    ohlcv_d = StockOHLCVDaily(
        symbol="FPT",
        trading_date=today,
        open=130000.0,
        high=135000.0,
        low=129500.0,
        close=134000.0,
        volume=5_000_000,
        value=670_000_000_000.0,
        change=4000.0,
        change_pct=3.08,
        buy_volume=3_200_000,
        sell_volume=1_800_000,
        foreign_buy_volume=1_000_000,
        foreign_sell_volume=400_000,
        foreign_net_volume=600_000,
        source="VCI",
    )
    assert ohlcv_d.close == 134000.0
    assert ohlcv_d.foreign_net_volume == 600_000

    # 3. StockOHLCVIntraday
    ohlcv_i = StockOHLCVIntraday(
        symbol="VN30F1M",
        timestamp=now,
        interval="1m",
        open=1320.0,
        high=1322.5,
        low=1319.5,
        close=1322.0,
        volume=1200,
        value=158_640_000_000.0,
        buy_volume=800,
        sell_volume=400,
        volume_delta=400,
        vwap=1321.2,
        source="VCI",
    )
    assert ohlcv_i.volume_delta == 400

    # 4. StockTickIntraday
    tick = StockTickIntraday(
        symbol="VN30F1M",
        timestamp=now,
        price=1322.0,
        volume=50,
        match_type="BU",
        accumulated_volume=12000,
        sequence_number=1,
        source="VCI",
    )
    assert tick.match_type == "BU"

    # 5. CompanyProfile
    profile = CompanyProfile(
        symbol="FPT",
        company_name="Công ty Cổ phần FPT",
        short_name="FPT",
        industry_name="Công nghệ thông tin",
        charter_capital=14_600_000_000_000.0,
        outstanding_shares=1_460_000_000.0,
        market_cap=195_640_000_000_000.0,
        free_float_pct=85.0,
        foreign_ownership_pct=49.0,
        max_foreign_ownership_pct=49.0,
    )
    assert profile.free_float_pct == 85.0

    # 6. FinancialReport
    report = FinancialReport(
        symbol="FPT",
        report_type="income_statement",
        period="quarter",
        year=2026,
        quarter=2,
        data={"revenue": 15000000000000, "net_profit": 2500000000000},
        source="VCI",
    )
    assert report.quarter == 2

    # 6b. FinancialReportItem (Relational Normalization)
    from app.models.entities import FinancialReportItem

    report_item = FinancialReportItem(
        report_id=report.id,
        item_code="REVENUE",
        item_name="Doanh thu bán hàng và cung cấp dịch vụ",
        value=15_000_000_000_000.0,
        order_index=1,
    )
    assert report_item.item_code == "REVENUE"
    assert report_item.value == 15_000_000_000_000.0

    # 7. FinancialRatio
    ratio = FinancialRatio(
        symbol="FPT",
        period="quarter",
        year=2026,
        quarter=2,
        pe=19.5,
        pb=4.2,
        roe=28.5,
        roa=12.8,
        roic=22.0,
        eps=6500.0,
        source="VCI",
    )
    assert ratio.roe == 28.5

    # 8. CorporateEvent
    event = CorporateEvent(
        symbol="FPT",
        event_type="cash_dividend",
        event_title="Trả cổ tức đợt 1 năm 2026 bằng tiền mặt",
        ex_date=today,
        cash_rate=1500.0,
        ratio_string="10:1.5",
        notes="Chi trả từ nguồn lợi nhuận giữ lại",
        source="VCI",
    )
    assert event.cash_rate == 1500.0
    assert event.ratio_string == "10:1.5"

    # 9. CompanyShareholder
    holder = CompanyShareholder(
        symbol="FPT",
        shareholder_name="Tổng công ty Đầu tư và Kinh doanh vốn Nhà nước (SCIC)",
        share_count=75_000_000.0,
        ownership_pct=5.14,
        is_state=True,
    )
    assert holder.is_state is True

    # 10. CompanyOfficer
    officer = CompanyOfficer(
        symbol="FPT",
        officer_name="Trương Gia Bình",
        position="Chủ tịch Hội đồng Quản trị",
        ownership_pct=6.5,
    )
    assert officer.officer_name == "Trương Gia Bình"

    # 11. IndexConstituent
    constituent = IndexConstituent(
        index_code="VN30",
        symbol="FPT",
        weight=8.45,
        effective_date=today,
    )
    assert constituent.weight == 8.45

    # 12. DataSyncLog
    sync_log = DataSyncLog(
        sync_type="daily_ohlcv",
        symbol="FPT",
        source="VCI",
        status="success",
        rows_synced=1,
    )
    assert sync_log.status == "success"

    # 13. DerivativeContract
    from app.models.entities import DerivativeContract

    contract = DerivativeContract(
        symbol="VN30F1M",
        underlying_symbol="VN30",
        multiplier=100_000.0,
        expiration_date=date(2026, 9, 17),
        settlement_price=1325.5,
    )
    assert contract.multiplier == 100_000.0
    assert contract.underlying_symbol == "VN30"


def test_signal_log_instantiation() -> None:
    """Kiểm tra tính hợp lệ và khả năng khởi tạo của bảng SignalLog."""
    from app.models.entities import SignalLog

    now = get_datetime_utc()
    signal = SignalLog(
        strategy_name="basis_arbitrage",
        symbol="VN30F1M",
        signal_type="BUY",
        action_price=1320.0,
        stop_loss=1314.0,
        take_profit=1332.0,
        timeframe="1m",
        strength=0.85,
        metadata_info={"basis": -3.5, "rsi_14": 32.4},
        created_at=now,
    )
    assert signal.strategy_name == "basis_arbitrage"
    assert signal.signal_type == "BUY"
    assert signal.strength == 0.85


def test_entities_import_completeness() -> None:
    """Kiểm tra việc import đầy đủ 26 bảng cơ sở dữ liệu từ app.models.entities."""
    import app.models.entities as entities

    expected_tables = [
        "User",
        "Item",
        # 14 Bảng Thực Thể Chứng Khoán & Phái Sinh Vnstock
        "StockSymbol",
        "StockOHLCVDaily",
        "StockOHLCVIntraday",
        "StockTickIntraday",
        "CompanyProfile",
        "FinancialReport",
        "FinancialReportItem",
        "FinancialRatio",
        "CorporateEvent",
        "CompanyShareholder",
        "CompanyOfficer",
        "IndexConstituent",
        "DataSyncLog",
        "DerivativeContract",
        # 6 Bảng Định lượng, Tín hiệu & Nghiên cứu Quant
        "ForecastJournal",
        "SignalLog",
        "MacroIndicator",
        "TickFlowAggregated",
        "InstitutionalFlow",
        "MarketBreadth",
        # 4 Bảng Giao Dịch Mô Phỏng Simulation
        "Portfolio",
        "Order",
        "Position",
        "Trade",
    ]
    for table_name in expected_tables:
        assert hasattr(entities, table_name), f"Thiếu entity bảng: {table_name}"
        model_cls = getattr(entities, table_name)
        assert hasattr(model_cls, "__tablename__"), (
            f"{table_name} không phải là bảng ORM"
        )


if __name__ == "__main__":
    test_aware_sqlmodel_rejects_naive_datetime()
    test_aware_sqlmodel_accepts_utc_datetime()
    test_forecast_journal_instantiation()
    test_simulation_models_instantiation()
    test_derivative_pnl_calculation()
    test_round_money()
    test_macro_and_market_breadth_models()
    test_stock_entities_instantiation()
    test_signal_log_instantiation()
    test_dto_models_instantiation()
    test_entities_import_completeness()
