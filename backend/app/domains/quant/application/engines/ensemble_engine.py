"""Động cơ Hợp nhất Đa tầng (Ensemble Decision Engine) & Hệ thống Tự động Ghi Sổ Nhật ký.

Điều phối kết quả đầu ra từ 3 Engine (Kỹ thuật, Thanh khoản & T+2, Định lượng ML)
kết hợp điều chỉnh trọng số động theo chu kỳ phiên (Time-of-Day Blending), giải quyết xung đột tín hiệu,
tính toán khoảng quản trị rủi ro Stop Loss / Take Profit động (đảm bảo R:R >= 1:2.0)
và bắt buộc tự động ghi nhận vào sổ nhật ký kiểm toán ForecastJournal (tuân thủ RULE 3).

Nâng cấp ML:
- Engine Disagreement Metric: std(E1,E2,E3) đo mức đồng thuận giữa các engines
- Adaptive Confidence: confidence phản ánh disagreement thay vì chỉ abs(score)
- Adaptive Conflict Threshold: ngưỡng xung đột thích ứng theo mức bất đồng
- Regime-Aware Weight Adjustment: điều chỉnh trọng số theo chế độ thị trường E1
"""

import statistics
import uuid
from datetime import datetime
from typing import Any

from sqlmodel import Session

from app.core.enums import (
    ForecastDirection,
    ForecastStatus,
    SessionPhase,
)
from app.core.models_base import VN_TZ
from app.domains.quant.application.engines.flow_engine import FlowLiquidityEngine
from app.domains.quant.application.engines.quant_ml_engine import QuantMLEngine
from app.domains.quant.application.engines.technical_engine import TechnicalEngine
from app.domains.quant.application.schemas import (
    EnsembleSignalRequest,
    EnsembleSignalResponse,
    EnsembleWeightsResponse,
)
from app.domains.quant.domain.indicators import compute_atr
from app.domains.quant.domain.models import ForecastJournal

# Bảng trọng số động theo chu kỳ phiên giao dịch chuẩn quy định tại TRD Phase 2
DEFAULT_SCHEDULE: dict[str, dict[str, float]] = {
    SessionPhase.PRE_ATO: {"w1": 0.20, "w2": 0.30, "w3": 0.50},
    SessionPhase.ATO: {"w1": 0.40, "w2": 0.20, "w3": 0.40},
    SessionPhase.MORNING_CONTINUOUS: {"w1": 0.55, "w2": 0.25, "w3": 0.20},
    SessionPhase.MIDDAY_INTERMISSION: {"w1": 0.30, "w2": 0.40, "w3": 0.30},
    SessionPhase.AFTERNOON_CONTINUOUS: {"w1": 0.50, "w2": 0.30, "w3": 0.20},
    SessionPhase.PRE_ATC: {"w1": 0.25, "w2": 0.25, "w3": 0.50},
    SessionPhase.ATC: {"w1": 0.15, "w2": 0.20, "w3": 0.65},
    SessionPhase.POST_MARKET: {"w1": 0.20, "w2": 0.35, "w3": 0.45},
}


