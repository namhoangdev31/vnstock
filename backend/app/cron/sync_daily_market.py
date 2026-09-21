"""Runner thực thi tác vụ đồng bộ nến ngày sau phiên ATC (Daily Market Cron Job).

Chạy định kỳ vào lúc 15:15 chiều từ Thứ 2 đến Thứ 6 hàng tuần (giờ làm việc thị trường).
Có thể chạy trực tiếp:
    python -m app.cron.sync_daily_market
    uv run python -m app.cron.sync_daily_market
"""

from __future__ import annotations

import logging
import sys
import time

from sqlmodel import Session

from app.core.db import engine
from app.models.models_stock import DataSyncLog
from app.services.data_sync import DataSyncManager
from app.services.vnstock_service import vnstock_service

logger = logging.getLogger(__name__)

# Danh sách các chỉ số thị trường trọng yếu cần cập nhật hàng ngày
CORE_INDEXES: list[str] = ["VNINDEX", "VN30", "HNX", "UPCOM"]


def run_sync_daily_market_job(
    session: Session | None = None,
    delay_sec: float = 0.3,
) -> list[DataSyncLog]:
    """Đồng bộ dữ liệu nến ngày (OHLCV Daily) cho các chỉ số chính và rổ cổ phiếu VN30 sau phiên ATC."""

    def _execute(mgr: DataSyncManager) -> list[DataSyncLog]:
        logs: list[DataSyncLog] = []

        # 1. Lấy danh sách mã rổ VN30
        try:
            vn30_symbols = mgr.svc.fetch_group_symbols("VN30")
        except Exception:
            logger.warning("Không thể tải rổ VN30, sử dụng danh sách chỉ số chính.")
            vn30_symbols = []

        target_symbols = list(set(CORE_INDEXES + vn30_symbols))
        logger.info(
            "Bắt đầu đồng bộ nến ngày cho %d mã sau phiên ATC...", len(target_symbols)
        )

        for sym in target_symbols:
            try:
                log = mgr.sync_daily_incremental(sym)
                logs.append(log)
                time.sleep(delay_sec)
            except Exception as exc:
                logger.warning("Lỗi đồng bộ nến ngày cho %s: %s", sym, exc)

        return logs

    if session is not None:
        manager = DataSyncManager(session, vnstock_service)
        return _execute(manager)

    with Session(engine) as db_session:
        manager = DataSyncManager(db_session, vnstock_service)
        return _execute(manager)


def main() -> int:
    """Entrypoint dòng lệnh để chạy cronjob nến ngày sau phiên ATC."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger.info("=== BẮT ĐẦU CRONJOB ĐỒNG BỘ NẾN NGÀY (SAU PHIÊN ATC 15:15) ===")
    try:
        logs = run_sync_daily_market_job()
        success_count = sum(1 for log in logs if log.status == "success")
        logger.info(
            "Hoàn tất đồng bộ nến ngày: %d/%d mã thành công!",
            success_count,
            len(logs),
        )
        return 0
    except Exception as exc:
        logger.exception("Lỗi ngoại lệ khi chạy cronjob nến ngày: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
