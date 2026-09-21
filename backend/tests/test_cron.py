"""Bộ kiểm thử đơn vị cho hệ thống Cronjob đồng bộ mã chứng khoán & phái sinh."""

from datetime import date, datetime
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

import pandas as pd
from sqlmodel import Session, select

from app.core.config import settings
from app.cron.scheduler import get_next_schedule_delay, start_scheduler_task
from app.cron.sync_symbols import run_sync_symbols_job
from app.models.models_stock import (
    DataSyncLog,
    DerivativeContract,
    StockSymbol,
)
from app.services.data_sync import DataSyncManager, get_third_thursday
from tests.utils.phase1 import (
    api_client,  # noqa: F401
    session,  # noqa: F401
    sqlite_engine,  # noqa: F401
    user,  # noqa: F401
)

VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")


def test_get_third_thursday() -> None:
    """Kiểm tra logic tính ngày đáo hạn hợp đồng phái sinh (Thứ Năm lần thứ 3 trong tháng)."""
    # Tháng 9/2024: Thứ 5 lần 1 là ngày 5, lần 2 là 12, lần 3 là 19
    assert get_third_thursday(2024, 9) == date(2024, 9, 19)

    # Tháng 9/2026: Thứ 5 lần 1 là ngày 3, lần 2 là 10, lần 3 là 17
    assert get_third_thursday(2026, 9) == date(2026, 9, 17)

    # Tháng 1/2025: Thứ 5 lần 1 là ngày 2, lần 2 là 9, lần 3 là 16
    assert get_third_thursday(2025, 1) == date(2025, 1, 16)


def test_get_next_schedule_delay() -> None:
    """Kiểm tra hàm tính độ trễ giây tới 08:00 Thứ 2 và Thứ 5 tiếp theo."""
    # Giả lập: Thứ 2 lúc 07:00 sáng -> còn đúng 3600 giây đến 08:00 cùng ngày
    monday_morning = datetime(2026, 9, 21, 7, 0, 0, tzinfo=VN_TZ)
    delay_mon = get_next_schedule_delay(now=monday_morning)
    assert delay_mon == 3600.0

    # Giả lập: Thứ 2 lúc 09:00 sáng -> lần chạy tiếp theo là Thứ 5 lúc 08:00 (cách 3 ngày trừ 1 giờ = 71 giờ)
    monday_after = datetime(2026, 9, 21, 9, 0, 0, tzinfo=VN_TZ)
    delay_next_thu = get_next_schedule_delay(now=monday_after)
    assert delay_next_thu == 71 * 3600.0

    # Giả lập: Thứ 5 lúc 09:00 sáng -> lần chạy tiếp theo là Thứ 2 tuần sau lúc 08:00 (cách 4 ngày trừ 1 giờ = 95 giờ)
    thursday_after = datetime(2026, 9, 24, 9, 0, 0, tzinfo=VN_TZ)
    delay_next_mon = get_next_schedule_delay(now=thursday_after)
    assert delay_next_mon == 95 * 3600.0


def test_run_sync_symbols_job_with_mock_data(session: Session) -> None:  # noqa: F811
    """Kiểm tra runner đồng bộ dữ liệu vào StockSymbol và DerivativeContract."""
    mock_svc = MagicMock()
    mock_svc.source = "VCI"

    # Giả lập danh sách cổ phiếu
    mock_svc.fetch_all_symbols.return_value = pd.DataFrame(
        [
            {
                "ticker": "VNM",
                "organName": "CTCP Sữa Việt Nam",
                "exchange": "HOSE",
                "icbCode": "3577",
                "icbName": "Thực phẩm và đồ uống",
                "type": "stock",
            },
            {
                "ticker": "FPT",
                "organName": "CTCP FPT",
                "exchange": "HOSE",
                "icbCode": "9533",
                "icbName": "Công nghệ thông tin",
                "type": "stock",
            },
        ]
    )

    # Giả lập rổ VN30
    mock_svc.fetch_group_symbols.return_value = ["VNM", "FPT"]

    # Giả lập hợp đồng phái sinh bổ sung
    mock_svc.fetch_derivatives_list.return_value = pd.DataFrame(
        [{"ticker": "VN30F2609"}]
    )

    with patch("app.cron.sync_symbols.vnstock_service", mock_svc):
        log = run_sync_symbols_job(session=session)

    assert log.status == "success"
    assert log.rows_synced >= 4

    # Kiểm tra mã VNM
    vnm = session.get(StockSymbol, "VNM")
    assert vnm is not None
    assert vnm.exchange == "HOSE"
    assert vnm.index_group == "VN30"
    assert vnm.icb_code == "3577"
    assert vnm.asset_type == "stock"
    assert vnm.lot_size == 100

    # Kiểm tra hợp đồng phái sinh chuẩn VN30F1M
    f1m = session.get(StockSymbol, "VN30F1M")
    assert f1m is not None
    assert f1m.asset_type == "derivative"
    assert f1m.lot_size == 1

    contract_f1m = session.get(DerivativeContract, "VN30F1M")
    assert contract_f1m is not None
    assert contract_f1m.underlying_symbol == "VN30"
    assert contract_f1m.multiplier == 100_000.0
    assert contract_f1m.is_active is True

    # Kiểm tra log kiểm toán DataSyncLog
    sync_logs = session.exec(
        select(DataSyncLog).where(DataSyncLog.sync_type == "symbols")
    ).all()
    assert len(sync_logs) >= 1
    assert sync_logs[0].status == "success"


