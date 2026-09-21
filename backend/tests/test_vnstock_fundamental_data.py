"""Unit and contract tests for Fundamental Data Layer (v4.0.6) in VnstockService."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from app.services.vnstock_service import VnstockService, VnstockServiceError


@pytest.fixture
def service() -> VnstockService:
    """Khởi tạo VnstockService với throttle mock cho test."""
    mock_limiter = MagicMock()
    return VnstockService(limiter=mock_limiter)


@patch("app.services.vnstock_service.Fundamental")
def test_fundamental_income_statement(
    mock_fnd_cls: MagicMock, service: VnstockService
) -> None:
    """Kiểm thử lấy kết quả kinh doanh qua Fundamental.equity.income_statement."""
    mock_fnd = MagicMock()
    mock_fnd_cls.return_value = mock_fnd
    mock_eq = MagicMock()
    mock_fnd.equity.return_value = mock_eq

    sample_df = pd.DataFrame(
        [
            {"item": "Doanh thu thuần", "unit": "VND", "2023": 100000, "2022": 90000},
            {"item": "Lợi nhuận sau thuế", "unit": "VND", "2023": 25000, "2022": 20000},
        ]
    )
    mock_eq.income_statement.return_value = sample_df

    # 1. Report orientation (mặc định theo năm)
    df_report = service.fetch_fundamental_income_statement(
        "VCB", period="year", orient="report"
    )
    assert len(df_report) == 2
    mock_eq.income_statement.assert_called_with(period="year", orient="report")

    # 2. Time series orientation (theo quý)
    df_ts = service.fetch_fundamental_income_statement(
        "VCB", period="quarter", orient="time_series"
    )
    assert len(df_ts) == 2
    mock_eq.income_statement.assert_called_with(period="quarter", orient="time_series")


@patch("app.services.vnstock_service.Fundamental")
def test_fundamental_balance_sheet(
    mock_fnd_cls: MagicMock, service: VnstockService
) -> None:
    """Kiểm thử lấy bảng cân đối kế toán qua Fundamental.equity.balance_sheet."""
    mock_fnd = MagicMock()
    mock_fnd_cls.return_value = mock_fnd
    mock_eq = MagicMock()
    mock_fnd.equity.return_value = mock_eq

    sample_df = pd.DataFrame(
        [
            {"item": "Tổng tài sản", "unit": "VND", "2023": 500000, "2022": 450000},
            {"item": "Vốn chủ sở hữu", "unit": "VND", "2023": 150000, "2022": 130000},
        ]
    )
    mock_eq.balance_sheet.return_value = sample_df

    df_bs = service.fetch_fundamental_balance_sheet(
        "VCB", period="year", orient="report"
    )
    assert len(df_bs) == 2
    mock_eq.balance_sheet.assert_called_with(period="year", orient="report")


@patch("app.services.vnstock_service.Fundamental")
def test_fundamental_cash_flow(
    mock_fnd_cls: MagicMock, service: VnstockService
) -> None:
    """Kiểm thử lấy báo cáo lưu chuyển tiền tệ qua Fundamental.equity.cash_flow."""
    mock_fnd = MagicMock()
    mock_fnd_cls.return_value = mock_fnd
    mock_eq = MagicMock()
    mock_fnd.equity.return_value = mock_eq

    sample_df = pd.DataFrame(
        [
            {"item": "Lưu chuyển tiền từ HĐKD", "unit": "VND", "2023": 30000},
            {"item": "Lưu chuyển tiền từ HĐĐT", "unit": "VND", "2023": -10000},
        ]
    )
    mock_eq.cash_flow.return_value = sample_df

    df_cf = service.fetch_fundamental_cash_flow(
        "VCB", period="quarter", orient="report"
    )
    assert len(df_cf) == 2
    mock_eq.cash_flow.assert_called_with(period="quarter", orient="report")


@patch("app.services.vnstock_service.Fundamental")
def test_fundamental_ratios(mock_fnd_cls: MagicMock, service: VnstockService) -> None:
    """Kiểm thử lấy bộ 50+ chỉ số tài chính định lượng qua Fundamental.equity.ratio / ratios."""
    mock_fnd = MagicMock()
    mock_fnd_cls.return_value = mock_fnd
    mock_eq = MagicMock()
    mock_fnd.equity.return_value = mock_eq

    sample_df = pd.DataFrame(
        [
            {
                "ticker": "VCB",
                "year": 2023,
                "priceToEarning": 14.5,
                "priceToBook": 2.8,
                "roe": 0.22,
            },
        ]
    )
    mock_eq.ratio.return_value = sample_df

    # 1. fetch_fundamental_ratio
    df_ratio = service.fetch_fundamental_ratio("VCB", orient="report")
    assert len(df_ratio) == 1
    mock_eq.ratio.assert_called_with(orient="report")

    # 2. fetch_fundamental_ratios alias
    df_ratios = service.fetch_fundamental_ratios("VCB", orient="time_series")
    assert len(df_ratios) == 1
    mock_eq.ratio.assert_called_with(orient="time_series")


@patch("app.services.vnstock_service.Finance")
@patch("app.services.vnstock_service.Fundamental")
def test_fundamental_fallback_to_finance(
    mock_fnd_cls: MagicMock, mock_fin_cls: MagicMock, service: VnstockService
) -> None:
    """Kiểm thử khi Fundamental bị lỗi, tự động fallback an toàn sang Finance."""
    mock_fnd = MagicMock()
    mock_fnd_cls.return_value = mock_fnd
    mock_fnd.equity.side_effect = Exception("Fundamental endpoint temporary down")

    mock_fin = MagicMock()
    mock_fin_cls.return_value = mock_fin
    mock_fin.income_statement.return_value = pd.DataFrame(
        [{"item": "Doanh thu", "2023": 80000}]
    )

    df = service.fetch_fundamental_income_statement("VCB", period="year")
    assert len(df) == 1
    assert df.iloc[0]["item"] == "Doanh thu"


@patch("app.services.vnstock_service.Finance")
@patch("app.services.vnstock_service.Fundamental")
def test_fundamental_error_handling_when_all_fail(
    mock_fnd_cls: MagicMock, mock_fin_cls: MagicMock, service: VnstockService
) -> None:
    """Kiểm thử ném VnstockServiceError khi cả Fundamental lẫn tất cả nguồn Finance đều lỗi."""
    mock_fnd = MagicMock()
    mock_fnd_cls.return_value = mock_fnd
    mock_fnd.equity.side_effect = Exception("Fundamental error")

    mock_fin = MagicMock()
    mock_fin_cls.return_value = mock_fin
    mock_fin.income_statement.side_effect = Exception("Finance error")

    with pytest.raises(VnstockServiceError):
        service.fetch_fundamental_income_statement("INVALID_SYMBOL", period="year")
