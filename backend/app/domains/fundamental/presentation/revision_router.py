"""Financial Report Revision & Point-in-Time Presentation Router."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import col, select

from app.api.deps import CurrentUser, SessionDep
from app.domains.fundamental.application.revision_service import (
    get_as_of_financial_report_revision,
)
from app.domains.fundamental.application.schemas import (
    FinancialReportRevisionPublic,
    FinancialReportRevisionsResponse,
)
from app.domains.fundamental.domain.models import (
    FinancialReport,
    FinancialReportRevision,
)

router = APIRouter(prefix="/stock", tags=["revisions"])


@router.get(
    "/{symbol}/financials/revisions",
    response_model=FinancialReportRevisionsResponse,
)
def get_financial_report_revisions(
    session: SessionDep,
    current_user: CurrentUser,  # noqa: ARG001
    symbol: str,
    report_type: str = Query(default="income_statement"),
    report_scope: str = Query(default="consolidated"),
    period: str = Query(default="quarter"),
    year: int = Query(...),
    quarter: int | None = Query(default=None),
) -> Any:
    """Tra cứu lịch sử sửa đổi / bổ sung của một kỳ Báo cáo tài chính."""
    sym = symbol.strip().upper()
    report = session.exec(
        select(FinancialReport)
        .where(FinancialReport.symbol == sym)
        .where(FinancialReport.report_type == report_type)
        .where(FinancialReport.report_scope == report_scope)
        .where(FinancialReport.period == period)
        .where(FinancialReport.year == year)
        .where(FinancialReport.quarter == quarter)
    ).first()

    if not report:
        raise HTTPException(
            status_code=404,
            detail=f"Financial report not found for {sym} {period} {year} Q{quarter or 0}",
        )

    revisions = list(
        session.exec(
            select(FinancialReportRevision)
            .where(FinancialReportRevision.report_id == report.id)
            .order_by(col(FinancialReportRevision.revision_number).desc())
        ).all()
    )

    data = [
        FinancialReportRevisionPublic(
            id=rev.id,
            report_id=rev.report_id,
            revision_number=rev.revision_number,
            payload_hash=rev.payload_hash,
            published_at=rev.published_at,
            is_provisional=rev.is_provisional,
            restated_reason=rev.restated_reason,
            data=rev.data,
            created_at=rev.created_at,
        )
        for rev in revisions
    ]
    return FinancialReportRevisionsResponse(
        symbol=sym,
        report_id=report.id,
        count=len(data),
        revisions=data,
    )


@router.get(
    "/{symbol}/financials/as-of",
    response_model=FinancialReportRevisionPublic,
)
def get_point_in_time_financial_report(
    session: SessionDep,
    current_user: CurrentUser,  # noqa: ARG001
    symbol: str,
    as_of: datetime = Query(
        ...,
        description="Mốc thời gian Point-in-Time (ISO format) loại trừ Look-ahead bias",
    ),
    report_type: str = Query(default="income_statement"),
    report_scope: str = Query(default="consolidated"),
    period: str = Query(default="quarter"),
    year: int = Query(...),
    quarter: int | None = Query(default=None),
    allow_provisional: bool = Query(default=True),
) -> Any:
    """Truy vấn BCTC có hiệu lực tại mốc thời gian quá khứ (Point-in-Time) chống rò rỉ dữ liệu tương lai."""
    sym = symbol.strip().upper()
    report = session.exec(
        select(FinancialReport)
        .where(FinancialReport.symbol == sym)
        .where(FinancialReport.report_type == report_type)
        .where(FinancialReport.report_scope == report_scope)
        .where(FinancialReport.period == period)
        .where(FinancialReport.year == year)
        .where(FinancialReport.quarter == quarter)
    ).first()

    if not report:
        raise HTTPException(
            status_code=404,
            detail=f"Financial report not found for {sym} {period} {year} Q{quarter or 0}",
        )

    if not report.instrument_id:
        raise HTTPException(
            status_code=400,
            detail=f"Report for {sym} does not have an associated instrument_id for Point-in-Time lookup",
        )

    rev = get_as_of_financial_report_revision(
        session=session,
        instrument_id=report.instrument_id,
        report_type=report_type,
        period=period,
        year=year,
        quarter=quarter,
        report_scope=report_scope,
        as_of_date=as_of,
        allow_provisional_if_ingested=allow_provisional,
    )

    if not rev:
        raise HTTPException(
            status_code=404,
            detail=f"No valid revision found as of {as_of.isoformat()} for {sym} {period} {year}",
        )

    return FinancialReportRevisionPublic(
        id=rev.id,
        report_id=rev.report_id,
        revision_number=rev.revision_number,
        payload_hash=rev.payload_hash,
        published_at=rev.published_at,
        is_provisional=rev.is_provisional,
        restated_reason=rev.restated_reason,
        data=rev.data,
        created_at=rev.created_at,
    )
