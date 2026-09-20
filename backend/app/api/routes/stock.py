"""Stock API routes — JWT protected endpoints for stock data.

All endpoints require authentication (CurrentUser dependency).
Data is primarily served from PostgreSQL, with on-demand vnstock fetching
for missing data ranges.
"""

import uuid
from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Header, HTTPException, Query
from sqlmodel import and_, col, func, select

from app.api.deps import CurrentUser, SessionDep
from app.core.config import settings
from app.models.models_quant import (
    InstitutionalFlow,
    InstitutionalFlowPublic,
    MacroIndicator,
    MacroIndicatorPublic,
    MacroLatestResponse,
    SymbolGroupResponse,
)
from app.models.models_stock import (
    CompanyOverviewPublic,
    CompanyProfile,
    DataSyncLog,
    FinancialReport,
    FinancialReportPublic,
    FinancialReportsResponse,
    OHLCVRecord,
    PriceHistoryResponse,
    StockOHLCVDaily,
    StockSymbol,
    StockSymbolPublic,
    StockSymbolsPublic,
    SyncStatusPublic,
)
from app.services.cache import metadata_cache, realtime_cache
from app.services.data_sync import DataSyncManager
from app.services.vnstock_service import VnstockServiceError, vnstock_service

router = APIRouter(prefix="/stock", tags=["stock"])


# ---------------------------------------------------------------------------
# GET /stock/symbols — List all stock symbols
# ---------------------------------------------------------------------------


@router.get("/symbols", response_model=StockSymbolsPublic)
def list_symbols(
    session: SessionDep,
    current_user: CurrentUser,  # noqa: ARG001
    skip: int = 0,
    limit: int = 100,
    exchange: str | None = None,
    asset_type: str | None = None,
    search: str | None = None,
) -> Any:
    """List all stock symbols with optional filters."""
    query = select(StockSymbol).where(StockSymbol.is_active == True)  # noqa: E712

    if exchange:
        query = query.where(StockSymbol.exchange == exchange)
    if asset_type:
        query = query.where(StockSymbol.asset_type == asset_type)
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            (col(StockSymbol.symbol).ilike(search_pattern))
            | (col(StockSymbol.organ_name).ilike(search_pattern))
        )

    count_query = select(func.count()).select_from(query.subquery())
    count = session.exec(count_query).one()

    symbols = session.exec(
        query.order_by(StockSymbol.symbol).offset(skip).limit(limit)
    ).all()

    return StockSymbolsPublic(
        data=[StockSymbolPublic.model_validate(s) for s in symbols],
        count=count,
    )


# ---------------------------------------------------------------------------
# GET /stock/symbol/by-id/{symbol_id} — Get stock symbol by internal UUID
# ---------------------------------------------------------------------------


@router.get("/symbol/by-id/{symbol_id}", response_model=StockSymbolPublic)
def get_symbol_by_id(
    session: SessionDep,
    current_user: CurrentUser,  # noqa: ARG001
    symbol_id: uuid.UUID,
) -> Any:
    """Tra cứu thông tin mã chứng khoán theo UUID định danh nội bộ."""
    sym = session.exec(select(StockSymbol).where(StockSymbol.id == symbol_id)).first()
    if not sym:
        raise HTTPException(
            status_code=404,
            detail=f"Stock symbol not found for ID: {symbol_id}",
        )
    return StockSymbolPublic.model_validate(sym)


# ---------------------------------------------------------------------------
# GET /stock/{symbol}/price/daily — Historical daily OHLCV
# ---------------------------------------------------------------------------


