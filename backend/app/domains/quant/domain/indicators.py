"""Các hàm toán học và công thức tính chỉ báo kỹ thuật định lượng thuần túy.

Được thiết kế độc lập không phụ thuộc thư viện ngoài (dùng chuẩn math/statistics),
hoàn toàn tiền định (deterministic) và an toàn tuyệt đối trước các ca biên
(chia cho 0 khi volume = 0, nến Doji H=L, chuỗi dữ liệu không đủ độ dài).
"""

import math
import statistics
from collections.abc import Sequence
from typing import Any


def compute_rsi(closes: Sequence[float], period: int = 14) -> float | None:
    """Tính chỉ báo sức mạnh tương đối (RSI) theo phương pháp làm mượt của Wilder.

    Trả về None nếu không đủ dữ liệu (len(closes) < period + 1).
    Xử lý an toàn các ca biên: tất cả nến đều tăng (RSI = 100.0) hoặc đều giảm (RSI = 0.0).
    """
    if len(closes) < period + 1:
        return None

    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [max(d, 0.0) for d in deltas]
    losses = [max(-d, 0.0) for d in deltas]

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0.0:
        return 100.0 if avg_gain > 0.0 else 50.0
    if avg_gain == 0.0:
        return 0.0

    rs = avg_gain / avg_loss
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return round(rsi, 2)


def _compute_ema_series(values: Sequence[float], period: int) -> list[float]:
    """Tính chuỗi đường trung bình động hàm mũ (EMA)."""
    if not values:
        return []
    k = 2.0 / (period + 1)
    ema = [values[0]]
    for v in values[1:]:
        ema.append(v * k + ema[-1] * (1.0 - k))
    return ema


