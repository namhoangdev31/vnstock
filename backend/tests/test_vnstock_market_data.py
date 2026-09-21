"""Unit and contract tests for all Market Data methods in VnstockService."""

from datetime import date
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from app.services.vnstock_service import VnstockService


@pytest.fixture
def service() -> VnstockService:
    """Khởi tạo VnstockService với throttle tối thiểu cho test."""
    mock_limiter = MagicMock()
    return VnstockService(limiter=mock_limiter)


def test_market_date_param_formatting(service: VnstockService) -> None:
    """Kiểm tra helper _format_date_param chuẩn hóa date và string chính xác."""
    assert service._format_date_param(None) is None
    assert service._format_date_param(date(2024, 1, 15)) == "2024-01-15"
    assert service._format_date_param("2024-02-20") == "2024-02-20"


@patch("app.services.vnstock_service.Market")
def test_market_equity_methods(
    mock_market_cls: MagicMock, service: VnstockService
) -> None:
    """Kiểm thử đầy đủ các phương thức thuộc lớp Market.equity (ohlcv, trades, quote)."""
    mock_mkt = MagicMock()
    mock_market_cls.return_value = mock_mkt
    mock_equity = MagicMock()
    mock_mkt.equity.return_value = mock_equity

    # 1. OHLCV
    sample_ohlcv = pd.DataFrame(
        [{"time": "2024-01-02", "open": 55.0, "close": 55.5, "volume": 1000}]
    )
    mock_equity.ohlcv.return_value = sample_ohlcv

    df_ohlcv = service.fetch_market_equity_ohlcv(
        symbol="FPT",
        start=date(2024, 1, 1),
        end=date(2024, 1, 31),
        interval="1D",
        count=50,
    )
    assert not df_ohlcv.empty
    assert len(df_ohlcv) == 1
    mock_equity.ohlcv.assert_called_once_with(
        interval="1D", count=50, start="2024-01-01", end="2024-01-31"
    )

    # 2. Trades
    sample_trades = pd.DataFrame([{"time": "09:15:00", "price": 55.2, "volume": 500}])
    mock_equity.trades.return_value = sample_trades
    df_trades = service.fetch_market_equity_trades("FPT")
    assert len(df_trades) == 1
    mock_equity.trades.assert_called_once()

    # 3. Quote
    sample_quote = pd.DataFrame(
        [{"symbol": "VCB", "price": 90.0, "ceiling": 96.0, "floor": 84.0}]
    )
    mock_equity.quote.return_value = sample_quote
    df_quote = service.fetch_market_equity_quote("VCB")
    assert len(df_quote) == 1
    assert df_quote.iloc[0]["symbol"] == "VCB"
    mock_mkt.equity.assert_called_with("VCB")


@patch("app.services.vnstock_service.Market")
def test_market_index_ohlcv(
    mock_market_cls: MagicMock, service: VnstockService
) -> None:
    """Kiểm thử nến chỉ số qua Market.index().ohlcv()."""
    mock_mkt = MagicMock()
    mock_market_cls.return_value = mock_mkt
    mock_idx = MagicMock()
    mock_mkt.index.return_value = mock_idx

    sample_index = pd.DataFrame([{"time": "2024-01-02", "close": 1130.0}])
    mock_idx.ohlcv.return_value = sample_index

    df = service.fetch_index_ohlcv("VNINDEX", start="2024-01-01", end="2024-01-31")
    assert not df.empty
    mock_mkt.index.assert_called_with("VNINDEX")
    mock_idx.ohlcv.assert_called_once_with(
        interval="1D", start="2024-01-01", end="2024-01-31"
    )


@patch("app.services.vnstock_service.Market")
def test_market_futures_methods(
    mock_market_cls: MagicMock, service: VnstockService
) -> None:
    """Kiểm thử đầy đủ các phương thức thuộc lớp Market.futures."""
    mock_mkt = MagicMock()
    mock_market_cls.return_value = mock_mkt
    mock_fut = MagicMock()
    mock_mkt.futures.return_value = mock_fut

    # 1. OHLCV
    sample_ohlcv = pd.DataFrame(
        [{"time": "2024-01-02", "close": 1135.0, "volume": 120000}]
    )
    mock_fut.ohlcv.return_value = sample_ohlcv
    df_ohlcv = service.fetch_market_futures_ohlcv("VN30F1M", interval="5m")
    assert not df_ohlcv.empty
    mock_fut.ohlcv.assert_called_once_with(interval="5m", count=100)

    # 2. Trades
    sample_trades = pd.DataFrame([{"time": "09:30:00", "price": 1135.5, "volume": 10}])
    mock_fut.trades.return_value = sample_trades
    df_trades = service.fetch_market_futures_trades("VN30F1M")
    assert len(df_trades) == 1

    # 3. Quote (và alias fetch_futures_quote)
    sample_quote = pd.DataFrame([{"symbol": "VN30F1M", "price": 1135.2, "oi": 45000}])
    mock_fut.quote.return_value = sample_quote
    df_quote1 = service.fetch_market_futures_quote("VN30F1M")
    df_quote2 = service.fetch_futures_quote("VN30F1M")
    assert len(df_quote1) == 1
    assert len(df_quote2) == 1


