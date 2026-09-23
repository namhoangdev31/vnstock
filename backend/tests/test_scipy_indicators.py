"""Unit tests cho các hàm Phần 3 (scipy/scikit-learn) trong indicators.py."""
import pytest
from app.domains.quant.domain.indicators import (
    compute_basis_zscore_scipy,
    compute_engine_correlation,
    compute_historical_volatility_v2,
    compute_linear_regression_slope_v2,
    compute_t2_pressure_scipy,
    detect_market_regime_gmm,
    detect_support_resistance,
    normalize_flow_robust,
    optimize_engine_weights_from_errors,
    simulate_monte_carlo_scipy,
)


class TestLinearRegressionSlopeV2:
    def test_perfect_uptrend(self):
        values = [100.0 + i for i in range(15)]
        r = compute_linear_regression_slope_v2(values, window=10)
        assert r["slope_normalized"] > 0.0
        assert float(r["r_squared"]) > 0.95
        assert float(r["p_value"]) < 0.01
        assert r["slope_significant"] is True

    def test_perfect_downtrend(self):
        values = [115.0 - i for i in range(15)]
        r = compute_linear_regression_slope_v2(values, window=10)
        assert r["slope_normalized"] < 0.0
        assert r["slope_significant"] is True

    def test_insufficient_data_returns_defaults(self):
        r = compute_linear_regression_slope_v2([100.0, 101.0], window=10)
        assert r["slope_normalized"] == 0.0
        assert r["p_value"] == 1.0
        assert r["slope_significant"] is False

    def test_empty_input(self):
        r = compute_linear_regression_slope_v2([], window=10)
        assert r["slope_normalized"] == 0.0


class TestNormalizeFlowRobust:
    def test_normal_range_within_bounds(self):
        history = [1e9, 2e9, 1.5e9, 3e9, 0.5e9, 2.5e9, 1e9]
        r = normalize_flow_robust(2e9, history)
        assert -1.0 <= r <= 1.0

    def test_fallback_short_history(self):
        r = normalize_flow_robust(5e8, [1e9, 2e9])
        assert -1.0 <= r <= 1.0

    def test_very_large_value_capped(self):
        history = [1e9] * 6
        r = normalize_flow_robust(100e9, history)
        assert -1.0 <= r <= 1.0

    def test_negative_flow(self):
        history = [-1e9, -2e9, -1.5e9, -3e9, -0.5e9]
        r = normalize_flow_robust(-2e9, history)
        assert -1.0 <= r <= 1.0


class TestHistoricalVolatilityV2:
    def test_returns_expected_keys(self):
        closes = [1300.0 + i * 0.5 for i in range(30)]
        r = compute_historical_volatility_v2(closes)
        assert "hv" in r and "kurtosis" in r and "skewness" in r

    def test_hv_non_negative(self):
        closes = [1000.0, 1010.0, 990.0, 1005.0, 995.0, 1020.0, 980.0] * 5
        r = compute_historical_volatility_v2(closes)
        assert r["hv"] >= 0.0

    def test_constant_price_zero_vol(self):
        r = compute_historical_volatility_v2([1300.0] * 20)
        assert r["hv"] == 0.0

    def test_empty(self):
        r = compute_historical_volatility_v2([])
        assert r["hv"] == 0.0


class TestDetectSupportResistance:
    def test_short_series_returns_empty(self):
        r = detect_support_resistance([100, 105, 110], order=5)
        assert r["supports"] == [] and r["resistances"] == []

    def test_empty_input(self):
        r = detect_support_resistance([])
        assert r["supports"] == [] and r["resistances"] == []

    def test_supports_below_current(self):
        closes = [100, 95, 90, 95, 100, 95, 90, 95, 100, 95, 90, 95, 100,
                  95, 90, 95, 100, 110, 120, 115, 120]
        r = detect_support_resistance(closes, order=3)
        for s in r["supports"]:
            assert s < closes[-1]


class TestDetectMarketRegimeGMM:
    def test_returns_valid_regime(self):
        closes = [1300.0 + i * 0.5 + (i % 3) * 2 for i in range(60)]
        r = detect_market_regime_gmm(closes)
        assert r["regime"] in ("TRENDING", "RANGING", "VOLATILE")

    def test_probabilities_sum_to_one(self):
        closes = [1300.0 + i * 0.2 for i in range(60)]
        r = detect_market_regime_gmm(closes)
        total = sum(r["regime_probabilities"].values())
        assert abs(total - 1.0) < 0.05

    def test_insufficient_data_returns_ranging(self):
        r = detect_market_regime_gmm([1300.0] * 10)
        assert r["regime"] == "RANGING"

    def test_deterministic(self):
        closes = [1300.0 + (i % 7) * 3.5 + i * 0.1 for i in range(60)]
        r1 = detect_market_regime_gmm(closes)
        r2 = detect_market_regime_gmm(closes)
        assert r1["regime"] == r2["regime"]


