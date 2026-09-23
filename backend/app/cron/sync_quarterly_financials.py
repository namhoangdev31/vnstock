"""CLI Runner: Đồng bộ báo cáo tài chính và dữ liệu doanh nghiệp định kỳ (Quarterly Financials Cron Job).

Chạy định kỳ (hàng tuần hoặc khi kết thúc mùa báo cáo tài chính quý).
Có thể chạy trực tiếp:
    python -m app.cron.sync_quarterly_financials
    uv run python -m app.cron.sync_quarterly_financials
"""

from __future__ import annotations

import argparse
import logging
import sys

from sqlmodel import Session

from app.domains.fundamental.application.jobs.sync_quarterly_financials_job import (
    FALLBACK_CORE_SYMBOLS,
)
from app.domains.fundamental.application.jobs.sync_quarterly_financials_job import (
    run_sync_quarterly_financials_job as _run_sync_quarterly_financials_job,
)
from app.domains.market_data.domain.models import DataSyncLog
from app.domains.market_data.infrastructure.vnstock_adapter import vnstock_service

logger = logging.getLogger(__name__)

__all__ = [
    "FALLBACK_CORE_SYMBOLS",
    "run_sync_quarterly_financials_job",
    "vnstock_service",
]


def run_sync_quarterly_financials_job(
    session: Session | None = None,
    group: str = "VN30",
    delay_sec: float = 0.3,
) -> list[DataSyncLog]:
    """Đồng bộ toàn bộ dữ liệu tài chính & doanh nghiệp cho rổ chỉ số (mặc định VN30)."""
    return _run_sync_quarterly_financials_job(
        session=session, group=group, delay_sec=delay_sec, service=vnstock_service
    )


def main() -> int:
    """Entrypoint dòng lệnh để chạy cronjob đồng bộ dữ liệu tài chính quý."""
    parser = argparse.ArgumentParser(
        description="Đồng bộ dữ liệu báo cáo tài chính & thông tin doanh nghiệp định kỳ"
    )
    parser.add_argument(
        "--group",
        default="VN30",
        help="Nhóm mã chứng khoán cần đồng bộ (mặc định: VN30)",
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
    logger.info(
        "=== BẮT ĐẦU CRONJOB ĐỒNG BỘ DỮ LIỆU TÀI CHÍNH QUÝ (NHÓM: %s) ===", args.group
    )
    try:
        logs = run_sync_quarterly_financials_job(group=args.group, delay_sec=args.delay)
        success_count = sum(1 for log in logs if log.status == "success")
        logger.info(
            "Hoàn tất đồng bộ dữ liệu tài chính quý: %d/%d tác vụ thành công!",
            success_count,
            len(logs),
        )
        return 0
    except Exception as exc:
        logger.exception("Lỗi ngoại lệ khi chạy cronjob tài chính quý: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
