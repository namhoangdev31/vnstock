"""Engine 2: Động cơ Phân tích Dòng tiền, Thanh khoản & Chu kỳ T+2 (FlowLiquidityEngine).

Theo dõi xung lực dòng tiền tổ chức (Khối ngoại và Tự doanh), các chỉ số độ rộng thị trường,
các chỉ báo vĩ mô (tỷ giá USD/VND, vàng SJC) và mô hình hóa chu kỳ thanh toán cổ phiếu T+2
cùng áp lực bán xả hàng phiên chiều tại thị trường chứng khoán Việt Nam.
"""

from collections.abc import Sequence
from datetime import date, datetime, timedelta
from typing import Any

from sqlmodel import Session, col, select

from app.models import VN_TZ
from app.models.enums import MacroIndicatorCode
from app.models.models_quant import (
    FlowLiquidityEngineResponse,
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

        Tỷ trọng kết hợp: 60% Mua ròng Khối ngoại + 40% Mua ròng Tự doanh.
        Tuân thủ RULE 3: Nếu thiếu số liệu Tự doanh (do vnstock v4 chưa có nguồn feed chính thức),
        hệ thống sẽ tự động chuẩn hóa 100% dựa trên Khối ngoại sẵn có mà không bịa đặt số liệu.
        """
        if not flows:
            return 0.0

        f_net_total = 0.0
        p_net_total = 0.0
        has_f = False
        has_p = False

        for fl in flows:
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

            if f_val is not None:
                f_net_total += float(f_val)
                has_f = True
            if p_val is not None:
                p_net_total += float(p_val)
                has_p = True

        if not has_f and not has_p:
            return 0.0

        # Mức chuẩn hóa: giả định chênh lệch dòng tiền 1,000 tỷ VND (~1e12) là xung lực lớn
        scale_denom = 1_000_000_000_000.0

        if has_f and has_p:
            norm_f = max(-1.0, min(1.0, f_net_total / scale_denom))
            norm_p = max(-1.0, min(1.0, p_net_total / scale_denom))
            ifm = 0.60 * norm_f + 0.40 * norm_p
        elif has_f:
            norm_f = max(-1.0, min(1.0, f_net_total / scale_denom))
            ifm = norm_f
        else:
            norm_p = max(-1.0, min(1.0, p_net_total / scale_denom))
            ifm = norm_p

        return round(max(-1.0, min(1.0, ifm)), 4)

    def compute_market_breadth(
        self,
        breadth_record: MarketBreadth | dict[str, Any] | None,
    ) -> float | None:
        """Tính chỉ số độ rộng thị trường (Market Breadth Index - MBI) trong [-1.0, +1.0].

        Công thức: (Mã tăng - Mã giảm) / Tổng số mã giao dịch.
        Xử lý ca biên: 100% mã giảm -> -1.0, 100% mã tăng -> +1.0.
        Tuân thủ RULE 3: Trả về None nếu không có dữ liệu độ rộng thị trường (không bịa đặt số liệu).
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
        return round(max(-1.0, min(1.0, adr)), 4)

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

        Nếu khối lượng giao dịch ngày T-2 bùng nổ vượt trội so với đường MA20,
        lượng hàng bắt đáy lớn sẽ về tài khoản lúc 13:00 hôm nay, tạo áp lực chốt lời/cắt lỗ gia tăng.
        """
        if len(daily_volumes) < 3:
            return 0.0

        # Khối lượng ngày T-2 là phần tử kế cuối
        vol_t2 = daily_volumes[-2]
        window = daily_volumes[max(0, len(daily_volumes) - baseline_ma_window - 2) : -2]
        if not window:
            return 0.0

        avg_vol = sum(window) / len(window)
        if avg_vol <= 0:
            return 0.0

        # Nếu vol_t2 gấp >1.5 lần trung bình, áp lực bán bắt đầu tăng dần tiệm cận 1.0
        ratio = vol_t2 / avg_vol
        if ratio <= 1.0:
            return 0.0

        pressure = (ratio - 1.0) / 2.0  # ratio = 3.0 -> pressure = 1.0
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
                # Đồng nội tệ mất giá mạnh > +0.5% là tín hiệu bất lợi cho chứng khoán
                if change > 0.5:
                    score -= min(1.0, (change - 0.5) * 2.0 + 0.3)
                elif change < -0.5:
                    score += 0.3
                count += 1
            elif code in (
                MacroIndicatorCode.SJC_GOLD_BUY,
                MacroIndicatorCode.SJC_GOLD_SELL,
            ):
                # Giá vàng trong nước tăng vọt > +1% báo hiệu dòng tiền tìm nơi trú ẩn
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
        as_of: datetime | None = None,
    ) -> FlowLiquidityEngineResponse:
        """Thực thi phân tích thanh khoản, dòng tiền và trả về FlowLiquidityEngineResponse."""
        now = as_of or datetime.now(VN_TZ)

        # Nạp dữ liệu từ DB nếu tham số chưa được truyền trực tiếp
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
        mbi = self.compute_market_breadth(breadth)
        t2_press = self.compute_t2_pressure_index(daily_volumes or [])
        macro = self.compute_macro_sentiment(macro_items or [])

        score = self.compute_composite_score(
            institutional_momentum=ifm,
            market_breadth=mbi,
            t2_pressure=t2_press,
            macro_sentiment=macro,
        )

        return FlowLiquidityEngineResponse(
            as_of=now,
            score=score,
            institutional_momentum=ifm,
            market_breadth=mbi,
            t2_pressure=t2_press,
            macro_sentiment=macro,
        )