class EnsembleEngine:
    """Động cơ Hợp nhất Tín hiệu Quyết định và Quản trị Rủi ro."""

    MODEL_VERSION = "v2.0.0"

    def __init__(self, session: Session | None = None) -> None:
        self.session = session
        self.engine1 = TechnicalEngine(session)
        self.engine2 = FlowLiquidityEngine(session)
        self.engine3 = QuantMLEngine(session)
        self._custom_weights_override: dict[str, float] | None = None

    def set_custom_weights_override(self, w1: float, w2: float, w3: float) -> None:
        """Thiết lập ghi đè trọng số tùy chỉnh thủ công trên toàn hệ thống (Dành cho Admin)."""
        norm_w = self.normalize_weights({"w1": w1, "w2": w2, "w3": w3})
        self._custom_weights_override = norm_w

    def normalize_weights(self, weights: dict[str, float]) -> dict[str, float]:
        """Chuẩn hóa trọng số bất kỳ đảm bảo tổng w1 + w2 + w3 = 1.0."""
        w1 = max(0.0, float(weights.get("w1", 0.0)))
        w2 = max(0.0, float(weights.get("w2", 0.0)))
        w3 = max(0.0, float(weights.get("w3", 0.0)))
        total = w1 + w2 + w3

        if total <= 1e-9:
            return {"w1": 0.34, "w2": 0.33, "w3": 0.33}

        return {
            "w1": round(w1 / total, 4),
            "w2": round(w2 / total, 4),
            "w3": round(w3 / total, 4),
        }

    def get_dynamic_weights(
        self,
        dt: datetime | None = None,
        custom_weights: dict[str, float] | None = None,
        regime: str = "RANGING",
    ) -> tuple[str, dict[str, float]]:
        """Lấy bộ trọng số tương ứng theo thời điểm giao dịch thực tế và chế độ thị trường.

        Chuẩn hóa tổng = 1.0. Regime-aware adjustment:
        - "VOLATILE": tăng w3 (basis/quant) +20%, giảm w1 (technical) -20% (ngoài ATC/PRE_ATC)
        - "TRENDING" : tăng w1 (technical momentum đáng tin) +10%, giảm w2 -10%
        - "RANGING"  : giữ nguyên trọng số phase
        """
        now = dt or datetime.now(VN_TZ)
        phase = self.engine3.classify_session_phase(now)

        if custom_weights:
            return phase, self.normalize_weights(custom_weights)

        if self._custom_weights_override:
            return phase, self._custom_weights_override

        schedule_w = DEFAULT_SCHEDULE.get(phase, {"w1": 0.34, "w2": 0.33, "w3": 0.33})
        base_w = self.normalize_weights(schedule_w)

        if regime == "VOLATILE" and phase not in (
            SessionPhase.ATC,
            SessionPhase.PRE_ATC,
        ):
            w1 = base_w["w1"] * 0.80
            w2 = base_w["w2"]
            w3 = base_w["w3"] * 1.20
            return phase, self.normalize_weights({"w1": w1, "w2": w2, "w3": w3})
        if regime == "TRENDING" and phase not in (
            SessionPhase.ATC,
            SessionPhase.PRE_ATC,
        ):
            w1 = base_w["w1"] * 1.10
            w2 = base_w["w2"] * 0.90
            w3 = base_w["w3"]
            return phase, self.normalize_weights({"w1": w1, "w2": w2, "w3": w3})

        return phase, base_w

    def resolve_signal_conflicts(
        self,
        score_e1: float,
        score_e2: float,
        score_e3: float,
        weights: dict[str, float],
    ) -> tuple[float, float, bool, float]:
        """Hợp nhất điểm số và xử lý triệt tiêu xung đột tín hiệu.

        Trả về (điểm_cuối_cùng, độ_tin_cậy, có_xung_đột, disagreement).

        Adaptive Conflict: ngưỡng xung đột phụ thuộc vào mức bất đồng:
        - Disagreement = std(E1, E2, E3) — đo mức "chênh nhau" giữa 3 engines
        - Conflict threshold = max(0.35, 0.50 - 0.10 * disagreement)
        - Khi agreement cao (low disagreement): threshold cao → khó trigger conflict hơn
        - Khi agreement thấp (high disagreement): threshold thấp → dễ neutralize hơn

        Nếu Engine 1 (Kỹ thuật) và Engine 3 (Định lượng/Basis) mâu thuẫn đối nghịch mạnh
        (|E1| > threshold và |E3| > threshold trái dấu), tín hiệu tự động đưa về NEUTRAL.
        """
        w1 = weights["w1"]
        w2 = weights["w2"]
        w3 = weights["w3"]
        raw_score = w1 * score_e1 + w2 * score_e2 + w3 * score_e3

        scores = [score_e1, score_e2, score_e3]
        disagreement = round(statistics.pstdev(scores), 4) if len(scores) >= 2 else 0.0

        conflict_threshold = max(0.35, 0.50 - 0.10 * disagreement)

        conflict = False
        if (score_e1 > conflict_threshold and score_e3 < -conflict_threshold) or (
            score_e1 < -conflict_threshold and score_e3 > conflict_threshold
        ):
            conflict = True
            final_score = 0.0
            confidence = 0.50
        else:
            final_score = max(-1.0, min(1.0, raw_score))
            # Adaptive confidence: phản ánh mức đồng thuận giữa engines
            # Cũ: abs(score) + 0.20 (oversimplified)
            # Mới: penalty khi disagreement cao, reward khi agreement cao
            agreement_factor = max(0.0, 1.0 - 0.8 * disagreement)
            confidence = round(
                max(0.10, abs(final_score) * agreement_factor + 0.15),
                4,
            )

        return round(final_score, 4), confidence, conflict, disagreement

    def classify_direction(self, score: float) -> str:
        """Phân loại xu hướng: Score >= +0.35 -> LONG, Score <= -0.35 -> SHORT, còn lại NEUTRAL."""
        if score >= 0.35:
            return ForecastDirection.BULLISH  # Khớp với schema trả về hiển thị "LONG"
        if score <= -0.35:
            return ForecastDirection.BEARISH  # Khớp với schema trả về hiển thị "SHORT"
        return ForecastDirection.NEUTRAL

    def calculate_risk_brackets(
        self,
        entry_price: float,
        direction: str,
        atr: float | None,
        camarilla_levels: dict[str, float] | None = None,
    ) -> tuple[float | None, float | None]:
        """Tính mốc cắt lỗ (Stop Loss) và chốt lời (Take Profit) đảm bảo tỷ lệ Risk:Reward >= 1:2.0."""
        if (
            direction not in ("LONG", "BULLISH", "SHORT", "BEARISH")
            or entry_price <= 0.0
        ):
            return None, None

        effective_atr = max(2.0, atr if atr and atr > 0 else 5.0)
        c_levels = camarilla_levels or {}

        if direction in ("LONG", "BULLISH"):
            # Cắt lỗ: Entry - 1.5 * ATR hoặc hỗ trợ Camarilla S3
            s3 = c_levels.get("s3")
            atr_sl = entry_price - 1.5 * effective_atr
            stop_loss = max(
                entry_price * 0.93,
                min(atr_sl, s3 if s3 and s3 < entry_price else atr_sl),
            )

            # Chốt lời: Tối thiểu gấp đôi mức rủi ro (R:R >= 1:2.0)
            risk = entry_price - stop_loss
            reward = max(risk * 2.0, 3.0 * effective_atr)
            take_profit = min(entry_price * 1.07, entry_price + reward)
            return round(stop_loss, 2), round(take_profit, 2)

        else:  # SHORT / BEARISH
            # Cắt lỗ: Entry + 1.5 * ATR hoặc kháng cự Camarilla R3
            r3 = c_levels.get("r3")
            atr_sl = entry_price + 1.5 * effective_atr
            stop_loss = min(
                entry_price * 1.07,
                max(atr_sl, r3 if r3 and r3 > entry_price else atr_sl),
            )

            # Chốt lời: Tối thiểu gấp đôi mức rủi ro (R:R >= 1:2.0)
            risk = stop_loss - entry_price
            reward = max(risk * 2.0, 3.0 * effective_atr)
            take_profit = max(entry_price * 0.93, entry_price - reward)
            return round(stop_loss, 2), round(take_profit, 2)

    def log_forecast_to_journal(
        self,
        symbol: str,
        horizon: str,
        predicted_at: datetime,
        predicted_value: float | None,
        predicted_direction: str,
        predicted_score: float,
        engine_weights: dict[str, float],
        engine_scores: dict[str, float],
        parameter_snapshot: dict[str, Any],
    ) -> uuid.UUID:
        """Bắt buộc ghi nhận dự báo vào bảng sổ nhật ký ForecastJournal (Tuân thủ RULE 3)."""
        journal_id = uuid.uuid4()
        if self.session is not None:
            mapped_direction = (
                ForecastDirection.BULLISH
                if predicted_direction in ("LONG", ForecastDirection.BULLISH)
                else ForecastDirection.BEARISH
                if predicted_direction in ("SHORT", ForecastDirection.BEARISH)
                else ForecastDirection.NEUTRAL
            )
            entry = ForecastJournal(
                id=journal_id,
                symbol=symbol,
                horizon=horizon,
                predicted_at=predicted_at,
                predicted_value=predicted_value,
                predicted_direction=mapped_direction,
                engine_weights=engine_weights,
                model_version=self.MODEL_VERSION,
                parameter_snapshot={
                    **parameter_snapshot,
                    "engine_scores": engine_scores,
                    "predicted_score": predicted_score,
                },
                status=ForecastStatus.PENDING,
            )
            self.session.add(entry)
            self.session.commit()
            self.session.refresh(entry)
            return entry.id
        return journal_id

    def generate_signal(
        self,
        request: EnsembleSignalRequest,
        entry_price: float = 1300.0,
        spot_price: float = 1300.0,
        highs: list[float] | None = None,
        lows: list[float] | None = None,
        closes: list[float] | None = None,
        volumes: list[float] | None = None,
        df_ticks: Any = None,
        flows: Any = None,
        breadth: Any = None,
        as_of: datetime | None = None,
    ) -> EnsembleSignalResponse:
        """Kích hoạt 3 Engine, phối hợp trọng số động, tính SL/TP và lưu vết vào ForecastJournal."""
        now = as_of or datetime.now(VN_TZ)

        # 1. Chạy 3 Engine phân tích
        e1_res = self.engine1.analyze(
            symbol=request.symbol,
            highs=highs,
            lows=lows,
            closes=closes,
            volumes=volumes,
            df_ticks=df_ticks,
            as_of=now,
        )
        e2_res = self.engine2.analyze(
            flows=flows,
            breadth=breadth,
            as_of=now,
        )
        e3_res = self.engine3.analyze(
            symbol=request.symbol,
            futures_price=entry_price,
            spot_index_price=spot_price,
            highs=highs,
            lows=lows,
            closes=closes,
            as_of=now,
        )

        regime = e1_res.regime
        _phase, weights = self.get_dynamic_weights(
            now, custom_weights=request.custom_weights, regime=regime
        )
        final_score, confidence, conflict, disagreement = self.resolve_signal_conflicts(
            score_e1=e1_res.score,
            score_e2=e2_res.score,
            score_e3=e3_res.score,
            weights=weights,
        )

        # 3. Phân loại xu hướng dự báo
        raw_direction = self.classify_direction(final_score)
        out_direction = (
            "LONG"
            if raw_direction == ForecastDirection.BULLISH
            else "SHORT"
            if raw_direction == ForecastDirection.BEARISH
            else "NEUTRAL"
        )

        # 4. Tính toán khoảng rủi ro SL / TP động
        atr_val = None
        if highs and lows and closes and len(closes) >= 15:
            atr_val = compute_atr(highs, lows, closes)

        stop_loss, take_profit = self.calculate_risk_brackets(
            entry_price=entry_price,
            direction=out_direction,
            atr=atr_val,
            camarilla_levels=e1_res.camarilla_levels,
        )

        engine_scores = {
            "engine1": e1_res.score,
            "engine2": e2_res.score,
            "engine3": e3_res.score,
        }

        # 5. Lưu vết kiểm toán bắt buộc (RULE 3)
        journal_id = self.log_forecast_to_journal(
            symbol=request.symbol,
            horizon=request.horizon,
            predicted_at=now,
            predicted_value=entry_price,
            predicted_direction=out_direction,
            predicted_score=final_score,
            engine_weights=weights,
            engine_scores=engine_scores,
            parameter_snapshot={
                "confidence": confidence,
                "conflict_detected": conflict,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "engine_disagreement": disagreement,
                "regime": regime,
            },
        )

        return EnsembleSignalResponse(
            journal_id=journal_id,
            symbol=request.symbol,
            horizon=request.horizon,
            predicted_at=now,
            predicted_direction=out_direction,
            ensemble_score=final_score,
            confidence=confidence,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            engine_weights=weights,
            engine_scores=engine_scores,
            model_version=self.MODEL_VERSION,
            engine_disagreement=disagreement,
        )

    def get_weights_status(self) -> EnsembleWeightsResponse:
        """Trả về cấu hình trọng số động và trạng thái phiên hiện tại."""
        now = datetime.now(VN_TZ)
        phase, weights = self.get_dynamic_weights(now)
        return EnsembleWeightsResponse(
            session_phase=phase,
            current_time_utc=now,
            weights=weights,
            schedule=DEFAULT_SCHEDULE,
        )
