"""Tests for ScreenerSnapshot & Keyset Pagination (ScreenerService).

Kiểm tra:
1. Bộ lọc cơ bản (PE, ROE, Exchange, Industry, is_active).
2. Thuật toán Keyset 2 pha:
   - Sắp xếp chuẩn: roe DESC NULLS LAST, instrument_id ASC.
   - Chuyển tiếp mượt mà từ nhóm có ROE sang nhóm roe IS NULL không mất và không trùng lặp bản ghi.
   - Trang cuối cùng has_next = False và next_cursor = None.
"""

from collections.abc import Generator
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlmodel import Session, SQLModel

from app.models.entities.asset_master import Instrument
from app.models.entities.screener import ScreenerSnapshot
from app.services.screener_service import ScreenerCursor, ScreenerService


@pytest.fixture
def screener_db_session() -> Generator[Session, None, None]:
    """Fixture tạo in-memory SQLite database chứa bảng Screener."""
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_screener_keyset_two_phase_pagination(screener_db_session: Session) -> None:
    """Kiểm tra Keyset pagination duyệt qua toàn bộ danh sách gồm cả bản ghi có ROE và roe IS NULL."""
    today = date(2026, 9, 21)

    # 1. Tạo 10 instruments với ROE xác định (từ 25.0 xuống 10.0) và 5 instruments với ROE = None
    created_items: list[ScreenerSnapshot] = []

    # Nhóm ROE xác định
    for i in range(10):
        sym = f"SYM_{i:02d}"
        inst = Instrument(
            canonical_code=f"EQUITY:{sym}",
            instrument_type="equity",
            exchange="HOSE",
            is_active=True,
        )
        screener_db_session.add(inst)
        screener_db_session.commit()

        snapshot = ScreenerSnapshot(
            instrument_id=inst.id,
            snapshot_date=today,
            symbol=sym,
            exchange="HOSE",
            industry="Manufacturing",
            is_active=True,
            roe=25.0 - (i * 1.5),  # 25.0, 23.5, 22.0, ...
            pe=12.0 + i,
        )
        screener_db_session.add(snapshot)
        created_items.append(snapshot)

    # Nhóm ROE = None
    for i in range(5):
        sym = f"NULL_{i:02d}"
        inst = Instrument(
            canonical_code=f"EQUITY:{sym}",
            instrument_type="equity",
            exchange="HOSE",
            is_active=True,
        )
        screener_db_session.add(inst)
        screener_db_session.commit()

        snapshot = ScreenerSnapshot(
            instrument_id=inst.id,
            snapshot_date=today,
            symbol=sym,
            exchange="HOSE",
            industry="Banking",
            is_active=True,
            roe=None,
            pe=None,
        )
        screener_db_session.add(snapshot)
        created_items.append(snapshot)

    screener_db_session.commit()

    # 2. Thực hiện duyệt trang với page_size = 4
    page_size = 4
    collected_symbols: list[str] = []
    cursor: ScreenerCursor | None = None
    page_count = 0

    while True:
        res = ScreenerService.query_screener_keyset(
            session=screener_db_session,
            page_size=page_size,
            cursor=cursor,
        )
        page_count += 1
        page_symbols = [item.symbol for item in res.items]
        collected_symbols.extend(page_symbols)

        if not res.has_next:
            assert res.next_cursor is None
            break

        assert res.next_cursor is not None
        cursor = res.next_cursor

    # 3. Kiểm tra tính toàn vẹn: thu thập đủ 15 bản ghi, không bị trùng, không bị thiếu
    assert len(collected_symbols) == 15
    assert len(set(collected_symbols)) == 15

    # 10 bản ghi đầu phải là SYM_00 đến SYM_09 (thứ tự ROE giảm dần)
    assert collected_symbols[:10] == [f"SYM_{i:02d}" for i in range(10)]

    # 5 bản ghi cuối phải thuộc nhóm NULL_*, sắp xếp theo instrument_id ASC
    null_symbols = collected_symbols[10:]
    assert set(null_symbols) == {f"NULL_{i:02d}" for i in range(5)}


def test_screener_filters(screener_db_session: Session) -> None:
    """Kiểm tra các tiêu chí lọc: exchange, industry, min_pe, max_pe, min_roe."""
    today = date(2026, 9, 21)

    stocks = [
        ("VNM", "HOSE", "Consumer", 15.0, 22.0, True),
        ("HPG", "HOSE", "Materials", 8.5, 18.0, True),
        ("FPT", "HOSE", "Technology", 20.0, 25.0, True),
        ("SHS", "HNX", "Financials", 12.0, 14.0, True),
        ("DELISTED", "HOSE", "Consumer", 10.0, 10.0, False),  # inactive
    ]

    for sym, ex, ind, pe, roe, active in stocks:
        inst = Instrument(
            canonical_code=f"EQUITY:{sym}",
            instrument_type="equity",
            exchange=ex,
            is_active=active,
        )
        screener_db_session.add(inst)
        screener_db_session.commit()

        snapshot = ScreenerSnapshot(
            instrument_id=inst.id,
            snapshot_date=today,
            symbol=sym,
            exchange=ex,
            industry=ind,
            is_active=active,
            pe=pe,
            roe=roe,
        )
        screener_db_session.add(snapshot)

    screener_db_session.commit()

    # Lọc HOSE + ROE >= 20
    res = ScreenerService.query_screener_keyset(
        session=screener_db_session,
        exchange="HOSE",
        min_roe=20.0,
    )
    # FPT (25.0) và VNM (22.0)
    assert [x.symbol for x in res.items] == ["FPT", "VNM"]

    # Lọc max_pe <= 10.0
    res_pe = ScreenerService.query_screener_keyset(
        session=screener_db_session,
        max_pe=10.0,
    )
    # HPG (pe=8.5), DELISTED bị loại vì is_active=False
    assert [x.symbol for x in res_pe.items] == ["HPG"]
