"""Tests for Vnstock Capabilities API and Service integration."""

from fastapi.testclient import TestClient

from app.services.vnstock_registry import (
    CapabilityStatus,
    VnstockCapabilityRegistry,
)
from app.services.vnstock_service import VnstockService
from tests.utils.phase1 import (
    api_client,  # noqa: F401
    session,  # noqa: F401
    sqlite_engine,  # noqa: F401
    user,  # noqa: F401
)


def test_vnstock_service_capability_methods() -> None:
    """Kiểm tra các helper method tích hợp capability trong VnstockService."""
    service = VnstockService()

    # 1. is_capability_available
    assert service.is_capability_available("quote.history_daily") is True
    assert service.is_capability_available("flow.proprietary") is False
    assert service.is_capability_available("external.crypto") is False
    assert service.is_capability_available("nonexistent.key") is False

    # 2. check_capability
    avail = service.check_capability("quote.history_daily")
    assert avail.status == CapabilityStatus.AVAILABLE
    assert "vci" in avail.supported_sources

    # 3. get_capability_sources
    sources = service.get_capability_sources("quote.history_daily")
    assert isinstance(sources, list)
    assert len(sources) > 0
    assert "vci" in sources

    # Capability không tồn tại hoặc unverified -> trả về list rỗng
    assert service.get_capability_sources("flow.proprietary") == []
    assert service.get_capability_sources("nonexistent.key") == []


def test_api_get_all_capabilities(api_client: TestClient) -> None:  # noqa: F811
    """Test endpoint GET /api/v1/vnstock/capabilities trả về toàn bộ ma trận."""
    response = api_client.get("/api/v1/vnstock/capabilities")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert len(data) == len(VnstockCapabilityRegistry.CAPABILITIES)
    assert "quote.history_daily" in data
    assert data["quote.history_daily"]["status"] == "available"


def test_api_get_capabilities_filtered_by_status(
    api_client: TestClient,  # noqa: F811
) -> None:
    """Test lọc capabilities theo status: available, unavailable, out_of_scope."""
    # Lọc available
    resp_avail = api_client.get("/api/v1/vnstock/capabilities?status=available")
    assert resp_avail.status_code == 200
    data_avail = resp_avail.json()
    assert all(item["status"] == "available" for item in data_avail.values())
    assert "quote.history_daily" in data_avail

    # Lọc unavailable
    resp_unavail = api_client.get("/api/v1/vnstock/capabilities?status=unavailable")
    assert resp_unavail.status_code == 200
    data_unavail = resp_unavail.json()
    assert all(item["status"] == "unavailable" for item in data_unavail.values())
    assert "flow.proprietary" in data_unavail

    # Lọc out_of_scope
    resp_oos = api_client.get("/api/v1/vnstock/capabilities?status=out_of_scope")
    assert resp_oos.status_code == 200
    data_oos = resp_oos.json()
    assert all(item["status"] == "out_of_scope" for item in data_oos.values())
    assert "external.crypto" in data_oos


def test_api_get_capabilities_filtered_by_module(
    api_client: TestClient,  # noqa: F811
) -> None:
    """Test lọc capabilities theo module."""
    resp = api_client.get("/api/v1/vnstock/capabilities?module=Quote")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) > 0
    assert all(item["module"].lower() == "quote" for item in data.values())


def test_api_get_capability_detail(api_client: TestClient) -> None:  # noqa: F811
    """Test endpoint GET /api/v1/vnstock/capabilities/{key}."""
    # 1. Key hợp lệ
    resp = api_client.get("/api/v1/vnstock/capabilities/quote.history_daily")
    assert resp.status_code == 200
    data = resp.json()
    assert data["module"] == "Quote"
    assert data["action"] == "history(interval='1D')"
    assert data["status"] == "available"
    assert data["primary_source"] == "vci"

    # 2. Key unavailable
    resp_unavail = api_client.get("/api/v1/vnstock/capabilities/flow.proprietary")
    assert resp_unavail.status_code == 200
    data_unavail = resp_unavail.json()
    assert data_unavail["status"] == "unavailable"
    assert "Vnstock v4 Community tier" in data_unavail["reason"]

    # 3. Key không tồn tại -> 404
    resp_404 = api_client.get("/api/v1/vnstock/capabilities/nonexistent.capability")
    assert resp_404.status_code == 404
    assert "không tồn tại" in resp_404.json()["detail"]