@patch("app.services.vnstock_service.Market")
def test_market_warrant_methods(
    mock_market_cls: MagicMock, service: VnstockService
) -> None:
    """Kiểm thử các phương thức thuộc lớp Market.warrant (CW)."""
    mock_mkt = MagicMock()
    mock_market_cls.return_value = mock_mkt
    mock_war = MagicMock()
    mock_mkt.warrant.return_value = mock_war

    mock_war.ohlcv.return_value = pd.DataFrame([{"time": "2024-01-02", "close": 2.5}])
    mock_war.trades.return_value = pd.DataFrame([{"time": "10:00:00", "price": 2.5}])
    mock_war.quote.return_value = pd.DataFrame([{"symbol": "CFPT2301", "price": 2.5}])

    assert not service.fetch_market_warrant_ohlcv("CFPT2301").empty
    assert not service.fetch_market_warrant_trades("CFPT2301").empty
    assert not service.fetch_market_warrant_quote("CFPT2301").empty


@patch("app.services.vnstock_service.Market")
def test_market_etf_methods(
    mock_market_cls: MagicMock, service: VnstockService
) -> None:
    """Kiểm thử các phương thức thuộc lớp Market.etf."""
    mock_mkt = MagicMock()
    mock_market_cls.return_value = mock_mkt
    mock_etf = MagicMock()
    mock_mkt.etf.return_value = mock_etf

    mock_etf.ohlcv.return_value = pd.DataFrame([{"time": "2024-01-02", "close": 24.5}])
    mock_etf.trades.return_value = pd.DataFrame([{"time": "10:00:00", "price": 24.5}])
    mock_etf.quote.return_value = pd.DataFrame([{"symbol": "E1VFVN30", "price": 24.5}])

    assert not service.fetch_market_etf_ohlcv("E1VFVN30").empty
    assert not service.fetch_market_etf_trades("E1VFVN30").empty
    assert not service.fetch_market_etf_quote("E1VFVN30").empty


@patch("app.services.vnstock_service.Market")
def test_market_fund_methods(
    mock_market_cls: MagicMock, service: VnstockService
) -> None:
    """Kiểm thử đầy đủ 5 phương thức thuộc lớp Market.fund (nav, history, holdings)."""
    mock_mkt = MagicMock()
    mock_market_cls.return_value = mock_mkt
    mock_fnd = MagicMock()
    mock_mkt.fund.return_value = mock_fnd

    mock_fnd.nav.return_value = pd.DataFrame([{"date": "2024-01-02", "nav": 28500.0}])
    mock_fnd.history.return_value = pd.DataFrame(
        [{"date": "2024-01-01", "nav": 28400.0}]
    )
    mock_fnd.top_holding.return_value = pd.DataFrame(
        [{"symbol": "FPT", "net_asset_percent": 12.5}]
    )
    mock_fnd.asset_holding.return_value = pd.DataFrame(
        [{"asset": "Stock", "percent": 90.0}]
    )
    mock_fnd.industry_holding.return_value = pd.DataFrame(
        [{"industry": "Technology", "percent": 25.0}]
    )

    assert not service.fetch_market_fund_nav("VESAF").empty
    assert not service.fetch_market_fund_history("VESAF").empty
    assert not service.fetch_market_fund_top_holding("VESAF").empty
    assert not service.fetch_market_fund_asset_holding("VESAF").empty
    assert not service.fetch_market_fund_industry_holding("VESAF").empty


@patch("app.services.vnstock_service.Market")
def test_market_international_and_macro_assets(
    mock_market_cls: MagicMock, service: VnstockService
) -> None:
    """Kiểm thử các lớp tài sản quốc tế & vĩ mô (forex, crypto, commodity)."""
    mock_mkt = MagicMock()
    mock_market_cls.return_value = mock_mkt

    # Forex
    mock_fx = MagicMock()
    mock_mkt.forex.return_value = mock_fx
    mock_fx.ohlcv.return_value = pd.DataFrame(
        [{"time": "2024-01-02", "close": 24500.0}]
    )
    assert not service.fetch_market_forex_ohlcv("USDVND").empty

    # Crypto
    mock_cr = MagicMock()
    mock_mkt.crypto.return_value = mock_cr
    mock_cr.ohlcv.return_value = pd.DataFrame(
        [{"time": "2024-01-02", "close": 45000.0}]
    )
    assert not service.fetch_market_crypto_ohlcv("BTC").empty

    # Commodity
    mock_com = MagicMock()
    mock_mkt.commodity.return_value = mock_com
    mock_com.ohlcv.return_value = pd.DataFrame(
        [{"time": "2024-01-02", "close": 2050.0}]
    )
    assert not service.fetch_market_commodity_ohlcv("Gold").empty


