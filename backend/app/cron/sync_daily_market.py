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

# Danh sách các chỉ số thị trường trọng yếu và phái sinh cần cập nhật hàng ngày
CORE_INDEXES: list[str] = ["VNINDEX", "VN30", "HNX", "UPCOM", "VN30F1M"]


def run_sync_daily_market_job(
    session: Session | None = None,
    delay_sec: float = 0.3,
) -> list[DataSyncLog]:
    """Đồng bộ dữ liệu nến ngày (OHLCV Daily) cho các chỉ số chính, rổ VN30, dòng tiền tổ chức và basis phái sinh."""

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
                sub_logs = mgr.sync_daily_incremental([sym])
                if isinstance(sub_logs, list):
                    logs.extend(sub_logs)
                else:
                    logs.append(sub_logs)
                time.sleep(delay_sec)
            except Exception as exc:
                logger.warning("Lỗi đồng bộ nến ngày cho %s: %s", sym, exc)

        # 2. Đồng bộ dòng tiền tổ chức (Khối ngoại, Tự doanh, Room ngoại)
        try:
            logger.info("Đang đồng bộ dòng tiền tổ chức...")
            flow_log = mgr.sync_institutional_flow(
                trading_date=None, symbols=target_symbols
            )
            logs.append(flow_log)
        except Exception as exc:
            logger.warning("Lỗi đồng bộ dòng tiền tổ chức: %s", exc)

        # 3. Tính toán và cập nhật Basis phái sinh (VN30F1M - VN30)
        try:
            logger.info("Đang tính toán Basis phái sinh VN30F1M...")
            mgr.compute_daily_derivative_basis(trading_date=None)
        except Exception as exc:
            logger.warning("Lỗi tính toán Basis phái sinh: %s", exc)

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
