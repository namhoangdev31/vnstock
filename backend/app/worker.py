"""Standalone Market Worker & 24/7 Session Engine (MarketWorker).

Độc lập hoàn toàn khỏi FastAPI web lifespan:
- Đảm bảo tính độc bản (Single Active Instance) qua PostgreSQL Advisory Lock:
    `SELECT pg_try_advisory_lock(8823910248102)`.
- Triển khai Finite State Machine (FSM) 9 trạng thái bám sát chu kỳ thực tế thị trường tài chính Việt Nam:
  * Phân tách phiên ATO phái sinh VN30F1M (08:45) và cổ phiếu (09:00).
  * Kiểm tra tự động lịch nghỉ lễ Việt Nam (Tết, Giỗ tổ, 30/4, 1/5, 2/9) và cuối tuần.
  * Tần suất adaptive polling: 0.5s (ATC/pre-ATC), 1.0s (phiên liên tục), 60s (nghỉ trưa), 300s (qua đêm/nghỉ lễ).
- Graceful shutdown với tín hiệu SIGINT / SIGTERM.
"""

import logging
import signal
import sys
import time
from datetime import datetime
from datetime import time as dtime
from enum import StrEnum
from types import FrameType
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine

from app.core.db import engine
from app.services.settlement_service import VietnamHolidayCalendar

logger = logging.getLogger("market_worker")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [Worker] %(message)s",
)

VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")
WORKER_ADVISORY_LOCK_ID = 8823910248102


class MarketSessionState(StrEnum):
    """9 trạng thái phiên giao dịch theo chuẩn Master Rules (AGENTS §3)."""

    PRE_ATO_SETUP = "PRE_ATO_SETUP"  # 08:30 - 08:45
    ATO_AUCTION = "ATO_AUCTION"  # 08:45 - 09:00 (Phái sinh mở 08:45)
    MORNING_CONTINUOUS = "MORNING_CONTINUOUS"  # 09:00 - 11:30 (Cơ sở mở 09:00)
    MIDDAY_INTERMISSION = "MIDDAY_INTERMISSION"  # 11:30 - 13:00
    AFTERNOON_CONTINUOUS = "AFTERNOON_CONTINUOUS"  # 13:00 - 14:15 (Hàng T+2 về 13:00)
    PRE_ATC_SETUP = "PRE_ATC_SETUP"  # 14:15 - 14:30 (Kích hoạt dự báo ATC)
    ATC_AUCTION = "ATC_AUCTION"  # 14:30 - 14:45
    POST_MARKET_EVAL = "POST_MARKET_EVAL"  # 14:45 - 15:30 (Đối soát sổ lệnh)
    OVERNIGHT_SIMULATION = "OVERNIGHT_SIMULATION"  # 15:30 - 08:30 / Nghỉ lễ / Cuối tuần


STATE_POLL_INTERVALS: dict[MarketSessionState, float] = {
    MarketSessionState.PRE_ATO_SETUP: 30.0,
    MarketSessionState.ATO_AUCTION: 1.0,
    MarketSessionState.MORNING_CONTINUOUS: 1.0,
    MarketSessionState.MIDDAY_INTERMISSION: 60.0,
    MarketSessionState.AFTERNOON_CONTINUOUS: 1.0,
    MarketSessionState.PRE_ATC_SETUP: 0.5,
    MarketSessionState.ATC_AUCTION: 0.5,
    MarketSessionState.POST_MARKET_EVAL: 60.0,
    MarketSessionState.OVERNIGHT_SIMULATION: 300.0,
}


def get_current_session_state(dt: datetime | None = None) -> MarketSessionState:
    """Xác định trạng thái phiên giao dịch Việt Nam theo mốc thời gian (múi giờ Asia/Ho_Chi_Minh).

    Tuân thủ đúng quy tắc:
    - Thứ Bảy, Chủ Nhật hoặc ngày nghỉ lễ -> OVERNIGHT_SIMULATION.
    - 08:45 phái sinh mở cửa ATO trước cơ sở 15 phút.
    """
    if dt is None:
        dt = datetime.now(VN_TZ)
    elif dt.tzinfo is None:
        dt = dt.replace(tzinfo=VN_TZ)
    else:
        dt = dt.astimezone(VN_TZ)

    current_date = dt.date()
    current_time = dt.time()

    # Kiểm tra cuối tuần hoặc ngày lễ
    if current_date.weekday() in (5, 6) or VietnamHolidayCalendar.is_holiday(
        current_date
    ):
        return MarketSessionState.OVERNIGHT_SIMULATION

    # Phân định các khung giờ ngày thường (Thứ 2 đến Thứ 6)
    if current_time < dtime(8, 30):
        return MarketSessionState.OVERNIGHT_SIMULATION
    if dtime(8, 30) <= current_time < dtime(8, 45):
        return MarketSessionState.PRE_ATO_SETUP
    if dtime(8, 45) <= current_time < dtime(9, 0):
        return MarketSessionState.ATO_AUCTION
    if dtime(9, 0) <= current_time < dtime(11, 30):
        return MarketSessionState.MORNING_CONTINUOUS
    if dtime(11, 30) <= current_time < dtime(13, 0):
        return MarketSessionState.MIDDAY_INTERMISSION
    if dtime(13, 0) <= current_time < dtime(14, 15):
        return MarketSessionState.AFTERNOON_CONTINUOUS
    if dtime(14, 15) <= current_time < dtime(14, 30):
        return MarketSessionState.PRE_ATC_SETUP
    if dtime(14, 30) <= current_time < dtime(14, 45):
        return MarketSessionState.ATC_AUCTION
    if dtime(14, 45) <= current_time < dtime(15, 30):
        return MarketSessionState.POST_MARKET_EVAL

    return MarketSessionState.OVERNIGHT_SIMULATION