@patch("app.services.vnstock_service.Market")
def test_market_bond_methods(
    mock_market_cls: MagicMock, service: VnstockService
) -> None:
    """Kiểm thử các phương thức thuộc lớp Market.bond (trái phiếu)."""
    mock_mkt = MagicMock()
    mock_market_cls.return_value = mock_mkt
    mock_bnd = MagicMock()
    mock_mkt.bond.return_value = mock_bnd

    mock_bnd.ohlcv.return_value = pd.DataFrame([{"time": "2024-01-02", "close": 100.0}])
    mock_bnd.quote.return_value = pd.DataFrame([{"symbol": "TP2024", "price": 100.0}])
    mock_bnd.trades.return_value = pd.DataFrame([{"time": "10:30:00", "price": 100.0}])

    assert not service.fetch_market_bond_ohlcv("TP2024").empty
    assert not service.fetch_market_bond_quote("TP2024").empty
    assert not service.fetch_market_bond_trades("TP2024").empty


@patch("app.services.vnstock_service.Market")
def test_market_quick_quote(
    mock_market_cls: MagicMock, service: VnstockService
) -> None:
    """Kiểm thử phương thức lấy bảng giá nhanh Market.quote()."""
    mock_mkt = MagicMock()
    mock_market_cls.return_value = mock_mkt

    sample_quotes = pd.DataFrame(
        [
            {"symbol": "VCB", "price": 90.0},
            {"symbol": "FPT", "price": 120.0},
        ]
    )
    mock_mkt.quote.return_value = sample_quotes

    df_list = service.fetch_market_quote(["VCB", "FPT"])
    assert len(df_list) == 2
    mock_mkt.quote.assert_called_with(["VCB", "FPT"])

    df_single = service.fetch_market_quote("VCB")
    assert len(df_single) == 2


@patch("app.services.vnstock_service.Market")
def test_market_graceful_error_handling(
    mock_market_cls: MagicMock, service: VnstockService
) -> None:
    """Đảm bảo mọi phương thức đều bắt ngoại lệ an toàn và trả về DataFrame rỗng khi API lỗi."""
    mock_mkt = MagicMock()
    mock_market_cls.return_value = mock_mkt

    mock_mkt.equity.side_effect = RuntimeError("Equity API network timeout")
    mock_mkt.futures.side_effect = ValueError("Invalid futures contract")
    mock_mkt.warrant.side_effect = Exception("Warrant service unavailable")
    mock_mkt.etf.side_effect = Exception("ETF service error")
    mock_mkt.fund.side_effect = Exception("Fund service error")
    mock_mkt.forex.side_effect = Exception("Forex error")
    mock_mkt.crypto.side_effect = Exception("Crypto error")
    mock_mkt.commodity.side_effect = Exception("Commodity error")
    mock_mkt.bond.side_effect = Exception("Bond error")
    mock_mkt.quote.side_effect = Exception("Quote error")

    assert service.fetch_market_equity_ohlcv("FPT").empty
    assert service.fetch_market_equity_trades("FPT").empty
    assert service.fetch_market_equity_quote("FPT").empty

    assert service.fetch_market_futures_ohlcv("VN30F1M").empty
    assert service.fetch_market_futures_trades("VN30F1M").empty
    assert service.fetch_market_futures_quote("VN30F1M").empty

    assert service.fetch_market_warrant_ohlcv("CW1").empty
    assert service.fetch_market_warrant_trades("CW1").empty
    assert service.fetch_market_warrant_quote("CW1").empty

    assert service.fetch_market_etf_ohlcv("ETF1").empty
    assert service.fetch_market_etf_trades("ETF1").empty
    assert service.fetch_market_etf_quote("ETF1").empty

    assert service.fetch_market_fund_nav("FUND1").empty
    assert service.fetch_market_fund_history("FUND1").empty
    assert service.fetch_market_fund_top_holding("FUND1").empty
    assert service.fetch_market_fund_asset_holding("FUND1").empty
    assert service.fetch_market_fund_industry_holding("FUND1").empty

    assert service.fetch_market_forex_ohlcv("USDVND").empty
    assert service.fetch_market_crypto_ohlcv("BTC").empty
    assert service.fetch_market_commodity_ohlcv("Gold").empty

    assert service.fetch_market_bond_ohlcv("BOND1").empty
    assert service.fetch_market_bond_quote("BOND1").empty
    assert service.fetch_market_bond_trades("BOND1").empty

    assert service.fetch_market_quote("VCB").empty
