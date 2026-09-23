"""Engine 2: Động cơ Phân tích Dòng tiền, Thanh khoản & Chu kỳ T+2 (FlowLiquidityEngine).

Theo dõi xung lực dòng tiền tổ chức (Khối ngoại và Tự doanh), các chỉ số độ rộng thị trường,
các chỉ báo vĩ mô (tỷ giá USD/VND, vàng SJC) và mô hình hóa chu kỳ thanh toán cổ phiếu T+2
cùng áp lực bán xả hàng phiên chiều tại thị trường chứng khoán Việt Nam.
"""

import math
from collections.abc import Sequence
from datetime import date, datetime, timedelta
from typing import Any

from sqlmodel import Session, col, select

from app.core.enums import MacroIndicatorCode
from app.core.models_base import VN_TZ
from app.domains.quant.application.schemas import FlowLiquidityEngineResponse
from app.domains.quant.domain.indicators import compute_exponential_smoothing
from app.domains.quant.domain.models import (
    InstitutionalFlow,
    MacroIndicator,
    MarketBreadth,
)


class FlowLiquidityEngine:
    """Động cơ Phân tích Thanh khoản, Dòng tiền Tổ chức và Dòng tiền Chu kỳ T+2."""

    def __init__(self, session: Session | None = None) -> None:
        self.session = session

    def compute_institutional_momentum(
        self,
        flows: Sequence[InstitutionalFlow | dict[str, Any]],
    ) -> float:
        """Tính toán xung lực dòng tiền tổ chức (Institutional Flow Momentum - IFM) trong [-1.0, +1.0].

        Quy trình chuẩn hóa theo TRD §2.2.2:
        - Tổng hợp mua ròng 5 phiên gần nhất (Rolling 5D): NetF_5D (Khối ngoại) và NetP_5D (Tự doanh).
        - Chuẩn hóa bằng Z-Score / Min-Max trên chuỗi lịch sử sẵn có, hoặc scale động an toàn.
        - Tỷ trọng kết hợp: 60% Khối ngoại + 40% Tự doanh.
        - Tuân thủ RULE 3: Nếu thiếu số liệu Tự doanh, tự động chuẩn hóa 100% theo Khối ngoại.
        """
        if not flows:
            return 0.0

        by_date: dict[Any, dict[str, float | None]] = {}
        for idx, fl in enumerate(flows):
            t_date = (
                fl.trading_date
                if isinstance(fl, InstitutionalFlow)
                else fl.get("trading_date", idx)
            )
            f_val = (
                fl.foreign_net_value
                if isinstance(fl, InstitutionalFlow)
                else fl.get("foreign_net_value")
            )
            p_val = (
                fl.prop_net_value
                if isinstance(fl, InstitutionalFlow)
                else fl.get("prop_net_value")
            )

            if t_date not in by_date:
                by_date[t_date] = {"f": 0.0, "p": 0.0, "has_f": False, "has_p": False}
            if f_val is not None:
                by_date[t_date]["f"] = (by_date[t_date]["f"] or 0.0) + float(f_val)
                by_date[t_date]["has_f"] = True
            if p_val is not None:
                by_date[t_date]["p"] = (by_date[t_date]["p"] or 0.0) + float(p_val)
                by_date[t_date]["has_p"] = True

        if not by_date:
            return 0.0

        sorted_dates = sorted(by_date.keys(), reverse=True)
        chronological = list(reversed(sorted_dates))
        f_series = [by_date[d]["f"] or 0.0 for d in chronological]
        p_series = [by_date[d]["p"] or 0.0 for d in chronological]
        f_smoothed = compute_exponential_smoothing(f_series, alpha=0.4)
        p_smoothed = compute_exponential_smoothing(p_series, alpha=0.4)
        by_date_smoothed: dict[Any, tuple[float, float]] = {
            d: (s_f, s_p)
            for d, s_f, s_p in zip(chronological, f_smoothed, p_smoothed, strict=True)
        }

        recent_5_dates = sorted_dates[:5]

        f_5d = 0.0
        p_5d = 0.0
        has_f = False
        has_p = False

        for d in recent_5_dates:
            entry = by_date[d]
            s_f, s_p = by_date_smoothed[d]
            if entry["has_f"]:
                f_5d += s_f
                has_f = True
            if entry["has_p"]:
                p_5d += s_p
                has_p = True

        if not has_f and not has_p:
            return 0.0

        def _normalize_series(current_val: float, history_vals: list[float]) -> float:
            if len(history_vals) >= 5:
                min_v = min(history_vals)
                max_v = max(history_vals)
                if max_v > min_v:
                    return 2.0 * (current_val - min_v) / (max_v - min_v) - 1.0
            scale_denom = 1_000_000_000.0
            return max(-1.0, min(1.0, current_val / scale_denom))

        f_history: list[float] = []
        p_history: list[float] = []
        if len(sorted_dates) > 5:
            for i in range(len(sorted_dates) - 4):
                w_dates = sorted_dates[i : i + 5]
                f_history.append(sum(by_date_smoothed[wd][0] for wd in w_dates))
                p_history.append(sum(by_date_smoothed[wd][1] for wd in w_dates))

        norm_f = _normalize_series(f_5d, f_history)
        norm_p = _normalize_series(p_5d, p_history)

        if has_f and has_p:
            ifm = 0.60 * norm_f + 0.40 * norm_p
        elif has_f:
            ifm = norm_f
        else:
            ifm = norm_p

        return round(max(-1.0, min(1.0, ifm)), 4)

    def compute_market_breadth(
        self,
        breadth_record: MarketBreadth | dict[str, Any] | None,
        ratio_ma20: float | None = None,
    ) -> float | None:
        """Tính chỉ số độ rộng thị trường (Market Breadth Index - MBI) trong [-1.0, +1.0].

        Công thức chuẩn hóa theo TRD §2.2.3:
        - ADR = (Mã tăng - Mã giảm) / (Mã tăng + Mã giảm + Mã không đổi)
        - Nếu có dữ liệu Ratio_MA20 (tỷ lệ cổ phiếu trên MA20):
            MBI = 0.70 * ADR + 0.30 * (2.0 * Ratio_MA20 - 1.0)
        - Nếu chưa có feed Ratio_MA20 (RULE 3 không bịa đặt số liệu):
            MBI = ADR thuần túy.
        """
        if breadth_record is None:
            return None

        adv = (
            breadth_record.advancers
            if isinstance(breadth_record, MarketBreadth)
            else breadth_record.get("advancers", 0)
        )
        dec = (
            breadth_record.decliners
            if isinstance(breadth_record, MarketBreadth)
            else breadth_record.get("decliners", 0)
        )
        flat = (
            breadth_record.unchanged
            if isinstance(breadth_record, MarketBreadth)
            else breadth_record.get("unchanged", 0)
        )

        total = adv + dec + flat
        if total <= 0:
            return 0.0

        adr = (adv - dec) / float(total)

        if ratio_ma20 is not None:
            clamped_ratio = max(0.0, min(1.0, float(ratio_ma20)))
            mbi = 0.70 * adr + 0.30 * (2.0 * clamped_ratio - 1.0)
        else:
            mbi = adr

        return round(max(-1.0, min(1.0, mbi)), 4)

    def compute_t2_settlement_date(self, buy_date: date) -> date:
        """Xác định ngày thanh toán bù trừ T+2 thị trường Việt Nam (bỏ qua cuối tuần).

        Cổ phiếu mua vào ngày T sẽ về tài khoản và được phép bán từ 13:00 ngày T+2.
        Ví dụ: Mua ngày Thứ 6 -> Hàng về chiều Thứ 3 tuần sau (bỏ qua Thứ 7, Chủ Nhật).
        """
        curr = buy_date
        added_days = 0
        while added_days < 2:
            curr += timedelta(days=1)
            # Thứ 2 = 0 ... Thứ 6 = 4, Thứ 7 = 5, Chủ Nhật = 6
            if curr.weekday() < 5:
                added_days += 1
        return curr

    def compute_t2_pressure_index(
        self,
        daily_volumes: Sequence[float],
        baseline_ma_window: int = 20,
    ) -> float:
        """Tính chỉ số áp lực bán phiên chiều T+2 (T+2 Pressure Index) trong dải [0.0, 1.0].

        Công thức chuẩn theo TRD §2.2.4 với bổ sung Z-score volume:
            Pressure_T2_base = min(1.0, Vol_T2 / (MA(Vol_20) * 1.5))
            Z_vol            = (Vol_T2 - MA20) / (Std20 + eps)
            Pressure_T2      = 0.7 * Pressure_T2_base + 0.3 * clip(Z_vol / 2, 0, 1)

        Kết hợp cả độ lớn tuyệt đối (MA-ratio) và độ bất ngờ (Z-score) để
        phân biệt "volume cao nhưng bình thường" với "volume spike thực sự".
        """
        if len(daily_volumes) < 3:
            return 0.0

        vol_t2 = daily_volumes[-2]
        window = daily_volumes[max(0, len(daily_volumes) - baseline_ma_window - 2) : -2]
        if not window:
            return 0.0

        avg_vol = sum(window) / len(window)
        if avg_vol <= 0:
            return 0.0

        pressure_base = vol_t2 / (avg_vol * 1.5)

        if len(window) >= 5:
            mean_w = sum(window) / len(window)
            var_w = sum((v - mean_w) ** 2 for v in window) / len(window)
            std_w = math.sqrt(var_w) if var_w > 1e-9 else avg_vol * 0.3
            z_vol = (vol_t2 - mean_w) / (std_w + 1e-9)
            pressure_z = max(0.0, min(1.0, z_vol / 2.0))
            pressure = 0.85 * min(1.0, pressure_base) + 0.15 * pressure_z
        else:
            pressure = min(1.0, pressure_base)

        return round(min(1.0, max(0.0, pressure)), 4)

    def compute_macro_sentiment(
        self,
        macro_records: Sequence[MacroIndicator | dict[str, Any]],
    ) -> float:
        """Tính điểm số tâm lý vĩ mô trong dải [-1.0, +1.0].

        - Tỷ giá USD/VND tăng nóng (> +0.5%/ngày) tác động tiêu cực tới dòng vốn ngoại FII.
        - Giá vàng biến động lệch pha mạnh phản ánh tâm lý phòng thủ rủi ro (Risk-off).
        """
        if not macro_records:
            return 0.0

        score = 0.0
        count = 0

        for r in macro_records:
            code = (
                r.indicator_code
                if isinstance(r, MacroIndicator)
                else r.get("indicator_code")
            )
            change = (
                r.change_pct if isinstance(r, MacroIndicator) else r.get("change_pct")
            )
            if change is None:
                continue

            if code == MacroIndicatorCode.USD_VND:
                if change > 0.5:
                    score -= min(1.0, (change - 0.5) * 2.0 + 0.3)
                elif change < -0.5:
                    score += min(0.5, abs(change + 0.5) * 1.0 + 0.2)
                count += 1
            elif code in (
                MacroIndicatorCode.SJC_GOLD_BUY,
                MacroIndicatorCode.SJC_GOLD_SELL,
            ):
                if change > 1.0:
                    score -= 0.2
                elif change < -1.0:
                    score += 0.1
                count += 1

        if count == 0:
            return 0.0

        return round(max(-1.0, min(1.0, score / count)), 4)

    def compute_composite_score(
        self,
        institutional_momentum: float,
        market_breadth: float | None,
        t2_pressure: float,
        macro_sentiment: float,
    ) -> float:
        """Tổng hợp điểm số của Engine 2 trong dải [-1.0, +1.0].

        Công thức chuẩn: 0.45 * IFM + 0.35 * MBI - 0.20 * Pressure_T2 + 0.10 * Macro.
        Dynamic Reweighting: Nếu market_breadth là None (nguồn feed chưa hỗ trợ hoặc unavailable),
        tái phân bổ trọng số 0.35 tỷ lệ sang 3 thành phần còn lại (tổng mẫu số = 0.45 + 0.20 + 0.10 = 0.75):
        - institutional_momentum: 0.45 / 0.75 = 0.60
        - t2_pressure: 0.20 / 0.75 = 0.2667
        - macro_sentiment: 0.10 / 0.75 = 0.1333
        """
        if market_breadth is None:
            raw = (
                (0.45 / 0.75) * institutional_momentum
                - (0.20 / 0.75) * t2_pressure
                + (0.10 / 0.75) * macro_sentiment
            )
        else:
            raw = (
                0.45 * institutional_momentum
                + 0.35 * market_breadth
                - 0.20 * t2_pressure
                + 0.10 * macro_sentiment
            )
        return round(max(-1.0, min(1.0, raw)), 4)

    def analyze(
        self,
        flows: Sequence[InstitutionalFlow | dict[str, Any]] | None = None,
        breadth: MarketBreadth | dict[str, Any] | None = None,
        daily_volumes: Sequence[float] | None = None,
        macro_items: Sequence[MacroIndicator | dict[str, Any]] | None = None,
        ratio_ma20: float | None = None,
        as_of: datetime | None = None,
    ) -> FlowLiquidityEngineResponse:
        """Thực thi phân tích thanh khoản, dòng tiền và trả về FlowLiquidityEngineResponse."""
        now = as_of or datetime.now(VN_TZ)

        if flows is None and self.session is not None:
            flows = self.session.exec(
                select(InstitutionalFlow)
                .order_by(col(InstitutionalFlow.trading_date).desc())
                .limit(10)
            ).all()

        if macro_items is None and self.session is not None:
            macro_items = self.session.exec(
                select(MacroIndicator)
                .order_by(col(MacroIndicator.recorded_date).desc())
                .limit(10)
            ).all()

        if breadth is None and self.session is not None:
            breadth = self.session.exec(
                select(MarketBreadth)
                .order_by(col(MarketBreadth.trading_date).desc())
                .limit(1)
            ).first()

        ifm = self.compute_institutional_momentum(flows or [])
        mbi = self.compute_market_breadth(breadth, ratio_ma20=ratio_ma20)
        t2_press = self.compute_t2_pressure_index(daily_volumes or [])
        macro = self.compute_macro_sentiment(macro_items or [])

        score = self.compute_composite_score(
            institutional_momentum=ifm,
            market_breadth=mbi,
            t2_pressure=t2_press,
            macro_sentiment=macro,
        )

        mbi_formula = (
            "0.7*ADR + 0.3*(2*Ratio_MA20 - 1)"
            if ratio_ma20 is not None
            else ("ADR" if mbi is not None else None)
        )

        return FlowLiquidityEngineResponse(
            as_of=now,
            score=score,
            institutional_momentum=ifm,
            market_breadth=mbi,
            market_breadth_ratio_ma20=ratio_ma20,
            mbi_formula=mbi_formula,
            t2_pressure=t2_press,
            macro_sentiment=macro,
        )
