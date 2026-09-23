"""Unit tests for Market Data & Ingestion Bounded Context (DDD).

Kiểm thử toàn diện Domain Models, Exceptions, Application Services (SymbolService, PriceService),
và Infrastructure (TickStorageService, RateLimiter, VnstockCapabilityRegistry).
"""

import uuid
from datetime import UTC, date, datetime

import pytest
from sqlmodel import Session, SQLModel, create_engine

from app.domains.market_data.application.price_service import PriceService
from app.domains.market_data.application.schemas import (
    StockSymbolPublic,
    StockSymbolsPublic,
)
from app.domains.market_data.application.symbol_service import SymbolService
from app.domains.market_data.domain.exceptions import (
    IngestionError,
    MarketDataError,
    SafePurgeGateError,
    SymbolNotFoundError,
)
from app.domains.market_data.domain.models import (
    BondSpecification,
    CoveredWarrant,
    DataSyncLog,
    DerivativeContract,
    IndexConstituent,
    StockOHLCVDaily,
    StockOHLCVIntraday,
    StockSymbol,
    StockTickIntraday,
)
from app.domains.market_data.infrastructure.rate_limiter import (
    CircuitBreakerOpenError,
    RateLimiter,
)
from app.domains.market_data.infrastructure.tick_storage import TickStorageService
from app.domains.market_data.infrastructure.vnstock_registry import (
    CapabilityStatus,
    VnstockCapabilityRegistry,
)


@pytest.fixture
def memory_session():
    """In-memory SQLite session for testing market_data domain models and services."""
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_domain_exceptions_hierarchy():
    """Verify domain exception inheritance."""
    assert issubclass(SymbolNotFoundError, MarketDataError)
    assert issubclass(IngestionError, MarketDataError)
    assert issubclass(SafePurgeGateError, MarketDataError)

    err = SymbolNotFoundError("TCB")
    assert err.symbol == "TCB"
    assert "TCB" in str(err)


def test_market_data_models_instantiation(memory_session: Session):
    """Verify market data SQLModel entities can be persisted and queried."""
    sym = StockSymbol(
        symbol="HPG",
        organ_name="Tập đoàn Hòa Phát",
        exchange="HOSE",
        industry="Thép",
        index_group="VN30",
        asset_type="stock",
        lot_size=100,
        is_active=True,
    )
    memory_session.add(sym)
    memory_session.commit()

    queried = memory_session.get(StockSymbol, "HPG")
    assert queried is not None
    assert queried.symbol == "HPG"
    assert queried.exchange == "HOSE"

    # Daily OHLCV
    daily = StockOHLCVDaily(
        symbol="HPG",
        trading_date=date(2025, 3, 1),
        open=28000.0,
        high=28500.0,
        low=27800.0,
        close=28200.0,
        volume=15000000,
        source="VCI",
    )
    memory_session.add(daily)
    memory_session.commit()

    # Intraday OHLCV
    now_utc = datetime.now(UTC)
    intraday = StockOHLCVIntraday(
        symbol="HPG",
        timestamp=now_utc,
        interval="1m",
        open=28100.0,
        high=28200.0,
        low=28100.0,
        close=28150.0,
        volume=50000,
        source="VCI",
    )
    memory_session.add(intraday)
    memory_session.commit()

    # Tick Intraday
    tick = StockTickIntraday(
        symbol="HPG",
        timestamp=now_utc,
        price=28150.0,
        volume=1000,
        match_type="BU",
        sequence_number=1,
        source="VCI",
    )
    memory_session.add(tick)
    memory_session.commit()

    # Index constituent
    constituent = IndexConstituent(
        index_code="VN30",
        symbol="HPG",
        weight=6.5,
        effective_date=date(2025, 1, 1),
    )
    memory_session.add(constituent)
    memory_session.commit()

    # Covered Warrant
    cw = CoveredWarrant(
        symbol="CHPG2501",
        underlying_symbol="HPG",
        issuer_name="SSI",
        warrant_type="call",
        is_active=True,
    )
    memory_session.add(cw)
    memory_session.commit()

    # Bond Specification
    bond = BondSpecification(
        symbol="HPG123001",
        bond_type="corporate",
        issuer_symbol="HPG",
        issuer_name="Tập đoàn Hòa Phát",
        is_active=True,
    )
    memory_session.add(bond)
    memory_session.commit()

    # Derivative Contract
    deriv = DerivativeContract(
        symbol="VN30F2503",
        underlying_symbol="VN30",
        expiration_date=date(2025, 3, 20),
        is_active=True,
    )
    memory_session.add(deriv)
    memory_session.commit()

    # Data Sync Log
    log = DataSyncLog(
        sync_type="daily_ohlcv",
        symbol="HPG",
        source="VCI",
        status="success",
        rows_synced=1,
    )
    memory_session.add(log)
    memory_session.commit()

    assert memory_session.get(CoveredWarrant, cw.id) is not None
    assert memory_session.get(BondSpecification, bond.id) is not None


