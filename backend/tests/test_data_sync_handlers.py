"""Unit tests cho các reusable handlers và consolidated functions trong DataSyncManager."""

from __future__ import annotations

from collections.abc import Generator
from datetime import date
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from sqlmodel import Session, SQLModel, col, create_engine, select

from app.models.models_quant import InstitutionalFlow
from app.models.models_stock import (
    CapitalHistory,
    CompanyOfficer,
    CompanyShareholder,
    CompanySubsidiary,
    CorporateEvent,
    FinancialRatio,
    IndexConstituent,
    InsiderTrading,
    StockOHLCVDaily,
    StockSymbol,
)
from app.services.data_sync import (
    STOCK_SYMBOL_UPDATE_FIELDS,
    DataSyncManager,
    _extract_financial_summary_fields,
)
from app.services.vnstock_service import VnstockServiceError


@pytest.fixture
def sqlite_session() -> Generator[Session, None, None]:
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
        sqlite_session.add(
            StockSymbol(symbol="TEMP_SYM", organ_name="Tạm thời", asset_type="stock")
        )
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


def test_safe_extractors() -> None:
    """Kiểm tra các helper trích xuất an toàn từ DataFrame row hoặc dictionary."""
    from datetime import date, datetime

    row = {
        "ticker": "HPG",
        "symbol": "",
        "parValue": "100000",
        "coupon_rate": 8.75,
        "tenor": 3,
        "issueDate": "2026-05-15",
        "timestamp": "2026-09-20 14:30:00",
        "empty_str": "   ",
        "none_val": None,
    }

    # _extract_str
    assert DataSyncManager._extract_str(row, "empty_str", "ticker") == "HPG"
    assert DataSyncManager._extract_str(row, "non_existent", default="DEF") == "DEF"

    # _extract_float
    assert DataSyncManager._extract_float(row, "parValue") == 100_000.0
    assert DataSyncManager._extract_float(row, "coupon_rate") == 8.75
    assert DataSyncManager._extract_float(row, "missing", default=1.5) == 1.5

    # _extract_int
    assert DataSyncManager._extract_int(row, "tenor") == 3
    assert DataSyncManager._extract_int(row, "parValue") == 100_000
    assert DataSyncManager._extract_int(row, "missing", default=10) == 10

    # _extract_date
    assert DataSyncManager._extract_date(row, "issueDate") == date(2026, 5, 15)
    assert DataSyncManager._extract_date(row, "non_date") is None

    # _extract_datetime
    assert DataSyncManager._extract_datetime(row, "timestamp") == datetime(
        2026, 9, 20, 14, 30, 0
    )


