"""Tests for SettlementService (T+2 lifecycle, Vietnam holiday calendar) and TickStorageService (Safe Purge Gate)."""

from collections.abc import Generator
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import create_engine
from sqlmodel import Session, SQLModel, select

from app.domains.market_data.domain.models import (
    StockOHLCVIntraday,
    StockSymbol,
    StockTickIntraday,
)
from app.domains.market_data.infrastructure.tick_storage import TickStorageService
from app.domains.quant.domain.models import TickFlowAggregated
from app.domains.simulation.domain.settlement import (
    SettlementService,
    SettlementStatus,
)

VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Fixture cung cấp in-memory SQLite session."""
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_vietnam_holidays_calendar() -> None:
    """Kiểm tra nhận diện ngày lễ chính thức của Việt Nam."""
    # 30/4 và 1/5 không phải ngày giao dịch
    assert SettlementService.is_trading_day(date(2026, 4, 30)) is False
    assert SettlementService.is_trading_day(date(2026, 5, 1)) is False
    # 2/9 Quốc khánh không phải ngày giao dịch
    assert SettlementService.is_trading_day(date(2026, 9, 2)) is False

    # Thứ 4 bình thường là ngày giao dịch
    assert SettlementService.is_trading_day(date(2026, 9, 16)) is True
    # Thứ 7, Chủ Nhật không phải ngày giao dịch
    assert SettlementService.is_trading_day(date(2026, 9, 19)) is False
    assert SettlementService.is_trading_day(date(2026, 9, 20)) is False


def test_settlement_date_with_weekend_and_holiday() -> None:
    """Kiểm tra tính ngày thanh toán T+2 qua kỳ nghỉ lễ Quốc khánh 2/9."""
    # Thứ 3 ngày 01/09/2026:
    # T+1: Thứ 4 (02/09) là ngày lễ -> Bỏ qua. Thứ 5 (03/09) là ngày nghỉ lễ kèm -> Bỏ qua.
    # T+1 hợp lệ là Thứ 6 (04/09).
    # T+2: Thứ 7, CN bỏ qua -> Thứ 2 (07/09/2026).
    trade_date = date(2026, 9, 1)
    settled = SettlementService.calculate_settlement_date(trade_date, cycle_days=2)
    assert settled == date(2026, 9, 7)


def test_evaluate_settlement_status_derivatives_vs_equity() -> None:
    """Kiểm tra phái sinh thanh toán T+0 ngay trong phiên, trong khi cổ phiếu tuân thủ T+2 lúc 13:00."""
    trade_time = datetime(2026, 9, 18, 10, 0, tzinfo=VN_TZ)  # Thứ 6 10:00 sáng

    # Phái sinh VN30F1M: Thanh toán ngay tại thời điểm giao dịch (T+0)
    status_futures = SettlementService.evaluate_settlement_status(
        trade_time=trade_time,
        current_time=trade_time,
        asset_type="FUTURES",
    )
    assert status_futures == SettlementStatus.SETTLED

    # Cổ phiếu cơ sở: Sáng Thứ 3 (T+2) lúc 11:00 vẫn là PENDING
    status_equity_morning = SettlementService.evaluate_settlement_status(
        trade_time=trade_time,
        current_time=datetime(2026, 9, 22, 11, 0, tzinfo=VN_TZ),
        asset_type="EQUITY",
    )
    assert status_equity_morning == SettlementStatus.PENDING

    # Cổ phiếu cơ sở: Chiều Thứ 3 (T+2) lúc 13:00 trở đi là SETTLED (hàng về)
    status_equity_afternoon = SettlementService.evaluate_settlement_status(
        trade_time=trade_time,
        current_time=datetime(2026, 9, 22, 13, 0, tzinfo=VN_TZ),
        asset_type="EQUITY",
    )
    assert status_equity_afternoon == SettlementStatus.SETTLED


def test_purchasing_power_calculation() -> None:
    """Kiểm tra tính toán sức mua tài sản với tiền đã về và tiền bán đang chờ."""
    power = SettlementService.calculate_purchasing_power(
        settled_cash=100_000_000.0,
        pending_cash=50_000_000.0,
        margin_ratio=1.5,
        advance_fee_rate=0.001,
    )
    assert power["settled_cash"] == 100_000_000.0
    assert power["pending_cash"] == 50_000_000.0
    assert power["total_purchasing_power"] > 200_000_000.0


def test_safe_purge_gate_blocks_deletion_without_aggregation(
    db_session: Session,
) -> None:
    """Safe Purge Gate: Chặn việc xóa tick nếu chưa có nến 1m hoặc bản tổng hợp (Rule 3)."""
    sym = StockSymbol(symbol="SSI", organ_name="Chứng khoán SSI", exchange="HOSE")
    db_session.add(sym)
    db_session.commit()

    old_day = date(2026, 8, 1)
    tick = StockTickIntraday(
        symbol="SSI",
        timestamp=datetime.combine(old_day, time(9, 30), tzinfo=VN_TZ),
        price=32000.0,
        volume=5000,
        match_type="BU",
        source="VCI",
    )
    db_session.add(tick)
    db_session.commit()

    # Chưa có nến 1m hay aggregated flow -> Gate trả về False
    assert TickStorageService.verify_safe_purge_gate(db_session, old_day) is False

    # Purge an toàn: Không xóa bản ghi nào vì gate chặn
    purged_count = TickStorageService.purge_ticks_before_date(
        db_session,
        cutoff_date=date(2026, 8, 15),
        force=False,
    )
    assert purged_count == 0


def test_safe_purge_gate_allows_deletion_when_aggregated(db_session: Session) -> None:
    """Safe Purge Gate: Kiểm tra điều kiện nến 1m đạt MIN_BARS_PER_SESSION hoặc có TickFlowAggregated."""
    sym = StockSymbol(symbol="VND", organ_name="VNDIRECT", exchange="HOSE")
    db_session.add(sym)
    db_session.commit()

    old_day = date(2026, 8, 1)
    tick = StockTickIntraday(
        symbol="VND",
        timestamp=datetime.combine(old_day, time(9, 30), tzinfo=VN_TZ),
        price=18000.0,
        volume=10000,
        match_type="SD",
        source="VCI",
    )
    db_session.add(tick)

    # 1. Nếu chỉ có 1 nến 1m (< MIN_BARS_PER_SESSION = 180) -> Gate CHẶN
    candle = StockOHLCVIntraday(
        symbol="VND",
        timestamp=datetime.combine(old_day, time(9, 30), tzinfo=VN_TZ),
        interval="1m",
        open=18000.0,
        high=18050.0,
        low=17950.0,
        close=18000.0,
        volume=10000,
        source="VCI",
    )
    db_session.add(candle)
    db_session.commit()

    # Mặc định cần 180 nến -> 1 nến chưa đủ điều kiện
    assert TickStorageService.verify_safe_purge_gate(db_session, old_day) is False
    assert (
        TickStorageService.purge_ticks_before_date(
            db_session, cutoff_date=date(2026, 8, 15), force=False
        )
        == 0
    )

    # 2. Thêm bản ghi tổng hợp TickFlowAggregated -> Gate THÔNG QUA
    flow_agg = TickFlowAggregated(
        symbol="VND",
        interval_start=datetime.combine(old_day, time(9, 30), tzinfo=VN_TZ),
        open=18000.0,
        high=18050.0,
        low=17950.0,
        close=18000.0,
        volume=10000,
        aggressive_buy_volume=0,
        aggressive_sell_volume=10000,
        volume_delta=-10000,
        trade_count=1,
        source="VCI",
    )
    db_session.add(flow_agg)
    db_session.commit()

    # Giờ đã có TickFlowAggregated -> Gate mở
    assert TickStorageService.verify_safe_purge_gate(db_session, old_day) is True

    # Purge thành công tick cũ bằng bulk delete
    purged_count = TickStorageService.purge_ticks_before_date(
        db_session,
        cutoff_date=date(2026, 8, 15),
        force=False,
    )
    assert purged_count == 1


def test_extended_holidays_2025_to_2029() -> None:
    """Kiểm tra nhận diện ngày nghỉ lễ mở rộng giai đoạn 2025–2029."""
    # 2025: Tết Ất Tỵ (29/1/2025) và Giỗ Tổ Hùng Vương (7/4/2025)
    assert SettlementService.is_trading_day(date(2025, 1, 29)) is False
    assert SettlementService.is_trading_day(date(2025, 4, 7)) is False

    # 2027: Tết Đinh Mùi (5/2/2027 - 11/2/2027)
    # Giao dịch ngày Thứ 4 03/02/2027:
    # T+1 là Thứ 5 04/02/2027
    # T+2 rơi vào Thứ 6 12/02/2027 (bỏ qua toàn bộ kỳ nghỉ Tết 5/2-11/2)
    settled_2027 = SettlementService.calculate_settlement_date(
        date(2027, 2, 3), cycle_days=2
    )
    assert settled_2027 == date(2027, 2, 12)

    # 2028: Tết Mậu Thân (27/1/2028)
    assert SettlementService.is_trading_day(date(2028, 1, 27)) is False

    # 2029: Tết Kỷ Dậu (14/2/2029) và Giỗ Tổ (24/4/2029)
    assert SettlementService.is_trading_day(date(2029, 2, 14)) is False
    assert SettlementService.is_trading_day(date(2029, 4, 24)) is False


def test_settlement_hook_credits_cash_and_creates_trade(db_session: Session) -> None:
    """Kiểm tra hook thanh toán bù trừ T+2 cộng tiền mặt, giải phóng margin và ghi Trade log."""
    import uuid
    from contextlib import contextmanager

    from app.core.enums import PositionSide, PositionStatus
    from app.domains.quant.application.daemon.scheduled_hooks import (
        run_settlement_hook,
    )
    from app.domains.simulation.domain.models import Portfolio, Position, Trade

    # 1. Tạo Portfolio mô phỏng
    portfolio = Portfolio(
        user_id=uuid.uuid4(),
        name="Settlement Test Portfolio",
        initial_balance=10_000_000.0,
        cash_balance=10_000_000.0,
        margin_used=500_000.0,
        equity=10_000_000.0,
    )
    db_session.add(portfolio)
    db_session.commit()
    db_session.refresh(portfolio)

    # 2. Tạo Position OPEN có settlement_date đã đến hạn (T+2)
    today = date(2026, 10, 1)
    pos = Position(
        portfolio_id=portfolio.id,
        symbol="HPG",
        side=PositionSide.LONG,
        quantity=100,
        entry_price=28000.0,
        current_price=30000.0,
        margin_required=500_000.0,
        settlement_date=today,
        status=PositionStatus.OPEN,
    )
    db_session.add(pos)
    db_session.commit()
    db_session.refresh(pos)

    # 3. Tạo session_factory trả về db_session
    @contextmanager
    def mock_session_factory():
        yield db_session

    result = run_settlement_hook(
        session_factory=mock_session_factory,
        today=today,
    )

    assert result["settled"] == 1
    assert len(result["errors"]) == 0

    # 4. Kiểm tra Position chuyển sang CLOSED
    db_session.refresh(pos)
    assert pos.status == PositionStatus.CLOSED

    # 5. Kiểm tra Portfolio được cộng tiền và giải phóng margin
    db_session.refresh(portfolio)
    expected_proceeds = 100 * 30000.0  # 3,000,000
    assert portfolio.cash_balance == 10_000_000.0 + expected_proceeds
    assert portfolio.margin_used == 0.0

    # 6. Kiểm tra Trade record được tạo
    trades = db_session.exec(
        select(Trade).where(Trade.portfolio_id == portfolio.id)
    ).all()
    assert len(trades) == 1
    assert trades[0].symbol == "HPG"
    assert trades[0].quantity == 100
    assert trades[0].price == 30000.0
