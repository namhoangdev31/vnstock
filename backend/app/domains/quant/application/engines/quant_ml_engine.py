"""Engine 3: Động cơ Định lượng, Thống kê & Học máy (QuantMLEngine).

Tập trung vào chênh lệch Basis giữa Hợp đồng tương lai VN30F1M và Chỉ số cơ sở VN30,
mô hình hóa độ biến động (Historical Volatility & Parkinson Volatility), phân loại
xác suất chuyển phiên và mô phỏng Monte Carlo đường đi giá T+1 giới hạn trong biên độ trần/sàn ±7%.
"""

import math
from collections.abc import Sequence
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from sqlmodel import Session

from app.core.enums import SessionPhase
from app.core.models_base import VN_TZ
from app.domains.quant.application.schemas import QuantMLEngineResponse
from app.domains.quant.domain.indicators import (
    compute_adf_stationarity,
    compute_basis_zscore_scipy,
    compute_garch_volatility,
    compute_historical_volatility_v2,
    compute_linear_regression_slope,
    compute_parkinson_volatility,
    predict_atc_lgbm,
    simulate_monte_carlo_scipy,
    simulate_t1_qmc_sobol,
)

_VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")


class QuantMLEngine:
    """Động cơ Phân tích Định lượng Thống kê, Độ biến động và Chênh lệch Basis."""

    def __init__(self, session: Session | None = None) -> None:
        self.session = session

    def classify_session_phase(self, dt: datetime | None = None) -> str:
        """Phân loại trạng thái phiên giao dịch theo đồng hồ thị trường chứng khoán Việt Nam.

        Lịch trình theo giờ Việt Nam (Asia/Ho_Chi_Minh):
        - 08:30 - 08:45: PRE_ATO (Chuẩn bị trước phiên ATO)
        - 08:45 - 09:00: ATO (Thị trường phái sinh mở cửa sớm 15 phút trước cơ sở)
        - 09:00 - 11:30: MORNING_CONTINUOUS (Khớp lệnh liên tục buổi sáng)
        - 11:30 - 13:00: MIDDAY_INTERMISSION (Nghỉ trưa)
        - 13:00 - 14:15: AFTERNOON_CONTINUOUS (Khớp lệnh liên tục buổi chiều)
        - 14:15 - 14:30: PRE_ATC (Chuẩn bị vào phiên khớp lệnh định kỳ đóng cửa)
        - 14:30 - 14:45: ATC (Đợt khớp lệnh định kỳ đóng cửa)
        - 14:45 - 08:30: POST_MARKET (Sau giờ giao dịch / Chạy mô phỏng qua đêm 24/7)
        """
        now_utc = dt or datetime.now(VN_TZ)
        vn_time = now_utc.astimezone(_VN_TZ)
        time_minutes = vn_time.hour * 60 + vn_time.minute

        # 08:30 = 510, 08:45 = 525, 09:00 = 540, 11:30 = 690, 13:00 = 780
        # 14:15 = 855, 14:30 = 870, 14:45 = 885
        if 510 <= time_minutes < 525:
            return SessionPhase.PRE_ATO
        if 525 <= time_minutes < 540:
            return SessionPhase.ATO
        if 540 <= time_minutes < 690:
            return SessionPhase.MORNING_CONTINUOUS
        if 690 <= time_minutes < 780:
            return SessionPhase.MIDDAY_INTERMISSION
        if 780 <= time_minutes < 855:
            return SessionPhase.AFTERNOON_CONTINUOUS
        if 855 <= time_minutes < 870:
            return SessionPhase.PRE_ATC
        if 870 <= time_minutes < 885:
            return SessionPhase.ATC
        return SessionPhase.POST_MARKET

    def compute_basis_zscore(
        self,
        futures_price: float,
        spot_index_price: float,
        historical_basis: Sequence[float] | None = None,
        highs: Sequence[float] | None = None,
        lows: Sequence[float] | None = None,
    ) -> tuple[float, float]:
        """Tính chênh lệch Basis và Z-score lăn (nay dùng t-distribution CI).

        Proxy → compute_basis_zscore_scipy() (Indicator Phần 3):
        - t-distribution CI 95% thay Normal assumption
        - Trả thêm mean_reverting flag và p_value (lưu vào ForecastJournal)

        Fallback ATR estimate giữ nguyên khi không có historical_basis.
        """
        if not historical_basis or len(historical_basis) < 2:
            if highs and lows and len(highs) >= 3 and len(lows) >= 3:
                recent_ranges = [
                    h - lo for h, lo in zip(highs[-5:], lows[-5:], strict=False)
                ]
                if recent_ranges:
                    atr_est = sum(recent_ranges) / len(recent_ranges)
                    adaptive_std = max(2.0, atr_est * 1.5)
                    basis = futures_price - spot_index_price
                    z = basis / adaptive_std
                    return round(basis, 2), round(max(-3.0, min(3.0, z)), 4)

        result = compute_basis_zscore_scipy(
            futures_price, spot_index_price, historical_basis
        )
        return float(result["basis"]), float(result["z_score"])

    def compute_volatilities(
        self,
        highs: Sequence[float],
        lows: Sequence[float],
        closes: Sequence[float],
    ) -> tuple[float, float]:
        """Trả về bộ đôi độ biến động (Historical Volatility v2, Parkinson Volatility).

        HV v2 dùng numpy vectorized + trả thêm kurtosis/skewness (duyên với tail risk).
        """
        hv_result = compute_historical_volatility_v2(closes)
        hv = hv_result["hv"]
        pv = compute_parkinson_volatility(highs, lows)
        return hv, pv

    def simulate_monte_carlo_t1(
        self,
        current_price: float,
        volatility: float,
        n_simulations: int = 1000,
        seed: int | None = 42,
        n_steps: int = 8,
    ) -> dict[str, float]:
        """Proxy → simulate_monte_carlo_scipy() — vectorized, ~50x nhanh hơn Python loop.

        Thêm vào response: var_95 (Value at Risk 95%) và cvar_95 (Expected Shortfall).
        Giữ signature gốc backward-compatible (seed có thể None, default = 42).
        """
        return simulate_monte_carlo_scipy(
            current_price=current_price,
            volatility=volatility,
            n_simulations=n_simulations,
            seed=seed if seed is not None else 42,
            n_steps=n_steps,
        )

    def simulate_t1_qmc_sobol(
        self,
        current_price: float,
        conditional_vol: float,
        drift: float = 0.0,
        degrees_of_freedom: float = 6.0,
        n_paths: int = 1024,
        price_limit_pct: float = 0.07,
    ) -> dict[str, Any]:
        return simulate_t1_qmc_sobol(
            current_price=current_price,
            conditional_vol=conditional_vol,
            drift=drift,
            degrees_of_freedom=degrees_of_freedom,
            n_paths=n_paths,
            price_limit_pct=price_limit_pct,
        )

    def predict_ato_gap(
        self,
        current_price: float,
        prev_close: float,
        overnight_basis: float = 0.0,
        historical_gaps: Sequence[float] | None = None,
    ) -> dict[str, Any]:
        """Phân loại độ lệch ATO Opening Gap lúc 08:45 dựa trên phân phối lịch sử (TRD §2.3.3).

        - Bullish Gap: Gap tăng vượt ngưỡng phân phối (nghiêng về phe Long)
        - Bearish Gap: Gap giảm vượt ngưỡng phân phối (nghiêng về phe Short)
        - Normal Gap: Biên độ thông thường
        """
        if prev_close <= 0.0:
            return {
                "gap_value": 0.0,
                "gap_pct": 0.0,
                "gap_type": "NORMAL_GAP",
                "direction_bias": "NEUTRAL",
                "transition_score": 0.0,
            }

        gap_value = current_price - prev_close
        gap_pct = (gap_value / prev_close) * 100.0

        if historical_gaps and len(historical_gaps) >= 10:
            mean_gap = sum(historical_gaps) / len(historical_gaps)
            var_gap = sum((g - mean_gap) ** 2 for g in historical_gaps) / len(
                historical_gaps
            )
            std_gap = math.sqrt(var_gap) if var_gap > 0 else 0.5
            z_gap = (gap_value - mean_gap) / (std_gap if std_gap > 0 else 1.0)
            if z_gap > 1.0:
                gap_type = "BULLISH_GAP"
                direction_bias = "BULLISH"
            elif z_gap < -1.0:
                gap_type = "BEARISH_GAP"
                direction_bias = "BEARISH"
            else:
                gap_type = "NORMAL_GAP"
                direction_bias = "NEUTRAL"
        else:
            adaptive_threshold = 0.30
            if gap_pct > adaptive_threshold:
                gap_type = "BULLISH_GAP"
                direction_bias = "BULLISH"
            elif gap_pct < -adaptive_threshold:
                gap_type = "BEARISH_GAP"
                direction_bias = "BEARISH"
            else:
                gap_type = "NORMAL_GAP"
                direction_bias = "NEUTRAL"

        combined_signal = (gap_pct / 1.0) + (overnight_basis / 5.0)
        transition_score = round(max(-1.0, min(1.0, combined_signal / 2.0)), 4)

        return {
            "gap_value": round(gap_value, 2),
            "gap_pct": round(gap_pct, 4),
            "gap_type": gap_type,
            "direction_bias": direction_bias,
            "transition_score": transition_score,
        }

    def predict_atc_transition(
        self,
        current_price: float,
        basis_zscore: float,
        order_imbalance: float = 0.0,
        fii_net_flow: float = 0.0,
        vwap_diff: float = 0.0,
        volatility: float = 0.15,
    ) -> dict[str, Any]:
        """Dự phóng mức dịch chuyển giá khớp cân bằng trong phiên ATC bằng tương tác phi tuyến."""
        return predict_atc_lgbm(
            current_price=current_price,
            basis_zscore=basis_zscore,
            order_imbalance=order_imbalance,
            fii_net_flow=fii_net_flow,
            vwap_diff=vwap_diff,
            volatility=volatility,
        )

    def compute_composite_score(
        self,
        basis_zscore: float,
        transition_score: float = 0.0,
        lr_trend_score: float | None = None,
    ) -> float:
        """Tổng hợp điểm số của Engine 3 trong dải [-1.0, +1.0].

        Logic Hồi quy Trung bình từ Basis:
        - Nếu Z > 0 (phái sinh đắt), điểm âm (Short bias)
        - Nếu Z < 0 (phái sinh rẻ), điểm dương (Long bias)

        Khi có lr_trend_score (linear regression slope 10 ngày):
        - 0.40 * mean_reversion_score + 0.40 * transition_score + 0.20 * lr_trend_score
        Khi không: fallback về 0.50/0.50 (backward-compatible)
        """
        mean_reversion_score = -1.0 * (basis_zscore / 2.5)
        mean_reversion_score = max(-1.0, min(1.0, mean_reversion_score))

        if lr_trend_score is not None:
            trend_signal = max(-1.0, min(1.0, lr_trend_score))
            score = (
                0.40 * mean_reversion_score
                + 0.40 * transition_score
                + 0.20 * trend_signal
            )
        else:
            score = 0.50 * mean_reversion_score + 0.50 * transition_score
        return round(max(-1.0, min(1.0, score)), 4)

    def analyze(
        self,
        symbol: str = "VN30F1M",
        futures_price: float = 1300.0,
        spot_index_price: float = 1300.0,
        historical_basis: Sequence[float] | None = None,
        highs: Sequence[float] | None = None,
        lows: Sequence[float] | None = None,
        closes: Sequence[float] | None = None,
        as_of: datetime | None = None,
    ) -> QuantMLEngineResponse:
        """Thực thi toàn bộ tính toán định lượng của Engine 3 và trả về QuantMLEngineResponse."""
        now = as_of or datetime.now(VN_TZ)
        phase = self.classify_session_phase(now)

        basis_val, basis_z = self.compute_basis_zscore(
            futures_price=futures_price,
            spot_index_price=spot_index_price,
            historical_basis=historical_basis,
            highs=highs,
            lows=lows,
        )

        hv = 0.15
        pv = 0.15
        mc_volatility = 0.15
        if closes and highs and lows:
            hv, pv = self.compute_volatilities(highs, lows, closes)
            if len(closes) >= 2:
                returns = [
                    math.log(current / previous)
                    for previous, current in zip(closes, closes[1:], strict=False)
                    if previous > 0.0 and current > 0.0
                ]
                garch_result = compute_garch_volatility(returns)
                mc_volatility = float(garch_result["volatility"])
            else:
                mc_volatility = hv

        qmc_targets = self.simulate_t1_qmc_sobol(
            current_price=futures_price,
            conditional_vol=mc_volatility,
        )

        if phase in (SessionPhase.PRE_ATO, SessionPhase.ATO):
            prev_c = closes[-1] if closes else futures_price
            trans_pred = self.predict_ato_gap(
                current_price=futures_price,
                prev_close=prev_c,
                overnight_basis=basis_val,
            )
        else:
            trans_pred = self.predict_atc_transition(
                current_price=futures_price,
                basis_zscore=basis_z,
                volatility=mc_volatility,
            )

        trans_score = float(trans_pred.get("transition_score", 0.0))

        lr_trend_score: float | None = None
        if closes and len(closes) >= 5:
            lr_trend_score = compute_linear_regression_slope(list(closes), window=10)

        adf_result = (
            compute_adf_stationarity(historical_basis)
            if historical_basis
            else {
                "adf_statistic": None,
                "p_value": 1.0,
                "stationary": False,
                "error": "no_basis_history",
            }
        )
        normalized_basis_z = 0.0 if not adf_result.get("stationary") else basis_z

        score = self.compute_composite_score(
            normalized_basis_z, trans_score, lr_trend_score
        )

        return QuantMLEngineResponse(
            symbol=symbol,
            as_of=now,
            score=score,
            basis_value=basis_val,
            basis_zscore=basis_z,
            historical_vol=hv,
            parkinson_vol=pv,
            session_phase=phase,
            monte_carlo_targets=qmc_targets,
            qmc_targets=qmc_targets,
            lr_trend_score=lr_trend_score if lr_trend_score is not None else 0.0,
            mc_max_drawdown_p50=float(qmc_targets.get("mc_max_drawdown_p50", 0.0)),
            basis_stationarity=adf_result,
        )
