"""Application Service / Use Case: Stock Detail retrieval for iBoard.

Tổng hợp thông tin chi tiết một mã:
- Nến kỹ thuật đa khung thời gian
- Sổ lệnh 3 cấp & trạng thái giá
- Dòng khớp lệnh (Time & Sales ticks)
- Hồ sơ doanh nghiệp & chỉ số tài chính (PE, PB, ROE, Market Cap)
- Sự kiện doanh nghiệp & chia cổ tức
"""

from __future__ import annotations

import logging
from typing import Any

from sqlmodel import Session, col, select

from app.domains.dnse import dnse_stream_manager
from app.domains.fundamental.domain.models import (
    CompanyProfile,
    CorporateEvent,
    FinancialRatio,
)
from app.domains.iboard.application.candles_service import IBoardCandlesService
from app.domains.iboard.application.schemas import (
    CompanyOverviewDTO,
    CorporateEventDTO,
    IBoardStockDetail,
    MatchedTickDTO,
    ShareholderDTO,
)
from app.domains.iboard.domain.policy import (
    make_stock_row,
    parse_eod_price_block,
    parse_live_price_block,
)
from app.domains.iboard.infrastructure.external_indices import (
    IBoardDataGateway,
)
from app.domains.market_data.domain.models import (
    StockSymbol,
    StockTickIntraday,
)
from app.domains.vnstock import VnstockService

logger = logging.getLogger(__name__)


