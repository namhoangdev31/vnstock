"""Distributed Rate Limiter & Circuit Breaker for outbound Vnstock requests.

Tuân thủ nghiêm ngặt AGENTS.md §7.2:
- Điều phối khoảng cách tối thiểu 0.2s - 0.5s giữa các lần gọi ra nhà cung cấp dữ liệu bên ngoài (anti-ban).
- Hỗ trợ cả chế độ in-memory cục bộ (multithread-safe) và điều phối phân tán đa tiến trình qua PostgreSQL table `provider_rate_limit_state` (với SELECT ... FOR UPDATE).
- Tích hợp mô hình Circuit Breaker với 3 trạng thái: CLOSED, OPEN, HALF_OPEN kèm Exponential Backoff with Jitter khi xảy ra lỗi liên tiếp.
- Injectable ``clock`` và ``sleep`` phục vụ deterministic unit tests không cần delay thực tế.
"""

import random
import threading
import time
from collections.abc import Callable
from datetime import datetime, timedelta
from enum import StrEnum

from sqlalchemy import text
from sqlmodel import Session

from app.models import VN_TZ


class CircuitState(StrEnum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerOpenError(Exception):
    """Ngoại lệ ném ra khi provider đang ở trạng thái ngắt mạch (Circuit OPEN)."""

    def __init__(
        self, provider: str, open_until: datetime | float | None = None
    ) -> None:
        self.provider = provider
        self.open_until = open_until
        super().__init__(
            f"Circuit Breaker for provider '{provider}' is OPEN until {open_until}. Requests are rejected to prevent cascading failures."
        )


class RateLimiter:
    """Bộ điều phối tốc độ gọi và ngắt mạch tự động (Rate Limiter & Circuit Breaker)."""

    def __init__(
        self,
        min_delay: float = 0.3,
        max_failures: int = 5,
        base_cooldown: float = 60.0,
        max_cooldown: float = 600.0,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.min_delay = min_delay
        self.max_failures = max_failures
        self.base_cooldown = base_cooldown
        self.max_cooldown = max_cooldown
        self._clock = clock
        self._sleep = sleep

        self._lock = threading.Lock()
        # Bộ đệm trạng thái in-memory
        self._last_calls: dict[str, float] = {}
        self._failures: dict[str, int] = {}
        self._circuit_states: dict[str, CircuitState] = {}
        self._circuit_open_until: dict[str, float] = {}

    def is_available(self, provider: str, session: Session | None = None) -> bool:
        """Kiểm tra provider có khả dụng để tiếp nhận request hay không."""
        provider_key = provider.upper()

        if session is not None:
            try:
                row = session.exec(
                    text(
                        "SELECT circuit_state, circuit_open_until FROM provider_rate_limit_state WHERE provider = :p"
                    ),
                    params={"p": provider_key},
                ).first()  # type: ignore
                if row:
                    state_str, open_until = row[0], row[1]
                    if state_str == CircuitState.OPEN.value:
                        now_utc = datetime.now(VN_TZ)
                        if open_until is not None and now_utc >= open_until:
                            # Đã hết thời gian chờ -> Chuyển sang HALF_OPEN để thăm dò
                            session.exec(
                                text(
                                    "UPDATE provider_rate_limit_state SET circuit_state = :s, updated_at = :u WHERE provider = :p"
                                ),
                                params={
                                    "s": CircuitState.HALF_OPEN.value,
                                    "u": now_utc,
                                    "p": provider_key,
                                },
                            )  # type: ignore
                            session.commit()
                            return True
                        return False
                    return True
            except Exception:
                # Nếu truy vấn DB lỗi, fallback sang bộ nhớ cục bộ
                pass

        with self._lock:
            state = self._circuit_states.get(provider_key, CircuitState.CLOSED)
            if state == CircuitState.OPEN:
                now = self._clock()
                until = self._circuit_open_until.get(provider_key, 0.0)
                if now >= until:
                    self._circuit_states[provider_key] = CircuitState.HALF_OPEN
                    return True
                return False
            return True

    def wait(self, provider: str = "DEFAULT", session: Session | None = None) -> float:
        """Thực hiện chờ nếu chưa đủ khoảng cách min_delay kể từ lần gọi trước.

        Ném CircuitBreakerOpenError nếu provider đang OPEN.
        Trả về: số giây đã chờ thực tế (0.0 nếu không cần chờ).
        """
        provider_key = provider.upper()

        # Kiểm tra Circuit Breaker trước khi chờ
        if not self.is_available(provider_key, session=session):
            with self._lock:
                until = self._circuit_open_until.get(provider_key)
            raise CircuitBreakerOpenError(provider_key, until)

        if session is not None:
            try:
                # Distributed atomic check via PostgreSQL SELECT ... FOR UPDATE
                row = session.exec(
                    text(
                        "SELECT last_request_at FROM provider_rate_limit_state WHERE provider = :p FOR UPDATE"
                    ),
                    params={"p": provider_key},
                ).first()  # type: ignore
                now_utc = datetime.now(VN_TZ)
                slept = 0.0
                if row and row[0]:
                    last_req: datetime = row[0]
                    # Chuyển đổi timestamp nếu cần
                    if last_req.tzinfo is None:
                        last_req = last_req.replace(tzinfo=VN_TZ)
                    elapsed = (now_utc - last_req).total_seconds()
                    remaining = self.min_delay - elapsed
                    if remaining > 0:
                        self._sleep(remaining)
                        slept = remaining

                # Cập nhật last_request_at
                now_after = datetime.now(VN_TZ)
                session.exec(
                    text(
                        """
                        INSERT INTO provider_rate_limit_state (provider, last_request_at, consecutive_failures, circuit_state, updated_at)
                        VALUES (:p, :now, 0, 'closed', :now)
                        ON CONFLICT (provider) DO UPDATE
                        SET last_request_at = :now, updated_at = :now;
                        """
                    ),
                    params={"p": provider_key, "now": now_after},
                )  # type: ignore
                session.commit()
                return slept
            except Exception:
                # Nếu DB lỗi hoặc lock thất bại, fallback sang in-memory throttle
                pass

        # In-memory throttle
        with self._lock:
            now = self._clock()
            last_call = self._last_calls.get(provider_key)
            if last_call is None:
                self._last_calls[provider_key] = now
                return 0.0

            elapsed = now - last_call
            remaining = self.min_delay - elapsed
            if remaining > 0:
                self._sleep(remaining)
                slept = remaining
            else:
                slept = 0.0

            self._last_calls[provider_key] = self._clock()
            return slept

    def record_success(self, provider: str, session: Session | None = None) -> None:
        """Ghi nhận yêu cầu thành công, reset bộ đếm lỗi và đóng mạch nếu đang HALF_OPEN."""
        provider_key = provider.upper()

        if session is not None:
            try:
                now_utc = datetime.now(VN_TZ)
                session.exec(
                    text(
                        """
                        UPDATE provider_rate_limit_state
                        SET consecutive_failures = 0,
                            circuit_state = 'closed',
                            circuit_open_until = NULL,
                            updated_at = :now
                        WHERE provider = :p
                        """
                    ),
                    params={"now": now_utc, "p": provider_key},
                )  # type: ignore
                session.commit()
            except Exception:
                pass

        with self._lock:
            self._failures[provider_key] = 0
            self._circuit_states[provider_key] = CircuitState.CLOSED
            self._circuit_open_until.pop(provider_key, None)

    def record_failure(self, provider: str, session: Session | None = None) -> None:
        """Ghi nhận yêu cầu thất bại, tăng bộ đếm lỗi nguyên tử và kích hoạt ngắt mạch nếu vượt ngưỡng."""
        provider_key = provider.upper()

        if session is not None:
            try:
                now_utc = datetime.now(VN_TZ)
                # Đảm bảo row tồn tại trước khi lock/update
                session.exec(
                    text(
                        """
                        INSERT INTO provider_rate_limit_state (provider, last_request_at, consecutive_failures, circuit_state, updated_at)
                        VALUES (:p, :now, 0, 'closed', :now)
                        ON CONFLICT (provider) DO NOTHING;
                        """
                    ),
                    params={"p": provider_key, "now": now_utc},
                )  # type: ignore

                bind = session.get_bind()
                is_pg = (
                    getattr(getattr(bind, "dialect", None), "name", "") == "postgresql"
                )
                lock_suffix = " FOR UPDATE" if is_pg else ""

                row = session.exec(
                    text(
                        f"SELECT consecutive_failures FROM provider_rate_limit_state WHERE provider = :p{lock_suffix}"
                    ),
                    params={"p": provider_key},
                ).first()  # type: ignore

                prev_fails = row[0] if row and row[0] is not None else 0
                curr_fails = prev_fails + 1

                if curr_fails >= self.max_failures:
                    exponent = curr_fails - self.max_failures
                    backoff = min(self.base_cooldown * (2**exponent), self.max_cooldown)
                    jitter = random.uniform(0.0, 5.0)
                    open_until_utc = now_utc + timedelta(seconds=backoff + jitter)
                    new_state = CircuitState.OPEN.value
                    cooldown_total = backoff + jitter
                else:
                    open_until_utc = None
                    new_state = CircuitState.CLOSED.value
                    cooldown_total = 0.0

                session.exec(
                    text(
                        """
                        UPDATE provider_rate_limit_state
                        SET consecutive_failures = :f,
                            circuit_state = :s,
                            circuit_open_until = :u,
                            updated_at = :now
                        WHERE provider = :p
                        """
                    ),
                    params={
                        "f": curr_fails,
                        "s": new_state,
                        "u": open_until_utc,
                        "now": now_utc,
                        "p": provider_key,
                    },
                )  # type: ignore
                session.commit()

                # Đồng bộ trạng thái vào in-memory RAM của tiến trình từ kết quả DB
                with self._lock:
                    self._failures[provider_key] = curr_fails
                    if curr_fails >= self.max_failures:
                        self._circuit_states[provider_key] = CircuitState.OPEN
                        self._circuit_open_until[provider_key] = (
                            self._clock() + cooldown_total
                        )
                    else:
                        self._circuit_states[provider_key] = CircuitState.CLOSED
                        self._circuit_open_until.pop(provider_key, None)
                return
            except Exception:
                pass

        with self._lock:
            curr_fails = self._failures.get(provider_key, 0) + 1
            self._failures[provider_key] = curr_fails

            if curr_fails >= self.max_failures:
                # Tính toán exponential backoff kèm jitter
                exponent = curr_fails - self.max_failures
                backoff = min(self.base_cooldown * (2**exponent), self.max_cooldown)
                jitter = random.uniform(0.0, 5.0)
                total_cooldown = backoff + jitter

                now = self._clock()
                self._circuit_states[provider_key] = CircuitState.OPEN
                self._circuit_open_until[provider_key] = now + total_cooldown
