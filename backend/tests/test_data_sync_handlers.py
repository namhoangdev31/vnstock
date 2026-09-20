"""Unit tests cho các reusable handlers và consolidated functions trong DataSyncManager."""

from __future__ import annotations

from unittest.mock import MagicMock

import pandas as pd
import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from app.models.models_stock import (
    StockSymbol,
)
from app.services.data_sync import (
    STOCK_SYMBOL_UPDATE_FIELDS,
    DataSyncManager,
)
from app.services.vnstock_service import VnstockServiceError


@pytest.fixture
def sqlite_session() -> Session:
    """Fixture cung cấp in-memory SQLite session cho unit test."""
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_resolve_symbol_column() -> None:
    """Kiểm tra helper _resolve_symbol_column nhận diện đúng cột mã."""
    df_empty = pd.DataFrame()
    assert DataSyncManager._resolve_symbol_column(df_empty) is None

    df_ticker = pd.DataFrame([{"ticker": "SSI", "val": 10}])
    assert DataSyncManager._resolve_symbol_column(df_ticker) == "ticker"

    df_symbol = pd.DataFrame([{"symbol": "VND", "val": 20}])
    assert DataSyncManager._resolve_symbol_column(df_symbol) == "symbol"

    df_custom = pd.DataFrame([{"code": "HPG", "val": 30}])
    assert DataSyncManager._resolve_symbol_column(df_custom) == "code"


def test_normalize_to_dataframe() -> None:
    """Kiểm tra helper _normalize_to_dataframe chuẩn hóa DataFrame, Series và list."""
    assert DataSyncManager._normalize_to_dataframe(None).empty
    assert DataSyncManager._normalize_to_dataframe([]).empty

    # List
    df_list = DataSyncManager._normalize_to_dataframe(["VNM", "VIC"])
    assert not df_list.empty
    assert list(df_list["symbol"]) == ["VNM", "VIC"]

    # Series
    series = pd.Series(["FPT", "MWG"])
    df_series = DataSyncManager._normalize_to_dataframe(series, symbol_col="ticker")
    assert not df_series.empty
    assert list(df_series["ticker"]) == ["FPT", "MWG"]

    # DataFrame
    raw_df = pd.DataFrame([{"symbol": "GAS"}])
    assert DataSyncManager._normalize_to_dataframe(raw_df).equals(raw_df)


def test_run_sync_task_success_and_failures(sqlite_session: Session) -> None:
    """Kiểm tra lifecycle của _run_sync_task khi thành công, lỗi VnstockServiceError và lỗi Exception."""
    mock_svc = MagicMock(source="VCI")
    manager = DataSyncManager(sqlite_session, mock_svc)

    # 1. Thành công
    def success_task() -> int:
        return 42

    log1 = manager._run_sync_task("test_sync", success_task)
    assert log1.status == "success"
    assert log1.rows_synced == 42
    assert log1.error_message is None

    # 2. VnstockServiceError
    def service_error_task() -> int:
        raise VnstockServiceError("API quota exceeded")

    log2 = manager._run_sync_task("test_sync", service_error_task)
    assert log2.status == "failed"
    assert "API quota exceeded" in (log2.error_message or "")

    # 3. Exception bất ngờ và rollback
    def unexpected_error_task() -> int:
        sqlite_session.add(StockSymbol(symbol="TEMP_SYM", organ_name="Tạm thời"))
        raise RuntimeError("Cúp điện đột xuất")

    log3 = manager._run_sync_task("test_sync", unexpected_error_task)
    assert log3.status == "failed"
    assert "Cúp điện đột xuất" in (log3.error_message or "")

    # Xác nhận transaction đã rollback, bản ghi TEMP_SYM không tồn tại
    temp_sym = sqlite_session.get(StockSymbol, "TEMP_SYM")
    assert temp_sym is None


def test_find_or_create_symbols_auto_create(sqlite_session: Session) -> None:
    """Kiểm tra _find_or_create_symbols với auto_create=True và False."""
    manager = DataSyncManager(sqlite_session, MagicMock())

    # Chưa tồn tại và auto_create=False
    existing = manager._find_or_create_symbols({"TCB", "MBB"}, auto_create=False)
    assert len(existing) == 0

    # auto_create=True -> Tự động thêm vào StockSymbol
    created = manager._find_or_create_symbols(
        {"TCB", "MBB"},
        auto_create=True,
        default_name_prefix="Ngân hàng",
        asset_type="stock",
    )
    assert created == {"TCB", "MBB"}

    tcb = sqlite_session.get(StockSymbol, "TCB")
    assert tcb is not None
    assert tcb.organ_name == "Ngân hàng TCB"
    assert tcb.asset_type == "stock"
    assert tcb.lot_size == 100

    # Gọi lại khi đã tồn tại -> Không tạo trùng lặp
    count_before = len(sqlite_session.exec(select(StockSymbol)).all())
    re_checked = manager._find_or_create_symbols({"TCB"}, auto_create=True)
    count_after = len(sqlite_session.exec(select(StockSymbol)).all())
    assert re_checked == {"TCB"}
    assert count_before == count_after


def test_bulk_upsert_preserves_uuid(sqlite_session: Session) -> None:
    """Kiểm tra _bulk_upsert cập nhật đúng thuộc tính mà không thay đổi UUID khóa chính."""
    manager = DataSyncManager(sqlite_session, MagicMock())

    # 1. Insert lần 1
    records_1 = [
        {
            "symbol": "VIC",
            "organ_name": "Tập đoàn Vingroup",
            "exchange": "HOSE",
            "asset_type": "stock",
            "lot_size": 100,
            "is_active": True,
        }
    ]
    manager._bulk_upsert(
        StockSymbol,
        records_1,
        conflict_keys=["symbol"],
        update_fields=STOCK_SYMBOL_UPDATE_FIELDS,
    )
    sqlite_session.commit()

    vic1 = sqlite_session.get(StockSymbol, "VIC")
    assert vic1 is not None
    orig_uuid = vic1.id
    assert vic1.organ_name == "Tập đoàn Vingroup"

    # 2. Upsert lần 2 với tên mới
    records_2 = [
        {
            "symbol": "VIC",
            "organ_name": "Tập đoàn Vingroup - CTCP",
            "exchange": "HOSE",
            "asset_type": "stock",
            "lot_size": 100,
            "is_active": True,
        }
    ]
    manager._bulk_upsert(
        StockSymbol,
        records_2,
        conflict_keys=["symbol"],
        update_fields=STOCK_SYMBOL_UPDATE_FIELDS,
    )
    sqlite_session.commit()

    vic2 = sqlite_session.get(StockSymbol, "VIC")
    assert vic2 is not None
    assert vic2.id == orig_uuid  # UUID KHÔNG ĐƯỢC ĐỔI
    assert vic2.organ_name == "Tập đoàn Vingroup - CTCP"