@router.get("/{symbol}/price/daily", response_model=PriceHistoryResponse)
def get_daily_price(
    session: SessionDep,
    current_user: CurrentUser,  # noqa: ARG001
    symbol: str,
    start: date = Query(description="Start date (YYYY-MM-DD)"),
    end: date = Query(default_factory=date.today, description="End date"),
) -> Any:
    """Get historical daily price data from PostgreSQL.

    If data gaps are detected, attempts to fetch missing data from vnstock.
    """
    # Query from PostgreSQL first
    rows = session.exec(
        select(StockOHLCVDaily)
        .where(StockOHLCVDaily.symbol == symbol)
        .where(StockOHLCVDaily.trading_date >= start)
        .where(StockOHLCVDaily.trading_date <= end)
        .order_by(col(StockOHLCVDaily.trading_date))
    ).all()

    # If no data, try to backfill from vnstock
    if not rows:
        try:
            manager = DataSyncManager(session, vnstock_service)
            log = manager.backfill_daily(symbol, start, end)
            if log.status == "success" and log.rows_synced > 0:
                rows = session.exec(
                    select(StockOHLCVDaily)
                    .where(StockOHLCVDaily.symbol == symbol)
                    .where(StockOHLCVDaily.trading_date >= start)
                    .where(StockOHLCVDaily.trading_date <= end)
                    .order_by(col(StockOHLCVDaily.trading_date))
                ).all()
        except VnstockServiceError:
            raise HTTPException(
                status_code=503,
                detail=f"No data available for {symbol} and external source is unavailable",
            )

    data = [
        OHLCVRecord(
            trading_date=str(r.trading_date),
            open=r.open,
            high=r.high,
            low=r.low,
            close=r.close,
            volume=r.volume,
            value=r.value,
        )
        for r in rows
    ]

    return PriceHistoryResponse(
        symbol=symbol,
        interval="1D",
        count=len(data),
        data=data,
    )


# ---------------------------------------------------------------------------
# GET /stock/{symbol}/price/realtime — Realtime price (cached 3-5s)
# ---------------------------------------------------------------------------


@router.get("/{symbol}/price/realtime")
def get_realtime_price(
    current_user: CurrentUser,  # noqa: ARG001
    symbol: str,
) -> Any:
    """Get latest realtime price (cached 3-5 seconds)."""
    cache_key = f"realtime:{symbol}"
    cached = realtime_cache.get(cache_key)
    if cached:
        return cached

    try:
        df = vnstock_service.fetch_intraday(symbol, interval="1m", count_back=1)
        if df is not None and not df.empty:
            row = df.iloc[-1]
            result = {
                "symbol": symbol,
                "open": float(row.get("open", 0)),
                "high": float(row.get("high", 0)),
                "low": float(row.get("low", 0)),
                "close": float(row.get("close", 0)),
                "volume": int(row.get("volume", 0)),
                "time": str(row.get("time", row.get("date", ""))),
            }
            realtime_cache.set(cache_key, result)
            return result
    except VnstockServiceError:
        pass

    raise HTTPException(
        status_code=503,
        detail=f"Realtime data not available for {symbol}",
    )


# ---------------------------------------------------------------------------
# GET /stock/{symbol}/overview — Company overview
# ---------------------------------------------------------------------------


@router.get("/{symbol}/overview", response_model=CompanyOverviewPublic)
def get_company_overview(
    session: SessionDep,
    current_user: CurrentUser,  # noqa: ARG001
    symbol: str,
) -> Any:
    """Get company overview/profile from PostgreSQL."""
    profile = session.get(CompanyProfile, symbol)

    if not profile:
        # Try to sync from vnstock
        try:
            manager = DataSyncManager(session, vnstock_service)
            log = manager.sync_company_profile(symbol)
            if log.status == "success":
                profile = session.get(CompanyProfile, symbol)
        except VnstockServiceError:
            pass

    if not profile:
        raise HTTPException(
            status_code=404, detail=f"Company profile not found for {symbol}"
        )

    return CompanyOverviewPublic.model_validate(profile)


# ---------------------------------------------------------------------------
# GET /stock/{symbol}/financials — Financial reports
# ---------------------------------------------------------------------------


