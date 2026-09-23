"""Các hàm toán học và công thức tính chỉ báo kỹ thuật định lượng thuần túy.

Được thiết kế độc lập không phụ thuộc thư viện ngoài (dùng chuẩn math/statistics),
hoàn toàn tiền định (deterministic) và an toàn tuyệt đối trước các ca biên
(chia cho 0 khi volume = 0, nến Doji H=L, chuỗi dữ liệu không đủ độ dài).
"""

import math
import statistics
from collections.abc import Sequence


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
