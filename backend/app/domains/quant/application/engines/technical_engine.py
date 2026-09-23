"""Engine 1: Động cơ Phân tích Kỹ thuật & Hành động Giá (TechnicalEngine).

Tính toán các chỉ báo kỹ thuật đa khung thời gian (RSI, MACD, Bollinger Bands, ATR, VWAP),
dòng lệnh khớp chủ động (Orderflow Delta & Imbalance) từ dữ liệu tick, các mốc đảo chiều
Camarilla, khoảng trống giá mất cân bằng (Fair Value Gap - FVG) và bẫy quét thanh khoản (Sweeps).
"""

import math
from collections.abc import Sequence
from datetime import datetime
from typing import Any

import pandas as pd
from sqlmodel import Session, col, select

from app.core.models_base import VN_TZ
from app.domains.market_data.domain.models import StockOHLCVDaily
from app.domains.quant.application.schemas import TechnicalEngineResponse
from app.domains.quant.domain.indicators import (
    compute_atr,
    compute_bollinger_bands,
    compute_camarilla_pivots,
    compute_macd,
    compute_roc,
    compute_rsi,
    compute_vwap,
    detect_market_regime,
)
from app.domains.quant.domain.models import TickFlowAggregated


def _sigmoid_rsi(rsi: float) -> float:
    """Transform RSI qua sigmoid liên tục — thay thế cliff tại 30/70.

    signal = 2/(1+exp(-k*(rsi-50)/50)) - 1, k = 5
    RSI 50 → 0.0, RSI 80 → +0.84, RSI 20 → -0.84, RSI 0/100 → ±1.0.
    """
    k = 5.0
    signal = 2.0 / (1.0 + math.exp(-k * (rsi - 50.0) / 50.0)) - 1.0
    return round(max(-1.0, min(1.0, signal)), 4)


