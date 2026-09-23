"""Unit and contract tests for all Reference Data methods in VnstockService."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from app.domains.market_data.infrastructure.vnstock_adapter import VnstockService


@pytest.fixture
def service() -> VnstockService:
    """Khởi tạo VnstockService với throttle mock cho test."""
    mock_limiter = MagicMock()
    return VnstockService(limiter=mock_limiter)


@patch("app.domains.market_data.infrastructure.vnstock_adapter.Reference")
def test_reference_equity_methods(
    mock_ref_cls: MagicMock, service: VnstockService
) -> None:
    """Kiểm thử đầy đủ các phương thức thuộc lớp Reference.equity."""
    mock_ref = MagicMock()
    mock_ref_cls.return_value = mock_ref
    mock_equity = MagicMock()
    mock_ref.equity.return_value = mock_equity

    # 1. list
    mock_equity.list.return_value = pd.DataFrame(
        [{"symbol": "VCB", "organ_name": "Vietcombank"}]
    )
    df_list = service.fetch_reference_equity_list()
    assert len(df_list) == 1
    assert df_list.iloc[0]["symbol"] == "VCB"
    mock_equity.list.assert_called_once()

    # 2. list_by_industry
    mock_equity.list_by_industry.return_value = pd.DataFrame(
        [{"symbol": "FPT", "industry": "Technology"}]
    )
    df_ind = service.fetch_reference_equity_by_industry()
    assert len(df_ind) == 1
    mock_equity.list_by_industry.assert_called_once()

    # 3. list_by_exchange
    mock_equity.list_by_exchange.return_value = pd.DataFrame(
        [{"symbol": "HPG", "exchange": "HOSE"}]
    )
    df_ex = service.fetch_reference_equity_by_exchange()
    assert len(df_ex) == 1
    mock_equity.list_by_exchange.assert_called_once()

    # 4. list_by_group
    mock_equity.list_by_group.return_value = pd.DataFrame(
        [{"symbol": "SSI", "group": "VN30"}]
    )
    df_grp = service.fetch_reference_equity_by_group("VN30")
    assert len(df_grp) == 1
    mock_equity.list_by_group.assert_called_once_with(group="VN30")


@patch("app.domains.market_data.infrastructure.vnstock_adapter.Reference")
def test_reference_index_methods(
    mock_ref_cls: MagicMock, service: VnstockService
) -> None:
    """Kiểm thử các phương thức thuộc lớp Reference.index."""
    mock_ref = MagicMock()
    mock_ref_cls.return_value = mock_ref
    mock_idx = MagicMock()
    mock_ref.index.return_value = mock_idx

    # 1. list
    mock_idx.list.return_value = pd.DataFrame(
        [{"symbol": "VNINDEX", "name": "VNINDEX", "group": "HOSE"}]
    )
    df_list = service.fetch_reference_index_list()
    assert len(df_list) == 1
    assert service.fetch_index_list().iloc[0]["symbol"] == "VNINDEX"

    # 2. groups
    mock_idx.groups.return_value = pd.DataFrame(
        [{"group": "HOSE", "name": "HOSE Indices"}]
    )
    df_groups = service.fetch_reference_index_groups()
    assert len(df_groups) == 1

    # 3. members
    mock_idx.members.return_value = ["VCB", "FPT", "HPG"]
    df_members = service.fetch_reference_index_members("VN30")
    assert len(df_members) == 3
    mock_idx.members.assert_called_with(symbol="VN30")


@patch("app.domains.market_data.infrastructure.vnstock_adapter.Reference")
def test_reference_other_asset_classes(
    mock_ref_cls: MagicMock, service: VnstockService
) -> None:
    """Kiểm thử các danh mục tài sản khác (ETF, Futures, Warrant, Bond, Fund)."""
    mock_ref = MagicMock()
    mock_ref_cls.return_value = mock_ref

    # 1. ETF
    mock_etf = MagicMock()
    mock_ref.etf.return_value = mock_etf
    mock_etf.list.return_value = ["E1VFVN30", "FUEVFVND"]
    df_etf = service.fetch_reference_etf_list()
    assert len(df_etf) == 2

    # 2. Futures
    mock_fut = MagicMock()
    mock_ref.futures.return_value = mock_fut
    mock_fut.list.return_value = ["VN30F1M", "VN30F2M"]
    df_fut = service.fetch_reference_futures_list()
    assert len(df_fut) == 2

    # 3. Warrant
    mock_war = MagicMock()
    mock_ref.warrant.return_value = mock_war
    mock_war.list.return_value = ["CFPT2301", "CHPG2301"]
    df_war = service.fetch_reference_warrant_list()
    assert len(df_war) == 2

    # 4. Bond
    mock_bnd = MagicMock()
    mock_ref.bond.return_value = mock_bnd
    mock_bnd.list.return_value = pd.DataFrame(
        [{"symbol": "TP2024", "name": "Trai phieu"}]
    )
    df_bnd = service.fetch_reference_bond_list()
    assert len(df_bnd) == 1

    # 5. Fund
    mock_fnd = MagicMock()
    mock_ref.fund.return_value = mock_fnd
    mock_fnd.list.return_value = pd.DataFrame(
        [{"symbol": "VESAF", "name": "VinaCapital VESAF"}]
    )
    df_fnd = service.fetch_reference_fund_list()
    assert len(df_fnd) == 1
    assert service.fetch_funds_list().iloc[0]["symbol"] == "VESAF"


@patch("app.domains.market_data.infrastructure.vnstock_adapter.Reference")
def test_reference_search_methods(
    mock_ref_cls: MagicMock, service: VnstockService
) -> None:
    """Kiểm thử chức năng tìm kiếm Reference.search."""
    mock_ref = MagicMock()
    mock_ref_cls.return_value = mock_ref
    mock_search = MagicMock()
    mock_ref.search = mock_search

    # 1. Search symbol
    mock_search.symbol.return_value = pd.DataFrame(
        [{"symbol": "FPT", "name": "Cong nghe FPT"}]
    )
    df_sym = service.search_reference_symbol("FPT", limit=5)
    assert len(df_sym) == 1
    mock_search.symbol.assert_called_once_with(query="FPT", limit=5)
    assert service.search_symbols("FPT").iloc[0]["symbol"] == "FPT"

    # 2. Search info
    mock_search.info.return_value = pd.DataFrame(
        [{"organ_name": "FPT Corp", "type": "Stock"}]
    )
    df_info = service.search_reference_info("FPT", limit=5)
    assert len(df_info) == 1
    mock_search.info.assert_called_once_with(query="FPT", limit=5)


@patch("app.domains.market_data.infrastructure.vnstock_adapter.Reference")
def test_reference_company_methods(
    mock_ref_cls: MagicMock, service: VnstockService
) -> None:
    """Kiểm thử đầy đủ 9 phương thức thuộc lớp Reference.company."""
    mock_ref = MagicMock()
    mock_ref_cls.return_value = mock_ref
    mock_comp = MagicMock()
    mock_ref.company.return_value = mock_comp

    # 1. info
    mock_comp.info.return_value = pd.DataFrame(
        [{"symbol": "VCB", "market_cap": 400000}]
    )
    assert not service.fetch_reference_company_info("VCB").empty
    mock_ref.company.assert_called_with("VCB")

    # 2. shareholders
    mock_comp.shareholders.return_value = pd.DataFrame(
        [{"name": "SBV", "percent": 74.8}]
    )
    assert not service.fetch_reference_company_shareholders("VCB").empty

    # 3. officers
    mock_comp.officers.return_value = pd.DataFrame(
        [{"name": "Nguyen Van A", "position": "Chairman"}]
    )
    assert not service.fetch_reference_company_officers("VCB").empty

    # 4. subsidiaries
    mock_comp.subsidiaries.return_value = pd.DataFrame(
        [{"name": "VCBS", "ownership": 100.0}]
    )
    assert not service.fetch_reference_company_subsidiaries("VCB").empty

    # 5. ownership
    mock_comp.ownership.return_value = pd.DataFrame(
        [{"category": "State", "percent": 74.8}]
    )
    assert not service.fetch_reference_company_ownership("VCB").empty

    # 6. insider_trading
    mock_comp.insider_trading.return_value = pd.DataFrame(
        [{"date": "2024-01-01", "volume": 10000}]
    )
    assert not service.fetch_reference_company_insider_trading("VCB").empty

    # 7. capital_history
    mock_comp.capital_history.return_value = pd.DataFrame(
        [{"year": 2023, "capital": 47325}]
    )
    assert not service.fetch_reference_company_capital_history("VCB").empty

    # 8. news
    mock_comp.news.return_value = pd.DataFrame(
        [{"title": "VCB announcement", "published_date": "2024-01-02"}]
    )
    assert not service.fetch_reference_company_news("VCB").empty

    # 9. events
    mock_comp.events.return_value = pd.DataFrame(
        [{"event": "Dividend", "date": "2024-05-15"}]
    )
    assert not service.fetch_reference_company_events("VCB").empty


@patch("app.domains.market_data.infrastructure.vnstock_adapter.Reference")
def test_reference_graceful_error_handling(
    mock_ref_cls: MagicMock, service: VnstockService
) -> None:
    """Đảm bảo mọi phương thức của Reference đều bắt lỗi an toàn và trả về DataFrame rỗng."""
    mock_ref = MagicMock()
    mock_ref_cls.return_value = mock_ref

    mock_ref.equity.side_effect = Exception("Equity network error")
    mock_ref.index.side_effect = Exception("Index error")
    mock_ref.etf.side_effect = Exception("ETF error")
    mock_ref.futures.side_effect = Exception("Futures error")
    mock_ref.warrant.side_effect = Exception("Warrant error")
    mock_ref.bond.side_effect = Exception("Bond error")
    mock_ref.fund.side_effect = Exception("Fund error")
    mock_ref.company.side_effect = Exception("Company error")

    mock_search = MagicMock()
    mock_search.symbol.side_effect = Exception("Search error")
    mock_search.info.side_effect = Exception("Search info error")
    mock_ref.search = mock_search

    assert service.fetch_reference_equity_list().empty
    assert service.fetch_reference_equity_by_industry().empty
    assert service.fetch_reference_equity_by_exchange().empty
    assert service.fetch_reference_equity_by_group("VN30").empty

    assert service.fetch_reference_index_list().empty
    assert service.fetch_reference_index_groups().empty
    assert service.fetch_reference_index_members("VN30").empty

    assert service.fetch_reference_etf_list().empty
    assert service.fetch_reference_futures_list().empty
    assert service.fetch_reference_warrant_list().empty
    assert service.fetch_reference_bond_list().empty
    assert service.fetch_reference_fund_list().empty

    assert service.search_reference_symbol("VCB").empty
    assert service.search_reference_info("VCB").empty

    assert service.fetch_reference_company_info("VCB").empty
    assert service.fetch_reference_company_shareholders("VCB").empty
    assert service.fetch_reference_company_officers("VCB").empty
    assert service.fetch_reference_company_subsidiaries("VCB").empty
    assert service.fetch_reference_company_ownership("VCB").empty
    assert service.fetch_reference_company_insider_trading("VCB").empty
    assert service.fetch_reference_company_capital_history("VCB").empty
    assert service.fetch_reference_company_events("VCB").empty
    assert service.fetch_reference_events_calendar().empty
    assert service.fetch_reference_industry_list().empty
    assert service.fetch_reference_market_status().empty


@patch("app.domains.market_data.infrastructure.vnstock_adapter.Reference")
def test_reference_events_industry_market(
    mock_ref_cls: MagicMock, service: VnstockService
) -> None:
    """Kiểm thử các phương thức Reference.events, Reference.industry, Reference.market."""
    mock_ref = MagicMock()
    mock_ref_cls.return_value = mock_ref

    mock_events = MagicMock()
    mock_ref.events = mock_events
    mock_events.calendar.return_value = pd.DataFrame(
        [{"event": "Dividend", "date": "2024-06-01"}]
    )
    df_events = service.fetch_reference_events_calendar()
    assert len(df_events) == 1

    mock_industry = MagicMock()
    mock_ref.industry = mock_industry
    mock_industry.list.return_value = pd.DataFrame(
        [{"industry_code": "8300", "industry_name": "Banks"}]
    )
    df_ind = service.fetch_reference_industry_list()
    assert len(df_ind) == 1

    mock_market = MagicMock()
    mock_ref.market = mock_market
    mock_market.status.return_value = pd.DataFrame(
        [{"status": "OPEN", "session": "CONTINUOUS"}]
    )
    df_status = service.fetch_reference_market_status()
    assert len(df_status) == 1


def test_reference_show_api_and_doc(service: VnstockService) -> None:
    """Kiểm thử phương thức tiện ích show_api và show_doc."""
    with patch("vnstock.show_api") as mock_api, patch("vnstock.show_doc") as mock_doc:
        service.show_api("Reference")
        mock_api.assert_called_once_with("Reference")

        service.show_doc(VnstockService)
        mock_doc.assert_called_once_with(VnstockService)
