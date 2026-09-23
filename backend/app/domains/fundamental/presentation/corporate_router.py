"""Corporate Data & Financial Statements Presentation Router."""

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import CurrentUser, SessionDep
from app.domains.fundamental.application.corporate_service import CorporateService
from app.domains.fundamental.application.schemas import (
    CapitalHistoryPublic,
    CapitalHistoryResponse,
    CompanyOfficerPublic,
    CompanyOfficersResponse,
    CompanyOverviewPublic,
    CompanyShareholderPublic,
    CompanyShareholdersResponse,
    CompanySubsidiariesResponse,
    CompanySubsidiaryPublic,
    CorporateEventPublic,
    CorporateEventsResponse,
    FinancialRatioPublic,
    FinancialRatiosResponse,
    FinancialReportPublic,
    FinancialReportsResponse,
    InsiderTradingPublic,
    InsiderTradingResponse,
)

router = APIRouter(prefix="/stock", tags=["corporate"])


@router.get("/{symbol}/overview", response_model=CompanyOverviewPublic)
def get_company_overview(
    session: SessionDep,
    current_user: CurrentUser,  # noqa: ARG001
    symbol: str,
) -> Any:
    """Get company overview/profile from PostgreSQL with fallback auto-sync."""
    profile = CorporateService.get_company_profile(session, symbol)
    if not profile:
        raise HTTPException(
            status_code=404, detail=f"Company profile not found for {symbol}"
        )
    return CompanyOverviewPublic.model_validate(profile)


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
    """Get financial reports from PostgreSQL with fallback auto-sync."""
    reports = CorporateService.get_financial_reports(
        session, symbol, report_type=report_type, period=period
    )
    data = [
        FinancialReportPublic(
            report_type=r.report_type,
            report_scope=r.report_scope,
            period=r.period,
            year=r.year,
            quarter=r.quarter,
            is_audited=r.is_audited,
            revenue=r.revenue,
            gross_profit=r.gross_profit,
            operating_profit=r.operating_profit,
            net_profit_parent=r.net_profit_parent,
            total_assets=r.total_assets,
            short_term_assets=r.short_term_assets,
            cash_and_equivalents=r.cash_and_equivalents,
            total_liabilities=r.total_liabilities,
            short_term_debt=r.short_term_debt,
            long_term_debt=r.long_term_debt,
            owners_equity=r.owners_equity,
            operating_cash_flow=r.operating_cash_flow,
            investing_cash_flow=r.investing_cash_flow,
            financing_cash_flow=r.financing_cash_flow,
            data=r.data,
        )
        for r in reports
    ]
    return FinancialReportsResponse(
        symbol=symbol.strip().upper(), count=len(data), data=data
    )


@router.get("/{symbol}/ratios", response_model=FinancialRatiosResponse)
def get_financial_ratios(
    session: SessionDep,
    current_user: CurrentUser,  # noqa: ARG001
    symbol: str,
    period: str = Query(default="quarter", description="quarter or year"),
) -> Any:
    """Tra cứu chỉ số tài chính (P/E, P/B, ROE, ROA, EPS, BVPS...) từ PostgreSQL."""
    sym_code = symbol.strip().upper()
    ratios = CorporateService.get_financial_ratios(session, sym_code, period=period)
    data = [FinancialRatioPublic.model_validate(r) for r in ratios]
    return FinancialRatiosResponse(symbol=sym_code, count=len(data), data=data)


@router.get("/{symbol}/shareholders", response_model=CompanyShareholdersResponse)
def get_shareholders(
    session: SessionDep,
    current_user: CurrentUser,  # noqa: ARG001
    symbol: str,
) -> Any:
    """Tra cứu cơ cấu cổ đông lớn và nội bộ từ PostgreSQL."""
    sym_code = symbol.strip().upper()
    shareholders = CorporateService.get_shareholders(session, sym_code)
    data = [CompanyShareholderPublic.model_validate(s) for s in shareholders]
    return CompanyShareholdersResponse(symbol=sym_code, count=len(data), data=data)


@router.get("/{symbol}/officers", response_model=CompanyOfficersResponse)
def get_officers(
    session: SessionDep,
    current_user: CurrentUser,  # noqa: ARG001
    symbol: str,
) -> Any:
    """Tra cứu danh sách ban điều hành và Hội đồng quản trị từ PostgreSQL."""
    sym_code = symbol.strip().upper()
    officers = CorporateService.get_officers(session, sym_code)
    data = [CompanyOfficerPublic.model_validate(o) for o in officers]
    return CompanyOfficersResponse(symbol=sym_code, count=len(data), data=data)


@router.get("/{symbol}/events", response_model=CorporateEventsResponse)
def get_corporate_events(
    session: SessionDep,
    current_user: CurrentUser,  # noqa: ARG001
    symbol: str,
) -> Any:
    """Tra cứu sự kiện doanh nghiệp và lịch chi trả cổ tức từ PostgreSQL."""
    sym_code = symbol.strip().upper()
    events = CorporateService.get_corporate_events(session, sym_code)
    data = [CorporateEventPublic.model_validate(e) for e in events]
    return CorporateEventsResponse(symbol=sym_code, count=len(data), data=data)


@router.get("/{symbol}/subsidiaries", response_model=CompanySubsidiariesResponse)
def get_subsidiaries(
    session: SessionDep,
    current_user: CurrentUser,  # noqa: ARG001
    symbol: str,
) -> Any:
    """Tra cứu danh sách công ty con và công ty liên kết từ PostgreSQL."""
    sym_code = symbol.strip().upper()
    subsidiaries = CorporateService.get_subsidiaries(session, sym_code)
    data = [CompanySubsidiaryPublic.model_validate(s) for s in subsidiaries]
    return CompanySubsidiariesResponse(symbol=sym_code, count=len(data), data=data)


@router.get("/{symbol}/insider-trading", response_model=InsiderTradingResponse)
def get_insider_trading(
    session: SessionDep,
    current_user: CurrentUser,  # noqa: ARG001
    symbol: str,
) -> Any:
    """Tra cứu lịch sử giao dịch nội bộ từ PostgreSQL."""
    sym_code = symbol.strip().upper()
    trades = CorporateService.get_insider_trading(session, sym_code)
    data = [InsiderTradingPublic.model_validate(t) for t in trades]
    return InsiderTradingResponse(symbol=sym_code, count=len(data), data=data)


@router.get("/{symbol}/capital-history", response_model=CapitalHistoryResponse)
def get_capital_history(
    session: SessionDep,
    current_user: CurrentUser,  # noqa: ARG001
    symbol: str,
) -> Any:
    """Tra cứu lịch sử tăng vốn điều lệ từ PostgreSQL."""
    sym_code = symbol.strip().upper()
    histories = CorporateService.get_capital_history(session, sym_code)
    data = [CapitalHistoryPublic.model_validate(h) for h in histories]
    return CapitalHistoryResponse(symbol=sym_code, count=len(data), data=data)