def test_bulk_upsert_composite_conflict_keys(sqlite_session: Session) -> None:
    """Kiểm tra _bulk_upsert với tổ hợp nhiều trường conflict keys (Intraday bars)."""
    from datetime import UTC, datetime

    from app.models.models_stock import StockOHLCVIntraday
    from app.services.data_sync import INTRADAY_OHLCV_UPDATE_FIELDS

    manager = DataSyncManager(sqlite_session, MagicMock())
    ts = datetime(2026, 9, 20, 14, 0, 0, tzinfo=UTC)

    # Đảm bảo mã VN30F1M tồn tại
    manager._ensure_symbol_exists(
        "VN30F1M", organ_name="HĐTL VN30", asset_type="derivative"
    )

    # 1. Insert ban đầu
    records_1 = [
        {
            "symbol": "VN30F1M",
            "timestamp": ts,
            "interval": "1m",
            "open": 1320.0,
            "high": 1325.0,
            "low": 1318.0,
            "close": 1322.0,
            "volume": 500,
            "source": "VCI",
        }
    ]
    manager._bulk_upsert(
        StockOHLCVIntraday,
        records_1,
        conflict_keys=["symbol", "timestamp", "interval"],
        update_fields=INTRADAY_OHLCV_UPDATE_FIELDS,
    )
    sqlite_session.commit()

    bar1 = sqlite_session.exec(
        select(StockOHLCVIntraday).where(
            StockOHLCVIntraday.symbol == "VN30F1M",
            StockOHLCVIntraday.timestamp == ts,
            StockOHLCVIntraday.interval == "1m",
        )
    ).first()
    assert bar1 is not None
    orig_bar_id = bar1.id
    assert bar1.close == 1322.0
    assert bar1.volume == 500

    # 2. Update cùng nến đó với volume và close mới
    records_2 = [
        {
            "symbol": "VN30F1M",
            "timestamp": ts,
            "interval": "1m",
            "open": 1320.0,
            "high": 1328.0,
            "low": 1318.0,
            "close": 1327.5,
            "volume": 850,
            "source": "VCI",
        }
    ]
    manager._bulk_upsert(
        StockOHLCVIntraday,
        records_2,
        conflict_keys=["symbol", "timestamp", "interval"],
        update_fields=INTRADAY_OHLCV_UPDATE_FIELDS,
    )
    sqlite_session.commit()

    bar2 = sqlite_session.exec(
        select(StockOHLCVIntraday).where(
            StockOHLCVIntraday.symbol == "VN30F1M",
            StockOHLCVIntraday.timestamp == ts,
            StockOHLCVIntraday.interval == "1m",
        )
    ).first()
    assert bar2 is not None
    assert bar2.id == orig_bar_id  # UUID giữ nguyên
    assert bar2.close == 1327.5
    assert bar2.volume == 850

    # Không sinh bản ghi trùng lặp
    all_bars = sqlite_session.exec(select(StockOHLCVIntraday)).all()
    assert len(all_bars) == 1


def test_deduplicate_records() -> None:
    """Kiểm tra khử trùng lặp bản ghi theo conflict_keys, giữ bản ghi xuất hiện sau cùng."""
    records = [
        {"symbol": "VNM", "name": "VNM Old", "val": 1},
        {"symbol": "VIC", "name": "VIC 1", "val": 2},
        {"symbol": "VNM", "name": "VNM New", "val": 3},  # Trùng VNM
    ]
    deduped = DataSyncManager._deduplicate_records(records, ["symbol"])
    assert len(deduped) == 2
    vnm = next(r for r in deduped if r["symbol"] == "VNM")
    assert vnm["name"] == "VNM New"
    assert vnm["val"] == 3


def test_standardize_record_keys() -> None:
    """Kiểm tra đồng nhất tập keys giữa các dictionary trong danh sách."""
    records = [
        {"a": 1, "b": 2},
        {"b": 20, "c": 30},
    ]
    standardized = DataSyncManager._standardize_record_keys(records)
    assert len(standardized) == 2
    assert set(standardized[0].keys()) == {"a", "b", "c"}
    assert set(standardized[1].keys()) == {"a", "b", "c"}
    assert standardized[0]["c"] is None
    assert standardized[1]["a"] is None


def test_upsert_postgresql_execution() -> None:
    """Kiểm tra _upsert_postgresql tạo câu lệnh INSERT ... ON CONFLICT chính xác cho PostgreSQL."""
    mock_session = MagicMock()
    manager = DataSyncManager(mock_session, MagicMock())

    records = [
        {"symbol": "FPT", "organ_name": "FPT Corp", "is_active": True},
        {"symbol": "VNM", "organ_name": "Vinamilk", "is_active": True},
    ]

    # 1. Có update_fields -> on_conflict_do_update
    count = manager._upsert_postgresql(
        StockSymbol,
        records,
        conflict_keys=["symbol"],
        update_fields=["organ_name", "is_active"],
        batch_size=500,
    )
    assert count == 2
    assert mock_session.exec.called or mock_session.execute.called
    assert mock_session.flush.called

    # 2. Không có update_fields -> on_conflict_do_nothing
    mock_session.reset_mock()
    count_nothing = manager._upsert_postgresql(
        StockSymbol,
        records,
        conflict_keys=["symbol"],
        update_fields=[],
        batch_size=500,
    )
    assert count_nothing == 2
    assert mock_session.exec.called or mock_session.execute.called
    assert mock_session.flush.called


