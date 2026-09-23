"""Screener Presentation Router."""

import uuid
from datetime import date
from typing import Any

from fastapi import APIRouter, Query
from sqlmodel import col, func, select

from app.api.deps import CurrentUser, SessionDep
from app.domains.fundamental.application.schemas import (
    ScreenerCursor,
    ScreenerResultItem,
    StockScreenerResponse,
)
from app.domains.fundamental.application.screener_service import ScreenerService
from app.domains.fundamental.domain.models import FinancialRatio, ScreenerSnapshot
from app.domains.market_data.domain.models import StockSymbol

router = APIRouter(prefix="/stock", tags=["screener"])


@router.get("/screener", response_model=StockScreenerResponse)
def screen_stocks(
    session: SessionDep,
    current_user: CurrentUser,  # noqa: ARG001
    min_pe: float | None = Query(default=None, description="P/E tối thiểu"),
    max_pe: float | None = Query(default=None, description="P/E tối đa"),
    min_pb: float | None = Query(default=None, description="P/B tối thiểu"),
    max_pb: float | None = Query(default=None, description="P/B tối đa"),
    min_roe: float | None = Query(default=None, description="ROE (%) tối thiểu"),
    max_roe: float | None = Query(default=None, description="ROE (%) tối đa"),
    min_roa: float | None = Query(default=None, description="ROA (%) tối thiểu"),
    max_debt_to_equity: float | None = Query(
        default=None, description="Tỷ lệ Nợ/Vốn CSH tối đa"
    ),
    min_revenue_growth_yoy: float | None = Query(
        default=None, description="Tăng trưởng doanh thu YoY (%) tối thiểu"
    ),
    min_net_profit_growth_yoy: float | None = Query(
        default=None, description="Tăng trưởng LNST YoY (%) tối thiểu"
    ),
    min_ev_to_ebitda: float | None = Query(
        default=None, description="EV/EBITDA tối thiểu"
    ),
    max_ev_to_ebitda: float | None = Query(
        default=None, description="EV/EBITDA tối đa"
    ),
    exchange: str | None = Query(
        default=None, description="Sàn niêm yết (HOSE, HNX, UPCOM)"
    ),
    industry: str | None = Query(default=None, description="Ngành"),
    period: str = Query(default="quarter", description="quarter hoặc year"),
    year: int | None = Query(default=None, description="Năm tài chính"),
    quarter: int | None = Query(default=None, description="Quý tài chính (1-4)"),
    skip: int = 0,
    limit: int = 50,
    cursor_roe: float | None = Query(
        default=None, description="Con trỏ ROE cho Keyset Pagination"
    ),
    cursor_instrument_id: uuid.UUID | None = Query(
        default=None, description="Con trỏ Instrument ID cho Keyset Pagination"
    ),
) -> Any:
    """Bộ lọc cổ phiếu định lượng tối ưu SLA P95 < 10ms qua Keyset Pagination & ScreenerSnapshot."""
    # 1. Ưu tiên sử dụng ScreenerService với bảng pre-computed ScreenerSnapshot (Keyset Pagination)
    clean_cursor_id = (
        cursor_instrument_id if isinstance(cursor_instrument_id, uuid.UUID) else None
    )
    clean_cursor_roe = (
        float(cursor_roe) if isinstance(cursor_roe, (int, float)) else None
    )
    cursor = None
    if clean_cursor_id is not None:
        cursor = ScreenerCursor(roe=clean_cursor_roe, instrument_id=clean_cursor_id)

    # Kiểm tra sự tồn tại của snapshot trong cơ sở dữ liệu
    has_snapshots = False
    try:
        has_snapshots = (
            session.exec(select(func.count()).select_from(ScreenerSnapshot)).one() > 0
        )
    except Exception:
        has_snapshots = False

    clean_limit = limit if isinstance(limit, int) else 50
    clean_exchange = exchange if isinstance(exchange, str) else None
    clean_industry = industry if isinstance(industry, str) else None
    clean_min_pe = float(min_pe) if isinstance(min_pe, (int, float)) else None
    clean_max_pe = float(max_pe) if isinstance(max_pe, (int, float)) else None
    clean_min_pb = float(min_pb) if isinstance(min_pb, (int, float)) else None
    clean_max_pb = float(max_pb) if isinstance(max_pb, (int, float)) else None
    clean_min_roe = float(min_roe) if isinstance(min_roe, (int, float)) else None
    clean_max_roe = float(max_roe) if isinstance(max_roe, (int, float)) else None
    clean_min_roa = float(min_roa) if isinstance(min_roa, (int, float)) else None
    clean_max_debt_to_equity = (
        float(max_debt_to_equity)
        if isinstance(max_debt_to_equity, (int, float))
        else None
    )
    clean_min_revenue_growth_yoy = (
        float(min_revenue_growth_yoy)
        if isinstance(min_revenue_growth_yoy, (int, float))
        else None
    )
    clean_min_net_profit_growth_yoy = (
        float(min_net_profit_growth_yoy)
        if isinstance(min_net_profit_growth_yoy, (int, float))
        else None
    )
    clean_min_ev_to_ebitda = (
        float(min_ev_to_ebitda) if isinstance(min_ev_to_ebitda, (int, float)) else None
    )
    clean_max_ev_to_ebitda = (
        float(max_ev_to_ebitda) if isinstance(max_ev_to_ebitda, (int, float)) else None
    )

    clean_year = year if isinstance(year, int) else date.today().year
    clean_quarter = quarter if isinstance(quarter, int) else None

    if has_snapshots or cursor is not None:
        screener_res = ScreenerService.query_screener_keyset(
            session=session,
            page_size=clean_limit,
            cursor=cursor,
            exchange=clean_exchange,
            industry=clean_industry,
            min_pe=clean_min_pe,
            max_pe=clean_max_pe,
            min_pb=clean_min_pb,
            max_pb=clean_max_pb,
            min_roe=clean_min_roe,
            max_roe=clean_max_roe,
            min_roa=clean_min_roa,
            max_debt_to_equity=clean_max_debt_to_equity,
            min_revenue_growth_yoy=clean_min_revenue_growth_yoy,
            min_net_profit_growth_yoy=clean_min_net_profit_growth_yoy,
            min_ev_to_ebitda=clean_min_ev_to_ebitda,
            max_ev_to_ebitda=clean_max_ev_to_ebitda,
        )
        if screener_res.items or cursor is not None:
            items = [
                ScreenerResultItem(
                    symbol=item.symbol,
                    organ_name=item.symbol,
                    exchange=item.exchange,
                    industry=item.industry,
                    fiscal_year=clean_year,
                    fiscal_quarter=clean_quarter,
                    pe=float(item.pe) if item.pe is not None else None,
                    pb=float(item.pb) if item.pb is not None else None,
                    roe=float(item.roe) if item.roe is not None else None,
                    roa=float(item.roa) if item.roa is not None else None,
                    debt_to_equity=(
                        float(item.debt_to_equity)
                        if item.debt_to_equity is not None
                        else None
                    ),
                    ev_to_ebitda=(
                        float(item.ev_to_ebitda)
                        if item.ev_to_ebitda is not None
                        else None
                    ),
                    net_profit_margin=(
                        float(item.net_margin) if item.net_margin is not None else None
                    ),
                    revenue_growth_yoy=(
                        float(item.revenue_growth_yoy)
                        if item.revenue_growth_yoy is not None
                        else None
                    ),
                    net_profit_growth_yoy=(
                        float(item.profit_growth_yoy)
                        if item.profit_growth_yoy is not None
                        else None
                    ),
                )
                for item in screener_res.items
            ]
            next_roe = (
                screener_res.next_cursor.roe if screener_res.next_cursor else None
            )
            next_inst_id = (
                screener_res.next_cursor.instrument_id
                if screener_res.next_cursor
                else None
            )
            return StockScreenerResponse(
                count=len(items),
                data=items,
                has_next=screener_res.has_next,
                next_cursor_roe=next_roe,
                next_cursor_instrument_id=next_inst_id,
            )

    # 2. Fallback sang logic truy vấn cũ nếu hệ thống chưa tạo pre-computed snapshot
    target_year = year
    target_quarter = quarter
    if target_year is None:
        latest_period = session.exec(
            select(FinancialRatio.year, FinancialRatio.quarter)
            .where(FinancialRatio.period == period)
            .order_by(
                col(FinancialRatio.year).desc(), col(FinancialRatio.quarter).desc()
            )
            .limit(1)
        ).first()
        if latest_period:
            target_year, target_quarter = latest_period[0], latest_period[1]

    query = (
        select(FinancialRatio, StockSymbol)
        .join(StockSymbol, col(FinancialRatio.symbol) == col(StockSymbol.symbol))
        .where(col(FinancialRatio.period) == period)
    )

    if target_year is not None:
        query = query.where(col(FinancialRatio.year) == target_year)
    if target_quarter is not None and period == "quarter":
        query = query.where(col(FinancialRatio.quarter) == target_quarter)

    if min_pe is not None:
        query = query.where(col(FinancialRatio.pe) >= min_pe)
    if max_pe is not None:
        query = query.where(col(FinancialRatio.pe) <= max_pe)
    if min_pb is not None:
        query = query.where(col(FinancialRatio.pb) >= min_pb)
    if max_pb is not None:
        query = query.where(col(FinancialRatio.pb) <= max_pb)
    if min_roe is not None:
        query = query.where(col(FinancialRatio.roe) >= min_roe)
    if max_roe is not None:
        query = query.where(col(FinancialRatio.roe) <= max_roe)
    if min_roa is not None:
        query = query.where(col(FinancialRatio.roa) >= min_roa)
    if max_debt_to_equity is not None:
        query = query.where(col(FinancialRatio.debt_to_equity) <= max_debt_to_equity)
    if min_revenue_growth_yoy is not None:
        query = query.where(
            col(FinancialRatio.revenue_growth_yoy) >= min_revenue_growth_yoy
        )
    if min_net_profit_growth_yoy is not None:
        query = query.where(
            col(FinancialRatio.net_profit_growth_yoy) >= min_net_profit_growth_yoy
        )
    if min_ev_to_ebitda is not None:
        query = query.where(col(FinancialRatio.ev_to_ebitda) >= min_ev_to_ebitda)
    if max_ev_to_ebitda is not None:
        query = query.where(col(FinancialRatio.ev_to_ebitda) <= max_ev_to_ebitda)

    if exchange:
        query = query.where(col(StockSymbol.exchange) == exchange.strip().upper())
    if industry:
        query = query.where(col(StockSymbol.industry) == industry.strip())

    # Tối ưu hóa truy vấn với Index B-Tree
    query = (
        query.order_by(col(FinancialRatio.roe).desc().nullslast())
        .offset(skip)
        .limit(limit)
    )
    records = session.exec(query).all()

    fallback_items = [
        ScreenerResultItem(
            symbol=sym.symbol,
            organ_name=sym.organ_name,
            exchange=sym.exchange,
            industry=sym.industry,
            fiscal_year=ratio.year,
            fiscal_quarter=ratio.quarter,
            pe=ratio.pe,
            pb=ratio.pb,
            roe=ratio.roe,
            roa=ratio.roa,
            debt_to_equity=ratio.debt_to_equity,
            ev_to_ebitda=ratio.ev_to_ebitda,
            net_profit_margin=ratio.net_margin,
            revenue_growth_yoy=ratio.revenue_growth_yoy,
            net_profit_growth_yoy=ratio.net_profit_growth_yoy,
        )
        for ratio, sym in records
    ]

    return StockScreenerResponse(count=len(fallback_items), data=fallback_items)
