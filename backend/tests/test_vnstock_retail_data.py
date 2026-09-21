"""Unit and contract tests for Retail Data Layer (v4.0.6) in VnstockService."""

from datetime import date
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from app.services.vnstock_service import VnstockService


@pytest.fixture
def service() -> VnstockService:
    """Khởi tạo VnstockService với throttle mock cho test."""
    mock_limiter = MagicMock()
    return VnstockService(limiter=mock_limiter)


@patch("app.services.vnstock_service.Retail")
def test_retail_gold_prices(
    mock_retail_cls: MagicMock, service: VnstockService
) -> None:
    """Kiểm thử tải giá vàng qua Retail.gold với các nguồn SJC và BTMC."""
    mock_retail = MagicMock()
    mock_retail_cls.return_value = mock_retail

    sample_gold_df = pd.DataFrame(
        [
            {
                "time": "2026-09-21 10:00",
                "buy": 80.5,
                "sell": 82.5,
                "type": "Vàng miếng SJC",
            },
        ]
    )
    mock_retail.gold.return_value = sample_gold_df

    # 1. Nguồn mặc định SJC, ngày mới nhất
    df_sjc = service.fetch_retail_gold(source="sjc")
    assert len(df_sjc) == 1
    mock_retail.gold.assert_called_with(source="sjc", date=None)

    # 2. Nguồn BTMC kèm chuỗi ngày
    df_btmc_str = service.fetch_retail_gold(source="btmc", date="2026-09-18")
    assert len(df_btmc_str) == 1
    mock_retail.gold.assert_called_with(source="btmc", date="2026-09-18")

    # 3. Nguồn BTMC kèm datetime.date object
    df_btmc_date = service.fetch_retail_gold(source="btmc", date=date(2026, 9, 18))
    assert len(df_btmc_date) == 1
    mock_retail.gold.assert_called_with(source="btmc", date="2026-09-18")

    # 4. Tương thích ngược qua fetch_gold_prices
    df_alias = service.fetch_gold_prices(source="sjc")
    assert len(df_alias) == 1


@patch("app.services.vnstock_service.Retail")
def test_retail_exchange_rate(
    mock_retail_cls: MagicMock, service: VnstockService
) -> None:
    """Kiểm thử tải tỷ giá ngoại hối Vietcombank qua Retail.exchange_rate."""
    mock_retail = MagicMock()
    mock_retail_cls.return_value = mock_retail

    sample_fx_df = pd.DataFrame(
        [
            {
                "currency": "USD",
                "buy_cash": 25100,
                "buy_transfer": 25130,
                "sell": 25470,
            },
            {
                "currency": "EUR",
                "buy_cash": 27200,
                "buy_transfer": 27300,
                "sell": 27800,
            },
        ]
    )
    mock_retail.exchange_rate.return_value = sample_fx_df

    # 1. Tỷ giá hiện tại (ngày trống)
    df_curr = service.fetch_retail_exchange_rate()
    assert len(df_curr) == 2
    mock_retail.exchange_rate.assert_called_with(date="")

    # 2. Tỷ giá theo chuỗi ngày
    df_date_str = service.fetch_retail_exchange_rate(date="2026-09-18")
    assert len(df_date_str) == 2
    mock_retail.exchange_rate.assert_called_with(date="2026-09-18")

    # 3. Tỷ giá theo datetime.date object
    df_date_obj = service.fetch_retail_exchange_rate(date=date(2026, 9, 18))
    assert len(df_date_obj) == 2
    mock_retail.exchange_rate.assert_called_with(date="2026-09-18")

    # 4. Tương thích ngược qua fetch_exchange_rate
    df_alias = service.fetch_exchange_rate(date_str="2026-09-18")
    assert len(df_alias) == 2


@patch("app.services.vnstock_service.Retail")
def test_retail_graceful_error_handling(
    mock_retail_cls: MagicMock, service: VnstockService
) -> None:
    """Kiểm thử bắt lỗi an toàn khi dịch vụ web nguồn SJC hoặc Vietcombank bị lỗi."""
    mock_retail = MagicMock()
    mock_retail_cls.return_value = mock_retail

    mock_retail.gold.side_effect = Exception("SJC portal timeout")
    mock_retail.exchange_rate.side_effect = Exception("VCB portal timeout")

    assert service.fetch_retail_gold().empty
    assert service.fetch_gold_prices().empty
    assert service.fetch_retail_exchange_rate().empty
    assert service.fetch_exchange_rate().empty
