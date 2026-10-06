"""Application Service for Market Pulse Analysis (iBoard Pulse).

Phân tích nhịp đập thị trường, độ rộng ngành, top tăng/giảm và tạo nhận định
định lượng tổng quan cho phiên giao dịch.
"""

from __future__ import annotations

from sqlmodel import Session, col, select

from app.domains.iboard.application.schemas import (
    IBoardMarketPulse,
    TopMoverItem,
)
from app.domains.market_data.domain.models import StockOHLCVDaily, StockSymbol


class IBoardPulseService:
    """Use Case: Phân tích và sinh nhận định nhịp đập thị trường."""

    @classmethod
    def get_market_pulse(cls, session: Session) -> IBoardMarketPulse:
        """Truy xuất nhận định thị trường và top cổ phiếu biến động dựa trên dữ liệu thực."""
        latest_bar = session.exec(
            select(StockOHLCVDaily)
            .order_by(col(StockOHLCVDaily.trading_date).desc())
            .limit(1)
        ).first()
        latest_date = latest_bar.trading_date if latest_bar else None

        prev_bar = (
            session.exec(
                select(StockOHLCVDaily)
                .where(col(StockOHLCVDaily.trading_date) < latest_date)
                .order_by(col(StockOHLCVDaily.trading_date).desc())
                .limit(1)
            ).first()
            if latest_date
            else None
        )
        prev_date = prev_bar.trading_date if prev_bar else None

        today_bars: dict[str, StockOHLCVDaily] = {}
        prev_bars: dict[str, StockOHLCVDaily] = {}
        if latest_date and prev_date:
            for b in session.exec(
                select(StockOHLCVDaily).where(
                    StockOHLCVDaily.trading_date == latest_date
                )
            ).all():
                today_bars[b.symbol] = b
            for b in session.exec(
                select(StockOHLCVDaily).where(StockOHLCVDaily.trading_date == prev_date)
            ).all():
                prev_bars[b.symbol] = b

        sym_recs = {
            s.symbol: s
            for s in session.exec(
                select(StockSymbol).where(StockSymbol.asset_type == "stock")
            ).all()
        }

        movers: list[tuple[str, str, float, float, float]] = []
        sector_pnl: dict[str, list[float]] = {}
        adv_count = dec_count = unch_count = 0

        for sym, bar in today_bars.items():
            if (
                sym in ("VNINDEX", "VN30", "HNX30", "HNXINDEX", "VN30F1M")
                or sym not in prev_bars
            ):
                continue
            prev_b = prev_bars[sym]
            if prev_b.close <= 0:
                continue

            chg = bar.close - prev_b.close
            pct = (chg / prev_b.close) * 100
            if chg > 0:
                adv_count += 1
            elif chg < 0:
                dec_count += 1
            else:
                unch_count += 1

            sym_info = sym_recs.get(sym)
            sec = (
                (sym_info.industry or sym_info.icb_name or "Khác")
                if sym_info
                else "Khác"
            )
            sector_pnl.setdefault(sec, []).append(pct)
            s_name = sym_info.organ_name if sym_info and sym_info.organ_name else sym
            movers.append((sym, s_name, bar.close, chg, pct))

        movers.sort(key=lambda x: x[4], reverse=True)

        top_gainers = [
            TopMoverItem(
                symbol=m[0],
                name=m[1],
                price=f"{m[2]:,.2f}",
                change=f"{m[4]:+.2f}%",
            )
            for m in movers[:4]
        ]
        top_losers = [
            TopMoverItem(
                symbol=m[0],
                name=m[1],
                price=f"{m[2]:,.2f}",
                change=f"{m[4]:+.2f}%",
            )
            for m in reversed(movers[-4:])
        ]

        sector_avg = {
            s: round(sum(p) / len(p), 2) for s, p in sector_pnl.items() if len(p) >= 2
        }

        vn_bar = today_bars.get("VNINDEX") or today_bars.get("VN30")
        prev_vn = prev_bars.get("VNINDEX") or prev_bars.get("VN30")
        insight = "Thị trường đang tổng hợp dữ liệu giao dịch."

        if vn_bar and prev_vn and prev_vn.close > 0:
            vn_chg = vn_bar.close - prev_vn.close
            vn_pct = (vn_chg / prev_vn.close) * 100
            vn_vol_mil = vn_bar.volume / 1e6
            index_label = vn_bar.symbol
            direction = (
                "tăng" if vn_chg > 0 else "điều chỉnh" if vn_chg < 0 else "đi ngang"
            )

            sorted_sec = sorted(sector_avg.items(), key=lambda x: x[1], reverse=True)
            sec_comment = ""
            if sorted_sec:
                best_sec, worst_sec = sorted_sec[0][0], sorted_sec[-1][0]
                g_note = (
                    f" ({top_gainers[0].symbol} {top_gainers[0].change})"
                    if top_gainers
                    else ""
                )
                l_note = (
                    f" ({top_losers[0].symbol} {top_losers[0].change})"
                    if top_losers
                    else ""
                )
                sec_comment = (
                    f" Dòng tiền tích cực luân chuyển vào nhóm {best_sec}{g_note}, "
                    f"trong khi áp lực bán tập trung tại nhóm {worst_sec}{l_note}."
                )

            insight = (
                f"{index_label} {direction} {vn_pct:+.2f}%, đóng cửa tại "
                f"{vn_bar.close:,.2f} điểm với thanh khoản toàn thị trường "
                f"{vn_vol_mil:,.2f} triệu cổ phiếu. "
                f"Độ rộng ghi nhận {adv_count} mã tăng so với {dec_count} mã giảm."
                f"{sec_comment}"
            )

        return IBoardMarketPulse(
            ai_insight=insight,
            top_gainers=top_gainers,
            top_losers=top_losers,
            sector_performance=sector_avg,
        )


__all__ = ["IBoardPulseService"]
