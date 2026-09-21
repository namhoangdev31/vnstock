"""Dịch vụ Screener Snapshot & Phân trang Keyset 2 pha Brokerage-Grade (ScreenerService).

Tuân thủ nghiêm ngặt SLA DB execution time P95 < 10 ms:
- Sử dụng pre-computed ScreenerSnapshot.
- Partial index: (roe DESC NULLS LAST, instrument_id ASC) WHERE is_active = true.
- Keyset cursor 2 pha xử lý triệt để nhóm roe IS NULL không sort spill ra đĩa:
  * Pha 1: cursor_roe IS NOT NULL -> (roe < cursor_roe) OR (roe == cursor_roe AND id > cursor_id) OR (roe IS NULL)
  * Pha 2: cursor_roe IS NULL -> roe IS NULL AND id > cursor_id
"""

import uuid

from pydantic import BaseModel
from sqlmodel import Session, and_, col, or_, select

from app.models.entities.screener import ScreenerSnapshot


class ScreenerCursor(BaseModel):
    """Thông tin con trỏ Keyset Pagination."""

    roe: float | None = None
    instrument_id: uuid.UUID | None = None


class ScreenerResponse(BaseModel):
    """Kết quả phân trang của Screener."""

    items: list[ScreenerSnapshot]
    total_count: int
    has_next: bool
    next_cursor: ScreenerCursor | None = None


class ScreenerService:
    """Xử lý truy vấn bộ lọc cổ phiếu với Keyset Pagination tối ưu."""

    @classmethod
    def query_screener_keyset(
        cls,
        session: Session,
        page_size: int = 50,
        cursor: ScreenerCursor | None = None,
        exchange: str | None = None,
        industry: str | None = None,
        min_pe: float | None = None,
        max_pe: float | None = None,
        min_roe: float | None = None,
    ) -> ScreenerResponse:
        """Truy vấn bảng ScreenerSnapshot bằng thuật toán Keyset 2 pha."""
        # Điều kiện lọc cơ bản
        base_filters = [col(ScreenerSnapshot.is_active).is_(True)]

        if exchange:
            base_filters.append(col(ScreenerSnapshot.exchange) == exchange.upper())
        if industry:
            base_filters.append(col(ScreenerSnapshot.industry) == industry)
        if min_pe is not None:
            base_filters.append(col(ScreenerSnapshot.pe) >= min_pe)
        if max_pe is not None:
            base_filters.append(col(ScreenerSnapshot.pe) <= max_pe)
        if min_roe is not None:
            base_filters.append(col(ScreenerSnapshot.roe) >= min_roe)

        query = select(ScreenerSnapshot).where(*base_filters)

        # Áp dụng Keyset Cursor
        if cursor is not None and cursor.instrument_id is not None:
            if cursor.roe is not None:
                # Pha 1: Cursor vẫn ở trong vùng giá trị ROE có số thực
                # Tìm các bản ghi có ROE nhỏ hơn HOẶC bằng nhưng ID lớn hơn HOẶC ROE là NULL
                cursor_cond = or_(
                    col(ScreenerSnapshot.roe) < cursor.roe,
                    and_(
                        col(ScreenerSnapshot.roe) == cursor.roe,
                        col(ScreenerSnapshot.instrument_id) > cursor.instrument_id,
                    ),
                    col(ScreenerSnapshot.roe).is_(None),
                )
                query = query.where(cursor_cond)
                query = query.order_by(
                    col(ScreenerSnapshot.roe).desc().nulls_last(),
                    col(ScreenerSnapshot.instrument_id).asc(),
                )
            else:
                # Pha 2: Cursor đã tiến vào vùng roe IS NULL
                cursor_cond = and_(
                    col(ScreenerSnapshot.roe).is_(None),
                    col(ScreenerSnapshot.instrument_id) > cursor.instrument_id,
                )
                query = query.where(cursor_cond)
                query = query.order_by(col(ScreenerSnapshot.instrument_id).asc())
        else:
            # Trang đầu tiên
            query = query.order_by(
                col(ScreenerSnapshot.roe).desc().nulls_last(),
                col(ScreenerSnapshot.instrument_id).asc(),
            )

        # Lấy dôi dư 1 bản ghi để biết có trang tiếp theo hay không
        query = query.limit(page_size + 1)
        results = list(session.exec(query).all())

        has_next = len(results) > page_size
        items = results[:page_size]

        next_cursor = None
        if has_next and items:
            last_item = items[-1]
            next_cursor = ScreenerCursor(
                roe=last_item.roe,
                instrument_id=last_item.instrument_id,
            )

        return ScreenerResponse(
            items=items,
            total_count=len(items),
            has_next=has_next,
            next_cursor=next_cursor,
        )
