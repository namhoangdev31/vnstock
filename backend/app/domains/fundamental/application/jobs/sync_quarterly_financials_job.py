"""Fundamental Application Job: Quarterly Financials & Corporate Data Sync.

Đồng bộ định kỳ báo cáo tài chính và dữ liệu doanh nghiệp:
- Hồ sơ doanh nghiệp (Company Profile & Overview)
- Báo cáo tài chính (Income Statement, Balance Sheet, Cash Flow)
- Chỉ số tài chính định lượng (Financial Ratios)
- Lịch sự kiện & cổ tức (Corporate Events)
- Ban lãnh đạo & Cổ đông lớn (Officers & Shareholders)
- Công ty con & liên kết (Subsidiaries)
- Giao dịch nội bộ (Insider Trading)
- Lịch sử tăng vốn (Capital History)
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

# Danh sách cổ phiếu cốt lõi dự phòng nếu không lấy được rổ VN30
FALLBACK_CORE_SYMBOLS: list[str] = [
    "FPT",
    "HPG",
    "TCB",
    "MBB",
    "VHM",
    "VIC",
    "VNM",
    "VCB",
    "MWG",
    "SSI",
]


def run_sync_quarterly_financials_job(
    session: Session | None = None,
    group: str = "VN30",
    delay_sec: float = 0.3,
    service: VnstockService | None = None,
) -> list[DataSyncLog]:
    """Đồng bộ toàn bộ dữ liệu tài chính & doanh nghiệp cho rổ chỉ số (mặc định VN30)."""
    svc = service if service is not None else vnstock_service

    def _execute(mgr: DataSyncManager) -> list[DataSyncLog]:
        logs: list[DataSyncLog] = []

        try:
            target_symbols = mgr.svc.fetch_group_symbols(group)
            if not target_symbols:
                target_symbols = FALLBACK_CORE_SYMBOLS
        except Exception:
            logger.warning(
                "Không thể tải danh sách mã cho nhóm %s, sử dụng danh sách cốt lõi dự phòng.",
                group,
            )
            target_symbols = FALLBACK_CORE_SYMBOLS

        logger.info(
            "Bắt đầu đồng bộ báo cáo tài chính & doanh nghiệp cho %d mã (rổ: %s)...",
            len(target_symbols),
            group,
        )

        for sym in target_symbols:
            try:
                sub_logs = [
                    mgr.sync_company_profile(sym),
                    mgr.sync_company_shareholders(sym),
                    mgr.sync_company_officers(sym),
                    mgr.sync_corporate_events(sym),
                    mgr.sync_company_subsidiaries(sym),
                    mgr.sync_insider_trading(sym),
                    mgr.sync_capital_history(sym),
                    mgr.sync_financials(
                        sym, report_type="income_statement", period="quarter"
                    ),
                    mgr.sync_financials(
                        sym, report_type="balance_sheet", period="quarter"
                    ),
                    mgr.sync_financials(sym, report_type="cash_flow", period="quarter"),
                    mgr.sync_financial_ratios(sym, period="quarter"),
                ]
                logs.extend(sub_logs)
                if delay_sec > 0:
                    time.sleep(delay_sec)
            except Exception as exc:
                logger.warning("Lỗi đồng bộ dữ liệu toàn diện cho %s: %s", sym, exc)

        return logs

    if session is not None:
        manager = DataSyncManager(session, svc)
        return _execute(manager)

    with Session(engine) as db_session:
        manager = DataSyncManager(db_session, svc)
        return _execute(manager)