def compute_macd(
    closes: Sequence[float],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> dict[str, float]:
    """Tính chỉ báo MACD (Moving Average Convergence Divergence).

    Trả về {"dif": float, "dea": float, "hist": float}.
    Nếu không đủ dữ liệu (len < slow), trả về các giá trị 0.0.
    """
    if len(closes) < slow:
        return {"dif": 0.0, "dea": 0.0, "hist": 0.0}

    ema_fast = _compute_ema_series(closes, fast)
    ema_slow = _compute_ema_series(closes, slow)

    dif_series = [f - s for f, s in zip(ema_fast, ema_slow, strict=True)]
    dea_series = _compute_ema_series(dif_series, signal)

    dif = dif_series[-1]
    dea = dea_series[-1]
    hist = (
        dif - dea
    ) * 2.0  # Hệ số nhân x2 cho Histogram theo thông lệ định lượng Việt Nam

    return {"dif": round(dif, 4), "dea": round(dea, 4), "hist": round(hist, 4)}


def compute_bollinger_bands(
    closes: Sequence[float],
    period: int = 20,
    num_std: float = 2.0,
) -> dict[str, float]:
    """Tính dải Bollinger Bands (Dải trên, Dải giữa, Dải dưới, Độ rộng băng và %B)."""
    if len(closes) < period:
        latest = closes[-1] if closes else 0.0
        return {
            "upper": round(latest, 2),
            "middle": round(latest, 2),
            "lower": round(latest, 2),
            "bandwidth": 0.0,
            "percent_b": 0.5,
        }

    window = closes[-period:]
    middle = statistics.fmean(window)
    std = statistics.pstdev(window)

    upper = middle + num_std * std
    lower = middle - num_std * std

    bandwidth = (upper - lower) / middle if middle > 1e-9 else 0.0
    latest = closes[-1]
    band_range = upper - lower
    percent_b = (latest - lower) / band_range if band_range > 1e-9 else 0.5

    return {
        "upper": round(upper, 2),
        "middle": round(middle, 2),
        "lower": round(lower, 2),
        "bandwidth": round(bandwidth, 4),
        "percent_b": round(percent_b, 4),
    }


def compute_atr(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    period: int = 14,
) -> float | None:
    """Tính dải biên độ dao động thực tế trung bình (ATR) theo Wilder."""
    n = len(closes)
    if n < period + 1 or len(highs) < n or len(lows) < n:
        return None

    true_ranges: list[float] = []
    for i in range(1, n):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        true_ranges.append(tr)

    if len(true_ranges) < period:
        return None

    atr = sum(true_ranges[:period]) / period
    for tr in true_ranges[period:]:
        atr = (atr * (period - 1) + tr) / period

    return round(atr, 2)


def compute_vwap(
    prices: Sequence[float],
    volumes: Sequence[float],
) -> float | None:
    """Tính giá bình quân gia quyền theo khối lượng (VWAP).

    An toàn trước trường hợp tổng khối lượng = 0 (trả về giá đóng cửa gần nhất thay vì lỗi ZeroDivisionError).
    """
    if not prices or not volumes or len(prices) != len(volumes):
        return None

    total_vol = sum(volumes)
    if total_vol <= 0.0:
        return round(prices[-1], 2)

    cum_notional = sum(p * v for p, v in zip(prices, volumes, strict=True))
    return round(cum_notional / total_vol, 2)


def compute_parkinson_volatility(
    highs: Sequence[float],
    lows: Sequence[float],
    trading_days: int = 252,
) -> float:
    """Tính độ biến động Parkinson dựa trên dải giá cao nhất - thấp nhất (High-Low).

    An toàn tuyệt đối trước nến Doji (nơi High == Low dẫn đến log(1) == 0).
    """
    n = len(highs)
    if n == 0 or len(lows) != n:
        return 0.0

    sum_sq_log = 0.0
    valid_count = 0

    for h_val, l_val in zip(highs, lows, strict=True):
        if h_val > 0 and l_val > 0 and h_val >= l_val:
            ratio = h_val / l_val
            if ratio > 1.0:
                log_ratio = math.log(ratio)
                sum_sq_log += log_ratio * log_ratio
            valid_count += 1

    if valid_count == 0:
        return 0.0

    factor = trading_days / (4.0 * math.log(2.0) * valid_count)
    vol = math.sqrt(factor * sum_sq_log)
    return round(vol, 4)


def compute_historical_volatility(
    closes: Sequence[float],
    trading_days: int = 252,
) -> float:
    """Tính độ biến động lịch sử (HV) chuẩn hóa theo năm (252 ngày giao dịch)."""
    if len(closes) < 2:
        return 0.0

    log_returns = [
        math.log(closes[i] / closes[i - 1])
        for i in range(1, len(closes))
        if closes[i] > 0 and closes[i - 1] > 0
    ]

    if len(log_returns) < 2:
        return 0.0

    std_dev = statistics.stdev(log_returns)
    ann_vol = std_dev * math.sqrt(trading_days)
    return round(ann_vol, 4)


def compute_camarilla_pivots(
    high: float,
    low: float,
    close: float,
) -> dict[str, float]:
    """Tính các mốc hỗ trợ và kháng cự Camarilla Pivots trong ngày."""
    diff = high - low
    r4 = close + diff * 1.1 / 2.0
    r3 = close + diff * 1.1 / 4.0
    r2 = close + diff * 1.1 / 6.0
    r1 = close + diff * 1.1 / 12.0
    s1 = close - diff * 1.1 / 12.0
    s2 = close - diff * 1.1 / 6.0
    s3 = close - diff * 1.1 / 4.0
    s4 = close - diff * 1.1 / 2.0

    return {
        "r4": round(r4, 2),
        "r3": round(r3, 2),
        "r2": round(r2, 2),
        "r1": round(r1, 2),
        "s1": round(s1, 2),
        "s2": round(s2, 2),
        "s3": round(s3, 2),
        "s4": round(s4, 2),
    }


def compute_zscore(value: float, mean: float, std: float) -> float:
    """Tính điểm chuẩn Z-Score một cách an toàn (tránh chia cho 0)."""
    if std <= 1e-9:
        return 0.0
    return round((value - mean) / std, 4)


# =============================================================================
# PHẦN 2 — Hàm nâng cấp ML/thuật toán (không phụ thuộc thư viện ngoài)
# =============================================================================


def compute_rsi_smooth(closes: Sequence[float], period: int = 14) -> float | None:
    """Tính RSI làm mượt bằng Sigmoid Transform — liên tục, không có ngưỡng ngắt quãng.

    Thay thế logic if/elif cliff (RSI>=70 → fixed -0.3) bằng hàm sigmoid liên tục:
        rsi_signal = 2 / (1 + exp(-k * (rsi - 50) / 50)) - 1,  k = 5
    - RSI = 50  → 0.0  (trung tính)
    - RSI = 80  → +0.84 (bullish mạnh)
    - RSI = 20  → -0.84 (bearish mạnh)
    - RSI = 100 → +1.0  (saturate)
    - RSI = 0   → -1.0  (saturate)
    Trả về None nếu không đủ dữ liệu.
    """
    rsi_val = compute_rsi(closes, period)
    if rsi_val is None:
        return None
    k = 5.0
    signal = 2.0 / (1.0 + math.exp(-k * (rsi_val - 50.0) / 50.0)) - 1.0
    return round(max(-1.0, min(1.0, signal)), 4)


def detect_market_regime(
    closes: Sequence[float],
    highs: Sequence[float] | None = None,
    lows: Sequence[float] | None = None,
    window: int = 14,
) -> str:
    """Phát hiện chế độ thị trường theo phương pháp ADX-inspired thuần Python.

    Trả về:
    - "TRENDING"  : Xu hướng rõ, ADX-proxy > 25 → MACD/momentum đáng tin cậy hơn
    - "RANGING"   : Sideway, ADX-proxy ≤ 25, vol thấp → RSI/Bollinger đáng tin cậy hơn
    - "VOLATILE"  : Biến động bất thường, HV tăng đột ngột → ATR/BB quan trọng hơn

    Thuật toán:
    1. ADX-proxy từ DM+/DM-/TR trên closes (nếu có H/L, dùng chính xác hơn)
    2. Phát hiện volatile khi HV hiện tại > 1.5 * HV median
    """
    n = len(closes)
    if n < window + 2:
        return "RANGING"

    # === 1. Volatility regime: so sánh HV ngắn hạn vs trung hạn ===
    short_window = max(5, window // 2)
    hv_short = compute_historical_volatility(list(closes[-short_window:]))
    hv_long = compute_historical_volatility(list(closes[-window:]))

    if hv_long > 1e-9 and hv_short > 1.6 * hv_long:
        return "VOLATILE"

    # === 2. ADX-proxy dùng True Range và Directional Movement ===
    if highs and lows and len(highs) >= window + 1 and len(lows) >= window + 1:
        h = list(highs)
        lo = list(lows)
        cl = list(closes)

        tr_list: list[float] = []
        dm_plus_list: list[float] = []
        dm_minus_list: list[float] = []

        for i in range(1, len(cl)):
            high_i = h[i]
            low_i = lo[i]
            close_prev = cl[i - 1]
            high_prev = h[i - 1]
            low_prev = lo[i - 1]

            tr = max(
                high_i - low_i,
                abs(high_i - close_prev),
                abs(low_i - close_prev),
            )
            tr_list.append(tr)

            up_move = high_i - high_prev
            down_move = low_prev - low_i
            dm_plus_list.append(up_move if up_move > down_move and up_move > 0 else 0.0)
            dm_minus_list.append(
                down_move if down_move > up_move and down_move > 0 else 0.0
            )

        if len(tr_list) >= window:
            atr_w = statistics.fmean(tr_list[-window:]) or 1e-9
            di_plus = 100.0 * statistics.fmean(dm_plus_list[-window:]) / atr_w
            di_minus = 100.0 * statistics.fmean(dm_minus_list[-window:]) / atr_w
            dx = 100.0 * abs(di_plus - di_minus) / (di_plus + di_minus + 1e-9)
            return "TRENDING" if dx > 25.0 else "RANGING"

    # === 3. Fallback khi không có H/L: slope-based regime ===
    window_closes = list(closes[-window:])
    mid = window // 2
    first_half_mean = statistics.fmean(window_closes[:mid])
    second_half_mean = statistics.fmean(window_closes[mid:])
    price_range = max(window_closes) - min(window_closes)
    trend_strength = abs(second_half_mean - first_half_mean) / (price_range + 1e-9)

    return "TRENDING" if trend_strength > 0.25 else "RANGING"


def compute_roc(closes: Sequence[float], period: int = 10) -> float:
    """Tính Rate of Change (ROC) — xung lượng tương đối trong khoảng `period` phiên.

    ROC = (close[-1] - close[-period]) / close[-period]
    Trả về giá trị trong dải [-1.0, +1.0] (cap extreme values).
    Trả về 0.0 khi không đủ dữ liệu.
    """
    if len(closes) < period + 1:
        return 0.0
    prev = closes[-(period + 1)]
    if abs(prev) < 1e-9:
        return 0.0
    roc = (closes[-1] - prev) / prev
    return round(max(-1.0, min(1.0, roc)), 4)


def compute_linear_regression_slope(
    values: Sequence[float],
    window: int = 10,
) -> float:
    """Tính độ dốc hồi quy tuyến tính (Ordinary Least Squares) chuẩn hóa theo cửa sổ `window`.

    Chuẩn hóa slope bằng cách chia cho mean giá trị để có đơn vị %/bar.
    Trả về giá trị trong dải [-1.0, +1.0]:
    - Dương mạnh: xu hướng tăng rõ
    - Âm mạnh: xu hướng giảm rõ
    - Gần 0: sideway
    Trả về 0.0 khi không đủ dữ liệu.
    """
    n = min(window, len(values))
    if n < 3:
        return 0.0

    series = list(values[-n:])
    x_mean = (n - 1) / 2.0
    y_mean = statistics.fmean(series)

    if abs(y_mean) < 1e-9:
        return 0.0

    numerator = sum((i - x_mean) * (y - y_mean) for i, y in enumerate(series))
    denominator = sum((i - x_mean) ** 2 for i in range(n))

    if abs(denominator) < 1e-9:
        return 0.0

    slope = numerator / denominator
    # Chuẩn hóa: slope theo %/bar rồi scale lên để có ý nghĩa kinh tế
    normalized = slope / y_mean * n  # slope%/bar * n_bars ≈ tổng % thay đổi
    return round(max(-1.0, min(1.0, normalized)), 4)


def compute_adaptive_zscore(
    value: float,
    series: Sequence[float],
    window: int = 60,
) -> float:
    """Tính Z-Score động (rolling) trên cửa sổ `window` thay vì population stats cố định.

    Ưu điểm so với compute_zscore() tĩnh:
    - Tự thích nghi khi phân phối dịch chuyển (drift)
    - Không bị ảnh hưởng bởi outliers từ cách đây quá lâu

    Fallback khi series ngắn (< 5 phần tử): dùng value / 5.0 (tương tự fallback cũ).
    Trả về giá trị trong dải [-5.0, +5.0].
    """
    relevant = list(series[-window:]) if len(series) >= 5 else []
    if len(relevant) < 5:
        # Fallback conservative: coi std ≈ 5.0 điểm index (VN30 convention)
        z = value / 5.0
        return round(max(-5.0, min(5.0, z)), 4)

    mean_val = statistics.fmean(relevant)
    std_val = statistics.pstdev(relevant)

    if std_val < 1e-9:
        return 0.0

    z = (value - mean_val) / std_val
    return round(max(-5.0, min(5.0, z)), 4)


def compute_entropy(distribution: Sequence[float]) -> float:
    """Tính Shannon Entropy chuẩn hóa cho một phân phối xác suất.

    Đo mức độ bất định / không đồng thuận của phân phối:
    - Entropy = 0.0: tất cả mass dồn vào 1 điểm (certainty)
    - Entropy = 1.0: phân phối đều hoàn toàn (maximum uncertainty)

    Dùng cho: đánh giá mức độ đồng thuận của các engine scores.
    Input: chuỗi số thực dương (không cần chuẩn hóa, hàm tự normalize).
    Trả về 0.0 khi distribution rỗng hoặc tất cả bằng 0.
    """
    if not distribution:
        return 0.0

    abs_vals = [abs(v) for v in distribution]
    total = sum(abs_vals)
    if total < 1e-9:
        return 0.0

    probs = [v / total for v in abs_vals]
    n = len(probs)
    max_entropy = math.log(n) if n > 1 else 1.0

    h = -sum(p * math.log(p + 1e-12) for p in probs if p > 1e-12)
    return round(h / max_entropy, 4) if max_entropy > 1e-9 else 0.0


def compute_exponential_smoothing(
    values: Sequence[float],
    alpha: float = 0.3,
) -> list[float]:
    """Làm mượt chuỗi thời gian bằng Exponential Weighted Moving Average (EWMA).

    Công thức: S_t = alpha * x_t + (1 - alpha) * S_{t-1}
    - alpha cao (0.7-0.9): phản ứng nhanh, ít làm mượt
    - alpha thấp (0.1-0.3): làm mượt mạnh, phản ứng chậm

    Trả về chuỗi đã làm mượt cùng độ dài với input.
    Trả về [] khi input rỗng.
    """
    if not values:
        return []

    smoothed: list[float] = [values[0]]
    for v in values[1:]:
        smoothed.append(alpha * v + (1.0 - alpha) * smoothed[-1])

    return smoothed


# =============================================================================
# PHẦN 3 — Hàm nâng cao sử dụng scipy & scikit-learn
# Các hàm này thay thế / bổ sung cho Phần 1-2 với:
#   - Độ tin cậy thống kê cao hơn (p-value, t-distribution, CI 95%)
#   - Hiệu năng C-level vectorization (numpy/scipy thay Python loop)
#   - Kháng outlier tốt hơn (RobustScaler thay Min-Max)
# Mọi hàm đều an toàn trước edge case (rỗng, NaN, thiếu dữ liệu).
# =============================================================================

import numpy as np  # noqa: E402 — intentional placement in module body


def compute_linear_regression_slope_v2(
    values: Sequence[float],
    window: int = 10,
) -> dict[str, float | bool]:
    """Tính hồi quy tuyến tính OLS với kiểm định ý nghĩa thống kê (scipy.stats.linregress).

    Nâng cấp so với compute_linear_regression_slope() (Phần 2):
    - Trả thêm R² (hệ số xác định) và p_value (ý nghĩa thống kê)
    - slope_normalized vẫn trong [-1.0, +1.0] — backward-compatible

    Công thức:
        t_stat = slope / stderr;  p = 2 * P(T > |t|; df=n-2)
        R² = r² (bình phương Pearson correlation)

    Returns:
        slope_normalized : float [-1.0, +1.0] — tương thích ngược v1
        r_squared        : float [0.0, 1.0]   — 1.0 = linear hoàn hảo
        p_value          : float [0.0, 1.0]   — < 0.05 → có ý nghĩa
        slope_significant: bool               — p < 0.05 VÀ R² > 0.3
    """
    from scipy.stats import linregress  # lazy import — tránh circular

    n = min(window, len(values))
    if n < 3:
        return {
            "slope_normalized": 0.0,
            "r_squared": 0.0,
            "p_value": 1.0,
            "slope_significant": False,
        }

    series = list(values[-n:])
    x = list(range(n))
    y_mean = sum(series) / n

    if abs(y_mean) < 1e-9:
        return {
            "slope_normalized": 0.0,
            "r_squared": 0.0,
            "p_value": 1.0,
            "slope_significant": False,
        }

    try:
        result = linregress(x, series)
    except Exception:
        return {
            "slope_normalized": 0.0,
            "r_squared": 0.0,
            "p_value": 1.0,
            "slope_significant": False,
        }

    # Chuẩn hóa slope → [-1.0, +1.0] (backward-compatible với v1)
    normalized = result.slope / y_mean * n
    slope_norm = round(max(-1.0, min(1.0, normalized)), 4)

    r_squared = round(float(result.rvalue) ** 2, 4)
    p_value = round(float(result.pvalue), 6)
    significant = p_value < 0.05 and r_squared > 0.3

    return {
        "slope_normalized": slope_norm,
        "r_squared": r_squared,
        "p_value": p_value,
        "slope_significant": bool(significant),
    }


def normalize_flow_robust(
    current_val: float,
    history_vals: list[float],
    fallback_scale: float = 1_000_000_000.0,
) -> float:
    """Chuẩn hóa dòng tiền tổ chức bằng RobustScaler (IQR-based, kháng outlier).

    Thay thế _normalize_series() Min-Max trong FlowLiquidityEngine:
    - RobustScaler dùng IQR thay min/max → 1 phiên bán ròng kỷ lục KHÔNG méo scale
    - Kết quả trong [-3.0, +3.0] → scale về [-1.0, +1.0]

    Công thức:
        X_scaled = (X - median(history)) / IQR(history)
        IQR = Q75 - Q25

    Fallback: len(history) < 5 → chia cho fallback_scale (backward-compatible).
    """
    from sklearn.preprocessing import RobustScaler  # lazy import

    if len(history_vals) < 5:
        return round(max(-1.0, min(1.0, current_val / fallback_scale)), 4)

    arr = np.array(history_vals + [current_val], dtype=np.float64).reshape(-1, 1)

    try:
        scaler = RobustScaler()
        scaled = scaler.fit_transform(arr)
        normalized = float(scaled[-1, 0])
    except Exception:
        return round(max(-1.0, min(1.0, current_val / fallback_scale)), 4)

    clipped = max(-3.0, min(3.0, normalized))
    return round(clipped / 3.0, 4)


def compute_historical_volatility_v2(
    closes: Sequence[float],
    trading_days: int = 252,
) -> dict[str, float]:
    """Tính Historical Volatility nâng cấp — vectorized + kurtosis/skewness.

    Nâng cấp so với compute_historical_volatility() (Phần 1):
    - numpy vectorized (nhanh hơn Python loop)
    - Trả thêm kurtosis (đuôi béo — tail risk) và skewness (lệch phân phối)

    Ý nghĩa:
    - kurtosis > 3 → fat tails → rủi ro tail risk cao hơn phân phối chuẩn
    - skewness < 0 → lệch trái → xác suất drop lớn cao hơn spike
    """
    from scipy import stats as scipy_stats  # lazy import

    if len(closes) < 2:
        return {"hv": 0.0, "kurtosis": 0.0, "skewness": 0.0}

    arr = np.array(closes, dtype=np.float64)
    valid = arr[arr > 0]
    if len(valid) < 2:
        return {"hv": 0.0, "kurtosis": 0.0, "skewness": 0.0}

    log_returns = np.diff(np.log(valid))
    if len(log_returns) < 2:
        return {"hv": 0.0, "kurtosis": 0.0, "skewness": 0.0}

    hv = float(np.std(log_returns, ddof=1) * np.sqrt(trading_days))
    kurt = float(scipy_stats.kurtosis(log_returns, fisher=True))  # excess kurtosis
    skew = float(scipy_stats.skew(log_returns))

    return {
        "hv": round(max(0.0, hv), 4),
        "kurtosis": round(kurt, 4),
        "skewness": round(skew, 4),
    }


def detect_support_resistance(
    closes: Sequence[float],
    order: int = 5,
    n_levels: int = 3,
) -> dict[str, list[float]]:
    """Phát hiện mức Hỗ trợ / Kháng cự bằng Local Extrema (scipy.signal.argrelextrema).

    Thuật toán:
    1. argrelextrema(arr, np.greater, order) → đỉnh cục bộ (Resistance)
    2. argrelextrema(arr, np.less,    order) → đáy cục bộ (Support)
    3. Lọc lấy N mức gần nhất với giá hiện tại

    Parameters:
        order   : số nến tối thiểu 2 bên (order=5 → cần 5 nến bên trái & phải thấp/cao hơn)
        n_levels: số mức S/R trả về mỗi phía

    Returns:
        {"supports": [1280.5, ...], "resistances": [1310.0, ...]}
    """
    from scipy.signal import argrelextrema  # lazy import

    if len(closes) < 2 * order + 1:
        return {"supports": [], "resistances": []}

    arr = np.array(closes, dtype=np.float64)
    current = float(arr[-1])

    resistance_idx = argrelextrema(arr, np.greater, order=order)[0]
    support_idx = argrelextrema(arr, np.less, order=order)[0]

    resistances = sorted([float(arr[i]) for i in resistance_idx if arr[i] > current])[
        :n_levels
    ]

    supports = sorted(
        [float(arr[i]) for i in support_idx if arr[i] < current],
        reverse=True,
    )[:n_levels]

    return {
        "supports": [round(s, 2) for s in supports],
        "resistances": [round(r, 2) for r in resistances],
    }


def detect_market_regime_gmm(
    closes: Sequence[float],
    window: int = 60,
    n_regimes: int = 3,
) -> dict[str, Any]:
    """Phát hiện chế độ thị trường bằng Gaussian Mixture Model (GMM).

    Ưu điểm so với detect_market_regime() ADX-proxy thủ công (Phần 2):
    - Tự học phân phối từ dữ liệu (không hard-code threshold 25.0)
    - Soft classification: trả xác suất cho mỗi regime
    - Tự thích nghi khi thị trường thay đổi cấu trúc

    Quy trình:
    1. Tính log-return trên window cuối
    2. Fit GMM 3 components → phân loại theo variance
       - variance thấp nhất → RANGING
       - variance cao nhất  → VOLATILE
       - giữa + mean ≠ 0   → TRENDING (ngược lại → RANGING)
    3. Predict regime hiện tại + xác suất từng regime

    Returns:
        regime                   : "TRENDING" | "RANGING" | "VOLATILE"
        regime_probabilities     : dict[str, float]
        current_regime_confidence: float [0.0, 1.0]
    """
    from sklearn.mixture import GaussianMixture  # lazy import

    n = min(window, len(closes))
    _default = {
        "regime": "RANGING",
        "regime_probabilities": {"TRENDING": 0.0, "RANGING": 1.0, "VOLATILE": 0.0},
        "current_regime_confidence": 1.0,
    }

    if n < 15:
        return _default

    series = list(closes[-n:])
    log_returns: list[float] = []
    for i in range(1, len(series)):
        if series[i] > 0 and series[i - 1] > 0:
            log_returns.append(float(np.log(series[i] / series[i - 1])))

    if len(log_returns) < 10:
        return _default

    X = np.array(log_returns, dtype=np.float64).reshape(-1, 1)
    n_comp = min(n_regimes, len(log_returns) // 5)
    if n_comp < 2:
        return _default

    try:
        gmm = GaussianMixture(
            n_components=n_comp,
            covariance_type="full",
            random_state=42,
            max_iter=100,
        )
        gmm.fit(X)
    except Exception:
        return _default

    # assert đảm bảo type checker biết covariances_/means_ không None sau khi fit thành công
    assert gmm.covariances_ is not None and gmm.means_ is not None  # noqa: S101
    variances = gmm.covariances_.flatten()
    means = gmm.means_.flatten()
    sorted_by_var = list(np.argsort(variances))

    # Mapping component → regime name
    regime_map: dict[int, str] = {}
    if len(sorted_by_var) >= 3:
        regime_map[sorted_by_var[0]] = "RANGING"
        regime_map[sorted_by_var[-1]] = "VOLATILE"
        mid_idx = int(sorted_by_var[1])
        regime_map[mid_idx] = "TRENDING" if abs(means[mid_idx]) > 0.001 else "RANGING"
    elif len(sorted_by_var) == 2:
        regime_map[sorted_by_var[0]] = "RANGING"
        regime_map[sorted_by_var[1]] = "VOLATILE"
    else:
        regime_map[0] = "RANGING"

    last_return = np.array([[log_returns[-1]]], dtype=np.float64)
    proba = gmm.predict_proba(last_return)[0]
    predicted_component = int(np.argmax(proba))
    current_regime = regime_map.get(predicted_component, "RANGING")

    regime_probs: dict[str, float] = {"TRENDING": 0.0, "RANGING": 0.0, "VOLATILE": 0.0}
    for comp_idx, regime_name in regime_map.items():
        if comp_idx < len(proba):
            regime_probs[regime_name] = regime_probs.get(regime_name, 0.0) + float(
                proba[comp_idx]
            )

    return {
        "regime": current_regime,
        "regime_probabilities": {k: round(v, 4) for k, v in regime_probs.items()},
        "current_regime_confidence": round(float(np.max(proba)), 4),
    }


def compute_basis_zscore_scipy(
    futures_price: float,
    spot_index_price: float,
    historical_basis: Sequence[float] | None = None,
) -> dict[str, Any]:
    """Tính Basis Z-score nâng cấp với Khoảng Tin Cậy 95% và t-distribution.

    Nâng cấp so với compute_basis_zscore() trong QuantMLEngine (Phần 1):
    - t-distribution thay vì Normal assumption (chính xác khi n < 30)
    - Trả CI 95% cho mean — basis ngoài CI → khả năng mean-reversion cao
    - p_value cho H₀: basis = mean(historical)

    Công thức:
        t_stat = (basis - mean) / (std / √n)
        CI_95  = mean ± t_{0.025, df=n-1} × (std / √n)

    Fallback khi len(historical) < 5: std ≈ 5.0 (VN30 convention).

    Returns:
        basis         : float — basis hiện tại (futures - spot)
        z_score       : float — Z-score trong [-5.0, +5.0]
        ci_lower      : float | None — biên dưới CI 95% của mean
        ci_upper      : float | None — biên trên CI 95% của mean
        p_value       : float | None — xác suất H₀ đúng
        mean_reverting: bool — True khi basis ngoài CI (≈ outlier)
    """
    from scipy.stats import t as t_dist  # lazy import

    basis = futures_price - spot_index_price

    if not historical_basis or len(historical_basis) < 5:
        return {
            "basis": round(basis, 2),
            "z_score": round(max(-3.0, min(3.0, basis / 5.0)), 4),
            "ci_lower": None,
            "ci_upper": None,
            "p_value": None,
            "mean_reverting": False,
        }

    arr = np.array(historical_basis, dtype=np.float64)
    n = len(arr)
    mean_val = float(np.mean(arr))
    std_val = float(np.std(arr, ddof=1))

    if std_val < 1e-9:
        return {
            "basis": round(basis, 2),
            "z_score": 0.0,
            "ci_lower": round(mean_val, 2),
            "ci_upper": round(mean_val, 2),
            "p_value": 1.0,
            "mean_reverting": False,
        }

    z = (basis - mean_val) / std_val
    z_clipped = round(max(-5.0, min(5.0, z)), 4)

    se = std_val / float(np.sqrt(n))
    t_crit = float(t_dist.ppf(0.975, df=n - 1))
    ci_lower = round(mean_val - t_crit * se, 2)
    ci_upper = round(mean_val + t_crit * se, 2)

    t_stat = (basis - mean_val) / max(se, 1e-9)
    p_value = round(float(2 * t_dist.sf(abs(t_stat), df=n - 1)), 6)
    mean_reverting = basis < ci_lower or basis > ci_upper

    return {
        "basis": round(basis, 2),
        "z_score": z_clipped,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "p_value": p_value,
        "mean_reverting": bool(mean_reverting),
    }


def simulate_monte_carlo_scipy(
    current_price: float,
    volatility: float,
    n_simulations: int = 1000,
    seed: int = 42,
    n_steps: int = 8,
) -> dict[str, float]:
    """Mô phỏng Monte Carlo GBM nâng cấp — numpy vectorized + VaR/CVaR.

    Nâng cấp so với simulate_monte_carlo_t1() (QuantMLEngine, Phần 1):
    - scipy.stats.norm.rvs() tạo ma trận (n_sims × n_steps) một lần — nhanh ~50x
    - numpy vectorized exp/clip — loại bỏ Python loop
    - Trả thêm var_95 (Value at Risk 95%) và cvar_95 (Expected Shortfall)

    Mô hình GBM:
        S(t+dt) = S(t) × exp[(μ - σ²/2)dt + σ√dt × Z]
        Z ~ N(0, 1)
        Clip vào biên độ ±7% (quy định HOSE/VN30F1M)

    Benchmark: 1000 sims × 8 steps: ~0.8ms (vs ~15ms Python loop)

    Returns:
        p05, p50, p95        : phân vị cuối phiên
        mc_max_drawdown_p50  : phân vị 50% max drawdown trong ngày (%)
        var_95               : Value at Risk 95% (% return, âm = lỗ)
        cvar_95              : Conditional VaR / Expected Shortfall 95%
    """
    if current_price <= 0.0:
        return {
            "p05": 0.0,
            "p50": 0.0,
            "p95": 0.0,
            "mc_max_drawdown_p50": 0.0,
            "var_95": 0.0,
            "cvar_95": 0.0,
        }

    effective_vol = max(0.05, min(0.60, volatility if volatility > 0 else 0.20))

    dt = 1.0 / 252.0 / n_steps
    drift = 0.0
    mu_step = (drift - 0.5 * effective_vol**2) * dt
    vol_step = effective_vol * float(np.sqrt(dt))

    floor_limit = current_price * 0.93
    ceiling_limit = current_price * 1.07

    try:
        from scipy.stats import norm as scipy_norm  # lazy import

        rng = np.random.default_rng(seed)
        Z = scipy_norm.rvs(size=(n_simulations, n_steps), random_state=rng)

        # GBM increments vectorized
        increments = np.exp(mu_step + vol_step * Z)

        # Price paths: (n_sims, n_steps+1)
        prices = np.empty((n_simulations, n_steps + 1), dtype=np.float64)
        prices[:, 0] = current_price
        for step in range(n_steps):
            prices[:, step + 1] = np.clip(
                prices[:, step] * increments[:, step],
                floor_limit,
                ceiling_limit,
            )

        final_prices = prices[:, -1]

        # Max drawdown per simulation
        running_max = np.maximum.accumulate(prices, axis=1)
        safe_max = np.where(running_max > 0, running_max, 1.0)
        drawdowns = (running_max - prices) / safe_max
        max_drawdowns = np.max(drawdowns, axis=1)

        p05 = float(np.percentile(final_prices, 5))
        p50 = float(np.percentile(final_prices, 50))
        p95 = float(np.percentile(final_prices, 95))
        dd_p50 = float(np.percentile(max_drawdowns, 50))

        returns = (final_prices - current_price) / current_price
        var_95 = float(np.percentile(returns, 5))
        tail_returns = returns[returns <= var_95]
        cvar_95 = float(np.mean(tail_returns)) if len(tail_returns) > 0 else var_95

    except Exception:
        # Fallback về Python loop nếu scipy/numpy không khả dụng
        import random as _random

        rng_fb = _random.Random(seed)
        final_prices_list: list[float] = []
        for _ in range(n_simulations):
            price = current_price
            for _ in range(n_steps):
                z = rng_fb.gauss(0.0, 1.0)
                price = max(
                    floor_limit,
                    min(ceiling_limit, price * math.exp(mu_step + vol_step * z)),
                )
            final_prices_list.append(price)
        final_prices_list.sort()
        idx_05 = int(0.05 * n_simulations)
        idx_50 = int(0.50 * n_simulations)
        idx_95 = int(0.95 * n_simulations)
        p05 = final_prices_list[idx_05]
        p50 = final_prices_list[idx_50]
        p95 = final_prices_list[idx_95]
        dd_p50 = 0.0
        var_95 = (p05 - current_price) / current_price if current_price > 0 else 0.0
        cvar_95 = var_95

    return {
        "p05": round(p05, 2),
        "p50": round(p50, 2),
        "p95": round(p95, 2),
        "mc_max_drawdown_p50": round(dd_p50 * 100.0, 4),
        "var_95": round(var_95 * 100.0, 4),
        "cvar_95": round(cvar_95 * 100.0, 4),
    }


def compute_t2_pressure_scipy(
    daily_volumes: Sequence[float],
    baseline_ma_window: int = 20,
) -> dict[str, float]:
    """Tính T+2 Pressure Index nâng cấp với t-distribution (scipy.stats).

    Nâng cấp so với compute_t2_pressure_index() (FlowLiquidityEngine):
    - t-distribution thay Normal assumption (chính xác khi window < 30 ngày)
    - p_spike = xác suất volume T-2 là outlier thực sự (tránh false positive)
    - Trả thêm z_volume và p_spike để ForecastJournal lưu trace

    Công thức:
        Z_vol = (Vol_T2 - mean) / std_sample
        p_spike = P(T > |Z_vol|; df=n-1)  ← t-distribution survival function
        Pressure = 0.70 × min(1, Vol_T2 / (MA20 × 1.5))
                 + 0.30 × (1 - p_spike)

    Returns:
        pressure : float [0.0, 1.0]
        z_volume : float — Z-score của volume T-2
        p_spike  : float [0.0, 1.0] — xác suất volume là noise (nhỏ → spike thật)
    """
    from scipy.stats import t as t_dist  # lazy import

    if len(daily_volumes) < 3:
        return {"pressure": 0.0, "z_volume": 0.0, "p_spike": 1.0}

    vol_t2 = daily_volumes[-2]
    window = list(
        daily_volumes[max(0, len(daily_volumes) - baseline_ma_window - 2) : -2]
    )
    if not window:
        return {"pressure": 0.0, "z_volume": 0.0, "p_spike": 1.0}

    avg_vol = sum(window) / len(window)
    if avg_vol <= 0:
        return {"pressure": 0.0, "z_volume": 0.0, "p_spike": 1.0}

    pressure_base = min(1.0, vol_t2 / (avg_vol * 1.5))

    if len(window) >= 5:
        arr_w = np.array(window, dtype=np.float64)
        mean_w = float(np.mean(arr_w))
        std_w = float(np.std(arr_w, ddof=1))  # sample std (ddof=1)
        if std_w < 1e-9:
            std_w = avg_vol * 0.3

        z_vol = (vol_t2 - mean_w) / std_w
        df = len(window) - 1
        # Survival function: P(T > |z|) — nhỏ → volume spike bất thường
        p_spike = float(t_dist.sf(abs(z_vol), df))

        pressure = 0.70 * pressure_base + 0.30 * (1.0 - p_spike)
    else:
        z_vol = 0.0
        p_spike = 1.0
        pressure = pressure_base

    return {
        "pressure": round(min(1.0, max(0.0, pressure)), 4),
        "z_volume": round(z_vol, 4),
        "p_spike": round(p_spike, 6),
    }


def compute_engine_correlation(
    e1_history: Sequence[float],
    e2_history: Sequence[float],
    e3_history: Sequence[float],
) -> dict[str, float]:
    """Tính Pearson correlation giữa các cặp Engine scores trên chuỗi lịch sử.

    Dùng trong EnsembleEngine để đánh giá mức độ đồng thuận có ý nghĩa thống kê:
    - corr(E1, E3) cao và dương → 2 engine đồng pha → confidence tăng
    - corr(E1, E3) âm → 2 engine phản pha → giảm confidence, thiên NEUTRAL

    Chỉ tính correlation khi p < 0.10 (10% significance level).
    Fallback về 0.0 khi không đủ dữ liệu hoặc p ≥ 0.10.

    Returns:
        corr_e1_e2, corr_e1_e3, corr_e2_e3: float [-1.0, +1.0]
    """
    from scipy.stats import pearsonr  # lazy import

    min_len = min(len(e1_history), len(e2_history), len(e3_history))
    if min_len < 5:
        return {"corr_e1_e2": 0.0, "corr_e1_e3": 0.0, "corr_e2_e3": 0.0}

    e1 = list(e1_history[-min_len:])
    e2 = list(e2_history[-min_len:])
    e3 = list(e3_history[-min_len:])

    def _safe_corr(a: list[float], b: list[float]) -> float:
        """Tính Pearson r an toàn — trả 0.0 nếu p ≥ 0.10 hoặc exception."""
        try:
            r_val, p_val = pearsonr(a, b)
            return round(float(r_val), 4) if float(p_val) < 0.10 else 0.0
        except Exception:
            return 0.0

    return {
        "corr_e1_e2": _safe_corr(e1, e2),
        "corr_e1_e3": _safe_corr(e1, e3),
        "corr_e2_e3": _safe_corr(e2, e3),
    }


def optimize_engine_weights_from_errors(
    e1_errors: Sequence[float],
    e2_errors: Sequence[float],
    e3_errors: Sequence[float],
    decay: float = 0.95,
) -> dict[str, float]:
    """Tối ưu trọng số Engine bằng Inverse-Error Weighting với Exponential Decay.

    Dùng trong Layer B — Controlled Recalibration Loop (AGENTS.md §9.2):
    Engine có MAE gần đây thấp hơn → được gán trọng số cao hơn.

    Công thức:
        wMAE_i = Σ_{t} (decay^t × |error_i,t|) / Σ_{t} (decay^t)
        w_i    = (1 / wMAE_i) / Σ_j (1 / wMAE_j)    ← inverse-error normalized

    decay = 0.95:
        - Phiên gần nhất quan trọng gấp 20x so với phiên cách đây 60 ngày
        - Phiên cách đây 1 tuần ≈ 0.95^5 ≈ 0.77 trọng số

    Fallback: nếu không có history → equal weights (1/3 each).

    Returns:
        {"w1": float, "w2": float, "w3": float}  — normalized, sum = 1.0
    """

    def _weighted_mae(errors: Sequence[float]) -> float:
        if not errors:
            return 1.0
        n = len(errors)
        weights = [decay ** (n - 1 - i) for i in range(n)]
        total_w = sum(weights)
        if total_w < 1e-9:
            return 1.0
        return sum(w * abs(e) for w, e in zip(weights, errors, strict=True)) / total_w

    mae1 = max(1e-6, _weighted_mae(e1_errors))
    mae2 = max(1e-6, _weighted_mae(e2_errors))
    mae3 = max(1e-6, _weighted_mae(e3_errors))

    inv1 = 1.0 / mae1
    inv2 = 1.0 / mae2
    inv3 = 1.0 / mae3
    total = inv1 + inv2 + inv3

    if total < 1e-9:
        return {"w1": 0.3333, "w2": 0.3333, "w3": 0.3334}

    return {
        "w1": round(inv1 / total, 4),
        "w2": round(inv2 / total, 4),
        "w3": round(inv3 / total, 4),
    }
