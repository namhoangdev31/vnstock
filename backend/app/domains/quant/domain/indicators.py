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
