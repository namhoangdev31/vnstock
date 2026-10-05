"""Application Service / Use Case: Candles retrieval for iBoard.

Tuân thủ Rule 7.2:
- DB-first cho nến ngày (StockOHLCVDaily).
- Intraday & Weekly gọi VnstockService.
- Đảm bảo thứ tự thời gian tăng dần (chronological order) tương thích TradingView/DNSE.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta

from sqlmodel import Session, col, select

from app.domains.market_data.application.iboard_schemas import IBoardCandleBar
from app.domains.market_data.domain.models import StockOHLCVDaily
from app.domains.market_data.infrastructure.external_indices import (
    IBoardDataGateway,
)
from app.domains.market_data.infrastructure.vnstock import VnstockService

logger = logging.getLogger(__name__)


class IBoardCandlesService:
    """Use Case: Truy xuất chuỗi nến kỹ thuật theo khung thời gian."""

    @staticmethod
    def get_candles(
        session: Session,
        symbol: str,
        timeframe: str = "1D",
        limit: int = 100,
    ) -> list[IBoardCandleBar]:
        sym_code = symbol.strip().upper()
        norm_tf = timeframe.strip()
        if norm_tf not in ("1m", "5m", "15m", "1H", "1D", "1W"):
            norm_tf = "1D"
        limit = max(min(limit, 300), 5)
        vn = VnstockService(db_session=session)

        # 1. Nến ngày (1D) — DB-first với backfill tự động
        if norm_tf == "1D":
            rows = IBoardDataGateway.backfill_ohlcv_daily(
                session, vn, sym_code, target_count=limit
            )
            return [
                IBoardCandleBar(
                    time=str(r.trading_date),
                    open=float(r.open),
                    high=float(r.high),
                    low=float(r.low),
                    close=float(r.close),
                    volume=int(r.volume),
                )
                for r in reversed(rows)
            ]

        # 2. Nến tuần (1W)
        if norm_tf == "1W":
            try:
                today = date.today()
                df = vn.fetch_price_history(
                    sym_code,
                    start=today - timedelta(weeks=max(limit * 2, 52)),
                    end=today,
                    count=limit,
                    interval="1W",
                )
                if df is not None and not df.empty:
                    return [
                        IBoardCandleBar(
                            time=str(r["time"])[:10],
                            open=float(r["open"]),
                            high=float(r["high"]),
                            low=float(r["low"]),
                            close=float(r["close"]),
                            volume=int(r["volume"]),
                        )
                        for _, r in df.iterrows()
                    ]
            except Exception as e:
                logger.warning("Không thể tải nến tuần cho %s: %s", sym_code, e)

        # 3. Nến intraday (1m, 5m, 15m, 1H)
        try:
            df = vn.fetch_intraday(sym_code, interval=norm_tf, count_back=limit)
            if df is not None and not df.empty:
                bars: list[IBoardCandleBar] = []
                for _, r in df.iterrows():
                    m_time = str(r["time"])
                    t_str = m_time.split(" ")[1][:5] if " " in m_time else m_time[:5]
                    bars.append(
                        IBoardCandleBar(
                            time=t_str,
                            open=float(r["open"]),
                            high=float(r["high"]),
                            low=float(r["low"]),
                            close=float(r["close"]),
                            volume=int(r["volume"]),
                        )
                    )
                return bars
        except Exception as e:
            logger.warning(
                "Không thể tải nến intraday %s cho %s: %s",
                norm_tf,
                sym_code,
                e,
            )

        # 4. Fallback: nến ngày từ DB
        rows = list(
            session.exec(
                select(StockOHLCVDaily)
                .where(StockOHLCVDaily.symbol == sym_code)
                .order_by(col(StockOHLCVDaily.trading_date).desc())
                .limit(limit)
            ).all()
        )
        return [
            IBoardCandleBar(
                time=str(r.trading_date),
                open=float(r.open),
                high=float(r.high),
                low=float(r.low),
                close=float(r.close),
                volume=int(r.volume),
            )
            for r in reversed(rows)
        ]