@router.get("/{symbol}/financials", response_model=FinancialReportsResponse)
def get_financials(
    session: SessionDep,
    current_user: CurrentUser,  # noqa: ARG001
    symbol: str,
    report_type: str = Query(
        default="income_statement",
        description="income_statement, balance_sheet, cash_flow",
    ),
    period: str = Query(default="quarterly", description="quarterly or annual"),
) -> Any:
    """Get financial reports from PostgreSQL."""
    reports = session.exec(
        select(FinancialReport)
        .where(FinancialReport.symbol == symbol)
        .where(FinancialReport.report_type == report_type)
        .where(FinancialReport.period == period)
        .order_by(col(FinancialReport.year).desc(), col(FinancialReport.quarter).desc())
    ).all()

    # If no data, try to sync
    if not reports:
        try:
            manager = DataSyncManager(session, vnstock_service)
            log = manager.sync_financials(
                symbol, report_type=report_type, period=period
            )
            if log.status == "success":
                reports = session.exec(
                    select(FinancialReport)
                    .where(FinancialReport.symbol == symbol)
                    .where(FinancialReport.report_type == report_type)
                    .where(FinancialReport.period == period)
                    .order_by(
                        col(FinancialReport.year).desc(),
                        col(FinancialReport.quarter).desc(),
                    )
                ).all()
        except VnstockServiceError:
            pass

    data = [
        FinancialReportPublic(
            report_type=r.report_type,
            period=r.period,
            year=r.year,
            quarter=r.quarter,
            data=r.data,
        )
        for r in reports
    ]

    return FinancialReportsResponse(symbol=symbol, count=len(data), data=data)


# ---------------------------------------------------------------------------
# POST /stock/sync/{sync_type} — Trigger manual sync (SuperUser only)
# ---------------------------------------------------------------------------


@router.post("/sync/{sync_type}", response_model=SyncStatusPublic)
def trigger_sync(
    session: SessionDep,
    current_user: CurrentUser,
    sync_type: str,
    symbol: str | None = Query(default=None),
    start: str | None = Query(default=None),
    end: str | None = Query(default=None),
    report_type: str = Query(default="income_statement"),
    period: str = Query(default="quarterly"),
) -> Any:
    """Trigger a manual data sync (SuperUser only)."""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough privileges")

    manager = DataSyncManager(session, vnstock_service)

    if sync_type == "symbols":
        log = manager.sync_symbols()
    elif sync_type == "daily":
        if not symbol:
            raise HTTPException(
                status_code=400, detail="symbol is required for daily sync"
            )
        start_date = date.fromisoformat(start) if start else date(2024, 1, 1)
        end_date = date.fromisoformat(end) if end else date.today()
        log = manager.backfill_daily(symbol, start_date, end_date)
    elif sync_type == "intraday":
        if not symbol:
            raise HTTPException(
                status_code=400, detail="symbol is required for intraday sync"
            )
        log = manager.collect_intraday(symbol)
    elif sync_type == "profile":
        if not symbol:
            raise HTTPException(
                status_code=400, detail="symbol is required for profile sync"
            )
        log = manager.sync_company_profile(symbol)
    elif sync_type == "financials":
        if not symbol:
            raise HTTPException(
                status_code=400, detail="symbol is required for financials sync"
            )
        log = manager.sync_financials(symbol, report_type=report_type, period=period)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown sync type: {sync_type}")

    return SyncStatusPublic.model_validate(log)


# ---------------------------------------------------------------------------
# POST /stock/cron/sync-symbols — Automated Cron Job Webhook
# ---------------------------------------------------------------------------


@router.post("/cron/sync-symbols", response_model=SyncStatusPublic)
def cron_sync_symbols(
    session: SessionDep,
    x_cron_secret: Annotated[str | None, Header(alias="X-Cron-Secret")] = None,
    secret_key: str | None = Query(default=None),
) -> Any:
    """Kích hoạt đồng bộ danh mục mã qua Cronjob (GitHub Actions hoặc Scheduled Webhook).

    Yêu cầu header 'X-Cron-Secret' hoặc query param 'secret_key' khớp với cấu hình hệ thống.
    """
    valid_secret = settings.CRON_SECRET_KEY or settings.SECRET_KEY
    provided_secret = x_cron_secret or secret_key

    if not provided_secret or provided_secret != valid_secret:
        raise HTTPException(
            status_code=403,
            detail="Mã bảo mật Cron (X-Cron-Secret) không hợp lệ",
        )

    manager = DataSyncManager(session, vnstock_service)
    log = manager.sync_symbols()
    return SyncStatusPublic.model_validate(log)


# ---------------------------------------------------------------------------
# GET /stock/sync/status — Recent sync logs
# ---------------------------------------------------------------------------