def test_sync_financial_ratios(sqlite_session: Session) -> None:
    """Kiểm tra đồng bộ chỉ số tài chính định lượng & định giá."""
    mock_svc = MagicMock()
    mock_svc.source = "VCI"
    mock_svc.fetch_financial_ratios.return_value = pd.DataFrame(
        [
            {
                "item": "Chỉ số giá thị trường trên thu nhập (P/E)",
                "item_id": "pe",
                "2024-Q3": 18.5,
                "2024-Q2": 17.2,
            },
            {
                "item": "Chỉ số giá thị trường trên giá trị sổ sách (P/B)",
                "item_id": "pb",
                "2024-Q3": 3.2,
                "2024-Q2": 3.0,
            },
            {
                "item": "Lợi nhuận trên vốn chủ sở hữu (ROE)",
                "item_id": "roe",
                "2024-Q3": 25.4,
                "2024-Q2": 24.1,
            },
        ]
    )
    manager = DataSyncManager(sqlite_session, mock_svc)
    log = manager.sync_financial_ratios("FPT", period="quarter")
    assert log.status == "success"
    assert log.rows_synced == 2

    ratios = sqlite_session.exec(
        select(FinancialRatio).where(FinancialRatio.symbol == "FPT")
    ).all()
    assert len(ratios) == 2
    r_q3 = next(r for r in ratios if r.quarter == 3)
    assert r_q3.pe == 18.5
    assert r_q3.pb == 3.2
    assert r_q3.roe == 25.4


def test_sync_company_shareholders(sqlite_session: Session) -> None:
    """Kiểm tra đồng bộ cơ cấu cổ đông lớn."""
    mock_svc = MagicMock()
    mock_svc.source = "VCI"
    mock_svc.fetch_company_shareholders.return_value = pd.DataFrame(
        [
            {
                "name": "Tổng Công ty Đầu tư và Kinh doanh vốn Nhà nước (SCIC)",
                "shares_owned": 75000000,
                "ownership_percentage": 5.8,
                "is_state": True,
            },
            {
                "name": "Trương Gia Bình",
                "shares_owned": 88000000,
                "ownership_percentage": 6.9,
                "is_institutional": False,
            },
        ]
    )
    manager = DataSyncManager(sqlite_session, mock_svc)
    log = manager.sync_company_shareholders("FPT")
    assert log.status == "success"
    assert log.rows_synced == 2

    shareholders = sqlite_session.exec(
        select(CompanyShareholder).where(CompanyShareholder.symbol == "FPT")
    ).all()
    assert len(shareholders) == 2


def test_sync_company_officers(sqlite_session: Session) -> None:
    """Kiểm tra đồng bộ ban điều hành và HĐQT."""
    mock_svc = MagicMock()
    mock_svc.source = "VCI"
    mock_svc.fetch_company_officers.return_value = pd.DataFrame(
        [
            {
                "name": "Trương Gia Bình",
                "position": "Chủ tịch HĐQT",
                "shares_owned": 88000000,
                "ownership_percentage": 6.9,
            },
            {
                "name": "Nguyễn Văn Khoa",
                "position": "Tổng Giám đốc",
                "shares_owned": 5000000,
                "ownership_percentage": 0.4,
            },
        ]
    )
    manager = DataSyncManager(sqlite_session, mock_svc)
    log = manager.sync_company_officers("FPT")
    assert log.status == "success"
    assert log.rows_synced == 2

    officers = sqlite_session.exec(
        select(CompanyOfficer).where(CompanyOfficer.symbol == "FPT")
    ).all()
    assert len(officers) == 2


