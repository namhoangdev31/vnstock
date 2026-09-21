"""Bộ lập lịch in-process background scheduler cho FastAPI.

Tự động tính toán độ trễ và kích hoạt các tác vụ định kỳ:
1. Đồng bộ danh mục mã: Thứ Hai & Thứ Năm lúc 08:00 sáng (Giờ Việt Nam UTC+7).
2. Đồng bộ nến ngày sau phiên ATC: Thứ Hai đến Thứ Sáu lúc 15:15 chiều (Giờ Việt Nam UTC+7).
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.core.config import settings
from app.cron.sync_daily_market import run_sync_daily_market_job
from app.cron.sync_symbols import run_sync_symbols_job

logger = logging.getLogger(__name__)

VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")


def get_next_schedule_delay(
    now: datetime | None = None,
    target_days: tuple[int, ...] = (0, 3),  # 0=Monday, 3=Thursday
    target_hour: int = 8,
    target_minute: int = 0,
) -> float:
    """Tính số giây từ thời điểm hiện tại đến mốc thời gian mục tiêu tiếp theo (giờ VN UTC+7)."""
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


async def run_symbols_scheduler_loop() -> None:
    """Vòng lặp định kỳ đồng bộ danh mục mã (Thứ 2 & Thứ 5 lúc 08:00 sáng VN)."""
    logger.info("Khởi động vòng lặp đồng bộ danh mục mã (T2, T5 08:00 sáng)...")
    while True:
        try:
            delay = get_next_schedule_delay(
                target_days=(0, 3), target_hour=8, target_minute=0
            )
            logger.info("Scheduler [Symbols]: Chờ %.1f giây đến lần chạy tiếp.", delay)
            await asyncio.sleep(delay)
            logger.info("Scheduler [Symbols]: Đang thực thi đồng bộ danh mục mã...")
            await asyncio.to_thread(run_sync_symbols_job)
            logger.info("Scheduler [Symbols]: Đồng bộ hoàn tất!")
            await asyncio.sleep(60)
        except asyncio.CancelledError:
            logger.info("Scheduler [Symbols] đã nhận lệnh dừng (shutdown).")
            break
        except Exception as exc:
            logger.exception("Lỗi trong vòng lặp Scheduler [Symbols]: %s", exc)
            await asyncio.sleep(60)


async def run_daily_market_scheduler_loop() -> None:
    """Vòng lặp định kỳ đồng bộ nến ngày sau phiên ATC (Thứ 2 - Thứ 6 lúc 15:15 chiều VN)."""
    logger.info("Khởi động vòng lặp đồng bộ nến ngày (T2-T6 lúc 15:15 chiều)...")
    while True:
        try:
            delay = get_next_schedule_delay(
                target_days=(0, 1, 2, 3, 4), target_hour=15, target_minute=15
            )
            logger.info(
                "Scheduler [Daily Market]: Chờ %.1f giây đến lần chạy tiếp.", delay
            )
            await asyncio.sleep(delay)
            logger.info("Scheduler [Daily Market]: Đang thực thi đồng bộ nến ngày...")
            await asyncio.to_thread(run_sync_daily_market_job)
            logger.info("Scheduler [Daily Market]: Đồng bộ hoàn tất!")
            await asyncio.sleep(60)
        except asyncio.CancelledError:
            logger.info("Scheduler [Daily Market] đã nhận lệnh dừng (shutdown).")
            break
        except Exception as exc:
            logger.exception("Lỗi trong vòng lặp Scheduler [Daily Market]: %s", exc)
            await asyncio.sleep(60)


async def run_inprocess_scheduler() -> None:
    """Chạy đồng thời các vòng lặp tác vụ định kỳ của hệ thống."""
    logger.info("Khởi động toàn diện bộ lập lịch in-process scheduler đa tác vụ...")
    await asyncio.gather(
        run_symbols_scheduler_loop(),
        run_daily_market_scheduler_loop(),
    )


def start_scheduler_task() -> asyncio.Task[None] | None:
    """Tạo asyncio background task nếu cấu hình ENABLE_INPROCESS_CRON được bật."""
    if not settings.ENABLE_INPROCESS_CRON:
        logger.info(
            "In-process scheduler đang TẮT (ENABLE_INPROCESS_CRON=False). Ưu tiên chạy qua GitHub Actions hoặc OS Cron."
        )
        return None
    return asyncio.create_task(run_inprocess_scheduler())
