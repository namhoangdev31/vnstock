"""Bộ lập lịch in-process background scheduler cho FastAPI.

Tự động tính toán độ trễ và kích hoạt tác vụ đồng bộ danh mục mã
vào đúng 08:00 sáng Thứ Hai và Thứ Năm hàng tuần (Giờ Việt Nam UTC+7).
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.core.config import settings
from app.cron.sync_symbols import run_sync_symbols_job

logger = logging.getLogger(__name__)

VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")


def get_next_schedule_delay(
    now: datetime | None = None,
    target_days: tuple[int, ...] = (0, 3),  # 0=Monday, 3=Thursday
    target_hour: int = 8,
    target_minute: int = 0,
) -> float:
    """Tính số giây từ thời điểm hiện tại đến 08:00 Thứ 2 hoặc Thứ 5 tiếp theo (giờ VN UTC+7)."""
    if now is None:
        now = datetime.now(VN_TZ)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=VN_TZ)
    else:
        now = now.astimezone(VN_TZ)

    candidates: list[datetime] = []
    for day_offset in range(8):
        check_date = (now + timedelta(days=day_offset)).date()
        if check_date.weekday() in target_days:
            candidate_dt = datetime(
                check_date.year,
                check_date.month,
                check_date.day,
                target_hour,
                target_minute,
                0,
                tzinfo=VN_TZ,
            )
            if candidate_dt > now:
                candidates.append(candidate_dt)

    if not candidates:
        return 3600.0

    next_run = min(candidates)
    delay = (next_run - now).total_seconds()
    return max(delay, 1.0)


async def run_inprocess_scheduler() -> None:
    """Vòng lặp chạy ngầm trong tiến trình FastAPI để thực thi cronjob định kỳ."""
    logger.info(
        "Khởi động bộ lập lịch in-process scheduler (Thứ 2 & Thứ 5 lúc 08:00 sáng VN)..."
    )
    while True:
        try:
            delay = get_next_schedule_delay()
            logger.info(
                "In-process scheduler: Chờ %.1f giây đến lần chạy tiếp theo.", delay
            )
            await asyncio.sleep(delay)
            logger.info("In-process scheduler: Đang thực thi đồng bộ danh mục mã...")
            # Chạy sync trong worker thread để không chặn event loop async
            await asyncio.to_thread(run_sync_symbols_job)
            logger.info("In-process scheduler: Đồng bộ hoàn tất!")
            # Tránh re-trigger lặp lại trong cùng một phút
            await asyncio.sleep(60)
        except asyncio.CancelledError:
            logger.info("In-process scheduler đã nhận lệnh dừng (shutdown).")
            break
        except Exception as exc:
            logger.exception("Lỗi trong vòng lặp in-process scheduler: %s", exc)
            await asyncio.sleep(60)


def start_scheduler_task() -> asyncio.Task[None] | None:
    """Tạo asyncio background task nếu cấu hình ENABLE_INPROCESS_CRON được bật."""
    if not settings.ENABLE_INPROCESS_CRON:
        logger.info(
            "In-process scheduler đang TẮT (ENABLE_INPROCESS_CRON=False). Ưu tiên chạy qua GitHub Actions hoặc OS Cron."
        )
        return None
    return asyncio.create_task(run_inprocess_scheduler())
