"""Unit tests for run_purge_ticks_job, CLI purge-ticks, and API webhook."""

from datetime import date, datetime, time
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select
from typer.testing import CliRunner

from app.cli import app as cli_app
from app.core.config import settings
from app.cron.purge_ticks import run_purge_ticks_job
from app.models.entities.stock import (
    DataSyncLog,
    StockOHLCVIntraday,
    StockSymbol,
    StockTickIntraday,
)
from tests.utils.phase1 import (
    api_client,  # noqa: F401
    session,  # noqa: F401
    sqlite_engine,  # noqa: F401
    user,  # noqa: F401
)

VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")
runner = CliRunner()


def test_run_purge_ticks_job_with_safe_gate_pass(
    session: Session,  # noqa: F811
) -> None:
    """Kiểm tra run_purge_ticks_job xóa tick cũ thành công khi Safe Purge Gate thỏa mãn."""
    sym = StockSymbol(symbol="HPG", organ_name="Hòa Phát", exchange="HOSE")
    session.add(sym)
    session.commit()

    old_date = date(2026, 7, 1)
    # Thêm 2 tick cũ
    for i in range(2):
        tick = StockTickIntraday(
            symbol="HPG",
            timestamp=datetime.combine(old_date, time(9, 30 + i), tzinfo=VN_TZ),
            price=28000.0,
            volume=1000,
            match_type="BU",
            source="VCI",
        )
        session.add(tick)

    # Thêm nến 1m để thỏa mãn Safe Purge Gate
    for m in range(5):
        bar = StockOHLCVIntraday(
            symbol="HPG",
            timestamp=datetime.combine(old_date, time(9, 15 + m), tzinfo=VN_TZ),
            interval="1m",
            open=28000.0,
            high=28200.0,
            low=27900.0,
            close=28100.0,
            volume=50000,
            source="VCI",
        )
        session.add(bar)
    session.commit()

    # Chạy job purge với min_bars=5, retention_days=1 (old_date cũ hơn hôm nay nhiều ngày)
    log = run_purge_ticks_job(
        session=session,
        retention_days=1,
        force=False,
        min_bars=5,
    )

    assert log.status == "success"
    assert log.sync_type == "tick_purge"
    assert log.rows_synced == 2

    # Kiểm tra ticks cũ đã bị xóa
    remaining_ticks = session.exec(select(StockTickIntraday)).all()
    assert len(remaining_ticks) == 0


def test_run_purge_ticks_job_with_safe_gate_blocked(
    session: Session,  # noqa: F811
) -> None:
    """Kiểm tra Safe Purge Gate chặn xóa ticks nếu chưa tổng hợp và không có force."""
    sym = StockSymbol(symbol="MBB", organ_name="MBBank", exchange="HOSE")
    session.add(sym)
    session.commit()

    old_date = date(2026, 7, 1)
    tick = StockTickIntraday(
        symbol="MBB",
        timestamp=datetime.combine(old_date, time(9, 30), tzinfo=VN_TZ),
        price=24000.0,
        volume=2000,
        match_type="SD",
        source="VCI",
    )
    session.add(tick)
    session.commit()

    # Chưa có nến 1m nào -> Safe Purge Gate chặn
    log = run_purge_ticks_job(
        session=session,
        retention_days=1,
        force=False,
        min_bars=180,
    )

    assert log.status == "success"
    assert log.rows_synced == 0

    # Tick vẫn còn nguyên trong DB
    remaining_ticks = session.exec(select(StockTickIntraday)).all()
    assert len(remaining_ticks) == 1


def test_run_purge_ticks_job_with_force(session: Session) -> None:  # noqa: F811
    """Kiểm tra force=True bỏ qua Safe Purge Gate và xóa tick."""
    sym = StockSymbol(symbol="TCB", organ_name="Techcombank", exchange="HOSE")
    session.add(sym)
    session.commit()

    old_date = date(2026, 7, 1)
    tick = StockTickIntraday(
        symbol="TCB",
        timestamp=datetime.combine(old_date, time(9, 30), tzinfo=VN_TZ),
        price=25000.0,
        volume=3000,
        match_type="BU",
        source="VCI",
    )
    session.add(tick)
    session.commit()

    # Force=True -> Purge bất kể không có nến 1m
    log = run_purge_ticks_job(
        session=session,
        retention_days=1,
        force=True,
    )

    assert log.status == "success"
    assert log.rows_synced == 1

    remaining_ticks = session.exec(select(StockTickIntraday)).all()
    assert len(remaining_ticks) == 0


def test_cron_purge_ticks_api_endpoint(
    api_client: TestClient,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Kiểm tra bảo mật và hoạt động của endpoint POST /api/v1/stock/cron/purge-ticks."""
    monkeypatch.setattr(settings, "CRON_SECRET_KEY", "test-secret-ticks-123")

    # 1. Không có secret -> 403
    resp_no_secret = api_client.post("/api/v1/stock/cron/purge-ticks")
    assert resp_no_secret.status_code == 403

    # 2. Sai secret -> 403
    resp_bad = api_client.post(
        "/api/v1/stock/cron/purge-ticks",
        headers={"X-Cron-Secret": "wrong-secret"},
    )
    assert resp_bad.status_code == 403

    # 3. Đúng secret qua Header -> 200 OK
    resp_ok = api_client.post(
        "/api/v1/stock/cron/purge-ticks",
        headers={"X-Cron-Secret": "test-secret-ticks-123"},
        params={"retention_days": 30},
    )
    assert resp_ok.status_code == 200
    data = resp_ok.json()
    assert data["sync_type"] == "tick_purge"
    assert data["status"] == "success"


def test_cli_purge_ticks_command() -> None:
    """Kiểm tra lệnh CLI purge-ticks."""
    mock_log = DataSyncLog(
        sync_type="tick_purge",
        source="system",
        status="success",
        rows_synced=42,
    )

    with patch("app.cli.run_purge_ticks_job", return_value=mock_log):
        result = runner.invoke(cli_app, ["purge-ticks", "--retention-days", "30"])
        assert result.exit_code == 0
        assert "Status: success" in result.output
        assert "Ticks purged: 42" in result.output
