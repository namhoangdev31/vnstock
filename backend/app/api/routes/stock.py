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
from app.cron.sync_daily_market import run_sync_daily_market_job
from app.cron.sync_quarterly_financials import run_sync_quarterly_financials_job
from app.models.models_quant import (
    InstitutionalFlow,
    InstitutionalFlowPublic,
    MacroIndicator,
    MacroIndicatorPublic,
    MacroLatestResponse,
    SymbolGroupResponse,
)
from app.models.models_stock import (
    BondSpecification,
    BondSpecificationPublic,
    CapitalHistory,
    CapitalHistoryPublic,
    CapitalHistoryResponse,
    CompanyOfficer,
    CompanyOfficerPublic,
    CompanyOfficersResponse,
    CompanyOverviewPublic,
    CompanyProfile,
    CompanyShareholder,
    CompanyShareholderPublic,
    CompanyShareholdersResponse,
    CompanySubsidiariesResponse,
    CompanySubsidiary,
    CompanySubsidiaryPublic,
    CorporateEvent,
    CorporateEventPublic,
    CorporateEventsResponse,
    CoveredWarrant,
    CoveredWarrantPublic,
    DataSyncLog,
    DerivativeContract,
    DerivativeContractPublic,
    FinancialRatio,
    FinancialRatioPublic,
    FinancialRatiosResponse,
    FinancialReport,
    FinancialReportPublic,
    FinancialReportsResponse,
    IndexConstituent,
    IndexConstituentPublic,
    IndexConstituentsResponse,
    InsiderTrading,
    InsiderTradingPublic,
    InsiderTradingResponse,
    OHLCVRecord,
    PriceHistoryResponse,
    RelatedAssetsResponse,
    ScreenerResultItem,
    StockOHLCVDaily,
    StockScreenerResponse,
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
# GET /stock/{symbol}/ratios — Financial valuation & performance ratios
# ---------------------------------------------------------------------------


@router.get("/{symbol}/ratios", response_model=FinancialRatiosResponse)
def get_financial_ratios(
    session: SessionDep,
    current_user: CurrentUser,  # noqa: ARG001
    symbol: str,
    period: str = Query(default="quarter", description="quarter or year"),
) -> Any:
    """Tra cứu chỉ số tài chính (P/E, P/B, ROE, ROA, EPS, BVPS...) từ PostgreSQL."""
    sym_code = symbol.strip().upper()
    ratios = session.exec(
        select(FinancialRatio)
        .where(FinancialRatio.symbol == sym_code)
        .where(FinancialRatio.period == period)
        .order_by(col(FinancialRatio.year).desc(), col(FinancialRatio.quarter).desc())
    ).all()

    if not ratios:
        try:
            manager = DataSyncManager(session, vnstock_service)
            log = manager.sync_financial_ratios(sym_code, period=period)
            if log.status == "success":
                ratios = session.exec(
                    select(FinancialRatio)
                    .where(FinancialRatio.symbol == sym_code)
                    .where(FinancialRatio.period == period)
                    .order_by(
                        col(FinancialRatio.year).desc(),
                        col(FinancialRatio.quarter).desc(),
                    )
                ).all()
        except VnstockServiceError:
            pass

    data = [FinancialRatioPublic.model_validate(r) for r in ratios]
    return FinancialRatiosResponse(symbol=sym_code, count=len(data), data=data)


# ---------------------------------------------------------------------------
# GET /stock/screener — Quantitative & financial ratio screener
# ---------------------------------------------------------------------------


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
) -> Any:
    """Bộ lọc cổ phiếu định lượng dựa trên các trường chỉ số tài chính đã được đánh chỉ mục B-Tree."""
    # Nếu không cung cấp năm, tìm kỳ báo cáo mới nhất trong cơ sở dữ liệu
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

    items = [
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

    return StockScreenerResponse(count=len(items), data=items)


# ---------------------------------------------------------------------------
# GET /stock/{symbol}/shareholders — Major shareholders & ownership structure
# ---------------------------------------------------------------------------


@router.get("/{symbol}/shareholders", response_model=CompanyShareholdersResponse)
def get_shareholders(
    session: SessionDep,
    current_user: CurrentUser,  # noqa: ARG001
    symbol: str,
) -> Any:
    """Tra cứu cơ cấu cổ đông lớn và nội bộ từ PostgreSQL."""
    sym_code = symbol.strip().upper()
    shareholders = session.exec(
        select(CompanyShareholder)
        .where(CompanyShareholder.symbol == sym_code)
        .order_by(col(CompanyShareholder.ownership_pct).desc())
    ).all()

    if not shareholders:
        try:
            manager = DataSyncManager(session, vnstock_service)
            log = manager.sync_company_shareholders(sym_code)
            if log.status == "success":
                shareholders = session.exec(
                    select(CompanyShareholder)
                    .where(CompanyShareholder.symbol == sym_code)
                    .order_by(col(CompanyShareholder.ownership_pct).desc())
                ).all()
        except VnstockServiceError:
            pass

    data = [CompanyShareholderPublic.model_validate(s) for s in shareholders]
    return CompanyShareholdersResponse(symbol=sym_code, count=len(data), data=data)


# ---------------------------------------------------------------------------
# GET /stock/{symbol}/officers — Corporate governance & officers
# ---------------------------------------------------------------------------


@router.get("/{symbol}/officers", response_model=CompanyOfficersResponse)
def get_officers(
    session: SessionDep,
    current_user: CurrentUser,  # noqa: ARG001
    symbol: str,
) -> Any:
    """Tra cứu danh sách ban điều hành và Hội đồng quản trị từ PostgreSQL."""
    sym_code = symbol.strip().upper()
    officers = session.exec(
        select(CompanyOfficer)
        .where(CompanyOfficer.symbol == sym_code)
        .order_by(col(CompanyOfficer.officer_name).asc())
    ).all()

    if not officers:
        try:
            manager = DataSyncManager(session, vnstock_service)
            log = manager.sync_company_officers(sym_code)
            if log.status == "success":
                officers = session.exec(
                    select(CompanyOfficer)
                    .where(CompanyOfficer.symbol == sym_code)
                    .order_by(col(CompanyOfficer.officer_name).asc())
                ).all()
        except VnstockServiceError:
            pass

    data = [CompanyOfficerPublic.model_validate(o) for o in officers]
    return CompanyOfficersResponse(symbol=sym_code, count=len(data), data=data)


# ---------------------------------------------------------------------------
# GET /stock/{symbol}/events — Corporate events & dividends
# ---------------------------------------------------------------------------


@router.get("/{symbol}/events", response_model=CorporateEventsResponse)
def get_corporate_events(
    session: SessionDep,
    current_user: CurrentUser,  # noqa: ARG001
    symbol: str,
) -> Any:
    """Tra cứu lịch sự kiện doanh nghiệp và chi trả cổ tức từ PostgreSQL."""
    sym_code = symbol.strip().upper()
    events = session.exec(
        select(CorporateEvent)
        .where(CorporateEvent.symbol == sym_code)
        .order_by(col(CorporateEvent.ex_date).desc().nullslast())
    ).all()

    if not events:
        try:
            manager = DataSyncManager(session, vnstock_service)
            log = manager.sync_corporate_events(sym_code)
            if log.status == "success":
                events = session.exec(
                    select(CorporateEvent)
                    .where(CorporateEvent.symbol == sym_code)
                    .order_by(col(CorporateEvent.ex_date).desc().nullslast())
                ).all()
        except VnstockServiceError:
            pass

    data = [CorporateEventPublic.model_validate(e) for e in events]
    return CorporateEventsResponse(symbol=sym_code, count=len(data), data=data)


# ---------------------------------------------------------------------------
# GET /stock/{symbol}/subsidiaries — Company subsidiaries & affiliates
# ---------------------------------------------------------------------------


@router.get("/{symbol}/subsidiaries", response_model=CompanySubsidiariesResponse)
def get_company_subsidiaries(
    session: SessionDep,
    current_user: CurrentUser,  # noqa: ARG001
    symbol: str,
) -> Any:
    """Tra cứu danh sách công ty con và công ty liên kết từ PostgreSQL."""
    sym_code = symbol.strip().upper()
    subsidiaries = session.exec(
        select(CompanySubsidiary)
        .where(CompanySubsidiary.symbol == sym_code)
        .order_by(col(CompanySubsidiary.ownership_percent).desc().nullslast())
    ).all()

    if not subsidiaries:
        try:
            manager = DataSyncManager(session, vnstock_service)
            log = manager.sync_company_subsidiaries(sym_code)
            if log.status == "success":
                subsidiaries = session.exec(
                    select(CompanySubsidiary)
                    .where(CompanySubsidiary.symbol == sym_code)
                    .order_by(
                        col(CompanySubsidiary.ownership_percent).desc().nullslast()
                    )
                ).all()
        except VnstockServiceError:
            pass

    data = [CompanySubsidiaryPublic.model_validate(s) for s in subsidiaries]
    return CompanySubsidiariesResponse(symbol=sym_code, count=len(data), data=data)


# ---------------------------------------------------------------------------
# GET /stock/{symbol}/insider-trading — Insider trading and major deals
# ---------------------------------------------------------------------------


@router.get("/{symbol}/insider-trading", response_model=InsiderTradingResponse)
def get_insider_trading(
    session: SessionDep,
    current_user: CurrentUser,  # noqa: ARG001
    symbol: str,
    limit: int = Query(default=50, ge=1, le=200),
) -> Any:
    """Tra cứu lịch sử giao dịch nội bộ và cổ đông lớn từ PostgreSQL."""
    sym_code = symbol.strip().upper()
    deals = session.exec(
        select(InsiderTrading)
        .where(InsiderTrading.symbol == sym_code)
        .order_by(col(InsiderTrading.deal_announce_date).desc().nullslast())
        .limit(limit)
    ).all()

    if not deals:
        try:
            manager = DataSyncManager(session, vnstock_service)
            log = manager.sync_insider_trading(sym_code)
            if log.status == "success":
                deals = session.exec(
                    select(InsiderTrading)
                    .where(InsiderTrading.symbol == sym_code)
                    .order_by(col(InsiderTrading.deal_announce_date).desc().nullslast())
                    .limit(limit)
                ).all()
        except VnstockServiceError:
            pass

    data = [InsiderTradingPublic.model_validate(d) for d in deals]
    return InsiderTradingResponse(symbol=sym_code, count=len(data), data=data)


# ---------------------------------------------------------------------------
# GET /stock/{symbol}/capital-history — Capital change history
# ---------------------------------------------------------------------------


@router.get("/{symbol}/capital-history", response_model=CapitalHistoryResponse)
def get_capital_history(
    session: SessionDep,
    current_user: CurrentUser,  # noqa: ARG001
    symbol: str,
) -> Any:
    """Tra cứu lịch sử tăng vốn điều lệ và phát hành cổ phiếu từ PostgreSQL."""
    sym_code = symbol.strip().upper()
    history = session.exec(
        select(CapitalHistory)
        .where(CapitalHistory.symbol == sym_code)
        .order_by(col(CapitalHistory.issue_date).desc().nullslast())
    ).all()

    if not history:
        try:
            manager = DataSyncManager(session, vnstock_service)
            log = manager.sync_capital_history(sym_code)
            if log.status == "success":
                history = session.exec(
                    select(CapitalHistory)
                    .where(CapitalHistory.symbol == sym_code)
                    .order_by(col(CapitalHistory.issue_date).desc().nullslast())
                ).all()
        except VnstockServiceError:
            pass

    data = [CapitalHistoryPublic.model_validate(h) for h in history]
    return CapitalHistoryResponse(symbol=sym_code, count=len(data), data=data)


# ---------------------------------------------------------------------------
# GET /stock/index-constituents/{group} — Index basket constituents DB-First
# ---------------------------------------------------------------------------


@router.get("/index-constituents/{group}", response_model=IndexConstituentsResponse)
def get_index_constituents(
    session: SessionDep,
    current_user: CurrentUser,  # noqa: ARG001
    group: str,
) -> Any:
    """Tra cứu thành phần và tỷ trọng rổ chỉ số (VN30, VN100, VNFINLEAD) từ PostgreSQL."""
    grp_code = group.strip().upper()
    rows = session.exec(
        select(IndexConstituent)
        .where(IndexConstituent.index_code == grp_code)
        .order_by(col(IndexConstituent.symbol).asc())
    ).all()

    if not rows:
        try:
            manager = DataSyncManager(session, vnstock_service)
            log = manager.sync_index_constituents(group=grp_code)
            if log.status == "success":
                rows = session.exec(
                    select(IndexConstituent)
                    .where(IndexConstituent.index_code == grp_code)
                    .order_by(col(IndexConstituent.symbol).asc())
                ).all()
        except VnstockServiceError:
            pass

    data = [IndexConstituentPublic.model_validate(r) for r in rows]
    return IndexConstituentsResponse(index_code=grp_code, count=len(data), data=data)


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
    elif sync_type == "ratios":
        if not symbol:
            raise HTTPException(
                status_code=400, detail="symbol is required for ratios sync"
            )
        clean_period = "quarter" if "quarter" in period else "year"
        log = manager.sync_financial_ratios(symbol, period=clean_period)
    elif sync_type == "shareholders":
        if not symbol:
            raise HTTPException(
                status_code=400, detail="symbol is required for shareholders sync"
            )
        log = manager.sync_company_shareholders(symbol)
    elif sync_type == "officers":
        if not symbol:
            raise HTTPException(
                status_code=400, detail="symbol is required for officers sync"
            )
        log = manager.sync_company_officers(symbol)
    elif sync_type == "events":
        if not symbol:
            raise HTTPException(
                status_code=400, detail="symbol is required for events sync"
            )
        log = manager.sync_corporate_events(symbol)
    elif sync_type == "subsidiaries":
        if not symbol:
            raise HTTPException(
                status_code=400, detail="symbol is required for subsidiaries sync"
            )
        log = manager.sync_company_subsidiaries(symbol)
    elif sync_type == "insider_trading":
        if not symbol:
            raise HTTPException(
                status_code=400, detail="symbol is required for insider_trading sync"
            )
        log = manager.sync_insider_trading(symbol)
    elif sync_type == "capital_history":
        if not symbol:
            raise HTTPException(
                status_code=400, detail="symbol is required for capital_history sync"
            )
        log = manager.sync_capital_history(symbol)
    elif sync_type == "constituents":
        target_group = symbol or "VN30"
        log = manager.sync_index_constituents(group=target_group)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown sync type: {sync_type}")

    return SyncStatusPublic.model_validate(log)


# ---------------------------------------------------------------------------
# POST /stock/sync/batch — Trigger batch sync across multiple symbols (SuperUser only)
# ---------------------------------------------------------------------------


@router.post("/sync/batch", response_model=dict[str, Any])
def trigger_batch_sync(
    session: SessionDep,
    current_user: CurrentUser,
    symbols: list[str] = Query(..., description="Danh sách mã cổ phiếu cần đồng bộ"),
    sync_types: list[str] = Query(
        default=[
            "profile",
            "financials",
            "ratios",
            "events",
            "subsidiaries",
            "insider_trading",
            "capital_history",
        ],
        description="Các loại dữ liệu cần đồng bộ",
    ),
    delay_sec: float = Query(
        default=0.3, ge=0.1, le=5.0, description="Độ trễ giữa các mã (giây)"
    ),
) -> Any:
    """Trigger bulk synchronization for multiple symbols (SuperUser only)."""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough privileges")

    manager = DataSyncManager(session, vnstock_service)
    return manager.sync_batch_symbols_data(
        symbols=symbols, sync_types=sync_types, delay_sec=delay_sec
    )


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
# POST /stock/cron/sync-daily-market — Automated Daily Market Sync Webhook
# ---------------------------------------------------------------------------


@router.post("/cron/sync-daily-market", response_model=list[SyncStatusPublic])
def cron_sync_daily_market(
    session: SessionDep,
    x_cron_secret: Annotated[str | None, Header(alias="X-Cron-Secret")] = None,
    secret_key: str | None = Query(default=None),
) -> Any:
    """Kích hoạt đồng bộ nến ngày cho các chỉ số và rổ VN30 sau phiên ATC (15:15).

    Yêu cầu header 'X-Cron-Secret' hoặc query param 'secret_key' khớp với cấu hình hệ thống.
    """
    valid_secret = settings.CRON_SECRET_KEY or settings.SECRET_KEY
    provided_secret = x_cron_secret or secret_key

    if not provided_secret or provided_secret != valid_secret:
        raise HTTPException(
            status_code=403,
            detail="Mã bảo mật Cron (X-Cron-Secret) không hợp lệ",
        )

    logs = run_sync_daily_market_job(session=session)
    return [SyncStatusPublic.model_validate(log) for log in logs]


# ---------------------------------------------------------------------------
# POST /stock/cron/sync-quarterly-financials — Quarterly Financials Sync Webhook
# ---------------------------------------------------------------------------


@router.post("/cron/sync-quarterly-financials", response_model=list[SyncStatusPublic])
def cron_sync_quarterly_financials(
    session: SessionDep,
    x_cron_secret: Annotated[str | None, Header(alias="X-Cron-Secret")] = None,
    secret_key: str | None = Query(default=None),
    group: str = Query(
        default="VN30", description="Nhóm chỉ số cần đồng bộ (VN30, VN100,...)"
    ),
) -> Any:
    """Kích hoạt đồng bộ báo cáo tài chính & chỉ số quý cho rổ chỉ số (VN30 mặc định).

    Yêu cầu header 'X-Cron-Secret' hoặc query param 'secret_key' khớp với cấu hình hệ thống.
    """
    valid_secret = settings.CRON_SECRET_KEY or settings.SECRET_KEY
    provided_secret = x_cron_secret or secret_key

    if not provided_secret or provided_secret != valid_secret:
        raise HTTPException(
            status_code=403,
            detail="Mã bảo mật Cron (X-Cron-Secret) không hợp lệ",
        )

    logs = run_sync_quarterly_financials_job(session=session, group=group)
    return [SyncStatusPublic.model_validate(log) for log in logs]


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


# ---------------------------------------------------------------------------
# GET /stock/{symbol}/related-assets — Cross-asset relational network
# ---------------------------------------------------------------------------


@router.get("/{symbol}/related-assets", response_model=RelatedAssetsResponse)
def get_related_assets(
    session: SessionDep,
    current_user: CurrentUser,  # noqa: ARG001
    symbol: str,
) -> Any:
    """Truy xuất mạng lưới tài sản liên kết chéo của một mã chứng khoán (CP, CW, Trái phiếu, Phái sinh, Index)."""
    sym_code = symbol.strip().upper()
    sym = session.exec(
        select(StockSymbol).where(StockSymbol.symbol == sym_code)
    ).first()
    if not sym:
        raise HTTPException(
            status_code=404,
            detail=f"Không tìm thấy mã chứng khoán: {symbol}",
        )

    # 1. Profile (nếu có)
    profile_dto = None
    if sym.profile:
        profile_dto = CompanyOverviewPublic.model_validate(sym.profile)
    else:
        db_prof = session.get(CompanyProfile, sym_code)
        if db_prof:
            profile_dto = CompanyOverviewPublic.model_validate(db_prof)

    # 2. Covered Warrants có cơ sở là mã này
    cw_rows = session.exec(
        select(CoveredWarrant).where(CoveredWarrant.underlying_symbol == sym_code)
    ).all()
    cws_dto = [CoveredWarrantPublic.model_validate(w) for w in cw_rows]

    # 3. Trái phiếu do mã này phát hành
    bond_rows = session.exec(
        select(BondSpecification).where(BondSpecification.issuer_symbol == sym_code)
    ).all()
    bonds_dto = [BondSpecificationPublic.model_validate(b) for b in bond_rows]

    # 4. Hợp đồng phái sinh dựa trên chỉ số này (e.g. VN30)
    deriv_rows = session.exec(
        select(DerivativeContract).where(
            DerivativeContract.underlying_symbol == sym_code
        )
    ).all()
    derivs_dto = [DerivativeContractPublic.model_validate(d) for d in deriv_rows]

    # 5. Nếu bản thân mã là Chứng quyền -> truy xuất ngược về cổ phiếu cơ sở
    underlying_asset_dto = None
    if sym.asset_type == "covered_warrant":
        cw_spec = session.exec(
            select(CoveredWarrant).where(CoveredWarrant.symbol == sym_code)
        ).first()
        if cw_spec and cw_spec.underlying_symbol:
            underlying_sym = session.exec(
                select(StockSymbol).where(
                    StockSymbol.symbol == cw_spec.underlying_symbol
                )
            ).first()
            if underlying_sym:
                underlying_asset_dto = StockSymbolPublic.model_validate(underlying_sym)

    # 6. Nếu bản thân mã là Phái sinh -> truy xuất ngược về chỉ số cơ sở (VN30)
    elif sym.asset_type == "derivative":
        deriv_spec = session.exec(
            select(DerivativeContract).where(DerivativeContract.symbol == sym_code)
        ).first()
        if deriv_spec and deriv_spec.underlying_symbol:
            underlying_sym = session.exec(
                select(StockSymbol).where(
                    StockSymbol.symbol == deriv_spec.underlying_symbol
                )
            ).first()
            if underlying_sym:
                underlying_asset_dto = StockSymbolPublic.model_validate(underlying_sym)

    # 7. Nếu bản thân mã là Trái phiếu -> truy xuất ngược về tổ chức phát hành
    issuer_asset_dto = None
    if sym.asset_type in ("corporate_bond", "government_bond"):
        bond_spec = session.exec(
            select(BondSpecification).where(BondSpecification.symbol == sym_code)
        ).first()
        if bond_spec and bond_spec.issuer_symbol:
            issuer_sym = session.exec(
                select(StockSymbol).where(StockSymbol.symbol == bond_spec.issuer_symbol)
            ).first()
            if issuer_sym:
                issuer_asset_dto = StockSymbolPublic.model_validate(issuer_sym)

    return RelatedAssetsResponse(
        symbol=sym.symbol,
        asset_type=sym.asset_type,
        organ_name=sym.organ_name,
        exchange=sym.exchange,
        profile=profile_dto,
        covered_warrants=cws_dto,
        issued_bonds=bonds_dto,
        derivative_contracts=derivs_dto,
        underlying_asset=underlying_asset_dto,
        issuer_asset=issuer_asset_dto,
    )


# ---------------------------------------------------------------------------
# GET /stock/warrants — List covered warrants
# ---------------------------------------------------------------------------


@router.get("/warrants", response_model=list[CoveredWarrantPublic])
def list_covered_warrants(
    session: SessionDep,
    current_user: CurrentUser,  # noqa: ARG001
    underlying_symbol: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """Danh sách các chứng quyền có bảo đảm kèm bộ lọc theo mã cổ phiếu cơ sở."""
    query = select(CoveredWarrant).where(CoveredWarrant.is_active == True)  # noqa: E712
    if underlying_symbol:
        query = query.where(
            CoveredWarrant.underlying_symbol == underlying_symbol.strip().upper()
        )

    warrants = session.exec(
        query.order_by(CoveredWarrant.symbol).offset(skip).limit(limit)
    ).all()
    return [CoveredWarrantPublic.model_validate(w) for w in warrants]


# ---------------------------------------------------------------------------
# GET /stock/bonds — List bonds (corporate & government)
# ---------------------------------------------------------------------------


@router.get("/bonds", response_model=list[BondSpecificationPublic])
def list_bonds(
    session: SessionDep,
    current_user: CurrentUser,  # noqa: ARG001
    bond_type: str | None = None,
    issuer_symbol: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """Danh sách trái phiếu doanh nghiệp & trái phiếu chính phủ kèm bộ lọc."""
    query = select(BondSpecification).where(BondSpecification.is_active == True)  # noqa: E712
    if bond_type:
        query = query.where(BondSpecification.bond_type == bond_type.lower())
    if issuer_symbol:
        query = query.where(
            BondSpecification.issuer_symbol == issuer_symbol.strip().upper()
        )

    bonds = session.exec(
        query.order_by(BondSpecification.symbol).offset(skip).limit(limit)
    ).all()
    return [BondSpecificationPublic.model_validate(b) for b in bonds]
