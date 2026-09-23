"""CLI Runner: Đồng bộ danh mục mã chứng khoán & phái sinh (Cron job).

Chạy định kỳ vào Thứ 2 và Thứ 5 hàng tuần lúc 08:00 sáng.
Có thể chạy trực tiếp:
    python -m app.cron.sync_symbols
    uv run python -m app.cron.sync_symbols
"""

from __future__ import annotations

import argparse
import logging
import sys

from sqlmodel import Session

from app.domains.market_data.application.jobs.sync_symbols_job import (
    run_sync_symbols_job as _run_sync_symbols_job,
)
from app.domains.market_data.domain.models import DataSyncLog
from app.domains.market_data.infrastructure.vnstock_adapter import vnstock_service

logger = logging.getLogger(__name__)

__all__ = ["main", "run_sync_symbols_job", "vnstock_service"]


def run_sync_symbols_job(session: Session | None = None) -> DataSyncLog:
    """Thực thi tác vụ đồng bộ danh mục mã chứng khoán & hợp đồng phái sinh.

    Được thiết kế để chạy độc lập từ CLI / Crontab hoặc từ API webhook / in-process scheduler.
    """
    return _run_sync_symbols_job(session=session, service=vnstock_service)


def main() -> int:
    """Entrypoint dòng lệnh để chạy cronjob đồng bộ mã."""
    parser = argparse.ArgumentParser(
        description="Đồng bộ danh mục mã chứng khoán & hợp đồng phái sinh định kỳ"
    )
    parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger.info("=== BẮT ĐẦU CRONJOB ĐỒNG BỘ DANH MỤC MÃ (THỨ 2 & THỨ 5) ===")
    try:
        log = run_sync_symbols_job()
        if log.status == "success":
            logger.info(
                "Đồng bộ thành công! Số lượng mã được cập nhật/thêm mới: %d",
                log.rows_synced,
            )
            return 0
        logger.error("Đồng bộ thất bại: %s", log.error_message)
        return 1
    except Exception as exc:
        logger.exception("Lỗi ngoại lệ khi chạy cronjob: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
