"""Tests for Distributed Rate Limiter & Circuit Breaker (RateLimiter).

Kiểm tra:
1. Độ trễ tối thiểu (Throttling wait) với mock clock và sleep.
2. Chuyển đổi trạng thái Circuit Breaker:
   - CLOSED -> liên tiếp 5 failures -> OPEN.
   - Khi OPEN: is_available = False, wait() ném CircuitBreakerOpenError.
   - Sau thời gian cooldown: chuyển sang HALF_OPEN.
   - Thăm dò thành công: chuyển về CLOSED, reset bộ đếm lỗi.
3. Điều phối qua Database (Session): cập nhật trạng thái trong provider_rate_limit_state.
"""

from collections.abc import Generator
from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlmodel import Session, SQLModel

from app.models import VN_TZ
from app.models.entities.rate_limit import ProviderRateLimitState
from app.services.rate_limit import CircuitBreakerOpenError, CircuitState, RateLimiter


@pytest.fixture
def rate_limit_db_session() -> Generator[Session, None, None]:
    """Fixture tạo SQLite session chứa bảng provider_rate_limit_state."""
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_rate_limiter_monotonic_throttle() -> None:
    """Kiểm tra điều phối khoảng cách tối thiểu giữa 2 request (anti-ban)."""
    current_time = 100.0
    slept_seconds: list[float] = []

    def mock_clock() -> float:
        nonlocal current_time
        return current_time

    def mock_sleep(seconds: float) -> None:
        nonlocal current_time
        slept_seconds.append(seconds)
        current_time += seconds

    limiter = RateLimiter(
        min_delay=0.3,
        clock=mock_clock,
        sleep=mock_sleep,
    )

    # Lần gọi 1: không cần ngủ
    s1 = limiter.wait(provider="VCI")
    assert s1 == 0.0
    assert len(slept_seconds) == 0

    # Lần gọi 2 ngay lập tức (cùng thời điểm current_time=100.0) -> phải ngủ 0.3s
    s2 = limiter.wait(provider="VCI")
    assert pytest.approx(s2, 0.001) == 0.3
    assert len(slept_seconds) == 1
    assert pytest.approx(slept_seconds[0], 0.001) == 0.3
    assert pytest.approx(current_time, 0.001) == 100.3

    # Lần gọi 3 sau 0.5s (current_time=100.8) -> không cần ngủ
    current_time = 100.8
    s3 = limiter.wait(provider="VCI")
    assert s3 == 0.0


def test_circuit_breaker_trip_and_recovery() -> None:
    """Kiểm tra ngắt mạch khi gặp 5 lỗi liên tiếp và hồi phục sau cooldown."""
    current_time = 1000.0

    def mock_clock() -> float:
        return current_time

    limiter = RateLimiter(
        min_delay=0.1,
        max_failures=5,
        base_cooldown=60.0,
        clock=mock_clock,
        sleep=lambda _: None,
    )

    provider = "KBS"

    # Ban đầu: khả dụng
    assert limiter.is_available(provider) is True

    # 4 lỗi liên tiếp -> mạch vẫn CLOSED
    for _ in range(4):
        limiter.record_failure(provider)
        assert limiter.is_available(provider) is True

    # Lỗi thứ 5 -> ngắt mạch (OPEN)
    limiter.record_failure(provider)
    assert limiter.is_available(provider) is False

    # Thử wait() khi đang OPEN -> ném CircuitBreakerOpenError
    with pytest.raises(CircuitBreakerOpenError):
        limiter.wait(provider)

    # Thời gian trôi qua 30s (chưa đủ cooldown 60s) -> vẫn OPEN
    current_time += 30.0
    assert limiter.is_available(provider) is False

    # Thời gian trôi qua 70s (> 60s cooldown) -> chuyển sang HALF_OPEN
    current_time += 40.0
    assert limiter.is_available(provider) is True

    # Thăm dò thành công -> đóng mạch (CLOSED)
    limiter.record_success(provider)
    assert limiter.is_available(provider) is True
    assert limiter._failures.get(provider) == 0
    assert limiter._circuit_states.get(provider) == CircuitState.CLOSED


def test_rate_limiter_with_db_session(rate_limit_db_session: Session) -> None:
    """Kiểm tra trạng thái được đồng bộ vào bảng provider_rate_limit_state."""
    now = datetime.now(VN_TZ)
    # Khởi tạo bản ghi ban đầu
    state = ProviderRateLimitState(
        provider="MSN",
        last_request_at=now,
        consecutive_failures=0,
        circuit_state="closed",
    )
    rate_limit_db_session.add(state)
    rate_limit_db_session.commit()

    limiter = RateLimiter(min_delay=0.2, max_failures=3, base_cooldown=30.0)

    # Ghi nhận 3 lỗi
    for _ in range(3):
        limiter.record_failure("MSN", session=rate_limit_db_session)

    # Kiểm tra DB đã chuyển sang OPEN
    updated_state = rate_limit_db_session.get(ProviderRateLimitState, "MSN")
    assert updated_state is not None
    assert updated_state.consecutive_failures == 3
    assert updated_state.circuit_state == "open"
    assert updated_state.circuit_open_until is not None

    # Ghi nhận thành công -> reset về closed
    limiter.record_success("MSN", session=rate_limit_db_session)
    reclosed_state = rate_limit_db_session.get(ProviderRateLimitState, "MSN")
    assert reclosed_state is not None
    assert reclosed_state.consecutive_failures == 0
    assert reclosed_state.circuit_state == "closed"
    assert reclosed_state.circuit_open_until is None
