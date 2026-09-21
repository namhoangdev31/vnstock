"""Tests for Asset Master models, temporal aliases, continuous contracts, and fact table links."""

import uuid
from collections.abc import Generator
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlmodel import Session, SQLModel, select

from app.models.entities.asset_master import (
    Instrument,
    InstrumentAlias,
    InstrumentRelation,
    LegalEntity,
)
from app.models.entities.stock import (
    FinancialRatio,
    FinancialReport,
    StockOHLCVDaily,
    StockSymbol,
)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Fixture cung cấp in-memory SQLite session có tạo đầy đủ bảng Asset Master."""
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_asset_master_creation_and_relations(db_session: Session) -> None:
    """Kiểm tra tạo LegalEntity, Instrument và liên kết quan hệ 1-N."""
    # 1. Tạo LegalEntity
    entity = LegalEntity(
        legal_name="Tập đoàn FPT",
        short_name="FPT",
        tax_id="0101248141",
        headquarters_address="Số 10 Phạm Văn Bạch, Cầu Giấy, Hà Nội",
    )
    db_session.add(entity)
    db_session.commit()
    db_session.refresh(entity)

    assert entity.id is not None
    assert entity.legal_name == "Tập đoàn FPT"

    # 2. Tạo Instrument cổ phiếu FPT
    inst = Instrument(
        legal_entity_id=entity.id,
        instrument_type="EQUITY",
        canonical_code="EQUITY:FPT",
        isin="VN000000FPT8",
        exchange="HOSE",
        currency="VND",
        is_active=True,
    )
    db_session.add(inst)
    db_session.commit()
    db_session.refresh(inst)

    assert inst.id is not None
    assert inst.legal_entity_id == entity.id

    # 3. Tạo InstrumentAlias
    alias = InstrumentAlias(
        instrument_id=inst.id,
        alias="FPT",
        alias_type="TICKER",
        valid_from=date(2006, 12, 13),
        valid_to=None,
    )
    db_session.add(alias)
    db_session.commit()
    db_session.refresh(alias)

    assert alias.instrument_id == inst.id
    assert alias.alias == "FPT"
    assert alias.valid_to is None


def test_continuous_futures_instrument_and_alias(db_session: Session) -> None:
    """Kiểm tra quản lý hợp đồng phái sinh liên tục VN30F1M qua Continuous Rolling Alias."""
    # Continuous instrument
    cont_inst = Instrument(
        instrument_type="FUTURES",
        canonical_code="FUTURES:VN30F1M:CONTINUOUS",
        exchange="VNFE",
        currency="VND",
        is_active=True,
    )
    db_session.add(cont_inst)
    db_session.commit()
    db_session.refresh(cont_inst)

    alias = InstrumentAlias(
        instrument_id=cont_inst.id,
        alias="VN30F1M",
        alias_type="CONTINUOUS_ROLLING",
        valid_from=date(2017, 8, 10),
        valid_to=None,
    )
    db_session.add(alias)
    db_session.commit()

    loaded_alias = db_session.exec(
        select(InstrumentAlias).where(InstrumentAlias.alias == "VN30F1M")
    ).first()
    assert loaded_alias is not None
    assert loaded_alias.instrument_id == cont_inst.id
    assert loaded_alias.alias_type == "CONTINUOUS_ROLLING"


def test_fact_tables_have_instrument_id(db_session: Session) -> None:
    """Kiểm tra các bảng Fact (StockOHLCVDaily, FinancialReport, FinancialRatio) chấp nhận instrument_id."""
    inst_id = uuid.uuid4()
    sym = StockSymbol(symbol="VNM", organ_name="Vinamilk", exchange="HOSE")
    db_session.add(sym)
    db_session.commit()

    # Fact 1: StockOHLCVDaily
    ohlcv = StockOHLCVDaily(
        symbol="VNM",
        instrument_id=inst_id,
        trading_date=date(2026, 9, 18),
        open=70000.0,
        high=71000.0,
        low=69500.0,
        close=70500.0,
        volume=2500000,
        source="VCI",
    )
    db_session.add(ohlcv)

    # Fact 2: FinancialReport
    report = FinancialReport(
        symbol="VNM",
        instrument_id=inst_id,
        report_type="income_statement",
        report_scope="consolidated",
        period="quarter",
        year=2026,
        quarter=2,
        source="VCI",
    )
    db_session.add(report)

    # Fact 3: FinancialRatio
    ratio = FinancialRatio(
        symbol="VNM",
        instrument_id=inst_id,
        period="quarter",
        year=2026,
        quarter=2,
        roe=28.5,
        source="VCI",
    )
    db_session.add(ratio)
    db_session.commit()

    # Query verify
    d_loaded = db_session.exec(
        select(StockOHLCVDaily).where(StockOHLCVDaily.symbol == "VNM")
    ).first()
    assert d_loaded is not None
    assert d_loaded.instrument_id == inst_id

    rep_loaded = db_session.exec(
        select(FinancialReport).where(FinancialReport.symbol == "VNM")
    ).first()
    assert rep_loaded is not None
    assert rep_loaded.instrument_id == inst_id

    rat_loaded = db_session.exec(
        select(FinancialRatio).where(FinancialRatio.symbol == "VNM")
    ).first()
    assert rat_loaded is not None
    assert rat_loaded.instrument_id == inst_id


def test_instrument_relation_underlying_mapping(db_session: Session) -> None:
    """Kiểm tra quan hệ tài sản phái sinh / chứng quyền tới tài sản cơ sở."""
    idx = Instrument(
        instrument_type="INDEX",
        canonical_code="INDEX:VN30",
        exchange="HOSE",
        currency="VND",
    )
    fut = Instrument(
        instrument_type="FUTURES",
        canonical_code="FUTURES:VN30F2610",
        exchange="VNFE",
        currency="VND",
    )
    db_session.add_all([idx, fut])
    db_session.commit()

    relation = InstrumentRelation(
        source_instrument_id=fut.id,
        target_instrument_id=idx.id,
        relation_type="UNDERLYING_OF_FUTURES",
        valid_from=date(2026, 9, 18),
    )
    db_session.add(relation)
    db_session.commit()

    loaded_rel = db_session.exec(
        select(InstrumentRelation).where(
            InstrumentRelation.source_instrument_id == fut.id
        )
    ).first()
    assert loaded_rel is not None
    assert loaded_rel.target_instrument_id == idx.id
    assert loaded_rel.relation_type == "UNDERLYING_OF_FUTURES"


def test_vn30f1m_continuous_instrument_and_roll_rule(db_session: Session) -> None:
    """Kiểm tra Instrument liên tục VN30F1M có roll_rule và alias CONTINUOUS_ROLLING chuẩn."""
    continuous_fut = Instrument(
        instrument_type="FUTURES",
        canonical_code="FUTURES:VN30F1M:CONTINUOUS",
        exchange="VNFE",
        currency="VND",
        roll_rule="THIRD_THURSDAY",
        is_active=True,
    )
    db_session.add(continuous_fut)
    db_session.commit()
    db_session.refresh(continuous_fut)

    alias = InstrumentAlias(
        instrument_id=continuous_fut.id,
        alias="VN30F1M",
        alias_type="CONTINUOUS_ROLLING",
        valid_from=date(2017, 8, 10),
    )
    db_session.add(alias)
    db_session.commit()

    loaded = db_session.exec(
        select(Instrument).where(
            Instrument.canonical_code == "FUTURES:VN30F1M:CONTINUOUS"
        )
    ).first()
    assert loaded is not None
    assert loaded.roll_rule == "THIRD_THURSDAY"
    assert loaded.aliases[0].alias == "VN30F1M"
    assert loaded.aliases[0].alias_type == "CONTINUOUS_ROLLING"