class TestBasisZscoreScipy:
    def test_normal_basis_with_history(self):
        hist = [2.0, -1.0, 3.0, 0.5, -2.0, 1.5, 0.0, -0.5, 2.5, 1.0]
        r = compute_basis_zscore_scipy(1302.0, 1300.0, hist)
        assert r["ci_lower"] is not None
        assert float(r["ci_lower"]) < float(r["ci_upper"])

    def test_extreme_basis_mean_reverting(self):
        hist = [1.0, 2.0, 0.5, 1.5, 0.0, 1.0, 2.0, 0.5, 1.5, 0.0]
        r = compute_basis_zscore_scipy(1350.0, 1300.0, hist)
        assert r["mean_reverting"] is True

    def test_no_history_fallback(self):
        r = compute_basis_zscore_scipy(1302.0, 1300.0)
        assert r["ci_lower"] is None
        assert abs(float(r["z_score"])) <= 3.0


class TestMonteCarloScipy:
    def test_returns_expected_keys(self):
        r = simulate_monte_carlo_scipy(1300.0, 0.20, n_simulations=100)
        for key in ("p05", "p50", "p95", "mc_max_drawdown_p50", "var_95", "cvar_95"):
            assert key in r

    def test_percentile_ordering(self):
        r = simulate_monte_carlo_scipy(1300.0, 0.20, n_simulations=500)
        assert r["p05"] <= r["p50"] <= r["p95"]

    def test_within_price_limits(self):
        current = 1300.0
        r = simulate_monte_carlo_scipy(current, 0.30, n_simulations=200)
        assert r["p05"] >= current * 0.93 - 1e-6
        assert r["p95"] <= current * 1.07 + 1e-6

    def test_zero_price_returns_zeros(self):
        r = simulate_monte_carlo_scipy(0.0, 0.20)
        assert r["p50"] == 0.0

    def test_deterministic_same_seed(self):
        r1 = simulate_monte_carlo_scipy(1300.0, 0.20, n_simulations=200, seed=42)
        r2 = simulate_monte_carlo_scipy(1300.0, 0.20, n_simulations=200, seed=42)
        assert r1["p50"] == r2["p50"]


class TestT2PressureScipy:
    def test_pressure_within_range(self):
        vols = [1e6, 1.2e6, 0.9e6, 1.1e6, 1.3e6, 1.0e6, 1.2e6, 1.1e6, 0.95e6, 1.15e6]
        r = compute_t2_pressure_scipy(vols)
        assert 0.0 <= r["pressure"] <= 1.0

    def test_volume_spike_high_pressure(self):
        vols = [1e6] * 18 + [5e6, 1e6, 1e6]
        r = compute_t2_pressure_scipy(vols)
        assert r["pressure"] > 0.5

    def test_insufficient_data(self):
        r = compute_t2_pressure_scipy([1e6, 1.2e6])
        assert r["pressure"] == 0.0


class TestEngineCorrelation:
    def test_returns_expected_keys(self):
        series = [0.1 * i for i in range(1, 10)]
        r = compute_engine_correlation(series, series, series)
        assert "corr_e1_e2" in r and "corr_e1_e3" in r and "corr_e2_e3" in r

    def test_short_history_returns_zeros(self):
        r = compute_engine_correlation([0.1, 0.2], [0.3, 0.4], [0.5, 0.6])
        assert r["corr_e1_e2"] == 0.0

    def test_values_in_valid_range(self):
        e1 = [0.1 * i for i in range(1, 10)]
        e2 = [-0.1 * i for i in range(1, 10)]
        e3 = [0.05 * i for i in range(1, 10)]
        r = compute_engine_correlation(e1, e2, e3)
        for v in r.values():
            assert -1.0 <= v <= 1.0


class TestOptimizeEngineWeightsFromErrors:
    def test_weights_sum_to_one(self):
        r = optimize_engine_weights_from_errors([0.1, 0.2], [0.3, 0.4], [0.05, 0.1])
        assert abs(r["w1"] + r["w2"] + r["w3"] - 1.0) < 0.01

    def test_lower_error_gets_higher_weight(self):
        r = optimize_engine_weights_from_errors(
            [0.5, 0.4, 0.6],    # lỗi lớn
            [0.3, 0.4, 0.35],   # lỗi trung bình
            [0.01, 0.02, 0.01], # lỗi nhỏ
        )
        assert r["w3"] > r["w1"]
        assert r["w3"] > r["w2"]

    def test_empty_errors_equal_weights(self):
        r = optimize_engine_weights_from_errors([], [], [])
        assert abs(r["w1"] + r["w2"] + r["w3"] - 1.0) < 0.01

    def test_all_weights_non_negative(self):
        r = optimize_engine_weights_from_errors([0.1], [0.3], [0.2])
        assert r["w1"] >= 0.0 and r["w2"] >= 0.0 and r["w3"] >= 0.0