def try_acquire_worker_advisory_lock(
    db_engine: Engine,
) -> tuple[bool, Connection | None]:
    """Cố gắng chiếm độc quyền PostgreSQL Advisory Lock cho tiến trình Market Worker.

    Trả về (True, conn) nếu chiếm lock thành công; connection này PHẢI được duy trì sống
    suốt vòng đời daemon để bảo vệ session-level lock.
    Trả về (False, None) nếu đã có worker khác đang giữ lock.
    Với SQLite (testing/local), trả về (True, None).
    """
    if db_engine.dialect.name != "postgresql":
        return True, None

    conn = db_engine.connect()
    try:
        result = conn.execute(
            text("SELECT pg_try_advisory_lock(:lock_id)"),
            {"lock_id": WORKER_ADVISORY_LOCK_ID},
        ).scalar()
        if bool(result):
            return True, conn
        conn.close()
        return False, None
    except Exception as exc:
        logger.error("Lỗi khi kiểm tra PostgreSQL Advisory Lock: %s", exc)
        conn.close()
        return False, None


def release_worker_advisory_lock(target: Connection | Engine | None) -> None:
    """Giải phóng PostgreSQL Advisory Lock trên connection đang giữ lock và đóng connection."""
    if target is None:
        return

    if isinstance(target, Engine):
        if target.dialect.name != "postgresql":
            return
        logger.warning(
            "release_worker_advisory_lock nhận Engine thay vì Connection giữ lock. Lock session-level cần connection cụ thể."
        )
        return

    conn: Connection = target
    if conn.closed:
        return

    try:
        conn.execute(
            text("SELECT pg_advisory_unlock(:lock_id)"),
            {"lock_id": WORKER_ADVISORY_LOCK_ID},
        )
        logger.info("Đã giải phóng thành công PostgreSQL Advisory Lock.")
    except Exception as exc:
        logger.warning("Không thể giải phóng advisory lock: %s", exc)
    finally:
        conn.close()


class MarketWorkerDaemon:
    """Daemon quản lý vòng đời tác vụ thị trường định lượng."""

    def __init__(self, db_engine: Engine = engine) -> None:
        self.db_engine = db_engine
        self._running = False
        self._has_lock = False
        self._lock_conn: Connection | None = None
        self.total_cycles = 0
        self.start_time: float | None = None

    def _signal_handler(self, sig: int, _frame: FrameType | None) -> None:
        sig_name = signal.Signals(sig).name
        logger.info("Đã nhận tín hiệu %s. Đang chuẩn bị Graceful Shutdown...", sig_name)
        self._running = False

    def execute_cycle(self, state: MarketSessionState) -> None:
        """Thực thi một chu kỳ công việc tương ứng với trạng thái phiên hiện tại."""
        self.total_cycles += 1
        logger.info(
            "Chu kỳ #%d | Phiên: %s | Polling: %.1fs",
            self.total_cycles,
            state.value,
            STATE_POLL_INTERVALS[state],
        )

        # Định tuyến tác vụ theo từng phiên
        if state == MarketSessionState.PRE_ATO_SETUP:
            # Đồng bộ pivots, tham chiếu
            pass
        elif state == MarketSessionState.ATO_AUCTION:
            # Giám sát ATO phái sinh
            pass
        elif state in (
            MarketSessionState.MORNING_CONTINUOUS,
            MarketSessionState.AFTERNOON_CONTINUOUS,
        ):
            # Khớp lệnh liên tục, tổng hợp dòng tiền
            pass
        elif state == MarketSessionState.PRE_ATC_SETUP:
            # Kích hoạt Engine dự phóng ATC
            pass
        elif state == MarketSessionState.ATC_AUCTION:
            # Khớp ATC thực tế
            pass
        elif state == MarketSessionState.POST_MARKET_EVAL:
            # Đối soát sổ nhật ký tín hiệu ForecastJournal
            pass
        elif state == MarketSessionState.OVERNIGHT_SIMULATION:
            # Tối ưu hóa mô phỏng Monte Carlo qua đêm
            pass

    def run(self, max_cycles: int | None = None, single_cycle: bool = False) -> None:
        """Bắt đầu vòng lặp tiến trình daemon."""
        # Đăng ký signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        logger.info("Khởi động Standalone Market Worker Daemon...")

        # Chiếm Advisory Lock và giữ Connection mở suốt thời gian chạy
        self._has_lock, self._lock_conn = try_acquire_worker_advisory_lock(
            self.db_engine
        )
        if not self._has_lock:
            logger.warning(
                "Đã có một tiến trình Market Worker khác đang giữ Advisory Lock (%d). Tiến trình này sẽ dừng ngay.",
                WORKER_ADVISORY_LOCK_ID,
            )
            return

        self._running = True
        self.start_time = time.monotonic()

        try:
            while self._running:
                now_dt = datetime.now(VN_TZ)
                state = get_current_session_state(now_dt)

                self.execute_cycle(state)

                if single_cycle:
                    break
                if max_cycles is not None and self.total_cycles >= max_cycles:
                    break

                interval = STATE_POLL_INTERVALS[state]
                time.sleep(interval)
        finally:
            self._running = False
            if self._has_lock:
                release_worker_advisory_lock(self._lock_conn)
                self._lock_conn = None
            logger.info(
                "Market Worker Daemon đã kết thúc sạch sẽ (Total cycles: %d).",
                self.total_cycles,
            )


if __name__ == "__main__":
    daemon = MarketWorkerDaemon()
    try:
        daemon.run()
    except KeyboardInterrupt:
        logger.info("Nhận ngắt từ bàn phím. Dừng worker.")
        sys.exit(0)