def test_sync_corporate_events(sqlite_session: Session) -> None:
    """Kiểm tra đồng bộ sự kiện doanh nghiệp & cổ tức."""
    mock_svc = MagicMock()
    mock_svc.source = "VCI"
    mock_svc.fetch_company_events.return_value = pd.DataFrame(
        [
            {
                "event_title": "Trả cổ tức đợt 1/2024 bằng tiền",
                "event_type": "cash_dividend",
                "ex_date": "2024-08-15",
                "cash_rate": 1000.0,
                "notes": "Tỷ lệ 10%",
            }
        ]
    )
    manager = DataSyncManager(sqlite_session, mock_svc)
    log = manager.sync_corporate_events("FPT")
    assert log.status == "success"
    assert log.rows_synced == 1

    events = sqlite_session.exec(
        select(CorporateEvent).where(CorporateEvent.symbol == "FPT")
    ).all()
    assert len(events) == 1
    assert events[0].cash_rate == 1000.0


def test_sync_index_constituents(sqlite_session: Session) -> None:
    """Kiểm tra đồng bộ thành phần rổ chỉ số VN30."""
    mock_svc = MagicMock()
    mock_svc.source = "VCI"
    mock_svc.fetch_group_symbols.return_value = ["FPT", "VIC", "VNM"]
    manager = DataSyncManager(sqlite_session, mock_svc)
    log = manager.sync_index_constituents("VN30")
    assert log.status == "success"
    assert log.rows_synced == 3

    constituents = sqlite_session.exec(
        select(IndexConstituent).where(IndexConstituent.index_code == "VN30")
    ).all()
    assert len(constituents) == 3


def test_sync_consolidated_and_batch(sqlite_session: Session) -> None:
    """Kiểm tra các hàm đồng bộ tổng hợp (Full Sync) và theo lô (Batch Sync)."""
    mock_svc = MagicMock()
    mock_svc.source = "VCI"
    mock_svc.fetch_company_overview.return_value = {"companyName": "CTCP FPT"}
    mock_svc.fetch_company_shareholders.return_value = pd.DataFrame()
    mock_svc.fetch_company_officers.return_value = pd.DataFrame()
    mock_svc.fetch_company_events.return_value = pd.DataFrame()
    mock_svc.fetch_financials.return_value = pd.DataFrame()
    mock_svc.fetch_financial_ratios.return_value = pd.DataFrame()

    manager = DataSyncManager(sqlite_session, mock_svc)
    company_res = manager.sync_company_full("FPT")
    assert "profile" in company_res

    fin_res = manager.sync_financials_full("FPT")
    assert "ratios" in fin_res

    batch_res = manager.sync_batch_symbols_data(
        ["FPT"], sync_types=["profile", "unknown_type"], delay_sec=0
    )
    assert "FPT" in batch_res
    assert batch_res["FPT"]["unknown_type"] == "unknown_sync_type"

    # Giả lập khi sync_company_profile ném ngoại lệ bất ngờ
    with patch.object(
        manager, "sync_company_profile", side_effect=RuntimeError("API Network Error")
    ):
        batch_err_res = manager.sync_batch_symbols_data(
            ["FPT"], sync_types=["profile"], delay_sec=0
        )
        assert batch_err_res["FPT"]["profile"] == "failed"


def test_sync_company_subsidiaries(sqlite_session: Session) -> None:
    """Kiểm tra đồng bộ danh sách công ty con và liên kết."""
    mock_svc = MagicMock()
    mock_svc.source = "VCI"
    mock_svc.fetch_company_subsidiaries.return_value = pd.DataFrame(
        [
            {
                "sub_organ_code": "FPT-IS",
                "organ_name": "Công ty TNHH Hệ thống Thông tin FPT",
                "ownership_percent": 100.0,
            },
            {
                "sub_organ_code": "FPT-TEL",
                "organ_name": "CTCP Viễn thông FPT",
                "ownership_percent": 45.65,
            },
        ]
    )
    manager = DataSyncManager(sqlite_session, mock_svc)
    log = manager.sync_company_subsidiaries("FPT")
    assert log.status == "success"
    assert log.rows_synced == 2

    rows = sqlite_session.exec(
        select(CompanySubsidiary).where(CompanySubsidiary.symbol == "FPT")
    ).all()
    assert len(rows) == 2
    assert any(
        r.sub_organ_code == "FPT-IS" and r.ownership_percent == 100.0 for r in rows
    )


