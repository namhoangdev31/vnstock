"""Tests for the Fundamental Domain Layer and Corporate Service."""

import uuid
from collections.abc import Generator
from datetime import date, datetime

import pytest
from sqlalchemy import create_engine
from sqlmodel import Session, SQLModel

from app.domains.fundamental.application.corporate_service import CorporateService
from app.domains.fundamental.application.revision_service import (
    get_as_of_financial_report_revision,
    record_financial_report_revision,
)
from app.domains.fundamental.domain.exceptions import (
    FinancialRevisionError,
    FundamentalError,
    ScreenerError,
)
from app.domains.fundamental.domain.models import (
    CapitalHistory,
    CompanyOfficer,
    CompanyProfile,
    CompanyShareholder,
    CompanySubsidiary,
    CorporateEvent,
    FinancialReport,
)
from app.domains.market_data.domain.asset_master import Instrument
from app.domains.market_data.domain.models import StockSymbol


@pytest.fixture
def fnd_session() -> Generator[Session, None, None]:
    """In-memory SQLite session for fundamental domain testing."""
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_fundamental_exceptions_inheritance() -> None:
    """Kiểm tra cây kế thừa domain exceptions."""
    assert issubclass(ScreenerError, FundamentalError)
    assert issubclass(FinancialRevisionError, FundamentalError)
    assert issubclass(FundamentalError, Exception)


def test_corporate_service_profile_query(fnd_session: Session) -> None:
    """Kiểm tra CorporateService lấy hồ sơ doanh nghiệp."""
    sym = StockSymbol(symbol="VIC", organ_name="Vingroup", exchange="HOSE")
    fnd_session.add(sym)
    prof = CompanyProfile(
        symbol="VIC",
        company_name="Tập đoàn Vingroup",
        charter_capital=38000000000.0,
    )
    fnd_session.add(prof)
    fnd_session.commit()

    res = CorporateService.get_company_profile(fnd_session, "VIC", auto_sync=False)
    assert res is not None
    assert res.symbol == "VIC"
    assert res.company_name == "Tập đoàn Vingroup"

    res_missing = CorporateService.get_company_profile(
        fnd_session, "NONEXISTENT", auto_sync=False
    )
    assert res_missing is None


def test_corporate_service_governance_queries(fnd_session: Session) -> None:
    """Kiểm tra CorporateService lấy thông tin quản trị: cổ đông, lãnh đạo, công ty con, sự kiện."""
    sym = StockSymbol(symbol="MBB", organ_name="MB Bank", exchange="HOSE")
    fnd_session.add(sym)

    shareholder = CompanyShareholder(
        symbol="MBB",
        shareholder_name="SCIC",
        ownership_pct=9.8,
        is_state=True,
    )
    officer = CompanyOfficer(
        symbol="MBB",
        officer_name="Nguyễn Văn A",
        position="Chủ tịch HĐQT",
    )
    subsidiary = CompanySubsidiary(
        symbol="MBB",
        sub_organ_code="MBS",
        organ_name="Chứng khoán MB",
        ownership_percent=79.5,
    )
    event = CorporateEvent(
        symbol="MBB",
        event_type="cash_dividend",
        event_title="Cổ tức tiền mặt 15%",
        ex_date=date(2026, 6, 1),
        cash_rate=1500.0,
        source="VCI",
    )
    capital = CapitalHistory(
        symbol="MBB",
        issue_date=date(2025, 12, 1),
        charter_capital=52000000000000.0,
        description="Phát hành riêng lẻ",
    )
    fnd_session.add_all([shareholder, officer, subsidiary, event, capital])
    fnd_session.commit()

    shs = CorporateService.get_shareholders(fnd_session, "MBB", auto_sync=False)
    assert len(shs) == 1
    assert shs[0].shareholder_name == "SCIC"

    offs = CorporateService.get_officers(fnd_session, "MBB", auto_sync=False)
    assert len(offs) == 1
    assert offs[0].position == "Chủ tịch HĐQT"

    subs = CorporateService.get_subsidiaries(fnd_session, "MBB", auto_sync=False)
    assert len(subs) == 1
    assert subs[0].sub_organ_code == "MBS"

    evts = CorporateService.get_corporate_events(fnd_session, "MBB", auto_sync=False)
    assert len(evts) == 1
    assert evts[0].cash_rate == 1500.0

    caps = CorporateService.get_capital_history(fnd_session, "MBB", auto_sync=False)
    assert len(caps) == 1
    assert caps[0].charter_capital == 52000000000000.0


def test_point_in_time_revision_with_provisional_flag(fnd_session: Session) -> None:
    """Kiểm tra logic Point-in-Time với cờ allow_provisional."""
    inst_id = uuid.uuid4()
    inst = Instrument(
        id=inst_id,
        canonical_code="EQUITY:TCB",
        instrument_type="equity",
        exchange="HOSE",
    )
    fnd_session.add(inst)

    report = FinancialReport(
        symbol="TCB",
        instrument_id=inst_id,
        report_type="income_statement",
        report_scope="consolidated",
        period="quarter",
        year=2026,
        quarter=1,
        source="VCI",
    )
    fnd_session.add(report)
    fnd_session.commit()

    # Tạo bản ghi provisional (chưa có published_at)
    data_prov = {"revenue": 10000, "profit": 3000}
    rev_prov = record_financial_report_revision(
        fnd_session,
        report,
        data_prov,
        published_at=None,  # Provisional
    )
    fnd_session.commit()

    as_of_future = datetime(2026, 12, 31, 23, 59, 59)

    # Khi allow_provisional_if_ingested = True -> tìm thấy bản ghi provisional
    found_prov = get_as_of_financial_report_revision(
        session=fnd_session,
        instrument_id=inst_id,
        report_type="income_statement",
        period="quarter",
        year=2026,
        quarter=1,
        as_of_date=as_of_future,
        allow_provisional_if_ingested=True,
    )
    assert found_prov is not None
    assert found_prov.id == rev_prov.id
    assert found_prov.is_provisional is True

    # Khi allow_provisional_if_ingested = False -> không lấy bản ghi provisional
    strict_found = get_as_of_financial_report_revision(
        session=fnd_session,
        instrument_id=inst_id,
        report_type="income_statement",
        period="quarter",
        year=2026,
        quarter=1,
        as_of_date=as_of_future,
        allow_provisional_if_ingested=False,
    )
    assert strict_found is None
