"""Application Service / Use Case: Trading Board (Bảng giá v2) multi-category retrieval.

Xử lý bảng giá theo từng danh mục:
- Phái sinh (Derivatives)
- Chứng quyền (Covered Warrants)
- Quỹ ETF
- Cổ phiếu niêm yết (Listed) / Nhóm ngành (Sectors)
"""

from __future__ import annotations

import logging
from typing import Any

from sqlmodel import Session, col, select

from app.domains.market_data.application.iboard_schemas import IBoardStockRow
from app.domains.market_data.domain.iboard_policy import (
    make_stock_row,
    parse_eod_price_block,
    parse_live_price_block,
)
from app.domains.market_data.domain.models import (
    DerivativeContract,
    StockOHLCVDaily,
    StockSymbol,
)
from app.domains.market_data.infrastructure.external_indices import (
    IBoardDataGateway,
)
from app.domains.market_data.infrastructure.vnstock import VnstockService

logger = logging.getLogger(__name__)


class IBoardTableService:
    """Use Case: Tổng hợp dữ liệu bảng giá chứng khoán chi tiết."""

    @staticmethod
    def get_board(
        session: Session,
        category: str = "listed",
        group: str = "VN30",
        sector: str | None = None,
        search: str | None = None,
        limit: int = 50,
    ) -> list[IBoardStockRow]:
        rows: list[IBoardStockRow] = []
        vn = VnstockService(db_session=session)

        # 1. Phái sinh (Derivatives)
        if category == "derivatives":
            contracts = list(
                session.exec(
                    select(DerivativeContract).where(
                        col(DerivativeContract.is_active).is_(True)
                    )
                ).all()
            )
            filtered = []
            for c in contracts:
                sym_rec = session.exec(
                    select(StockSymbol).where(StockSymbol.symbol == c.symbol)
                ).first()
                c_name = (
                    sym_rec.organ_name
                    if sym_rec and sym_rec.organ_name
                    else f"HĐTL {c.symbol}"
                )
                if (
                    search
                    and search.strip().upper() not in c.symbol.upper()
                    and search.strip().upper() not in c_name.upper()
                ):
                    continue
                filtered.append((c, c_name))

            quote_map = IBoardDataGateway.fetch_batch_quotes(
                vn, [c.symbol for c, _ in filtered]
            )
            for c, c_name in filtered:
                bars = IBoardDataGateway.backfill_ohlcv_daily(
                    session, vn, c.symbol, target_count=100
                )
                spark = [float(b.close) for b in reversed(bars)] if bars else []
                qrow = quote_map.get(c.symbol)
                blk = (
                    parse_live_price_block(qrow, is_derivatives=True)
                    if qrow is not None
                    else parse_eod_price_block(bars, exchange="DERIVATIVES")
                )
                rows.append(
                    make_stock_row(
                        symbol=c.symbol,
                        name=c_name,
                        exchange="DERIVATIVES",
                        blk=blk,
                        sparkline=spark,
                        category="derivatives",
                        expiry_date=c.expiration_date.strftime("%d/%m/%Y"),
                    )
                )
            return rows

        # 2. Chứng quyền (Covered Warrants)
        if category == "warrants":
            try:
                wdf = vn.fetch_covered_warrants_list()
                if wdf is not None and not wdf.empty:
                    count = 0
                    for _, w in wdf.iterrows():
                        if count >= limit:
                            break
                        w_sym = str(w.get("symbol", "")).strip().upper()
                        if not w_sym or (
                            search and search.strip().upper() not in w_sym
                        ):
                            continue
                        bars = list(
                            session.exec(
                                select(StockOHLCVDaily)
                                .where(StockOHLCVDaily.symbol == w_sym)
                                .order_by(col(StockOHLCVDaily.trading_date).desc())
                                .limit(8)
                            ).all()
                        )
                        if not bars:
                            continue
                        w_name = str(w.get("organ_name", "") or f"Chứng quyền {w_sym}")
                        exp_raw = str(
                            w.get("maturity_date", "") or w.get("due_date", "") or ""
                        )
                        blk = parse_eod_price_block(bars, exchange="HOSE")
                        rows.append(
                            make_stock_row(
                                symbol=w_sym,
                                name=w_name,
                                exchange="HOSE",
                                blk=blk,
                                sparkline=[float(b.close) for b in reversed(bars)],
                                category="warrants",
                                expiry_date=exp_raw[:10] if exp_raw else None,
                            )
                        )
                        count += 1
            except Exception as e:
                logger.warning("Không thể tải danh sách chứng quyền: %s", e)
            return rows

        # 3. Quỹ ETF
        if category == "etf":
            known_etfs = [
                "E1VFVN30",
                "FUEVFVND",
                "FUESSVFL",
                "FUESSV30",
                "FUESSV50",
                "FUEKIV30",
                "FUEKIVFS",
                "FUEMAV30",
                "FUEMAVND",
                "FUEIP100",
            ]
            visible = [
                e for e in known_etfs if not search or search.strip().upper() in e
            ][:limit]
            etf_quotes = IBoardDataGateway.fetch_batch_quotes(vn, visible)
            for etf_sym in visible:
                bars = list(
                    session.exec(
                        select(StockOHLCVDaily)
                        .where(StockOHLCVDaily.symbol == etf_sym)
                        .order_by(col(StockOHLCVDaily.trading_date).desc())
                        .limit(8)
                    ).all()
                )
                if not bars:
                    continue
                qrow = etf_quotes.get(etf_sym)
                blk = (
                    parse_live_price_block(qrow, is_derivatives=False)
                    if qrow is not None
                    else parse_eod_price_block(bars, exchange="HOSE")
                )
                rows.append(
                    make_stock_row(
                        symbol=etf_sym,
                        name=f"Quỹ ETF {etf_sym}",
                        exchange="HOSE",
                        blk=blk,
                        sparkline=[float(b.close) for b in reversed(bars)],
                        category="etf",
                    )
                )
            return rows

        # 4. Cổ phiếu niêm yết (Listed) / Ngành (Sectors)
        stmt = select(StockSymbol).where(StockSymbol.asset_type == "stock")

        if category == "sectors" and sector:
            sector_keywords: dict[str, list[str]] = {
                "bank": ["ngân hàng", "tài chính", "ngan hang", "bank"],
                "real_estate": [
                    "bất động sản",
                    "bat dong san",
                    "địa ốc",
                    "xây dựng",
                ],
                "logistics": [
                    "vận tải",
                    "van tai",
                    "cảng",
                    "logistics",
                    "kho bãi",
                ],
                "materials": [
                    "thép",
                    "nguyên vật liệu",
                    "hóa chất",
                    "kim loại",
                    "vật liệu",
                ],
                "food_beverage": [
                    "thực phẩm",
                    "đồ uống",
                    "thuc pham",
                    "nông nghiệp",
                    "thủy sản",
                ],
                "industrial": [
                    "công nghiệp",
                    "cong nghiep",
                    "chế tạo",
                    "sản xuất",
                ],
                "utilities": [
                    "điện",
                    "nước",
                    "tiện ích",
                    "năng lượng",
                    "khí đốt",
                ],
                "telecom": ["viễn thông", "công nghệ", "phần mềm", "fpt"],
                "retail": ["bán lẻ", "phân phối", "thương mại", "tiêu dùng"],
            }
            kws = sector_keywords.get(sector.lower(), [sector.lower()])
            cond: Any = None
            for kw in kws:
                p = f"%{kw}%"
                kw_cond = (
                    col(StockSymbol.industry).ilike(p)
                    | col(StockSymbol.icb_name).ilike(p)
                    | col(StockSymbol.organ_name).ilike(p)
                )
                cond = cond | kw_cond if cond is not None else kw_cond
            if cond is not None:
                stmt = stmt.where(cond)
        else:
            if group == "VN30":
                has_vn30 = session.exec(
                    select(StockSymbol)
                    .where(StockSymbol.index_group == "VN30")
                    .limit(1)
                ).first()
                if has_vn30:
                    stmt = stmt.where(StockSymbol.index_group == "VN30")
                else:
                    try:
                        vn30_members = vn.fetch_group_symbols("VN30")
                        if vn30_members:
                            stmt = stmt.where(col(StockSymbol.symbol).in_(vn30_members))
                    except Exception as e:
                        logger.debug("Không thể tải danh sách mã VN30: %s", e)
            elif group in ("HSX", "HOSE"):
                stmt = stmt.where(StockSymbol.exchange == "HOSE")
            elif group == "HNX":
                stmt = stmt.where(StockSymbol.exchange == "HNX")
            elif group == "UPCOM":
                stmt = stmt.where(StockSymbol.exchange == "UPCOM")

        if search:
            q = f"%{search.strip().upper()}%"
            stmt = stmt.where(
                col(StockSymbol.symbol).ilike(q) | col(StockSymbol.organ_name).ilike(q)
            )

        symbols = session.exec(stmt.limit(limit)).all()
        quote_map = IBoardDataGateway.fetch_batch_quotes(
            vn, [sym.symbol for sym in symbols]
        )

        for sym in symbols:
            daily_rows = IBoardDataGateway.backfill_ohlcv_daily(
                session, vn, sym.symbol, target_count=100
            )
            if not daily_rows:
                continue

            sparkline = [float(r.close) for r in reversed(daily_rows)]
            sector_name = sym.industry or sym.icb_name or "Chưa phân ngành"
            exchange = sym.exchange or "HOSE"

            qrow = quote_map.get(sym.symbol)
            blk = (
                parse_live_price_block(qrow, is_derivatives=False)
                if qrow is not None
                else parse_eod_price_block(list(daily_rows), exchange=exchange)
            )

            rows.append(
                make_stock_row(
                    symbol=sym.symbol,
                    name=sym.organ_name or sym.symbol,
                    exchange=exchange,
                    blk=blk,
                    sparkline=sparkline,
                    category="listed",
                    sector=sector_name,
                )
            )

        return rows
