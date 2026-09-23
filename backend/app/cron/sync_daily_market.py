"""CLI Runner: Đồng bộ nến ngày sau phiên ATC (Daily Market Cron Job).

Chạy định kỳ vào lúc 15:15 chiều từ Thứ 2 đến Thứ 6 hàng tuần (giờ làm việc thị trường).
Có thể chạy trực tiếp:
    python -m app.cron.sync_daily_market
    uv run python -m app.cron.sync_daily_market
"""

from __future__ import annotations

import argparse
import logging
import sys

from sqlmodel import Session

from app.domains.market_data.application.jobs.sync_daily_market_job import (
    CORE_INDEXES,
)
from app.domains.market_data.application.jobs.sync_daily_market_job import (
    run_sync_daily_market_job as _run_sync_daily_market_job,
)
from app.domains.market_data.domain.models import DataSyncLog
from app.domains.market_data.infrastructure.vnstock_adapter import vnstock_service

logger = logging.getLogger(__name__)

__all__ = ["CORE_INDEXES", "main", "run_sync_daily_market_job", "vnstock_service"]


def run_sync_daily_market_job(
    session: Session | None = None,
    delay_sec: float = 0.3,
) -> list[DataSyncLog]:
    """Đồng bộ dữ liệu nến ngày (OHLCV Daily) cho các chỉ số chính, rổ VN30, dòng tiền tổ chức và basis phái sinh."""
    return _run_sync_daily_market_job(
        session=session, delay_sec=delay_sec, service=vnstock_service
    )


def main() -> int:
    """Entrypoint dòng lệnh để chạy cronjob nến ngày sau phiên ATC."""
    parser = argparse.ArgumentParser(
        description="Đồng bộ nến ngày sau phiên ATC cho các chỉ số và rổ VN30"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.3,
        help="Độ trễ giữa các mã (giây) nhằm tuân thủ chống chặn IP (mặc định: 0.3)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger.info("=== BẮT ĐẦU CRONJOB ĐỒNG BỘ NẾN NGÀY (SAU PHIÊN ATC 15:15) ===")
    try:
        logs = run_sync_daily_market_job(delay_sec=args.delay)
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