@router.get("/sync/status", response_model=list[SyncStatusPublic])
def get_sync_status(
    session: SessionDep,
    current_user: CurrentUser,
    last: int = Query(default=10, ge=1, le=100),
) -> Any:
    """Get recent data sync logs (SuperUser only)."""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough privileges")

    logs = session.exec(
        select(DataSyncLog).order_by(col(DataSyncLog.started_at).desc()).limit(last)
    ).all()

    return [SyncStatusPublic.model_validate(log) for log in logs]


# ---------------------------------------------------------------------------
# GET /stock/symbols/group/{group} — Index-basket constituents (e.g. VN30)
# ---------------------------------------------------------------------------


@router.get("/symbols/group/{group}", response_model=SymbolGroupResponse)
def get_symbol_group(
    current_user: CurrentUser,  # noqa: ARG001
    group: str,
) -> Any:
    """Get the constituent symbols of an index group (VN30, VNDIAMOND, ...).

    Served from vnstock with a 24h metadata cache (AGENTS §7.2).
    """
    cache_key = f"symbols_group:{group.upper()}"
    cached = metadata_cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        symbols = vnstock_service.fetch_group_symbols(group=group)
    except VnstockServiceError:
        raise HTTPException(
            status_code=503,
            detail=f"Symbol group {group} unavailable from all data sources",
        )

    result = SymbolGroupResponse(
        group=group.upper(), count=len(symbols), symbols=symbols
    )
    metadata_cache.set(cache_key, result)
    return result


# ---------------------------------------------------------------------------
# GET /stock/macro/latest — Latest gold & FX snapshot
# ---------------------------------------------------------------------------


@router.get("/macro/latest", response_model=MacroLatestResponse)
def get_macro_latest(
    session: SessionDep,
    current_user: CurrentUser,  # noqa: ARG001
) -> Any:
    """Latest macro indicator per code (USD/VND, SJC gold buy/sell).

    Returns the most recent persisted row for each indicator code. If no macro
    data exists yet, the response is empty — the gap is surfaced, never guessed
    (RULE 3).
    """
    subq = (
        select(
            MacroIndicator.indicator_code,
            func.max(MacroIndicator.recorded_date).label("max_date"),
        )
        .group_by(col(MacroIndicator.indicator_code))
        .subquery()
    )
    rows = session.exec(
        select(MacroIndicator)
        .join(
            subq,
            and_(
                col(MacroIndicator.indicator_code) == subq.c.indicator_code,
                col(MacroIndicator.recorded_date) == subq.c.max_date,
            ),
        )
        .order_by(col(MacroIndicator.indicator_code))
    ).all()

    data = [MacroIndicatorPublic.model_validate(r) for r in rows]
    as_of = max((r.recorded_date for r in rows), default=None)
    if as_of is None:
        raise HTTPException(status_code=404, detail="No macro data available yet")
    return MacroLatestResponse(as_of=as_of, data=data)


# ---------------------------------------------------------------------------
# GET /stock/institutional-flow — Foreign & proprietary flow (DB-backed)
# ---------------------------------------------------------------------------


@router.get("/institutional-flow", response_model=list[InstitutionalFlowPublic])
def get_institutional_flow(
    session: SessionDep,
    current_user: CurrentUser,  # noqa: ARG001
    trading_date: date | None = None,
    symbol: str | None = None,
    limit: int = Query(default=30, ge=1, le=200),
) -> Any:
    """Persisted institutional flow rows (foreign + proprietary desk).

    Schema-only in Phase 1: vnstock v4 exposes no proprietary-desk values, so
    this returns whatever a verified source has stored — possibly nothing. It
    never fabricates flow (RULE 3).
    """
    query = select(InstitutionalFlow)
    if trading_date is not None:
        query = query.where(InstitutionalFlow.trading_date == trading_date)
    if symbol is not None:
        query = query.where(InstitutionalFlow.symbol == symbol)
    rows = session.exec(
        query.order_by(col(InstitutionalFlow.trading_date).desc()).limit(limit)
    ).all()
    return [InstitutionalFlowPublic.model_validate(r) for r in rows]