class IBoardDetailService:
    """Use Case: Truy xuất snapshot chi tiết một mã chứng khoán."""

    @staticmethod
    def get_stock_detail(
        session: Session,
        symbol: str,
        timeframe: str = "1D",
    ) -> IBoardStockDetail:
        sym_code = symbol.strip().upper()
        dnse_stream_manager.subscribe_symbols_background([sym_code])
        vn = VnstockService(db_session=session)

        sym = session.exec(
            select(StockSymbol).where(StockSymbol.symbol == sym_code)
        ).first()

        candles = IBoardCandlesService.get_candles(
            session=session, symbol=sym_code, timeframe=timeframe, limit=100
        )

        daily_rows = IBoardDataGateway.backfill_ohlcv_daily(
            session, vn, sym_code, target_count=100
        )

        live_quote_map = IBoardDataGateway.fetch_batch_quotes(vn, [sym_code])
        live_quote_row = live_quote_map.get(sym_code)

        exchange = sym.exchange if sym and sym.exchange else "HOSE"
        is_deriv = (
            (sym.asset_type == "derivative") if sym else sym_code.startswith("VN30F")
        )

        blk = (
            parse_live_price_block(live_quote_row, is_derivatives=is_deriv)
            if live_quote_row is not None
            else parse_eod_price_block(list(daily_rows), exchange=exchange)
        )

        stock_row = make_stock_row(
            symbol=sym_code,
            name=sym.organ_name if sym and sym.organ_name else sym_code,
            exchange=exchange,
            blk=blk,
            sparkline=[float(r.close) for r in reversed(daily_rows)]
            if daily_rows
            else [],
            category="listed" if not is_deriv else "derivatives",
            sector=sym.industry or sym.icb_name or "Chưa phân ngành"
            if sym
            else "Chưa phân ngành",
        )

        matched_ticks: list[MatchedTickDTO] = []
        dnse_ticks = dnse_stream_manager.normalizer.get_recent_ticks(sym_code, limit=20)
        if dnse_ticks:
            matched_ticks = [
                MatchedTickDTO(
                    time=t["time"],
                    price=float(t["price"]),
                    volume=int(t["volume"]),
                    side=str(t["side"]),
                )
                for t in dnse_ticks
            ]
        else:
            tick_rows = list(
                session.exec(
                    select(StockTickIntraday)
                    .where(StockTickIntraday.symbol == sym_code)
                    .order_by(col(StockTickIntraday.timestamp).desc())
                    .limit(20)
                ).all()
            )

            if tick_rows:
                matched_ticks = [
                    MatchedTickDTO(
                        time=t.timestamp.strftime("%H:%M:%S"),
                        price=float(t.price),
                        volume=int(t.volume),
                        side="B" if str(t.match_type).upper().startswith("B") else "S",
                    )
                    for t in tick_rows
                ]
            else:
                try:
                    tdf = vn.fetch_tick_orderflow(sym_code, page_size=20)
                    if tdf is not None and not tdf.empty:
                        for _, row in tdf.iterrows():
                            m_time = str(row["time"])
                            t_str = (
                                m_time.split(" ")[1][:8]
                                if " " in m_time
                                else m_time[:8]
                            )
                            price_val = float(row["price"])
                            vol_val = int(row["volume"])
                            side_str = (
                                "B"
                                if str(row["match_type"]).upper().startswith("B")
                                else "S"
                            )
                            matched_ticks.append(
                                MatchedTickDTO(
                                    time=t_str,
                                    price=price_val,
                                    volume=vol_val,
                                    side=side_str,
                                )
                            )
                except Exception as e:
                    logger.debug(
                        "Không thể tải tick từ vnstock cho %s: %s", sym_code, e
                    )

        prof = session.exec(
            select(CompanyProfile).where(CompanyProfile.symbol == sym_code)
        ).first()
        ratio = session.exec(
            select(FinancialRatio)
            .where(FinancialRatio.symbol == sym_code)
            .order_by(
                col(FinancialRatio.year).desc(),
                col(FinancialRatio.quarter).desc(),
            )
            .limit(1)
        ).first()

        live_overview: dict[str, Any] = {}
        if not prof or not ratio:
            try:
                live_overview = vn.fetch_company_overview(sym_code) or {}
            except Exception as e:
                logger.debug(
                    "Không thể tải hồ sơ doanh nghiệp online cho %s: %s",
                    sym_code,
                    e,
                )

        last_p = blk["last_p"]
        mcap_raw = (
            prof.market_cap
            if prof and prof.market_cap
            else float(live_overview.get("market_cap") or 0.0)
        )
        shares_raw = (
            prof.outstanding_shares
            if prof and prof.outstanding_shares
            else int(live_overview.get("issue_share") or 0)
        )

        market_cap_bil = (
            round(mcap_raw / 1e9, 2)
            if mcap_raw > 0
            else round(last_p * shares_raw * 1000 / 1e9, 2)
            if shares_raw > 0
            else 0.0
        )
        pe_val = round(float(ratio.pe), 2) if ratio and ratio.pe is not None else 0.0
        pb_val = round(float(ratio.pb), 2) if ratio and ratio.pb is not None else 0.0
        roe_val = round(float(ratio.roe), 2) if ratio and ratio.roe is not None else 0.0

        overview = CompanyOverviewDTO(
            market_cap_billion=market_cap_bil,
            pe=pe_val,
            pb=pb_val,
            roe=roe_val,
        )

        event_models = list(
            session.exec(
                select(CorporateEvent)
                .where(CorporateEvent.symbol == sym_code)
                .order_by(col(CorporateEvent.ex_date).desc())
                .limit(5)
            ).all()
        )
        events = [
            CorporateEventDTO(
                date=str(ev.ex_date or ev.effective_date or ""),
                title=ev.event_title,
            )
            for ev in event_models
        ]
        if not events:
            try:
                ev_df = vn.fetch_company_events(sym_code)
                if ev_df is not None and not ev_df.empty:
                    for _, ev_row in ev_df.head(5).iterrows():
                        ev_title = str(
                            ev_row.get("event_title")
                            or ev_row.get("content")
                            or "Sự kiện doanh nghiệp"
                        )
                        ev_date_raw = str(
                            ev_row.get("event_date") or ev_row.get("ex_date") or ""
                        )
                        events.append(
                            CorporateEventDTO(date=ev_date_raw[:10], title=ev_title)
                        )
            except Exception as e:
                logger.info(
                    "Không thể tải sự kiện doanh nghiệp cho %s: %s",
                    sym_code,
                    e,
                )

        company_desc = (
            str(live_overview.get("company_profile") or "")
            if live_overview
            else (prof.description if prof and prof.description else "")
        )

        shareholders: list[ShareholderDTO] = []
        try:
            sh_df = vn.fetch_company_shareholders(sym_code)
            if sh_df is not None and not sh_df.empty:
                for _, sh_row in sh_df.head(6).iterrows():
                    sh_name = str(sh_row.get("share_holder") or "")
                    sh_pct = round(
                        float(sh_row.get("share_own_percent") or 0.0) * 100, 2
                    )
                    sh_qty = int(sh_row.get("quantity") or 0)
                    if sh_name and sh_pct > 0:
                        shareholders.append(
                            ShareholderDTO(
                                name=sh_name,
                                share_percent=sh_pct,
                                quantity=sh_qty,
                            )
                        )
        except Exception as e:
            logger.debug("Không thể tải danh sách cổ đông cho %s: %s", sym_code, e)

        perf_5d: float | None = None
        perf_1y: float | None = None
        if daily_rows and len(daily_rows) >= 5:
            base_5d = float(daily_rows[4].close)
            curr_close = float(daily_rows[0].close)
            if base_5d > 0:
                perf_5d = round(((curr_close - base_5d) / base_5d) * 100, 2)
        if daily_rows and len(daily_rows) >= 20:
            base_1y = float(daily_rows[-1].close)
            curr_close = float(daily_rows[0].close)
            if base_1y > 0:
                perf_1y = round(((curr_close - base_1y) / base_1y) * 100, 2)

        active_buy = sum(t.volume for t in matched_ticks if t.side == "B")
        active_sell = sum(t.volume for t in matched_ticks if t.side == "S")
        if active_buy == 0 and active_sell == 0 and stock_row.volume > 0:
            active_buy = int(stock_row.volume * (stock_row.buy_ratio / 100.0))
            active_sell = stock_row.volume - active_buy

        tot_bid_qtty = sum(b.volume for b in stock_row.bid_book)
        tot_ask_qtty = sum(a.volume for a in stock_row.ask_book)

        return IBoardStockDetail(
            stock=stock_row,
            matched_ticks=matched_ticks,
            overview=overview,
            events=events,
            candles=candles,
            company_profile=company_desc,
            shareholders=shareholders,
            performance_5d=perf_5d,
            performance_1y=perf_1y,
            active_buy_vol=active_buy,
            active_sell_vol=active_sell,
            total_bid_qtty=tot_bid_qtty,
            total_ask_qtty=tot_ask_qtty,
        )


__all__ = ["IBoardDetailService"]