def test_symbol_service_queries(memory_session: Session):
    """Test SymbolService methods."""
    s1 = StockSymbol(
        symbol="VCB",
        organ_name="Vietcombank",
        exchange="HOSE",
        industry="Ngân hàng",
        index_group="VN30",
        asset_type="stock",
        is_active=True,
    )
    s2 = StockSymbol(
        symbol="ACB",
        organ_name="Á Châu",
        exchange="HOSE",
        industry="Ngân hàng",
        index_group="VN30",
        asset_type="stock",
        is_active=True,
    )
    s3 = StockSymbol(
        symbol="INACTIVE",
        organ_name="Ngừng giao dịch",
        exchange="UPCOM",
        asset_type="stock",
        is_active=False,
    )
    memory_session.add_all([s1, s2, s3])
    memory_session.commit()

    # 1. list_symbols
    res = SymbolService.list_symbols(memory_session, exchange="HOSE")
    assert isinstance(res, StockSymbolsPublic)
    assert res.count == 2
    assert [x.symbol for x in res.data] == ["ACB", "VCB"]

    # 2. get_symbol_by_id
    detail = SymbolService.get_symbol_by_id(memory_session, s1.id)
    assert isinstance(detail, StockSymbolPublic)
    assert detail.symbol == "VCB"

    # 3. get_symbol_by_id not found
    with pytest.raises(SymbolNotFoundError):
        SymbolService.get_symbol_by_id(memory_session, uuid.uuid4())


def test_price_service_queries(memory_session: Session):
    """Test PriceService methods."""
    sym = StockSymbol(
        symbol="FPT",
        organ_name="FPT Corp",
        exchange="HOSE",
        asset_type="stock",
        is_active=True,
    )
    bar1 = StockOHLCVDaily(
        symbol="FPT",
        trading_date=date(2025, 3, 1),
        open=120000.0,
        high=122000.0,
        low=119000.0,
        close=121000.0,
        volume=3000000,
        source="VCI",
    )
    bar2 = StockOHLCVDaily(
        symbol="FPT",
        trading_date=date(2025, 3, 2),
        open=121000.0,
        high=125000.0,
        low=120500.0,
        close=124000.0,
        volume=4000000,
        source="VCI",
    )
    cw = CoveredWarrant(
        symbol="CFPT2501",
        underlying_symbol="FPT",
        issuer_name="SSI",
        is_active=True,
    )
    bond = BondSpecification(
        symbol="FPT123001",
        bond_type="corporate",
        issuer_symbol="FPT",
        is_active=True,
    )
    memory_session.add_all([sym, bar1, bar2, cw, bond])
    memory_session.commit()

    # 1. get_daily_price from DB
    hist = PriceService.get_daily_price(
        memory_session, "FPT", date(2025, 3, 1), date(2025, 3, 2)
    )
    assert hist.count == 2
    assert hist.symbol == "FPT"
    assert hist.data[0].close == 121000.0
    assert hist.data[1].close == 124000.0

    # 2. get_related_assets
    graph = PriceService.get_related_assets(memory_session, "FPT")
    assert graph.symbol == "FPT"
    assert len(graph.covered_warrants) == 1
    assert graph.covered_warrants[0].symbol == "CFPT2501"
    assert len(graph.issued_bonds) == 1
    assert graph.issued_bonds[0].symbol == "FPT123001"

    # 3. list_covered_warrants
    cws = PriceService.list_covered_warrants(memory_session, underlying_symbol="FPT")
    assert len(cws) == 1
    assert cws[0].symbol == "CFPT2501"

    # 4. list_bonds
    bonds = PriceService.list_bonds(memory_session, issuer_symbol="FPT")
    assert len(bonds) == 1
    assert bonds[0].symbol == "FPT123001"