class TechnicalEngine:
    """Động cơ Phân tích Kỹ thuật và Hành động Giá."""

    def __init__(self, session: Session | None = None) -> None:
        self.session = session

    def compute_orderflow_metrics(
        self,
        ticks_or_aggregated: pd.DataFrame | Sequence[Any] | None,
    ) -> tuple[int, float]:
        """Tính chênh lệch khối lượng (Volume Delta) và tỷ lệ mất cân bằng lệnh (Order Imbalance) [-1.0, +1.0].

        Hỗ trợ DataFrame có cột 'match_type' & 'volume', hoặc danh sách các bản ghi TickFlowAggregated.
        Xử lý các ca biên: 100% mua chủ động -> +1.0, 100% bán chủ động -> -1.0, tổng volume bằng 0 -> 0.0.
        """
        if ticks_or_aggregated is None:
            return 0, 0.0

        buy_vol = 0
        sell_vol = 0

        if isinstance(ticks_or_aggregated, pd.DataFrame):
            if ticks_or_aggregated.empty or "volume" not in ticks_or_aggregated.columns:
                return 0, 0.0
            col_type = (
                "match_type"
                if "match_type" in ticks_or_aggregated.columns
                else "type"
                if "type" in ticks_or_aggregated.columns
                else None
            )
            if col_type is not None:
                mt = ticks_or_aggregated[col_type].astype(str).str.upper()
                buy_vol = int(ticks_or_aggregated.loc[mt == "BUY", "volume"].sum())
                sell_vol = int(ticks_or_aggregated.loc[mt == "SELL", "volume"].sum())
            else:
                buy_vol = int(ticks_or_aggregated["volume"].sum())
        else:
            for item in ticks_or_aggregated:
                if isinstance(item, TickFlowAggregated):
                    buy_vol += item.aggressive_buy_volume
                    sell_vol += item.aggressive_sell_volume
                elif hasattr(item, "aggressive_buy_volume"):
                    buy_vol += int(getattr(item, "aggressive_buy_volume", 0))
                    sell_vol += int(getattr(item, "aggressive_sell_volume", 0))

        delta = buy_vol - sell_vol
        total = buy_vol + sell_vol

        if total <= 0:
            return 0, 0.0

        if sell_vol == 0:
            imbalance = 1.0
        elif buy_vol == 0:
            imbalance = -1.0
        else:
            imbalance = max(-1.0, min(1.0, delta / float(total)))

        return delta, round(imbalance, 4)

    def detect_fair_value_gaps(
        self,
        highs: Sequence[float],
        lows: Sequence[float],
    ) -> tuple[bool, dict[str, Any]]:
        """Nhận diện khoảng trống giá mất cân bằng (Fair Value Gap - FVG) giữa cụm 3 nến liên tiếp."""
        if len(highs) < 3 or len(lows) < 3:
            return False, {}

        # FVG Tăng giá (Bullish FVG): Đáy nến 3 nằm cao hơn hoàn toàn đỉnh nến 1
        if lows[-1] > highs[-3]:
            return True, {
                "type": "BULLISH_FVG",
                "top": round(lows[-1], 2),
                "bottom": round(highs[-3], 2),
                "size": round(lows[-1] - highs[-3], 2),
            }

        # FVG Giảm giá (Bearish FVG): Đỉnh nến 3 nằm thấp hơn hoàn toàn đáy nến 1
        if highs[-1] < lows[-3]:
            return True, {
                "type": "BEARISH_FVG",
                "top": round(lows[-3], 2),
                "bottom": round(highs[-1], 2),
                "size": round(lows[-3] - highs[-1], 2),
            }

        return False, {}

    def detect_liquidity_sweeps(
        self,
        highs: Sequence[float],
        lows: Sequence[float],
        closes: Sequence[float],
        window: int = 20,
    ) -> dict[str, Any]:
        """Phát hiện bẫy quét thanh khoản đỉnh/đáy kèm nến rút râu đảo chiều."""
        n = len(closes)
        if n < 5:
            return {"bearish_sweep": False, "bullish_sweep": False}

        lookback = min(window, n - 1)
        prev_highs = highs[-(lookback + 1) : -1]
        prev_lows = lows[-(lookback + 1) : -1]

        if not prev_highs or not prev_lows:
            return {"bearish_sweep": False, "bullish_sweep": False}

        swing_high = max(prev_highs)
        swing_low = min(prev_lows)

        curr_high = highs[-1]
        curr_low = lows[-1]
        curr_close = closes[-1]

        # Quét đỉnh (Bearish sweep): High vượt qua đỉnh cũ nhưng Close quay đầu đóng cửa bên dưới
        bearish_sweep = curr_high > swing_high > curr_close

        # Quét đáy (Bullish sweep): Low chọc thủng đáy cũ nhưng Close hồi phục đóng cửa bên trên
        bullish_sweep = curr_low < swing_low < curr_close

        return {
            "bearish_sweep": bool(bearish_sweep),
            "bullish_sweep": bool(bullish_sweep),
            "swing_high": round(swing_high, 2),
            "swing_low": round(swing_low, 2),
        }

    def compute_composite_score(
        self,
        rsi: float | None,
        macd_hist: float,
        vwap_diff_pct: float,
        imbalance: float,
        fvg_detected: bool,
        fvg_type: str | None,
        sweeps: dict[str, Any],
        regime: str = "RANGING",
        percent_b: float | None = None,
        roc: float | None = None,
    ) -> float:
        """Tổng hợp điểm số của Engine 1 trong dải [-1.0, +1.0].

        Tỷ trọng thành phần (điều chỉnh theo chế độ thị trường):
        - Cấu phần Kỹ thuật (50%): Xu hướng + RSI + MACD + Vị thế tương đối so với VWAP
        - Cấu phần Dòng lệnh (30%): Mất cân bằng lệnh (Order Imbalance)
        - Cấu phần Hành động giá (20%): FVG + Quét thanh khoản (Liquidity Sweeps)

        Regime-aware:
        - "TRENDING" : Tăng trọng MACD (bám sát xu hướng), giảm RSI reversion
        - "RANGING"  : Tăng trọng RSI (mean-reversion hiệu quả khi sideway)
        - "VOLATILE" : Tăng trọng VWAP/BB (định giá tương đối trong biến động cao)
        """
        # 1. Cấu phần Kỹ thuật (50%)
        tech_score = 0.0

        # Trọng số con theo regime (tổng = 1.0 trong cấu phần kỹ thuật)
        regime_factors: dict[str, dict[str, float]] = {
            "TRENDING": {"macd": 0.5, "rsi": 0.2, "vwap": 0.2, "bb": 0.1},
            "RANGING": {"macd": 0.2, "rsi": 0.4, "vwap": 0.2, "bb": 0.2},
            "VOLATILE": {"macd": 0.2, "rsi": 0.2, "vwap": 0.3, "bb": 0.3},
        }
        factors = regime_factors.get(regime, regime_factors["RANGING"])

        # RSI smoothed (sigmoid, liên tục — không còn cliff tại 30/70)
        if rsi is not None:
            tech_score += factors["rsi"] * _sigmoid_rsi(rsi)

        # MACD histogram với scaling thích ứng theo biến động giá gần đây
        if macd_hist != 0.0:
            macd_scale = 0.4
            tech_score += (
                factors["macd"]
                * math.copysign(min(abs(macd_hist), macd_scale), macd_hist)
                / macd_scale
                * (1.0 if abs(macd_hist) >= macd_scale else abs(macd_hist) / macd_scale)
            )

        # VWAP position
        if vwap_diff_pct != 0.0:
            tech_score += factors["vwap"] * max(-1.0, min(1.0, vwap_diff_pct * 10.0))

        # Bollinger %B: > 0.8 → quá mua, < 0.2 → quá bán (mean-reversion)
        if percent_b is not None:
            bb_signal = 0.5 - percent_b
            tech_score += factors["bb"] * max(-1.0, min(1.0, bb_signal))
        elif rsi is None and macd_hist == 0.0:
            tech_score += 0.0

        # ROC momentum bonus (ngoài 50% cấu phần kỹ thuật, scale nhỏ)
        if roc is not None:
            tech_score += 0.10 * max(-1.0, min(1.0, roc))

        tech_score = max(-1.0, min(1.0, tech_score))

        # 2. Cấu phần Dòng lệnh (30%)
        orderflow_score = max(-1.0, min(1.0, imbalance))

        # 3. Cấu phần Hành động giá (20%)
        pa_score = 0.0
        if fvg_detected and fvg_type:
            pa_score += 0.5 if fvg_type == "BULLISH_FVG" else -0.5

        if sweeps.get("bullish_sweep"):
            pa_score += 0.5
        if sweeps.get("bearish_sweep"):
            pa_score -= 0.5

        pa_score = max(-1.0, min(1.0, pa_score))

        composite = 0.50 * tech_score + 0.30 * orderflow_score + 0.20 * pa_score
        return round(max(-1.0, min(1.0, composite)), 4)

    def analyze(
        self,
        symbol: str = "VN30F1M",
        highs: Sequence[float] | None = None,
        lows: Sequence[float] | None = None,
        closes: Sequence[float] | None = None,
        volumes: Sequence[float] | None = None,
        df_ticks: pd.DataFrame | Sequence[Any] | None = None,
        as_of: datetime | None = None,
    ) -> TechnicalEngineResponse:
        """Thực thi phân tích kỹ thuật và trả về kết quả TechnicalEngineResponse."""
        now = as_of or datetime.now(VN_TZ)

        # Tự động nạp dữ liệu OHLCV từ DB nếu tham số chưa được truyền vào
        if (closes is None or not closes) and self.session is not None:
            db_bars = self.session.exec(
                select(StockOHLCVDaily)
                .where(StockOHLCVDaily.symbol == symbol)
                .order_by(col(StockOHLCVDaily.trading_date).desc())
                .limit(60)
            ).all()
            if db_bars:
                db_bars = list(reversed(db_bars))
                highs = [b.high for b in db_bars]
                lows = [b.low for b in db_bars]
                closes = [b.close for b in db_bars]
                volumes = [float(b.volume) for b in db_bars]

        if not closes or not highs or not lows or len(closes) == 0:
            # Dữ liệu rỗng: trả về trạng thái trung tính mặc định
            return TechnicalEngineResponse(
                symbol=symbol,
                as_of=now,
                score=0.0,
                rsi=None,
                macd={"dif": 0.0, "dea": 0.0, "hist": 0.0},
                vwap=None,
                order_imbalance=0.0,
                volume_delta=0,
                camarilla_levels={},
                fvg_detected=False,
                fvg_details={},
                liquidity_sweeps={},
            )

        vols = volumes if volumes else [1.0] * len(closes)
        rsi = compute_rsi(closes, period=14)
        macd = compute_macd(closes, fast=12, slow=26, signal=9)
        bb = compute_bollinger_bands(closes, period=20)
        _atr = compute_atr(highs, lows, closes, period=14)
        if highs and lows and len(highs) == len(closes) and len(lows) == len(closes):
            typical_prices = [
                (h + low_p + c) / 3.0
                for h, low_p, c in zip(highs, lows, closes, strict=True)
            ]
            vwap = compute_vwap(typical_prices, vols)
        else:
            vwap = compute_vwap(closes, vols)
        camarilla = compute_camarilla_pivots(highs[-1], lows[-1], closes[-1])

        delta, imbalance = self.compute_orderflow_metrics(df_ticks)
        fvg_detected, fvg_details = self.detect_fair_value_gaps(highs, lows)
        sweeps = self.detect_liquidity_sweeps(highs, lows, closes)

        vwap_diff_pct = 0.0
        if vwap is not None and vwap > 0:
            vwap_diff_pct = (closes[-1] - vwap) / vwap

        # Tự động phát hiện chế độ thị trường (ADX-inspired)
        regime = detect_market_regime(closes, highs=highs, lows=lows)

        # Rate of Change momentum
        roc = compute_roc(closes, period=10)

        # Bollinger %B (đã tính trong bb)
        percent_b = bb.get("percent_b")

        score = self.compute_composite_score(
            rsi=rsi,
            macd_hist=macd.get("hist", 0.0),
            vwap_diff_pct=vwap_diff_pct,
            imbalance=imbalance,
            fvg_detected=fvg_detected,
            fvg_type=fvg_details.get("type"),
            sweeps=sweeps,
            regime=regime,
            percent_b=percent_b,
            roc=roc,
        )

        return TechnicalEngineResponse(
            symbol=symbol,
            as_of=now,
            score=score,
            rsi=rsi,
            macd=macd,
            vwap=vwap,
            order_imbalance=imbalance,
            volume_delta=delta,
            camarilla_levels=camarilla,
            fvg_detected=fvg_detected,
            fvg_details=fvg_details,
            liquidity_sweeps=sweeps,
            regime=regime,
            roc=roc,
        )
