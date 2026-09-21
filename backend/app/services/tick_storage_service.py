"""Quản lý vòng đời lưu trữ và Purge an toàn dữ liệu Tick khớp lệnh quan sát (TickStorageService).

Tuân thủ AGENTS §7.2:
- Ticks từ Quote.intraday() là dữ liệu mẫu quan sát (observational polling).
- Giữ lại 30 ngày gần nhất để phục vụ phân tích microstructure.
- Safe Purge Gate: Chỉ thực hiện DROP dữ liệu cũ khi nến 1m (StockOHLCVIntraday) hoặc
  bản ghi tổng hợp TickFlowAggregated của ngày đó đã được lưu trữ an toàn trong DB.
"""

import logging
from datetime import date

from sqlalchemy import func
from sqlmodel import Session, select

from app.models.entities.quant import TickFlowAggregated
from app.models.entities.stock import StockOHLCVIntraday, StockTickIntraday

logger = logging.getLogger(__name__)


class SafePurgeGateError(Exception):
    """Ngoại lệ phát sinh khi Safe Purge Gate chặn việc xóa dữ liệu do chưa có bản tổng hợp thay thế."""


class TickStorageService:
    """Điều phối chính sách lưu trữ và dọn dẹp tick giao dịch theo chu kỳ 30 ngày."""

    DEFAULT_RETENTION_DAYS: int = 30

    @classmethod
    def verify_safe_purge_gate(
        cls,
        session: Session,
        target_date: date,
    ) -> bool:
        """Kiểm tra Safe Purge Gate cho một ngày giao dịch cụ thể.

        Điều kiện hợp lệ:
        - Có ít nhất một bản ghi nến 1m trong stock_ohlcv_intraday của target_date, HOẶC
        - Có bản ghi tổng hợp trong tick_flow_aggregated của target_date.
        """
        # Kiểm tra tồn tại trong StockOHLCVIntraday
        ohlcv_count = session.exec(
            select(func.count())
            .select_from(StockOHLCVIntraday)
            .where(func.date(StockOHLCVIntraday.timestamp) == target_date)
        ).one()

        if ohlcv_count > 0:
            return True

        # Kiểm tra tồn tại trong TickFlowAggregated
        flow_count = session.exec(
            select(func.count())
            .select_from(TickFlowAggregated)
            .where(func.date(TickFlowAggregated.interval_start) == target_date)
        ).one()

        return flow_count > 0

    @classmethod
    def purge_ticks_before_date(
        cls,
        session: Session,
        cutoff_date: date,
        force: bool = False,
    ) -> int:
        """Dọn dẹp các tick khớp lệnh trước ngày cutoff_date.

        Áp dụng Safe Purge Gate:
        - Với mỗi ngày cần purge, nếu chưa được tổng hợp và force=False -> Bỏ qua ngày đó để tránh mất dữ liệu.
        - Trả về tổng số lượng bản ghi tick đã được dọn dẹp.
        """
        # Lấy danh sách các ngày có dữ liệu tick cũ hơn cutoff_date
        old_dates = session.exec(
            select(func.date(StockTickIntraday.timestamp))
            .where(func.date(StockTickIntraday.timestamp) < cutoff_date)
            .distinct()
        ).all()

        total_purged = 0

        for d_str in old_dates:
            if not d_str:
                continue

            target_d = (
                date.fromisoformat(str(d_str)) if isinstance(d_str, str) else d_str
            )

            # Kiểm tra Safe Purge Gate
            gate_passed = cls.verify_safe_purge_gate(session, target_d)
            if not gate_passed and not force:
                logger.warning(
                    "Safe Purge Gate CHẶN xóa ticks ngày %s: Chưa tìm thấy nến 1m hoặc bản tổng hợp!",
                    target_d,
                )
                continue

            # Thực hiện xóa an toàn
            ticks_to_delete = session.exec(
                select(StockTickIntraday).where(
                    func.date(StockTickIntraday.timestamp) == target_d
                )
            ).all()

            for t in ticks_to_delete:
                session.delete(t)

            total_purged += len(ticks_to_delete)
            logger.info(
                "Đã purge an toàn %d ticks ngày %s", len(ticks_to_delete), target_d
            )

        session.commit()
        return total_purged