def test_rate_limiter_and_circuit_breaker():
    """Verify RateLimiter logic and CircuitBreaker transitions."""
    limiter = RateLimiter(min_delay=0.01, max_failures=2, base_cooldown=10.0)
    assert limiter.is_available("vci") is True

    limiter.record_failure("vci")
    assert limiter.is_available("vci") is True

    # Failure count reaches threshold -> trip to OPEN
    limiter.record_failure("vci")
    assert limiter.is_available("vci") is False

    with pytest.raises(CircuitBreakerOpenError):
        limiter.wait("vci")

    limiter.record_success("vci")
    assert limiter.is_available("vci") is True


def test_capability_registry():
    """Verify Capability Registry checks."""
    avail = VnstockCapabilityRegistry.check_availability("quote.history_daily")
    assert avail.status == CapabilityStatus.AVAILABLE
    assert "vci" in avail.supported_sources


def test_tick_storage_safe_purge_gate(memory_session: Session):
    """Verify SafePurgeGate prevents tick drop if condition not met."""
    target_date = date(2025, 3, 1)
    assert (
        TickStorageService.verify_safe_purge_gate(memory_session, target_date) is False
    )

    # Add 180 bars
    bars = [
        StockOHLCVIntraday(
            symbol="TCB",
            timestamp=datetime(2025, 3, 1, 9, i // 60, i % 60, tzinfo=UTC),
            interval="1m",
            open=25000.0,
            high=25100.0,
            low=24900.0,
            close=25050.0,
            volume=1000,
            source="VCI",
        )
        for i in range(180)
    ]
    memory_session.add_all(bars)
    memory_session.commit()

    assert (
        TickStorageService.verify_safe_purge_gate(memory_session, target_date) is True
    )


def test_domain_jobs_and_core_scheduler():
    """Verify domain application jobs and core scheduler exports and contracts."""
    from app.core.scheduler import get_next_schedule_delay, start_scheduler_task
    from app.domains.fundamental.application.jobs import (
        FALLBACK_CORE_SYMBOLS,
        run_sync_quarterly_financials_job,
    )
    from app.domains.market_data.application.jobs import (
        CORE_INDEXES,
        run_purge_ticks_job,
        run_sync_daily_market_job,
        run_sync_symbols_job,
    )

    # Verify contracts and constants
    assert "VN30F1M" in CORE_INDEXES
    assert "FPT" in FALLBACK_CORE_SYMBOLS
    assert callable(run_sync_symbols_job)
    assert callable(run_sync_daily_market_job)
    assert callable(run_purge_ticks_job)
    assert callable(run_sync_quarterly_financials_job)
    assert callable(get_next_schedule_delay)
    assert callable(start_scheduler_task)

    # Check delay calculation
    delay = get_next_schedule_delay(now=datetime(2026, 9, 21, 7, 0, 0, tzinfo=UTC))
    assert delay > 0
