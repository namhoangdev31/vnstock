"""Runner thực thi tác vụ dọn dẹp tick khớp lệnh quan sát (Tick Purge Cron Job).

Chạy định kỳ vào lúc 23:00 từ Thứ 2 đến Thứ 6 (sau phiên giao dịch và sau khi nến 1m đã được chốt).
Thực thi chính sách lưu trữ phân tầng 30 ngày qua Safe Purge Gate (AGENTS §7.2).
Có thể chạy trực tiếp:
    python -m app.cron.purge_ticks
    uv run python -m app.cron.purge_ticks
"""

from __future__ import annotations

import logging
import sys
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlmodel import Session

from app.core.db import engine
from app.models.models_stock import DataSyncLog
from app.services.tick_storage_service import TickStorageService

logger = logging.getLogger(__name__)
VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")


def run_purge_ticks_job(
    session: Session | None = None,
    retention_days: int = TickStorageService.DEFAULT_RETENTION_DAYS,
    force: bool = False,
    min_bars: int | None = None,
) -> DataSyncLog:
    """Thực thi tác vụ dọn dẹp dữ liệu tick quan sát cũ hơn retention_days ngày.

    Áp dụng Safe Purge Gate: Chỉ xóa các ngày đã có nến 1m hoặc bản tổng hợp TickFlowAggregated.
    """
    cutoff_date = date.today() - timedelta(days=retention_days)
    started_at = datetime.now(VN_TZ)

    def _do_purge(db_sess: Session) -> DataSyncLog:
        logger.info(
            "Bắt đầu dọn dẹp tick trước ngày %s (retention=%d ngày, force=%s)...",
            cutoff_date,
            retention_days,
            force,
        )
        try:
            purged_count = TickStorageService.purge_ticks_before_date(
                session=db_sess,
                cutoff_date=cutoff_date,
                force=force,
                min_bars=min_bars,
            )
            completed_at = datetime.now(VN_TZ)
            sync_log = DataSyncLog(
                sync_type="tick_purge",
                symbol=None,
                source="system",
                status="success",
                rows_synced=purged_count,
                started_at=started_at,
                completed_at=completed_at,
                error_message=None,
            )
            db_sess.add(sync_log)
            db_sess.commit()
            db_sess.refresh(sync_log)
            logger.info(
                "Hoàn tất dọn dẹp tick! Đã purge an toàn %d bản ghi tick.",
                purged_count,
            )
            return sync_log
        except Exception as exc:
            db_sess.rollback()
            completed_at = datetime.now(VN_TZ)
            err_msg = str(exc)
            logger.exception("Lỗi khi thực thi dọn dẹp tick: %s", err_msg)
            sync_log = DataSyncLog(
                sync_type="tick_purge",
                symbol=None,
                source="system",
                status="failed",
                rows_synced=0,
                started_at=started_at,
                completed_at=completed_at,
                error_message=err_msg,
            )
            try:
                db_sess.add(sync_log)
                db_sess.commit()
                db_sess.refresh(sync_log)
            except Exception:
                pass
            return sync_log

    if session is not None:
        return _do_purge(session)

    with Session(engine) as db_sess:
        return _do_purge(db_sess)


def main() -> int:
    """Entrypoint dòng lệnh để chạy trực tiếp cronjob dọn dẹp tick."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger.info("=== BẮT ĐẦU CRONJOB DỌN DẸP TICK QUÁ HẠN (SAFE PURGE GATE) ===")
    try:
        log = run_purge_ticks_job()
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
