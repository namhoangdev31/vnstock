"""Tests for financial report revisions, canonical JSON hashing, advisory locking, and point-in-time queries."""

import uuid
from collections.abc import Generator
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import create_engine
from sqlmodel import Session, SQLModel, select

from app.models.entities.asset_master import Instrument
from app.models.entities.stock import (
    FinancialReport,
    FinancialReportRevision,
    StockSymbol,
)
from app.services.financial_revision_service import (
    acquire_financial_report_lock,
    canonical_payload_hash,
    get_as_of_financial_report_revision,
    record_financial_report_revision,
)

VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Fixture cung cấp in-memory SQLite session."""
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_canonical_payload_hash_key_order_independence() -> None:
    """Kiểm tra hash SHA-256 không phụ thuộc vào thứ tự keys trong JSON."""
    dict_a = {"revenue": 1000, "profit": 200, "meta": {"auditor": "PwC", "year": 2026}}
    dict_b = {"meta": {"year": 2026, "auditor": "PwC"}, "profit": 200, "revenue": 1000}

    hash_a = canonical_payload_hash(dict_a)
    hash_b = canonical_payload_hash(dict_b)

    assert hash_a == hash_b
    assert len(hash_a) == 64

    # Thay đổi nhỏ phải sinh hash khác biệt
    dict_c = {"revenue": 1001, "profit": 200, "meta": {"auditor": "PwC", "year": 2026}}
    assert canonical_payload_hash(dict_c) != hash_a


def test_record_financial_report_revision_deduplication(db_session: Session) -> None:
    """Kiểm tra không tạo trùng lặp revision nếu payload không thay đổi."""
    sym = StockSymbol(symbol="HPG", organ_name="Hòa Phát", exchange="HOSE")
    db_session.add(sym)
    db_session.commit()

    report = FinancialReport(
        symbol="HPG",
        report_type="income_statement",
        report_scope="consolidated",
        period="quarter",
        year=2026,
        quarter=2,
        source="VCI",
    )
    db_session.add(report)
    db_session.commit()

    data_v1 = {"revenue": 39000000000000.0, "net_profit": 3300000000000.0}

    # Lần 1: Tạo revision 1
    rev1 = record_financial_report_revision(
        db_session,
        report,
        data_v1,
        published_at=datetime(2026, 7, 25, 10, 0, tzinfo=VN_TZ),
    )
    db_session.commit()

    assert rev1.revision_number == 1
    assert rev1.is_provisional is False

    # Lần 2: Ghi nhận lại cùng payload -> Giữ nguyên revision 1, không tạo mới
    rev2 = record_financial_report_revision(
        db_session,
        report,
        data_v1,
        published_at=datetime(2026, 7, 25, 10, 0, tzinfo=VN_TZ),
    )
    assert rev2.id == rev1.id
    assert rev2.revision_number == 1


def test_record_financial_report_revision_restatement(db_session: Session) -> None:
    """Kiểm tra tự động tăng revision_number khi có số liệu điều chỉnh sau kiểm toán."""
    sym = StockSymbol(symbol="MBB", organ_name="Ngân hàng MB", exchange="HOSE")
    db_session.add(sym)
    db_session.commit()

    report = FinancialReport(
        symbol="MBB",
        report_type="income_statement",
        report_scope="consolidated",
        period="year",
        year=2025,
        quarter=None,
        source="VCI",
    )
    db_session.add(report)
    db_session.commit()

    # Bản tự lập (chưa có ngày công bố xác thực -> is_provisional = True)
    data_draft = {"net_profit": 25000000000000.0}
    rev1 = record_financial_report_revision(
        db_session,
        report,
        data_draft,
        published_at=None,
    )
    db_session.commit()

    assert rev1.revision_number == 1
    assert rev1.is_provisional is True

    # Bản kiểm toán chính thức có điều chỉnh LNST
    data_audited = {"net_profit": 24800000000000.0}
    rev2 = record_financial_report_revision(
        db_session,
        report,
        data_audited,
        published_at=datetime(2026, 3, 15, 15, 0, tzinfo=VN_TZ),
        restated_reason="Báo cáo tài chính kiểm toán năm 2025 bởi KPMG",
    )
    db_session.commit()

    assert rev2.revision_number == 2
    assert rev2.is_provisional is False
    assert rev2.restated_reason is not None


def test_point_in_time_query_eliminates_look_ahead_bias(db_session: Session) -> None:
    """Kiểm tra Point-in-time query loại bỏ rò rỉ thông tin tương lai trong backtest."""
    inst_id = uuid.uuid4()
    inst = Instrument(
        id=inst_id,
        instrument_type="EQUITY",
        canonical_code="EQUITY:TCB",
        exchange="HOSE",
        currency="VND",
    )
    sym = StockSymbol(symbol="TCB", organ_name="Techcombank", exchange="HOSE")
    db_session.add_all([inst, sym])
    db_session.commit()

    report = FinancialReport(
        symbol="TCB",
        instrument_id=inst_id,
        report_type="income_statement",
        report_scope="consolidated",
        period="quarter",
        year=2026,
        quarter=2,
        source="VCI",
    )
    db_session.add(report)
    db_session.commit()

    # Revision 1 công bố ngày 20/07/2026
    record_financial_report_revision(
        db_session,
        report,
        {"profit": 6000},
        published_at=datetime(2026, 7, 20, 9, 0, tzinfo=VN_TZ),
    )
    # Revision 2 soát xét công bố ngày 15/08/2026
    record_financial_report_revision(
        db_session,
        report,
        {"profit": 5900},
        published_at=datetime(2026, 8, 15, 9, 0, tzinfo=VN_TZ),
    )
    db_session.commit()

    # Truy vấn tại ngày 01/08/2026 (trước ngày công bố rev 2)
    pit_july = get_as_of_financial_report_revision(
        db_session,
        instrument_id=inst_id,
        report_type="income_statement",
        period="quarter",
        year=2026,
        quarter=2,
        as_of_date=datetime(2026, 8, 1, 0, 0, tzinfo=VN_TZ),
    )
    assert pit_july is not None
    assert pit_july.revision_number == 1
    assert pit_july.data["profit"] == 6000

    # Truy vấn tại ngày 20/08/2026 (sau ngày công bố rev 2)
    pit_aug = get_as_of_financial_report_revision(
        db_session,
        instrument_id=inst_id,
        report_type="income_statement",
        period="quarter",
        year=2026,
        quarter=2,
        as_of_date=datetime(2026, 8, 20, 0, 0, tzinfo=VN_TZ),
    )
    assert pit_aug is not None
    assert pit_aug.revision_number == 2
    assert pit_aug.data["profit"] == 5900


def test_advisory_lock_helper(db_session: Session) -> None:
    """Kiểm tra acquire_financial_report_lock hoạt động không phát sinh ngoại lệ."""
    acquire_financial_report_lock(
        db_session,
        instrument_id=uuid.uuid4(),
        report_type="balance_sheet",
        report_scope="consolidated",
        period="quarter",
        year=2026,
        quarter=2,
    )


def test_sync_financials_creates_revisions_in_data_sync(db_session: Session) -> None:
    """Kiểm tra DataSyncManager.sync_financials() tự động tích hợp FinancialRevisionService."""
    from unittest.mock import MagicMock

    import pandas as pd

    from app.services.data_sync import DataSyncManager

    sym = StockSymbol(symbol="HPG", organ_name="Tập đoàn Hòa Phát", exchange="HOSE")
    db_session.add(sym)
    db_session.commit()

    mock_svc = MagicMock()
    mock_svc.source = "VCI"
    mock_svc.fetch_financials.return_value = pd.DataFrame(
        [
            {
                "year": 2026,
                "quarter": 1,
                "revenue": 35000000000000.0,
                "net_profit": 3200000000000.0,
            }
        ]
    )

    manager = DataSyncManager(db_session, mock_svc)
    log = manager.sync_financials(
        "HPG", report_type="income_statement", period="quarter"
    )
    assert log.rows_synced == 1
    assert log.status == "success"

    revisions = db_session.exec(select(FinancialReportRevision)).all()
    assert len(revisions) == 1
    assert revisions[0].revision_number == 1
    assert revisions[0].is_provisional is True
    assert revisions[0].payload_hash is not None
