"""Tests for Standalone Market Worker & 9-Session Lifecycle Engine (MarketWorker).

Kiểm tra:
1. Độ chính xác của Finite State Machine 9 trạng thái phiên:
   - 08:35: PRE_ATO_SETUP
   - 08:47: ATO_AUCTION (phái sinh mở trước 15p)
   - 09:15: MORNING_CONTINUOUS (cơ sở mở)
   - 11:45: MIDDAY_INTERMISSION
   - 13:05: AFTERNOON_CONTINUOUS (hàng T+2 về)
   - 14:22: PRE_ATC_SETUP
   - 14:35: ATC_AUCTION
   - 14:50: POST_MARKET_EVAL
   - 22:00 / Cuối tuần / Ngày nghỉ lễ: OVERNIGHT_SIMULATION
2. Cơ chế Advisory Lock và chu kỳ chạy độc lập.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import create_engine
from sqlmodel import SQLModel

from app.worker import (
    MarketSessionState,
    MarketWorkerDaemon,
    get_current_session_state,
    release_worker_advisory_lock,
    try_acquire_worker_advisory_lock,
)

VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")


def test_session_state_schedule_transitions() -> None:
    """Kiểm tra độ chính xác của 9 trạng thái phiên theo thời gian thực."""
    # Thứ Hai ngày thường: 2026-09-21
    cases = [
        (datetime(2026, 9, 21, 8, 35, tzinfo=VN_TZ), MarketSessionState.PRE_ATO_SETUP),
        (datetime(2026, 9, 21, 8, 47, tzinfo=VN_TZ), MarketSessionState.ATO_AUCTION),
        (
            datetime(2026, 9, 21, 9, 15, tzinfo=VN_TZ),
            MarketSessionState.MORNING_CONTINUOUS,
        ),
        (
            datetime(2026, 9, 21, 11, 45, tzinfo=VN_TZ),
            MarketSessionState.MIDDAY_INTERMISSION,
        ),
        (
            datetime(2026, 9, 21, 13, 5, tzinfo=VN_TZ),
            MarketSessionState.AFTERNOON_CONTINUOUS,
        ),
        (datetime(2026, 9, 21, 14, 22, tzinfo=VN_TZ), MarketSessionState.PRE_ATC_SETUP),
        (datetime(2026, 9, 21, 14, 35, tzinfo=VN_TZ), MarketSessionState.ATC_AUCTION),
        (
            datetime(2026, 9, 21, 14, 50, tzinfo=VN_TZ),
            MarketSessionState.POST_MARKET_EVAL,
        ),
        (
            datetime(2026, 9, 21, 22, 0, tzinfo=VN_TZ),
            MarketSessionState.OVERNIGHT_SIMULATION,
        ),
    ]

    for dt, expected_state in cases:
        actual = get_current_session_state(dt)
        assert actual == expected_state, (
            f"Sai lệch tại {dt}: mong đợi {expected_state}, thực tế {actual}"
        )


def test_session_state_weekend_and_holidays() -> None:
    """Kiểm tra ngày nghỉ lễ và cuối tuần luôn đưa về OVERNIGHT_SIMULATION."""
    # Thứ Bảy: 2026-09-26 10:00 sáng
    saturday_dt = datetime(2026, 9, 26, 10, 0, tzinfo=VN_TZ)
    assert (
        get_current_session_state(saturday_dt)
        == MarketSessionState.OVERNIGHT_SIMULATION
    )

    # Chủ Nhật: 2026-09-27 14:00 chiều
    sunday_dt = datetime(2026, 9, 27, 14, 0, tzinfo=VN_TZ)
    assert (
        get_current_session_state(sunday_dt) == MarketSessionState.OVERNIGHT_SIMULATION
    )

    # Ngày lễ Quốc khánh 2/9 (rơi vào Thứ Tư ngày thường): 2026-09-02 09:30 sáng
    holiday_dt = datetime(2026, 9, 2, 9, 30, tzinfo=VN_TZ)
    assert (
        get_current_session_state(holiday_dt) == MarketSessionState.OVERNIGHT_SIMULATION
    )


def test_worker_daemon_single_cycle() -> None:
    """Kiểm tra daemon chạy hoàn tất 1 chu kỳ kiểm tra mà không gặp lỗi."""
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    daemon = MarketWorkerDaemon(db_engine=engine)
    daemon.run(single_cycle=True)

    assert daemon.total_cycles == 1
    assert daemon._running is False


def test_worker_advisory_lock_sqlite_fallback() -> None:
    """Kiểm tra hàm try_acquire_worker_advisory_lock tương thích với SQLite."""
    engine = create_engine("sqlite:///:memory:")
    assert try_acquire_worker_advisory_lock(engine) is True
    release_worker_advisory_lock(engine)  # Không được ném lỗi
