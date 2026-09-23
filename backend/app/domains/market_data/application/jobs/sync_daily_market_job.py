"""Market Data Application Job: Daily Market Sync after ATC.

Đồng bộ nến ngày (OHLCV Daily) cho các chỉ số chính, rổ VN30,
dòng tiền tổ chức và basis phái sinh.
"""

from __future__ import annotations

import logging
import time

from sqlmodel import Session

from app.core.db import engine
from app.domains.market_data.application.sync_service import DataSyncManager
from app.domains.market_data.domain.models import DataSyncLog
from app.domains.market_data.infrastructure.vnstock_adapter import (
    VnstockService,
    vnstock_service,
)

logger = logging.getLogger(__name__)

# LƯU Ý: "UPCOM" bị loại bỏ vì vnstock v4 validate_symbol() từ chối tên sàn.
# "HNX" được giữ vì source msn hỗ trợ fallback thành công.
CORE_INDEXES: list[str] = ["VNINDEX", "VN30", "HNX", "VN30F1M"]


def run_sync_daily_market_job(
    session: Session | None = None,
    delay_sec: float = 0.3,
    service: VnstockService | None = None,
) -> list[DataSyncLog]:
    """Đồng bộ dữ liệu nến ngày (OHLCV Daily) cho các chỉ số chính, rổ VN30, dòng tiền tổ chức và basis phái sinh."""
    svc = service if service is not None else vnstock_service

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
                if delay_sec > 0:
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
        manager = DataSyncManager(session, svc)
        return _execute(manager)

    with Session(engine) as db_session:
        manager = DataSyncManager(db_session, svc)
        return _execute(manager)
