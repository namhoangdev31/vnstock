"""CLI Runner: Dọn dẹp tick khớp lệnh quan sát (Tick Purge Cron Job).

Chạy định kỳ vào lúc 23:00 từ Thứ 2 đến Thứ 6 (sau phiên giao dịch và sau khi nến 1m đã được chốt).
Thực thi chính sách lưu trữ phân tầng 30 ngày qua Safe Purge Gate (AGENTS §7.2).
Có thể chạy trực tiếp:
    python -m app.cron.purge_ticks
    uv run python -m app.cron.purge_ticks
"""

from __future__ import annotations

import argparse
import logging
import sys

from app.domains.market_data.application.jobs.purge_ticks_job import (
    VN_TZ,
    run_purge_ticks_job,
)

logger = logging.getLogger(__name__)

__all__ = ["VN_TZ", "main", "run_purge_ticks_job"]


def main() -> int:
    """Entrypoint dòng lệnh để chạy trực tiếp cronjob dọn dẹp tick."""
    parser = argparse.ArgumentParser(
        description="Dọn dẹp dữ liệu tick quan sát cũ hơn N ngày qua Safe Purge Gate"
    )
    parser.add_argument(
        "--retention-days",
        type=int,
        default=30,
        help="Số ngày lưu trữ tick (mặc định 30 ngày theo AGENTS §7.2)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        default=False,
        help="Bỏ qua Safe Purge Gate (chỉ dùng khi bắt buộc)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger.info("=== BẮT ĐẦU CRONJOB DỌN DẸP TICK QUÁ HẠN (SAFE PURGE GATE) ===")
    try:
        log = run_purge_ticks_job(
            retention_days=args.retention_days,
            force=args.force,
        )
        if log.status == "success":
            logger.info(
                "Dọn dẹp tick thành công! Đã purge an toàn %d ticks cũ.",
                log.rows_synced,
            )
            return 0
        logger.error("Dọn dẹp tick thất bại: %s", log.error_message)
        return 1
    except Exception as exc:
        logger.exception("Lỗi ngoại lệ khi chạy cronjob dọn dẹp tick: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
