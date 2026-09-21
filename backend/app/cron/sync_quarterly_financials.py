"""Runner thực thi tác vụ đồng bộ báo cáo tài chính và dữ liệu doanh nghiệp định kỳ (Quarterly Financials Cron Job).

Chạy định kỳ (hàng tuần hoặc khi kết thúc mùa báo cáo tài chính quý) để cập nhật:
- Hồ sơ doanh nghiệp (Company Profile & Overview)
- Báo cáo tài chính (Income Statement, Balance Sheet, Cash Flow)
- Chỉ số tài chính định lượng & JSONB (Financial Ratios)
- Lịch sự kiện & cổ tức (Corporate Events)
- Ban lãnh đạo (Officers) & Cổ đông lớn (Shareholders)
- Công ty con & liên kết (Subsidiaries)
- Giao dịch nội bộ (Insider Trading)
- Lịch sử tăng vốn (Capital History)

Có thể chạy trực tiếp:
    python -m app.cron.sync_quarterly_financials
    uv run python -m app.cron.sync_quarterly_financials
"""

from __future__ import annotations

import argparse
import logging
import sys
import time

from sqlmodel import Session

from app.core.db import engine
from app.models.models_stock import DataSyncLog
from app.services.data_sync import DataSyncManager
from app.services.vnstock_service import vnstock_service

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
) -> list[DataSyncLog]:
    """Đồng bộ toàn bộ dữ liệu tài chính & doanh nghiệp cho rổ chỉ số (mặc định VN30)."""

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
                time.sleep(delay_sec)
            except Exception as exc:
                logger.warning("Lỗi đồng bộ dữ liệu toàn diện cho %s: %s", sym, exc)

        return logs

    if session is not None:
        manager = DataSyncManager(session, vnstock_service)
        return _execute(manager)

    with Session(engine) as db_session:
        manager = DataSyncManager(db_session, vnstock_service)
        return _execute(manager)


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
