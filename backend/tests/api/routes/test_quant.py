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
from datetime import UTC

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

import app.domains.market_data.domain.models  # noqa: F401
import app.domains.quant.domain.models  # noqa: F401
import app.domains.simulation.domain.models  # noqa: F401
from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.domains.identity.domain.models import User
from app.main import app as fastapi_app


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
        hashed_password="fakehashedpassword",
        is_active=True,
        is_superuser=True,
        full_name="Người Dùng Kiểm Thử Quant",
    )

    def override_get_current_user():
        return fake_user

    fastapi_app.dependency_overrides[get_db] = override_get_db
    fastapi_app.dependency_overrides[get_current_user] = override_get_current_user

    with TestClient(fastapi_app) as client:
        yield client
    fastapi_app.dependency_overrides.pop(get_db, None)
    fastapi_app.dependency_overrides.pop(get_current_user, None)


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


def test_api_forecast_journal_lifecycle(api_client: TestClient):
    """Kiểm tra toàn bộ vòng đời của Forecast Journal qua REST API (RULE 3 Audit Ledger)."""
    from datetime import datetime

    # 1. Tạo bản ghi dự phóng mới (pending)
    pred_time = datetime(2026, 9, 23, 9, 0, tzinfo=UTC).isoformat()
    create_payload = {
        "symbol": "VN30F1M",
        "horizon": "T_PLUS_1",
        "predicted_at": pred_time,
        "predicted_value": 1315.5,
        "predicted_direction": "BULLISH",
        "model_version": "v2.0.0",
        "engine_weights": {"w1": 0.5, "w2": 0.25, "w3": 0.25},
        "parameter_snapshot": {"confidence": 0.85},
    }
    res_post = api_client.post(f"{settings.API_V1_STR}/forecast", json=create_payload)
    assert res_post.status_code == 200
    entry = res_post.json()
    journal_id = entry["id"]
    assert entry["symbol"] == "VN30F1M"
    assert entry["status"] == "pending"

    # 2. Truy vấn danh sách và chi tiết
    res_list = api_client.get(f"{settings.API_V1_STR}/forecast?symbol=VN30F1M")
    assert res_list.status_code == 200
    assert len(res_list.json()) >= 1

    res_get = api_client.get(f"{settings.API_V1_STR}/forecast/{journal_id}")
    assert res_get.status_code == 200
    assert res_get.json()["id"] == journal_id

    # 3. Chốt kết quả thực tế (resolve)
    real_time = datetime(2026, 9, 23, 15, 0, tzinfo=UTC).isoformat()
    resolve_payload = {
        "actual_value": 1320.0,
        "actual_direction": "BULLISH",
        "realized_at": real_time,
    }
    res_resolve = api_client.post(
        f"{settings.API_V1_STR}/forecast/{journal_id}/resolve",
        json=resolve_payload,
    )
    assert res_resolve.status_code == 200
    resolved_entry = res_resolve.json()
    assert resolved_entry["status"] == "resolved"
    assert resolved_entry["actual_value"] == 1320.0

    # 4. Chấm điểm dự phóng (score)
    res_score = api_client.post(f"{settings.API_V1_STR}/forecast/{journal_id}/score")
    assert res_score.status_code == 200
    scored_entry = res_score.json()
    assert scored_entry["status"] == "scored"
    assert scored_entry["error"] == 4.5  # |1315.5 - 1320.0|
    assert scored_entry["score"] == 1.0  # Direction đúng

    # 5. Tổng hợp độ chính xác (aggregate)
    res_agg = api_client.get(f"{settings.API_V1_STR}/forecast/aggregate?symbol=VN30F1M")
    assert res_agg.status_code == 200
    agg_data = res_agg.json()
    assert agg_data["count"] >= 1
    assert agg_data["directional_accuracy"] == 1.0
    assert agg_data["mae"] == 4.5

    # 6. Kiểm tra các nhánh 404
    non_existent = str(uuid.uuid4())
    assert (
        api_client.get(f"{settings.API_V1_STR}/forecast/{non_existent}").status_code
        == 404
    )
    assert (
        api_client.post(
            f"{settings.API_V1_STR}/forecast/{non_existent}/resolve",
            json={"actual_value": 1.0, "actual_direction": "BULLISH"},
        ).status_code
        == 404
    )
    assert (
        api_client.post(
            f"{settings.API_V1_STR}/forecast/{non_existent}/score"
        ).status_code
        == 404
    )

    # 7. Kiểm tra tham số bộ lọc danh sách
    res_filtered = api_client.get(
        f"{settings.API_V1_STR}/forecast?status=scored&from_date=2026-09-01T00:00:00Z&to_date=2026-09-30T23:59:59Z"
    )
    assert res_filtered.status_code == 200
    assert len(res_filtered.json()) >= 1