def test_sync_insider_trading(sqlite_session: Session) -> None:
    """Kiểm tra đồng bộ nhật ký giao dịch nội bộ."""
    mock_svc = MagicMock()
    mock_svc.source = "VCI"
    mock_svc.fetch_company_insider_trading.return_value = pd.DataFrame(
        [
            {
                "officer_name": "Trương Gia Bình",
                "officer_position": "Chủ tịch HĐQT",
                "deal_action": "Bán",
                "deal_quantity": 500000.0,
                "deal_price": 130000.0,
                "deal_ratio": 7.5,
                "deal_announce_date": "2026-03-15",
            }
        ]
    )
    manager = DataSyncManager(sqlite_session, mock_svc)
    log = manager.sync_insider_trading("FPT")
    assert log.status == "success"
    assert log.rows_synced == 1

    rows = sqlite_session.exec(
        select(InsiderTrading).where(InsiderTrading.symbol == "FPT")
    ).all()
    assert len(rows) == 1
    assert rows[0].officer_name == "Trương Gia Bình"
    assert rows[0].deal_action == "Bán"


def test_sync_capital_history(sqlite_session: Session) -> None:
    """Kiểm tra đồng bộ lịch sử tăng vốn điều lệ."""
    mock_svc = MagicMock()
    mock_svc.source = "VCI"
    mock_svc.fetch_company_capital_history.return_value = pd.DataFrame(
        [
            {
                "issue_date": "2025-06-20",
                "charter_capital": 14500000000000.0,
                "shares_issued": 150000000.0,
                "description": "Chi trả cổ tức bằng cổ phiếu tỷ lệ 15%",
            }
        ]
    )
    manager = DataSyncManager(sqlite_session, mock_svc)
    log = manager.sync_capital_history("FPT")
    assert log.status == "success"
    assert log.rows_synced == 1

    rows = sqlite_session.exec(
        select(CapitalHistory).where(CapitalHistory.symbol == "FPT")
    ).all()
    assert len(rows) == 1
    assert rows[0].shares_issued == 150000000.0
    assert rows[0].charter_capital == 14500000000000.0


def test_extract_financial_summary_fields() -> None:
    """Kiểm tra helper _extract_financial_summary_fields phân tích chính xác 14 chỉ tiêu tài chính cốt lõi."""
    payload = {
        "Doanh thu thuần về bán hàng và cung cấp dịch vụ": "52851000000000",
        "Lợi nhuận gộp về bán hàng và cung cấp dịch vụ": "19850000000000",
        "Lợi nhuận thuần từ hoạt động kinh doanh": "9200000000000",
        "Lợi nhuận sau thuế của công ty mẹ": "7800000000000",
        "TỔNG CỘNG TÀI SẢN": "60200000000000",
        "TÀI SẢN NGẮN HẠN": "38500000000000",
        "Tiền và các khoản tương đương tiền": "8500000000000",
        "NỢ PHẢI TRẢ": "28500000000000",
        "Vay và nợ thuê tài chính ngắn hạn": "12000000000000",
        "Vay và nợ thuê tài chính dài hạn": "1500000000000",
        "VỐN CHỦ SỞ HỮU": "31700000000000",
        "Lưu chuyển tiền thuần từ hoạt động kinh doanh": "6500000000000",
        "Lưu chuyển tiền thuần từ hoạt động đầu tư": "-3200000000000",
        "Lưu chuyển tiền thuần từ hoạt động tài chính": "-1500000000000",
    }
    res = _extract_financial_summary_fields(payload)
    assert res["revenue"] == 52851000000000.0
    assert res["gross_profit"] == 19850000000000.0
    assert res["operating_profit"] == 9200000000000.0
    assert res["net_profit_parent"] == 7800000000000.0
    assert res["total_assets"] == 60200000000000.0
    assert res["short_term_assets"] == 38500000000000.0
    assert res["cash_and_equivalents"] == 8500000000000.0
    assert res["total_liabilities"] == 28500000000000.0
    assert res["short_term_debt"] == 12000000000000.0
    assert res["long_term_debt"] == 1500000000000.0
    assert res["owners_equity"] == 31700000000000.0
    assert res["operating_cash_flow"] == 6500000000000.0
    assert res["investing_cash_flow"] == -3200000000000.0
    assert res["financing_cash_flow"] == -1500000000000.0


