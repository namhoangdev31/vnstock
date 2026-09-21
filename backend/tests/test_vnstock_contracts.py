"""Contract tests for Vnstock v4 Capability Registry, Source Provenance and Availability."""

from app.services.vnstock_registry import (
    CapabilityStatus,
    DataAvailability,
    ProviderResponse,
    VnstockCapabilityRegistry,
)
from app.services.vnstock_service import VnstockService


def test_registry_fallback_order_excludes_dnse():
    """Fallback order must prioritize stable sources and exclude unsupported sources like DNSE."""
    order = VnstockCapabilityRegistry.FALLBACK_ORDER
    assert order == ["vci", "kbs", "msn"]
    assert "dnse" not in order


def test_registry_available_capabilities():
    """Verify that mapped and supported capabilities are marked as AVAILABLE."""
    available_keys = [
        "quote.history_daily",
        "quote.history_intraday",
        "quote.intraday_ticks",
        "listing.all_symbols",
        "listing.group_symbols",
        "listing.industries_icb",
        "company.overview",
        "finance.income_statement",
        "finance.balance_sheet",
        "finance.cash_flow",
        "fundamental.ratios",
        "fundamental.income_statement",
        "fundamental.balance_sheet",
        "fundamental.cash_flow",
        "fundamental.ratio",
        "retail.gold",
        "retail.exchange_rate",
        "market.quote",
        "market.equity_ohlcv",
        "market.equity_trades",
        "market.equity_quote",
        "market.index_ohlcv",
        "market.futures",
        "market.futures_ohlcv",
        "market.futures_trades",
        "market.warrant_ohlcv",
        "market.warrant_quote",
        "market.warrant_trades",
        "market.etf_ohlcv",
        "market.etf_quote",
        "market.etf_trades",
        "market.fund_nav",
        "market.fund_history",
        "market.fund_top_holding",
        "market.fund_asset_holding",
        "market.fund_industry_holding",
        "market.forex_ohlcv",
        "market.crypto_ohlcv",
        "market.commodity_ohlcv",
        "market.bond_ohlcv",
        "market.bond_quote",
        "market.bond_trades",
        "reference.equity_list",
        "reference.equity_list_by_industry",
        "reference.equity_list_by_exchange",
        "reference.equity_list_by_group",
        "reference.index_list",
        "reference.index_groups",
        "reference.index_members",
        "reference.company_info",
        "reference.company_shareholders",
        "reference.company_officers",
        "reference.company_subsidiaries",
        "reference.company_ownership",
        "reference.company_insider_trading",
        "reference.company_capital_history",
        "reference.company_news",
        "reference.company_events",
        "reference.etf_list",
        "reference.futures_list",
        "reference.warrant_list",
        "reference.bond_list",
        "reference.fund_list",
        "reference.search_symbol",
        "reference.search_info",
        "reference.events_calendar",
        "reference.industry_list",
        "reference.market_status",
        "reference.show_api",
        "reference.show_doc",
    ]
    for key in available_keys:
        assert VnstockCapabilityRegistry.is_available(key) is True
        avail = VnstockCapabilityRegistry.check_availability(key)
        assert avail.status == CapabilityStatus.AVAILABLE
        assert len(avail.supported_sources) > 0


def test_registry_unavailable_capabilities():
    """Verify unverified/unsupported capabilities return UNAVAILABLE with reason (Rule 3)."""
    unavailable_keys = ["flow.proprietary", "flow.market_breadth_ad"]
    for key in unavailable_keys:
        assert VnstockCapabilityRegistry.is_available(key) is False
        avail = VnstockCapabilityRegistry.check_availability(key)
        assert avail.status == CapabilityStatus.UNAVAILABLE
        assert avail.reason is not None
        assert len(avail.supported_sources) == 0


def test_registry_out_of_scope_capabilities():
    """Verify out-of-scope assets (crypto, global commodities) return OUT_OF_SCOPE."""
    out_of_scope_keys = ["external.crypto", "external.global_commodities"]
    for key in out_of_scope_keys:
        assert VnstockCapabilityRegistry.is_available(key) is False
        avail = VnstockCapabilityRegistry.check_availability(key)
        assert avail.status == CapabilityStatus.OUT_OF_SCOPE
        assert avail.reason is not None


def test_registry_unknown_key():
    """Verify unknown capability key returns UNAVAILABLE with descriptive reason."""
    avail = VnstockCapabilityRegistry.check_availability("nonexistent.capability")
    assert avail.status == CapabilityStatus.UNAVAILABLE
    assert "not registered" in (avail.reason or "")


def test_provider_response_serialization():
    """Test ProviderResponse container serialization and metadata."""
    avail = DataAvailability(
        status=CapabilityStatus.AVAILABLE,
        supported_sources=["vci", "kbs"],
        is_fallback=True,
        actual_source="kbs",
    )
    resp = ProviderResponse(
        data={"symbol": "HPG", "close": 28500.0},
        actual_source="kbs",
        is_fallback=True,
        latency_ms=12.5,
        availability=avail,
    )
    data = resp.model_dump()
    assert data["actual_source"] == "kbs"
    assert data["is_fallback"] is True
    assert data["latency_ms"] == 12.5
    assert data["availability"]["status"] == "available"


def test_vnstock_service_source_provenance():
    """Test VnstockService tracking of last_successful_source."""
    service = VnstockService()
    # Initially None before any call
    assert service.last_successful_source is None
    # Source candidate priority
    assert service.sources == ["vci", "kbs", "msn"]
