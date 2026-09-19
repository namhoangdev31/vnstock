"""Engine 3: Động cơ Định lượng, Thống kê & Học máy (QuantMLEngine).

Tập trung vào chênh lệch Basis giữa Hợp đồng tương lai VN30F1M và Chỉ số cơ sở VN30,
mô hình hóa độ biến động (Historical Volatility & Parkinson Volatility), phân loại
xác suất chuyển phiên và mô phỏng Monte Carlo đường đi giá T+1 giới hạn trong biên độ trần/sàn ±7%.
"""

import math
import random
import statistics
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

from sqlmodel import Session

from app.models.enums import SessionPhase
from app.models.models_quant import QuantMLEngineResponse
from app.services.quant.indicators import (
    compute_historical_volatility,
    compute_parkinson_volatility,
    compute_zscore,
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
        now_utc = dt or datetime.now(UTC)
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
    ) -> tuple[float, float]:
        """Tính chênh lệch Basis (Phái sinh - Cơ sở) và Z-score lăn.

        Nguyên lý Hồi quy Trung bình (Mean-Reversion):
        - Z_basis > +2.0: Phái sinh đắt hơn bất thường -> Thiên hướng Bán (Short Bias)
        - Z_basis < -2.0: Phái sinh chiết khấu quá sâu -> Thiên hướng Mua (Long Bias)
        """
        basis = futures_price - spot_index_price
        if not historical_basis or len(historical_basis) < 2:
            # Khi thiếu lịch sử, giả định trung bình = 0.0 và độ lệch chuẩn điển hình = 5.0 điểm
            z = basis / 5.0
            return round(basis, 2), round(max(-3.0, min(3.0, z)), 4)

        mean_val = statistics.fmean(historical_basis)
        std_val = statistics.pstdev(historical_basis)
        z = compute_zscore(basis, mean_val, std_val)
        return round(basis, 2), round(max(-5.0, min(5.0, z)), 4)

    def compute_volatilities(
        self,
        highs: Sequence[float],
        lows: Sequence[float],
        closes: Sequence[float],
    ) -> tuple[float, float]:
        """Trả về bộ đôi độ biến động (Historical Volatility, Parkinson Volatility)."""
        hv = compute_historical_volatility(closes)
        pv = compute_parkinson_volatility(highs, lows)
        return hv, pv

    def simulate_monte_carlo_t1(
        self,
        current_price: float,
        volatility: float,
        n_simulations: int = 1000,
        seed: int | None = 42,
    ) -> dict[str, float]:
        """Thực hiện mô phỏng Monte Carlo cho đường đi giá phiên tiếp theo (T+1).

        Áp dụng mô hình Chuyển động Brown Hình học (GBM) kèm ràng buộc biên độ trần/sàn Việt Nam:
        Giới hạn biến động trong ngày là ±7.0% tính từ giá tham chiếu.
        Trả về {"p05": phân vị 5% (đáy), "p50": trung vị, "p95": phân vị 95% (đỉnh)}.
        """
        if current_price <= 0.0:
            return {"p05": 0.0, "p50": 0.0, "p95": 0.0}

        rng = random.Random(seed)
        effective_vol = max(0.05, min(0.60, volatility if volatility > 0 else 0.20))

        # Khung thời gian 1 ngày (1/252 ngày giao dịch trong năm)
        dt = 1.0 / 252.0
        drift = 0.0  # Giả định xu hướng trôi trung tính cho mô phỏng
        mu_step = (drift - 0.5 * (effective_vol**2)) * dt
        vol_step = effective_vol * math.sqrt(dt)

        # Biên độ trần/sàn ±7% của HOSE và Hợp đồng tương lai VN30F1M
        floor_limit = round(current_price * 0.93, 2)
        ceiling_limit = round(current_price * 1.07, 2)

        simulated_prices: list[float] = []
        for _ in range(n_simulations):
            z = rng.gauss(0.0, 1.0)
            p = current_price * math.exp(mu_step + vol_step * z)
            bounded_p = max(floor_limit, min(ceiling_limit, p))
            simulated_prices.append(bounded_p)

        simulated_prices.sort()

        idx_05 = int(0.05 * n_simulations)
        idx_50 = int(0.50 * n_simulations)
        idx_95 = int(0.95 * n_simulations)

        return {
            "p05": round(simulated_prices[idx_05], 2),
            "p50": round(simulated_prices[idx_50], 2),
            "p95": round(simulated_prices[idx_95], 2),
        }

    def predict_atc_transition(
        self,
        current_price: float,
        basis_zscore: float,
        order_imbalance: float = 0.0,
    ) -> dict[str, Any]:
        """Dự phóng mức dịch chuyển giá khớp cân bằng trong phiên khớp lệnh định kỳ đóng cửa ATC."""
        # Hội tụ Basis: Trong phiên ATC, basis phái sinh có xu hướng co hẹp về chỉ số cơ sở
        # Nếu basis dương cao, giá có áp lực kéo xuống để thu hẹp khoảng cách
        convergence_delta = -basis_zscore * 0.5
        imbalance_impact = order_imbalance * 1.5

        expected_delta = convergence_delta + imbalance_impact
        projected_close = round(current_price + expected_delta, 2)

        direction_bias = (
            "BULLISH"
            if expected_delta > 0.3
            else "BEARISH"
            if expected_delta < -0.3
            else "NEUTRAL"
        )

        return {
            "projected_price": projected_close,
            "expected_delta": round(expected_delta, 2),
            "direction_bias": direction_bias,
            "transition_score": round(max(-1.0, min(1.0, expected_delta / 3.0)), 4),
        }

    def compute_composite_score(
        self,
        basis_zscore: float,
        transition_score: float = 0.0,
    ) -> float:
        """Tổng hợp điểm số của Engine 3 trong dải [-1.0, +1.0].

        Logic Hồi quy Trung bình từ Basis:
        - Nếu Z > 0 (phái sinh đắt), điểm âm (Short bias)
        - Nếu Z < 0 (phái sinh rẻ), điểm dương (Long bias)
        """
        # Đảo ngược dấu Z-Score theo lực kéo hồi quy trung bình
        mean_reversion_score = -1.0 * (basis_zscore / 2.5)
        mean_reversion_score = max(-1.0, min(1.0, mean_reversion_score))

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
        now = as_of or datetime.now(UTC)
        phase = self.classify_session_phase(now)

        basis_val, basis_z = self.compute_basis_zscore(
            futures_price=futures_price,
            spot_index_price=spot_index_price,
            historical_basis=historical_basis,
        )

        hv = 0.15
        pv = 0.15
        if closes and highs and lows:
            hv, pv = self.compute_volatilities(highs, lows, closes)

        mc_targets = self.simulate_monte_carlo_t1(
            current_price=futures_price,
            volatility=max(hv, pv),
        )

        atc_pred = self.predict_atc_transition(
            current_price=futures_price,
            basis_zscore=basis_z,
        )

        trans_score = float(atc_pred.get("transition_score", 0.0))
        score = self.compute_composite_score(basis_z, trans_score)

        return QuantMLEngineResponse(
            symbol=symbol,
            as_of=now,
            score=score,
            basis_value=basis_val,
            basis_zscore=basis_z,
            historical_vol=hv,
            parkinson_vol=pv,
            session_phase=phase,
            monte_carlo_targets=mc_targets,
        )