def test_sync_financial_ratios_with_explicit_columns(sqlite_session: Session) -> None:
    """Kiểm tra đồng bộ chỉ số tài chính lưu đầy đủ 17 cột tường minh phục vụ screener."""
    mock_svc = MagicMock()
    mock_svc.source = "VCI"
    # Dạng bảng phẳng với các chỉ số nâng cao
    mock_svc.fetch_financial_ratios.return_value = pd.DataFrame(
        [
            {
                "symbol": "FPT",
                "year": 2026,
                "quarter": 2,
                "pe": 18.5,
                "pb": 3.8,
                "roe": 26.5,
                "roa": 12.8,
                "debt_to_equity": 0.42,
                "ev_to_ebitda": 14.2,
                "ev_to_ebit": 16.5,
                "p_to_fcf": 21.0,
                "ebit_margin": 17.5,
                "ebitda_margin": 22.0,
                "revenue_growth_yoy": 19.5,
                "net_profit_growth_yoy": 21.2,
            }
        ]
    )
    manager = DataSyncManager(sqlite_session, mock_svc)
    log = manager.sync_financial_ratios("FPT", period="quarter")
    assert log.status == "success"
    assert log.rows_synced == 1

    ratio = sqlite_session.exec(
        select(FinancialRatio)
        .where(FinancialRatio.symbol == "FPT")
        .where(FinancialRatio.year == 2026)
        .where(FinancialRatio.quarter == 2)
    ).first()
    assert ratio is not None
    assert ratio.pe == 18.5
    assert ratio.roe == 26.5
    assert ratio.ev_to_ebitda == 14.2
    assert ratio.revenue_growth_yoy == 19.5
    assert ratio.net_profit_growth_yoy == 21.2


def test_compute_daily_derivative_basis(sqlite_session: Session) -> None:
    """Kiểm tra tính toán Basis phái sinh = VN30F1M.close - VN30.close."""
    d = date(2026, 9, 18)
    # Tạo nến cơ sở VN30 và nến phái sinh VN30F1M
    bar_vn30 = StockOHLCVDaily(
        symbol="VN30",
        trading_date=d,
        open=1240.0,
        high=1248.0,
        low=1239.0,
        close=1245.5,
        volume=250000000,
        source="VCI",
    )
    bar_vn30f = StockOHLCVDaily(
        symbol="VN30F1M",
        trading_date=d,
        open=1242.0,
        high=1252.0,
        low=1241.0,
        close=1250.0,
        volume=180000,
        open_interest=52000,
        source="VCI",
    )
    sqlite_session.add(bar_vn30)
    sqlite_session.add(bar_vn30f)
    sqlite_session.commit()

    manager = DataSyncManager(sqlite_session, MagicMock())
    updated_count = manager.compute_daily_derivative_basis(trading_date=d)
    assert updated_count == 1

    # Kiểm tra basis đã được tính và lưu
    sqlite_session.refresh(bar_vn30f)
    assert bar_vn30f.basis == 4.5  # 1250.0 - 1245.5


