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
from datetime import datetime

from sqlmodel import Session, col, select

from app.core.models_base import VN_TZ
from app.domains.fundamental.domain.models import (
    CompanyProfile,
    CorporateEvent,
    FinancialRatio,
)
from app.domains.market_data.application.iboard_candles import (
    IBoardCandlesService,
)
from app.domains.market_data.application.iboard_schemas import (
    CompanyOverviewDTO,
    CorporateEventDTO,
    IBoardStockDetail,
    MatchedTickDTO,
)
from app.domains.market_data.domain.iboard_policy import (
    make_stock_row,
    parse_eod_price_block,
    parse_live_price_block,
)
from app.domains.market_data.domain.models import (
    StockSymbol,
    StockTickIntraday,
)
from app.domains.market_data.infrastructure.external_indices import (
    IBoardDataGateway,
)
from app.domains.market_data.infrastructure.vnstock import VnstockService

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
        vn = VnstockService(db_session=session)

        sym = session.exec(
            select(StockSymbol).where(StockSymbol.symbol == sym_code)
        ).first()

        # 1. Chuỗi nến kỹ thuật
        candles = IBoardCandlesService.get_candles(
            session=session, symbol=sym_code, timeframe=timeframe, limit=100
        )

        # 2. Nến ngày cho giá tham chiếu, sparkline
        daily_rows = IBoardDataGateway.backfill_ohlcv_daily(
            session, vn, sym_code, target_count=100
        )

        # 3. Live quote — giá khớp, orderbook 3 cấp, room ngoại
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

        # 4. Time & Sales (Dòng khớp lệnh)
        matched_ticks: list[MatchedTickDTO] = []
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
                    new_tick_models: list[StockTickIntraday] = []
                    seq_counter: dict[datetime, int] = {}
                    for _, row in tdf.iterrows():
                        m_time = str(row["time"])
                        t_str = (
                            m_time.split(" ")[1][:8] if " " in m_time else m_time[:8]
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
                        try:
                            t_parsed = datetime.strptime(
                                m_time[:19], "%Y-%m-%d %H:%M:%S"
                            ).replace(tzinfo=VN_TZ)
                        except Exception:
                            t_parsed = datetime.now(VN_TZ)
                        seq_num = seq_counter.get(t_parsed, 0)
                        seq_counter[t_parsed] = seq_num + 1
                        new_tick_models.append(
                            StockTickIntraday(
                                symbol=sym_code,
                                timestamp=t_parsed,
                                price=price_val,
                                volume=vol_val,
                                match_type=side_str,
                                sequence_number=seq_num,
                                source=vn.last_successful_source or "vci",
                            )
                        )
                    try:
                        with session.begin_nested():
                            for item in new_tick_models:
                                session.add(item)
                            session.flush()
                        session.commit()
                    except Exception as tick_err:
                        logger.debug(
                            "Bỏ qua lỗi trùng lặp tick %s: %s",
                            sym_code,
                            tick_err,
                        )
            except Exception as e:
                logger.info("Không thể tải tick từ vnstock cho %s: %s", sym_code, e)

        # 5. Hồ sơ doanh nghiệp & Tỷ số tài chính
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

        if not prof or not ratio:
            try:
                ov = vn.fetch_company_overview(sym_code)
                if ov and not prof:
                    prof = CompanyProfile(
                        symbol=sym_code,
                        company_name=str(ov.get("organ_name") or sym_code),
                        market_cap=float(ov.get("market_cap") or 0),
                        outstanding_shares=int(ov.get("issue_share") or 0),
                    )
                    session.add(prof)
                    session.commit()
            except Exception as e:
                logger.info(
                    "Không thể đồng bộ hồ sơ doanh nghiệp cho %s: %s",
                    sym_code,
                    e,
                )

        last_p = blk["last_p"]
        market_cap_bil = (
            round(prof.market_cap / 1e9, 2)
            if prof and prof.market_cap
            else round(last_p * prof.outstanding_shares * 1000 / 1e9, 2)
            if prof and prof.outstanding_shares
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

        # 6. Sự kiện doanh nghiệp (ex_date, effective_date)
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

        return IBoardStockDetail(
            stock=stock_row,
            matched_ticks=matched_ticks,
            overview=overview,
            events=events,
            candles=candles,
        )
