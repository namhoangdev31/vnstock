"""Market Data Application Job: Purge Ticks with Safe Purge Gate.

Dọn dẹp dữ liệu tick quan sát cũ hơn N ngày theo chính sách lưu trữ phân tầng (AGENTS §7.2).
Áp dụng Safe Purge Gate: chỉ xóa các ngày đã có nến 1m hoặc bản tổng hợp TickFlowAggregated.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlmodel import Session

from app.core.db import engine
from app.domains.market_data.domain.models import DataSyncLog
from app.domains.market_data.infrastructure.tick_storage import TickStorageService

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
