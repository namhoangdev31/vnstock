"""Bộ kiểm thử cho route vnstock (/api/v1/vnstock)."""

from unittest.mock import patch

import pandas as pd
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


@patch(
    "app.domains.market_data.presentation.vnstock_router.vnstock_service.fetch_symbols_by_exchange"
)
def test_get_vnstock_symbols(mock_fetch_symbols):
    """Kiểm tra endpoint GET /api/v1/vnstock trả về danh sách {symbol, organ_name, exchange}."""
    mock_fetch_symbols.return_value = pd.DataFrame(
        {
            "symbol": ["VNM", "SHB"],
            "organ_name": ["Vinamilk", "Ngân hàng SHB"],
            "exchange": ["HOSE", "HNX"],
        }
    )
    client = TestClient(app)
    response = client.get(f"{settings.API_V1_STR}/vnstock")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]["symbol"] == "VNM"
    assert data[0]["organ_name"] == "Vinamilk"
    assert data[0]["exchange"] == "HOSE"
    assert data[1]["symbol"] == "SHB"
    assert data[1]["exchange"] == "HNX"


@patch(
    "app.domains.market_data.presentation.vnstock_router.vnstock_service.fetch_symbols_by_exchange"
)
def test_get_vnstock_symbols_filter_exchange(mock_fetch_symbols):
    """Kiểm tra endpoint GET /api/v1/vnstock?exchange=HOSE có lọc theo sàn."""
    mock_fetch_symbols.return_value = pd.DataFrame(
        {
            "symbol": ["VNM"],
            "organ_name": ["Vinamilk"],
            "exchange": ["HOSE"],
        }
    )
    client = TestClient(app)
    response = client.get(f"{settings.API_V1_STR}/vnstock?exchange=HOSE")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["symbol"] == "VNM"
    assert data[0]["exchange"] == "HOSE"
    mock_fetch_symbols.assert_called_once_with(exchange="HOSE")


def test_get_vnstock_sources():
    """Kiểm tra endpoint GET /api/v1/vnstock/sources trả về danh sách nguồn dữ liệu."""
    client = TestClient(app)
    response = client.get(f"{settings.API_V1_STR}/vnstock/sources")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert any(s in data for s in ["vci", "kbs", "msn", "tcbs", "dnse"])
