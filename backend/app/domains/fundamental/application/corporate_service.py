"""Dịch vụ tra cứu hồ sơ doanh nghiệp, báo cáo tài chính & quản trị công ty (CorporateService)."""

from __future__ import annotations

import logging

from sqlmodel import Session, col, select

from app.domains.fundamental.domain.models import (
    CapitalHistory,
    CompanyOfficer,
    CompanyProfile,
    CompanyShareholder,
    CompanySubsidiary,
    CorporateEvent,
    FinancialRatio,
    FinancialReport,
    InsiderTrading,
)
from app.domains.market_data.application.sync_service import DataSyncManager
from app.domains.market_data.infrastructure.vnstock_adapter import vnstock_service

logger = logging.getLogger(__name__)


class CorporateService:
    """Xử lý nghiệp vụ truy vấn thông tin cơ bản của doanh nghiệp niêm yết."""

    @classmethod
    def get_company_profile(
        cls,
        session: Session,
        symbol: str,
        auto_sync: bool = True,
    ) -> CompanyProfile | None:
        """Lấy hồ sơ doanh nghiệp niêm yết từ DB, tự động đồng bộ từ vnstock nếu chưa có."""
        sym = symbol.strip().upper()
        profile = session.get(CompanyProfile, sym)
        if not profile and auto_sync:
            try:
                manager = DataSyncManager(session, vnstock_service)
                log = manager.sync_company_profile(sym)
                if log.status == "success":
                    profile = session.get(CompanyProfile, sym)
            except Exception as e:
                logger.debug("Failed auto-sync company profile for %s: %s", sym, e)
        return profile

    @classmethod
    def get_financial_reports(
        cls,
        session: Session,
        symbol: str,
        report_type: str = "income_statement",
        period: str = "quarterly",
        auto_sync: bool = True,
    ) -> list[FinancialReport]:
        """Lấy danh sách các kỳ báo cáo tài chính của doanh nghiệp."""
        sym = symbol.strip().upper()
        reports = list(
            session.exec(
                select(FinancialReport)
                .where(FinancialReport.symbol == sym)
                .where(FinancialReport.report_type == report_type)
                .where(FinancialReport.period == period)
                .order_by(
                    col(FinancialReport.year).desc(),
                    col(FinancialReport.quarter).desc(),
                )
            ).all()
        )

        if not reports and auto_sync:
            try:
                manager = DataSyncManager(session, vnstock_service)
                log = manager.sync_financials(
                    sym, report_type=report_type, period=period
                )
                if log.status == "success":
                    reports = list(
                        session.exec(
                            select(FinancialReport)
                            .where(FinancialReport.symbol == sym)
                            .where(FinancialReport.report_type == report_type)
                            .where(FinancialReport.period == period)
                            .order_by(
                                col(FinancialReport.year).desc(),
                                col(FinancialReport.quarter).desc(),
                            )
                        ).all()
                    )
            except Exception as e:
                logger.debug("Failed auto-sync financials for %s: %s", sym, e)

        return reports

    @classmethod
    def get_financial_ratios(
        cls,
        session: Session,
        symbol: str,
        period: str = "quarter",
        auto_sync: bool = True,
    ) -> list[FinancialRatio]:
        """Tra cứu chỉ số tài chính (P/E, P/B, ROE, ROA, EPS, BVPS...) của doanh nghiệp."""
        sym = symbol.strip().upper()
        ratios = list(
            session.exec(
                select(FinancialRatio)
                .where(FinancialRatio.symbol == sym)
                .where(FinancialRatio.period == period)
                .order_by(
                    col(FinancialRatio.year).desc(), col(FinancialRatio.quarter).desc()
                )
            ).all()
        )

        if not ratios and auto_sync:
            try:
                manager = DataSyncManager(session, vnstock_service)
                log = manager.sync_financial_ratios(sym, period=period)
                if log.status == "success":
                    ratios = list(
                        session.exec(
                            select(FinancialRatio)
                            .where(FinancialRatio.symbol == sym)
                            .where(FinancialRatio.period == period)
                            .order_by(
                                col(FinancialRatio.year).desc(),
                                col(FinancialRatio.quarter).desc(),
                            )
                        ).all()
                    )
            except Exception as e:
                logger.debug("Failed auto-sync ratios for %s: %s", sym, e)

        return ratios

    @classmethod
    def get_shareholders(
        cls,
        session: Session,
        symbol: str,
        auto_sync: bool = True,
    ) -> list[CompanyShareholder]:
        """Tra cứu cơ cấu cổ đông lớn và nội bộ."""
        sym = symbol.strip().upper()
        shareholders = list(
            session.exec(
                select(CompanyShareholder)
                .where(CompanyShareholder.symbol == sym)
                .order_by(col(CompanyShareholder.ownership_pct).desc())
            ).all()
        )

        if not shareholders and auto_sync:
            try:
                manager = DataSyncManager(session, vnstock_service)
                log = manager.sync_company_shareholders(sym)
                if log.status == "success":
                    shareholders = list(
                        session.exec(
                            select(CompanyShareholder)
                            .where(CompanyShareholder.symbol == sym)
                            .order_by(col(CompanyShareholder.ownership_pct).desc())
                        ).all()
                    )
            except Exception as e:
                logger.debug("Failed auto-sync shareholders for %s: %s", sym, e)

        return shareholders

    @classmethod
    def get_officers(
        cls,
        session: Session,
        symbol: str,
        auto_sync: bool = True,
    ) -> list[CompanyOfficer]:
        """Tra cứu danh sách ban điều hành và Hội đồng quản trị."""
        sym = symbol.strip().upper()
        officers = list(
            session.exec(
                select(CompanyOfficer)
                .where(CompanyOfficer.symbol == sym)
                .order_by(col(CompanyOfficer.officer_name).asc())
            ).all()
        )

        if not officers and auto_sync:
            try:
                manager = DataSyncManager(session, vnstock_service)
                log = manager.sync_company_officers(sym)
                if log.status == "success":
                    officers = list(
                        session.exec(
                            select(CompanyOfficer)
                            .where(CompanyOfficer.symbol == sym)
                            .order_by(col(CompanyOfficer.officer_name).asc())
                        ).all()
                    )
            except Exception as e:
                logger.debug("Failed auto-sync officers for %s: %s", sym, e)

        return officers

    @classmethod
    def get_corporate_events(
        cls,
        session: Session,
        symbol: str,
        auto_sync: bool = True,
    ) -> list[CorporateEvent]:
        """Tra cứu lịch sự kiện doanh nghiệp và chi trả cổ tức."""
        sym = symbol.strip().upper()
        events = list(
            session.exec(
                select(CorporateEvent)
                .where(CorporateEvent.symbol == sym)
                .order_by(col(CorporateEvent.ex_date).desc().nulls_last())
            ).all()
        )

        if not events and auto_sync:
            try:
                manager = DataSyncManager(session, vnstock_service)
                log = manager.sync_corporate_events(sym)
                if log.status == "success":
                    events = list(
                        session.exec(
                            select(CorporateEvent)
                            .where(CorporateEvent.symbol == sym)
                            .order_by(col(CorporateEvent.ex_date).desc().nulls_last())
                        ).all()
                    )
            except Exception as e:
                logger.debug("Failed auto-sync corporate events for %s: %s", sym, e)

        return events

    @classmethod
    def get_subsidiaries(
        cls,
        session: Session,
        symbol: str,
        auto_sync: bool = True,
    ) -> list[CompanySubsidiary]:
        """Tra cứu danh sách công ty con và công ty liên kết."""
        sym = symbol.strip().upper()
        subsidiaries = list(
            session.exec(
                select(CompanySubsidiary)
                .where(CompanySubsidiary.symbol == sym)
                .order_by(col(CompanySubsidiary.ownership_percent).desc())
            ).all()
        )

        if not subsidiaries and auto_sync:
            try:
                manager = DataSyncManager(session, vnstock_service)
                log = manager.sync_company_subsidiaries(sym)
                if log.status == "success":
                    subsidiaries = list(
                        session.exec(
                            select(CompanySubsidiary)
                            .where(CompanySubsidiary.symbol == sym)
                            .order_by(col(CompanySubsidiary.ownership_percent).desc())
                        ).all()
                    )
            except Exception as e:
                logger.debug("Failed auto-sync subsidiaries for %s: %s", sym, e)

        return subsidiaries

    @classmethod
    def get_insider_trading(
        cls,
        session: Session,
        symbol: str,
        auto_sync: bool = True,
    ) -> list[InsiderTrading]:
        """Tra cứu nhật ký giao dịch người nội bộ và người có liên quan."""
        sym = symbol.strip().upper()
        trades = list(
            session.exec(
                select(InsiderTrading)
                .where(InsiderTrading.symbol == sym)
                .order_by(col(InsiderTrading.deal_announce_date).desc().nulls_last())
            ).all()
        )

        if not trades and auto_sync:
            try:
                manager = DataSyncManager(session, vnstock_service)
                log = manager.sync_insider_trading(sym)
                if log.status == "success":
                    trades = list(
                        session.exec(
                            select(InsiderTrading)
                            .where(InsiderTrading.symbol == sym)
                            .order_by(
                                col(InsiderTrading.deal_announce_date)
                                .desc()
                                .nulls_last()
                            )
                        ).all()
                    )
            except Exception as e:
                logger.debug("Failed auto-sync insider trading for %s: %s", sym, e)

        return trades

    @classmethod
    def get_capital_history(
        cls,
        session: Session,
        symbol: str,
        auto_sync: bool = True,
    ) -> list[CapitalHistory]:
        """Tra cứu lịch sử tăng vốn điều lệ và phát hành cổ phiếu."""
        sym = symbol.strip().upper()
        histories = list(
            session.exec(
                select(CapitalHistory)
                .where(CapitalHistory.symbol == sym)
                .order_by(col(CapitalHistory.issue_date).desc().nulls_last())
            ).all()
        )

        if not histories and auto_sync:
            try:
                manager = DataSyncManager(session, vnstock_service)
                log = manager.sync_capital_history(sym)
                if log.status == "success":
                    histories = list(
                        session.exec(
                            select(CapitalHistory)
                            .where(CapitalHistory.symbol == sym)
                            .order_by(
                                col(CapitalHistory.issue_date).desc().nulls_last()
                            )
                        ).all()
                    )
            except Exception as e:
                logger.debug("Failed auto-sync capital history for %s: %s", sym, e)

        return histories