def test_sync_institutional_flow_explicit_metrics(sqlite_session: Session) -> None:
    """Kiểm tra đồng bộ dữ liệu dòng tiền khối ngoại và tự doanh với đầy đủ khối lượng và room ngoại."""
    d = date(2026, 9, 18)
    mock_svc = MagicMock()
    mock_svc.source = "VCI"
    # Giả lập trả về từ VCI/TCBS
    mock_svc.fetch_foreign_flow.return_value = pd.DataFrame(
        [
            {
                "symbol": "FPT",
                "buy_val": 150000000000.0,
                "sell_val": 80000000000.0,
                "net_val": 70000000000.0,
                "buy_vol": 1150000,
                "sell_vol": 615000,
                "net_vol": 535000,
                "room_total": 490000000,
                "room_current": 4900000,
                "room_pct": 1.0,
            }
        ]
    )
    mock_svc.fetch_prop_flow.return_value = pd.DataFrame(
        [
            {
                "symbol": "FPT",
                "buy_val": 30000000000.0,
                "sell_val": 10000000000.0,
                "net_val": 20000000000.0,
                "buy_vol": 230000,
                "sell_vol": 77000,
                "net_vol": 153000,
            }
        ]
    )
    manager = DataSyncManager(sqlite_session, mock_svc)
    log = manager.sync_institutional_flow(trading_date=d, symbols=["FPT"])
    assert log.status == "success"
    assert log.rows_synced == 1

    flow = sqlite_session.exec(
        select(InstitutionalFlow)
        .where(InstitutionalFlow.symbol == "FPT")
        .where(InstitutionalFlow.trading_date == d)
    ).first()
    assert flow is not None
    assert flow.foreign_net_value == 70000000000.0
    assert flow.foreign_net_volume == 535000
    assert flow.prop_net_value == 20000000000.0
    assert flow.prop_net_volume == 153000
    assert flow.foreign_room_pct == 1.0


def test_screener_query_with_explicit_indexes(sqlite_session: Session) -> None:
    """Kiểm tra truy vấn lọc cổ phiếu định lượng hoạt động chính xác trên các trường số học."""
    # Tạo các mã chứng khoán
    s1 = StockSymbol(
        symbol="FPT", organ_name="Tập đoàn FPT", exchange="HOSE", industry="Công nghệ"
    )
    s2 = StockSymbol(
        symbol="HPG", organ_name="Tập đoàn Hòa Phát", exchange="HOSE", industry="Thép"
    )
    s3 = StockSymbol(
        symbol="VND",
        organ_name="Chứng khoán VNDirect",
        exchange="VND",
        industry="Chứng khoán",
    )
    sqlite_session.add_all([s1, s2, s3])
    sqlite_session.commit()

    # Thêm chỉ số tài chính quý 2/2026
    r1 = FinancialRatio(
        symbol="FPT",
        period="quarter",
        year=2026,
        quarter=2,
        pe=18.0,
        roe=28.0,
        debt_to_equity=0.4,
        revenue_growth_yoy=20.0,
        source="VCI",
    )
    r2 = FinancialRatio(
        symbol="HPG",
        period="quarter",
        year=2026,
        quarter=2,
        pe=9.5,
        roe=16.0,
        debt_to_equity=0.8,
        revenue_growth_yoy=12.0,
        source="VCI",
    )
    r3 = FinancialRatio(
        symbol="VND",
        period="quarter",
        year=2026,
        quarter=2,
        pe=14.0,
        roe=11.0,
        debt_to_equity=1.5,
        revenue_growth_yoy=5.0,
        source="VCI",
    )
    sqlite_session.add_all([r1, r2, r3])
    sqlite_session.commit()

    # Lọc cổ phiếu có ROE >= 20% và Nợ/VCSH <= 0.5
    query = (
        select(FinancialRatio, StockSymbol)
        .join(StockSymbol, col(FinancialRatio.symbol) == col(StockSymbol.symbol))
        .where(col(FinancialRatio.period) == "quarter")
        .where(col(FinancialRatio.year) == 2026)
        .where(col(FinancialRatio.quarter) == 2)
        .where(col(FinancialRatio.roe) >= 20.0)
        .where(col(FinancialRatio.debt_to_equity) <= 0.5)
    )
    matched = sqlite_session.exec(query).all()
    assert len(matched) == 1
    ratio, sym = matched[0]
    assert sym.symbol == "FPT"
    assert ratio.roe == 28.0
