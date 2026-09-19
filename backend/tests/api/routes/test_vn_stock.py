"""Bộ kiểm thử cho route vnstock (/api/v1/vnstock)."""

from unittest.mock import patch

import pandas as pd
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


@patch("app.api.routes.vn_stock.vnstock_service.fetch_all_symbols")
def test_get_vnstock_symbols(mock_fetch_all_symbols):
    """Kiểm tra endpoint GET /api/v1/vnstock trả về danh sách {symbol, organ_name}."""
    mock_fetch_all_symbols.return_value = pd.DataFrame(
        {
            "symbol": ["VNM", "FPT"],
            "organ_name": ["Công ty Cổ phần Sữa Việt Nam", "Công ty Cổ phần FPT"],
        }
    )
    client = TestClient(app)
    response = client.get(f"{settings.API_V1_STR}/vnstock")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]["symbol"] == "VNM"
    assert data[0]["organ_name"] == "Công ty Cổ phần Sữa Việt Nam"
    assert data[1]["symbol"] == "FPT"
    assert data[1]["organ_name"] == "Công ty Cổ phần FPT"


@patch("app.api.routes.vn_stock.vnstock_service.fetch_all_symbols")
def test_get_vnstock_symbols_trailing_slash(mock_fetch_all_symbols):
    """Kiểm tra endpoint GET /api/v1/vnstock/ có dấu gạch chéo cuối."""
    mock_fetch_all_symbols.return_value = pd.DataFrame(
        {
            "symbol": ["VNM"],
            "organ_name": ["Vinamilk"],
        }
    )
    client = TestClient(app)
    response = client.get(f"{settings.API_V1_STR}/vnstock/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["symbol"] == "VNM"


def test_get_vnstock_sources():
    """Kiểm tra endpoint GET /api/v1/vnstock/sources trả về danh sách nguồn dữ liệu."""
    client = TestClient(app)
    response = client.get(f"{settings.API_V1_STR}/vnstock/sources")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert any(s in data for s in ["vci", "kbs", "msn", "tcbs", "dnse"])
