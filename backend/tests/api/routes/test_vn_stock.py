"""Bộ kiểm thử cho route vnstock (/api/v1/vnstock)."""

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


def test_get_vnstock_sources():
    """Kiểm tra endpoint GET /api/v1/vnstock trả về danh sách nguồn dữ liệu."""
    client = TestClient(app)
    response = client.get(f"{settings.API_V1_STR}/vnstock")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    # Đảm bảo các nguồn cốt lõi có trong danh sách
    assert any(s in data for s in ["vci", "kbs", "msn", "tcbs", "dnse"])


def test_get_vnstock_sources_trailing_slash():
    """Kiểm tra endpoint GET /api/v1/vnstock/ có trailing slash."""
    client = TestClient(app)
    response = client.get(f"{settings.API_V1_STR}/vnstock/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
