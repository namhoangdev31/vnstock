"""Runner thực thi tác vụ đồng bộ danh mục mã chứng khoán & phái sinh (Cron job).

Chạy định kỳ vào Thứ 2 và Thứ 5 hàng tuần lúc 08:00 sáng.
Có thể chạy trực tiếp:
    python -m app.cron.sync_symbols
    uv run python -m app.cron.sync_symbols
"""

from __future__ import annotations

import logging
import sys

from sqlmodel import Session

from app.core.db import engine
from app.models.models_stock import DataSyncLog
from app.services.data_sync import DataSyncManager
from app.services.vnstock_service import vnstock_service

logger = logging.getLogger(__name__)


def run_sync_symbols_job(session: Session | None = None) -> DataSyncLog:
    """Thực thi tác vụ đồng bộ danh mục mã chứng khoán & hợp đồng phái sinh.

    Được thiết kế để chạy độc lập từ CLI / Crontab hoặc từ API webhook / in-process scheduler.
    """
    if session is not None:
        manager = DataSyncManager(session, vnstock_service)
        return manager.sync_symbols()

    with Session(engine) as db_session:
        manager = DataSyncManager(db_session, vnstock_service)
        return manager.sync_symbols()


def main() -> int:
    """Entrypoint dòng lệnh để chạy cronjob đồng bộ mã."""
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
