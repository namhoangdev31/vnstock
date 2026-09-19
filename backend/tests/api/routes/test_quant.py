"""Kiểm thử tích hợp cho các API Endpoints /api/v1/quant/* (Phase 2).

Kiểm thử 8 REST Endpoints định nghĩa trong TRD Phase 2:
1. GET /api/v1/quant/engine1/technical/{symbol}
2. GET /api/v1/quant/engine2/flow-liquidity
3. GET /api/v1/quant/engine3/basis-volatility
4. POST /api/v1/quant/ensemble/signal
5. GET /api/v1/quant/ensemble/atc-forecast
6. GET /api/v1/quant/ensemble/next-day-forecast
7. GET /api/v1/quant/ensemble/weights
8. PUT /api/v1/quant/ensemble/weights
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

import app.models.models_quant  # noqa: F401
import app.models.models_simulation  # noqa: F401
import app.models.models_stock  # noqa: F401
from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.main import app
from app.models.models_user import User


@pytest.fixture(name="api_client")
def api_client_fixture():
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(test_engine)

    def override_get_db():
        with Session(test_engine) as session:
            yield session

    fake_user = User(
        id=uuid.uuid4(),
        email="test_quant@example.com",
        is_active=True,
        is_superuser=True,
        full_name="Người Dùng Kiểm Thử Quant",
    )

    def override_get_current_user():
        return fake_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


def test_api_engine1_technical(api_client: TestClient):
    """Kiểm tra gọi API GET /api/v1/quant/engine1/technical/VN30F1M."""
    res = api_client.get(f"{settings.API_V1_STR}/quant/engine1/technical/VN30F1M")
    assert res.status_code == 200
    data = res.json()
    assert data["symbol"] == "VN30F1M"
    assert "score" in data
    assert "macd" in data
    assert "camarilla_levels" in data


def test_api_engine2_flow_liquidity(api_client: TestClient):
    """Kiểm tra gọi API GET /api/v1/quant/engine2/flow-liquidity."""
    res = api_client.get(f"{settings.API_V1_STR}/quant/engine2/flow-liquidity")
    assert res.status_code == 200
    data = res.json()
    assert "score" in data
    assert "institutional_momentum" in data
    assert "t2_pressure" in data


def test_api_engine3_basis_volatility(api_client: TestClient):
    """Kiểm tra gọi API GET /api/v1/quant/engine3/basis-volatility."""
    res = api_client.get(
        f"{settings.API_V1_STR}/quant/engine3/basis-volatility?symbol=VN30F1M"
    )
    assert res.status_code == 200
    data = res.json()
    assert data["symbol"] == "VN30F1M"
    assert "basis_value" in data
    assert "basis_zscore" in data
    assert "monte_carlo_targets" in data


def test_api_ensemble_signal(api_client: TestClient):
    """Kiểm tra gọi API POST /api/v1/quant/ensemble/signal (Tuân thủ RULE 3 & RULE 4)."""
    payload = {
        "symbol": "VN30F1M",
        "horizon": "INTRADAY",
        "custom_weights": {"w1": 0.5, "w2": 0.25, "w3": 0.25},
    }
    res = api_client.post(f"{settings.API_V1_STR}/quant/ensemble/signal", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "journal_id" in data
    assert data["symbol"] == "VN30F1M"
    assert data["predicted_direction"] in ("LONG", "SHORT", "NEUTRAL")
    assert "disclaimer" in data
    assert "RULE 4" in data["disclaimer"]


def test_api_atc_forecast(api_client: TestClient):
    """Kiểm tra gọi API GET /api/v1/quant/ensemble/atc-forecast."""
    res = api_client.get(
        f"{settings.API_V1_STR}/quant/ensemble/atc-forecast?symbol=VN30F1M"
    )
    assert res.status_code == 200
    data = res.json()
    assert data["symbol"] == "VN30F1M"
    assert "projected_price" in data
    assert "direction_bias" in data
    assert "disclaimer" in data


def test_api_next_day_forecast(api_client: TestClient):
    """Kiểm tra gọi API GET /api/v1/quant/ensemble/next-day-forecast."""
    res = api_client.get(
        f"{settings.API_V1_STR}/quant/ensemble/next-day-forecast?symbol=VN30F1M"
    )
    assert res.status_code == 200
    data = res.json()
    assert data["symbol"] == "VN30F1M"
    assert "monte_carlo_targets" in data
    assert "price_limit_band" in data
    assert "disclaimer" in data


def test_api_ensemble_weights_get_and_put(api_client: TestClient):
    """Kiểm tra gọi API GET và PUT /api/v1/quant/ensemble/weights."""
    # Lấy thông tin cấu hình trọng số
    res_get = api_client.get(f"{settings.API_V1_STR}/quant/ensemble/weights")
    assert res_get.status_code == 200
    data_get = res_get.json()
    assert "session_phase" in data_get
    assert "weights" in data_get
    assert "schedule" in data_get

    # Cập nhật trọng số tùy chỉnh
    update_payload = {"w1": 0.6, "w2": 0.2, "w3": 0.2}
    res_put = api_client.put(
        f"{settings.API_V1_STR}/quant/ensemble/weights",
        json=update_payload,
    )
    assert res_put.status_code == 200
    data_put = res_put.json()
    assert data_put["weights"]["w1"] == 0.6
    assert data_put["weights"]["w2"] == 0.2
    assert data_put["weights"]["w3"] == 0.2