def test_cron_sync_symbols_api_endpoint(api_client, monkeypatch) -> None:  # noqa: F811
    """Kiểm tra bảo mật và hoạt động của endpoint POST /api/v1/stock/cron/sync-symbols."""
    monkeypatch.setattr(settings, "CRON_SECRET_KEY", "test-cron-secret-12345")

    # 1. Gọi không kèm secret -> Bị từ chối 403
    resp_no_secret = api_client.post("/api/v1/stock/cron/sync-symbols")
    assert resp_no_secret.status_code == 403

    # 2. Gọi kèm secret sai -> Bị từ chối 403
    resp_bad_secret = api_client.post(
        "/api/v1/stock/cron/sync-symbols",
        headers={"X-Cron-Secret": "wrong-secret"},
    )
    assert resp_bad_secret.status_code == 403

    # 3. Gọi kèm secret đúng qua Header
    with patch.object(DataSyncManager, "sync_symbols") as mock_sync:
        mock_log = DataSyncLog(
            sync_type="symbols",
            source="VCI",
            status="success",
            rows_synced=15,
        )
        mock_sync.return_value = mock_log

        resp_ok = api_client.post(
            "/api/v1/stock/cron/sync-symbols",
            headers={"X-Cron-Secret": "test-cron-secret-12345"},
        )
        assert resp_ok.status_code == 200
        data = resp_ok.json()
        assert data["status"] == "success"
        assert data["rows_synced"] == 15

    # 4. Gọi kèm secret đúng qua Query param
    with patch.object(DataSyncManager, "sync_symbols") as mock_sync:
        mock_log = DataSyncLog(
            sync_type="symbols",
            source="VCI",
            status="success",
            rows_synced=10,
        )
        mock_sync.return_value = mock_log

        resp_query = api_client.post(
            "/api/v1/stock/cron/sync-symbols?secret_key=test-cron-secret-12345"
        )
        assert resp_query.status_code == 200
        data = resp_query.json()
        assert data["status"] == "success"
        assert data["rows_synced"] == 10


def test_start_scheduler_task_flag() -> None:
    """Kiểm tra cờ ENABLE_INPROCESS_CRON."""
    with patch.object(settings, "ENABLE_INPROCESS_CRON", False):
        task = start_scheduler_task()
        assert task is None


def test_run_sync_daily_market_job(session: Session) -> None:  # noqa: F811
    """Kiểm tra runner đồng bộ nến ngày sau phiên ATC."""
    from app.cron.sync_daily_market import run_sync_daily_market_job

    mock_svc = MagicMock()
    mock_svc.source = "VCI"
    mock_svc.fetch_group_symbols.return_value = ["FPT"]
    mock_log = DataSyncLog(
        sync_type="daily",
        symbol="FPT",
        source="VCI",
        status="success",
        rows_synced=1,
    )
    with (
        patch("app.cron.sync_daily_market.vnstock_service", mock_svc),
        patch.object(DataSyncManager, "sync_daily_incremental", return_value=mock_log),
    ):
        logs = run_sync_daily_market_job(session=session, delay_sec=0)
        assert len(logs) >= 1
        assert logs[0].status == "success"
