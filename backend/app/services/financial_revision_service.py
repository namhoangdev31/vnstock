"""Dịch vụ quản lý phiên bản Báo cáo tài chính (Financial Report Revisions & Restatements).

Tuân thủ nghiêm ngặt AGENTS Rule 3 (No look-ahead bias, Auditability):
- Transaction Advisory Lock theo Natural Key để chống race-condition khi đồng thời cập nhật.
- Canonical JSON SHA-256 Checksum đảm bảo nhận diện thay đổi nội dung độc lập với thứ tự key.
- Đánh dấu is_provisional nếu thiếu published_at chính thức.
- Point-in-time query phục vụ nghiên cứu định lượng không rò rỉ dữ liệu tương lai.
"""

import hashlib
import json
import logging
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import func
from sqlmodel import Session, col, select

from app.models.base import VN_TZ
from app.models.entities.stock import FinancialReport, FinancialReportRevision

logger = logging.getLogger(__name__)


def canonical_payload_hash(data: dict[str, Any]) -> str:
    """Tạo chuỗi băm SHA-256 từ payload JSON được chuẩn hóa (sort_keys=True, compact separators).

    Đảm bảo tính tất định: Hai payload có cùng nội dung nhưng khác thứ tự key
    luôn cho ra cùng một mã băm duy nhất.
    """
    canonical_json_str = json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical_json_str.encode("utf-8")).hexdigest()


def acquire_financial_report_lock(
    session: Session,
    instrument_id: uuid.UUID,
    report_type: str,
    report_scope: str,
    period: str,
    year: int,
    quarter: int | None = None,
) -> None:
    """Khóa an toàn đồng thời bằng PostgreSQL Transaction Advisory Lock.

    Khóa tự động được giải phóng khi transaction hiện tại commit hoặc rollback.
    Nếu đang chạy trên SQLite (môi trường kiểm thử in-memory), lệnh advisory lock sẽ được bỏ qua an toàn.
    """
    bind = session.get_bind()
    if bind is not None and bind.dialect.name == "postgresql":
        key_str = f"{instrument_id}:{report_type}:{report_scope}:{period}:{year}:{quarter or 0}"
        session.exec(select(func.pg_advisory_xact_lock(func.hashtext(key_str))))


def record_financial_report_revision(
    session: Session,
    report: FinancialReport,
    data: dict[str, Any],
    published_at: datetime | None = None,
    restated_reason: str | None = None,
) -> FinancialReportRevision:
    """Ghi nhận phiên bản mới của Báo cáo tài chính hoặc giữ nguyên nếu nội dung không đổi.

    - Nếu nội dung data sinh ra hash trùng với bản revision mới nhất -> Không nhân bản.
    - Nếu có thay đổi số liệu -> Tạo revision kế tiếp (revision_number += 1).
    - Nếu published_at is None -> Đánh dấu is_provisional = True (chống look-ahead bias).
    """
    payload_hash = canonical_payload_hash(data)

    latest_rev = session.exec(
        select(FinancialReportRevision)
        .where(FinancialReportRevision.report_id == report.id)
        .order_by(col(FinancialReportRevision.revision_number).desc())
    ).first()

    if latest_rev and latest_rev.payload_hash == payload_hash:
        # Dữ liệu không thay đổi so với bản trước đó
        return latest_rev

    next_rev_num = (latest_rev.revision_number + 1) if latest_rev else 1
    is_provisional = published_at is None

    revision = FinancialReportRevision(
        report_id=report.id,
        revision_number=next_rev_num,
        payload_hash=payload_hash,
        published_at=published_at,
        is_provisional=is_provisional,
        restated_reason=restated_reason,
        data=data,
        created_at=datetime.now(VN_TZ),
    )
    session.add(revision)
    session.flush()
    return revision


def get_as_of_financial_report_revision(
    session: Session,
    instrument_id: uuid.UUID,
    report_type: str,
    period: str,
    year: int,
    as_of_date: datetime,
    report_scope: str = "consolidated",
    quarter: int | None = None,
) -> FinancialReportRevision | None:
    """Truy vấn bản sửa đổi BCTC có hiệu lực tại một thời điểm quá khứ (Point-in-Time Query).

    Quy tắc chống Look-Ahead Bias:
    - Chỉ lấy bản ghi có published_at xác thực <= as_of_date.
    - Tuyệt đối loại bỏ các bản ghi is_provisional = True (dữ liệu chưa rõ thời điểm công bố).
    - Lấy bản revision mới nhất được công bố tính đến thời điểm as_of_date.
    """
    query = (
        select(FinancialReportRevision)
        .join(
            FinancialReport,
            col(FinancialReport.id) == col(FinancialReportRevision.report_id),
        )
        .where(col(FinancialReport.instrument_id) == instrument_id)
        .where(col(FinancialReport.report_type) == report_type)
        .where(col(FinancialReport.report_scope) == report_scope)
        .where(col(FinancialReport.period) == period)
        .where(col(FinancialReport.year) == year)
        .where(col(FinancialReport.quarter) == quarter)
        .where(col(FinancialReportRevision.is_provisional).is_(False))
        .where(col(FinancialReportRevision.published_at).is_not(None))
        .where(col(FinancialReportRevision.published_at) <= as_of_date)
        .order_by(col(FinancialReportRevision.revision_number).desc())
    )
    return session.exec(query).first()
