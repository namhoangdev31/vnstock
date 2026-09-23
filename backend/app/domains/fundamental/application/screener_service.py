"""Dịch vụ Screener Snapshot & Phân trang Keyset 2 pha Brokerage-Grade (ScreenerService).

Tuân thủ nghiêm ngặt SLA DB execution time P95 < 10 ms:
- Sử dụng pre-computed ScreenerSnapshot.
- Partial index: (roe DESC NULLS LAST, instrument_id ASC) WHERE is_active = true.
- Keyset cursor 2 pha xử lý triệt để nhóm roe IS NULL không sort spill ra đĩa:
  * Pha 1: cursor_roe IS NOT NULL -> (roe < cursor_roe) OR (roe == cursor_roe AND id > cursor_id) OR (roe IS NULL)
  * Pha 2: cursor_roe IS NULL -> roe IS NULL AND id > cursor_id
"""

from datetime import date, datetime

from sqlmodel import Session, and_, col, or_, select

from app.core.models_base import VN_TZ
from app.domains.fundamental.application.schemas import ScreenerCursor, ScreenerResponse
from app.domains.fundamental.domain.models import (
    CompanyProfile,
    FinancialRatio,
    ScreenerSnapshot,
    ScreenerSnapshotHistorical,
)
from app.domains.market_data.domain.asset_master import Instrument
from app.domains.market_data.domain.models import StockOHLCVDaily


class ScreenerService:
    """Xử lý truy vấn bộ lọc cổ phiếu với Keyset Pagination tối ưu."""

    @classmethod
    def query_screener_keyset(
        cls,
        session: Session,
        page_size: int = 50,
        cursor: ScreenerCursor | None = None,
        exchange: str | None = None,
        industry: str | None = None,
        min_pe: float | None = None,
        max_pe: float | None = None,
        min_pb: float | None = None,
        max_pb: float | None = None,
        min_roe: float | None = None,
        max_roe: float | None = None,
        min_roa: float | None = None,
        max_debt_to_equity: float | None = None,
        min_revenue_growth_yoy: float | None = None,
        min_net_profit_growth_yoy: float | None = None,
        min_ev_to_ebitda: float | None = None,
        max_ev_to_ebitda: float | None = None,
    ) -> ScreenerResponse:
        """Truy vấn bảng ScreenerSnapshot bằng thuật toán Keyset 2 pha với đầy đủ bộ lọc."""
        # Điều kiện lọc cơ bản
        base_filters = [col(ScreenerSnapshot.is_active).is_(True)]

        if exchange:
            base_filters.append(col(ScreenerSnapshot.exchange) == exchange.upper())
        if industry:
            base_filters.append(col(ScreenerSnapshot.industry) == industry)
        if min_pe is not None:
            base_filters.append(col(ScreenerSnapshot.pe) >= min_pe)
        if max_pe is not None:
            base_filters.append(col(ScreenerSnapshot.pe) <= max_pe)
        if min_pb is not None:
            base_filters.append(col(ScreenerSnapshot.pb) >= min_pb)
        if max_pb is not None:
            base_filters.append(col(ScreenerSnapshot.pb) <= max_pb)
        if min_roe is not None:
            base_filters.append(col(ScreenerSnapshot.roe) >= min_roe)
        if max_roe is not None:
            base_filters.append(col(ScreenerSnapshot.roe) <= max_roe)
        if min_roa is not None:
            base_filters.append(col(ScreenerSnapshot.roa) >= min_roa)
        if max_debt_to_equity is not None:
            base_filters.append(
                col(ScreenerSnapshot.debt_to_equity) <= max_debt_to_equity
            )
        if min_revenue_growth_yoy is not None:
            base_filters.append(
                col(ScreenerSnapshot.revenue_growth_yoy) >= min_revenue_growth_yoy
            )
        if min_net_profit_growth_yoy is not None:
            base_filters.append(
                col(ScreenerSnapshot.profit_growth_yoy) >= min_net_profit_growth_yoy
            )
        if min_ev_to_ebitda is not None:
            base_filters.append(col(ScreenerSnapshot.ev_to_ebitda) >= min_ev_to_ebitda)
        if max_ev_to_ebitda is not None:
            base_filters.append(col(ScreenerSnapshot.ev_to_ebitda) <= max_ev_to_ebitda)

        query = select(ScreenerSnapshot).where(*base_filters)

        # Áp dụng Keyset Cursor
        if cursor is not None and cursor.instrument_id is not None:
            if cursor.roe is not None:
                # Pha 1: Cursor vẫn ở trong vùng giá trị ROE có số thực
                # Tìm các bản ghi có ROE nhỏ hơn HOẶC bằng nhưng ID lớn hơn HOẶC ROE là NULL
                cursor_cond = or_(
                    col(ScreenerSnapshot.roe) < cursor.roe,
                    and_(
                        col(ScreenerSnapshot.roe) == cursor.roe,
                        col(ScreenerSnapshot.instrument_id) > cursor.instrument_id,
                    ),
                    col(ScreenerSnapshot.roe).is_(None),
                )
                query = query.where(cursor_cond)
                query = query.order_by(
                    col(ScreenerSnapshot.roe).desc().nulls_last(),
                    col(ScreenerSnapshot.instrument_id).asc(),
                )
            else:
                # Pha 2: Cursor đã tiến vào vùng roe IS NULL
                cursor_cond = and_(
                    col(ScreenerSnapshot.roe).is_(None),
                    col(ScreenerSnapshot.instrument_id) > cursor.instrument_id,
                )
                query = query.where(cursor_cond)
                query = query.order_by(col(ScreenerSnapshot.instrument_id).asc())
        else:
            # Trang đầu tiên
            query = query.order_by(
                col(ScreenerSnapshot.roe).desc().nulls_last(),
                col(ScreenerSnapshot.instrument_id).asc(),
            )

        # Lấy dôi dư 1 bản ghi để biết có trang tiếp theo hay không
        query = query.limit(page_size + 1)
        results = list(session.exec(query).all())

        has_next = len(results) > page_size
        items = results[:page_size]

        next_cursor = None
        if has_next and items:
            last_item = items[-1]
            next_cursor = ScreenerCursor(
                roe=last_item.roe,
                instrument_id=last_item.instrument_id,
            )

        return ScreenerResponse(
            items=items,
            total_count=len(items),
            has_next=has_next,
            next_cursor=next_cursor,
        )

    @classmethod
    def query_screener_fallback(
        cls,
        session: Session,
        period: str = "quarter",
        year: int | None = None,
        quarter: int | None = None,
        exchange: str | None = None,
        industry: str | None = None,
        min_pe: float | None = None,
        max_pe: float | None = None,
        min_pb: float | None = None,
        max_pb: float | None = None,
        min_roe: float | None = None,
        max_roe: float | None = None,
        min_roa: float | None = None,
        max_debt_to_equity: float | None = None,
        min_revenue_growth_yoy: float | None = None,
        min_net_profit_growth_yoy: float | None = None,
        min_ev_to_ebitda: float | None = None,
        max_ev_to_ebitda: float | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[dict]:
        """Fallback screener: truy vấn FinancialRatio trực tiếp, lọc exchange/industry qua FK text.

        Không yêu cầu StockSymbol model — lọc theo các trường được denormalise trong
        FinancialRatio.symbol (FK text). exchange/industry được lọc qua subquery trên
        bảng stock_symbol theo tên bảng (SQLAlchemy text join) để tránh cross-domain import.
        """
        from sqlalchemy import text  # noqa: PLC0415

        target_year = year
        target_quarter = quarter
        if target_year is None:
            latest_period = session.exec(
                select(FinancialRatio.year, FinancialRatio.quarter)
                .where(FinancialRatio.period == period)
                .order_by(
                    col(FinancialRatio.year).desc(), col(FinancialRatio.quarter).desc()
                )
                .limit(1)
            ).first()
            if latest_period:
                target_year, target_quarter = latest_period[0], latest_period[1]

        query = select(FinancialRatio).where(col(FinancialRatio.period) == period)

        if target_year is not None:
            query = query.where(col(FinancialRatio.year) == target_year)
        if target_quarter is not None and period == "quarter":
            query = query.where(col(FinancialRatio.quarter) == target_quarter)
        if min_pe is not None:
            query = query.where(col(FinancialRatio.pe) >= min_pe)
        if max_pe is not None:
            query = query.where(col(FinancialRatio.pe) <= max_pe)
        if min_pb is not None:
            query = query.where(col(FinancialRatio.pb) >= min_pb)
        if max_pb is not None:
            query = query.where(col(FinancialRatio.pb) <= max_pb)
        if min_roe is not None:
            query = query.where(col(FinancialRatio.roe) >= min_roe)
        if max_roe is not None:
            query = query.where(col(FinancialRatio.roe) <= max_roe)
        if min_roa is not None:
            query = query.where(col(FinancialRatio.roa) >= min_roa)
        if max_debt_to_equity is not None:
            query = query.where(col(FinancialRatio.debt_to_equity) <= max_debt_to_equity)
        if min_revenue_growth_yoy is not None:
            query = query.where(
                col(FinancialRatio.revenue_growth_yoy) >= min_revenue_growth_yoy
            )
        if min_net_profit_growth_yoy is not None:
            query = query.where(
                col(FinancialRatio.net_profit_growth_yoy) >= min_net_profit_growth_yoy
            )
        if min_ev_to_ebitda is not None:
            query = query.where(col(FinancialRatio.ev_to_ebitda) >= min_ev_to_ebitda)
        if max_ev_to_ebitda is not None:
            query = query.where(col(FinancialRatio.ev_to_ebitda) <= max_ev_to_ebitda)

        # Lọc exchange / industry qua subquery trên stock_symbol (không import cross-domain model)
        if exchange:
            sym_subq = session.exec(
                text(
                    "SELECT symbol FROM stock_symbol WHERE exchange = :ex"
                ).bindparams(ex=exchange.strip().upper())
            ).all()
            sym_codes = [r[0] for r in sym_subq]
            if not sym_codes:
                return []
            query = query.where(col(FinancialRatio.symbol).in_(sym_codes))
        if industry:
            sym_subq = session.exec(
                text(
                    "SELECT symbol FROM stock_symbol WHERE industry = :ind"
                ).bindparams(ind=industry.strip())
            ).all()
            sym_codes = [r[0] for r in sym_subq]
            if not sym_codes:
                return []
            query = query.where(col(FinancialRatio.symbol).in_(sym_codes))

        query = (
            query.order_by(col(FinancialRatio.roe).desc().nulls_last())
            .offset(skip)
            .limit(limit)
        )
        ratios = session.exec(query).all()

        # Lấy organ_name từ stock_symbol qua raw text query để tránh cross-domain
        symbols = [r.symbol for r in ratios]
        org_map: dict[str, dict] = {}
        if symbols:
            rows = session.exec(
                text(
                    "SELECT symbol, organ_name, exchange, industry FROM stock_symbol"
                    " WHERE symbol = ANY(:syms)"
                ).bindparams(syms=symbols)
            ).all()
            org_map = {r[0]: {"organ_name": r[1], "exchange": r[2], "industry": r[3]} for r in rows}

        return [
            {
                "symbol": ratio.symbol,
                "organ_name": org_map.get(ratio.symbol, {}).get("organ_name"),
                "exchange": org_map.get(ratio.symbol, {}).get("exchange"),
                "industry": org_map.get(ratio.symbol, {}).get("industry"),
                "fiscal_year": ratio.year,
                "fiscal_quarter": ratio.quarter,
                "pe": ratio.pe,
                "pb": ratio.pb,
                "roe": ratio.roe,
                "roa": ratio.roa,
                "debt_to_equity": ratio.debt_to_equity,
                "ev_to_ebitda": ratio.ev_to_ebitda,
                "net_profit_margin": ratio.net_margin,
                "revenue_growth_yoy": ratio.revenue_growth_yoy,
                "net_profit_growth_yoy": ratio.net_profit_growth_yoy,
            }
            for ratio in ratios
        ]

    @classmethod
    def generate_daily_snapshot(
        cls,
        session: Session,
        snapshot_date: date | None = None,
        target_date: date | None = None,
        force: bool = False,  # noqa: ARG003
    ) -> int:
        """Tạo snapshot định lượng hàng ngày và lưu trữ lịch sử Point-in-Time một cách idempotent."""
        final_date = target_date or snapshot_date or date.today()
        # Lấy danh sách Instrument đang hoạt động
        instruments = session.exec(
            select(Instrument).where(col(Instrument.is_active).is_(True))
        ).all()
        if not instruments:
            return 0

        # Lấy trước các historical snapshot đã có cho ngày final_date để đảm bảo tính idempotent
        existing_hist_map = {
            h.instrument_id: h
            for h in session.exec(
                select(ScreenerSnapshotHistorical).where(
                    col(ScreenerSnapshotHistorical.snapshot_date) == final_date
                )
            ).all()
        }

        # Lấy bản đồ profile công ty
        profiles = {p.symbol: p for p in session.exec(select(CompanyProfile)).all()}

        created_count = 0
        now_utc = datetime.now(VN_TZ)

        for inst in instruments:
            sym = inst.canonical_code.split(":")[-1]
            prof = profiles.get(sym)

            # Lấy giá đóng cửa ngày gần nhất
            daily_bar = session.exec(
                select(StockOHLCVDaily)
                .where(
                    or_(
                        col(StockOHLCVDaily.instrument_id) == inst.id,
                        col(StockOHLCVDaily.symbol) == sym,
                    )
                )
                .where(col(StockOHLCVDaily.trading_date) <= final_date)
                .order_by(col(StockOHLCVDaily.trading_date).desc())
            ).first()

            # Lấy chỉ số tài chính gần nhất
            ratio = session.exec(
                select(FinancialRatio)
                .where(
                    or_(
                        col(FinancialRatio.instrument_id) == inst.id,
                        col(FinancialRatio.symbol) == sym,
                    )
                )
                .order_by(
                    col(FinancialRatio.year).desc(),
                    col(FinancialRatio.quarter).desc().nulls_last(),
                )
            ).first()

            price_val = float(daily_bar.close) if daily_bar else None
            change_val = (
                float(daily_bar.change_pct)
                if daily_bar and daily_bar.change_pct is not None
                else None
            )
            vol_val = float(daily_bar.volume) if daily_bar else None

            # Upsert vào ScreenerSnapshot
            snap = session.exec(
                select(ScreenerSnapshot).where(
                    col(ScreenerSnapshot.instrument_id) == inst.id
                )
            ).first()

            snap_data = {
                "instrument_id": inst.id,
                "snapshot_date": final_date,
                "symbol": sym,
                "exchange": inst.exchange or "HOSE",
                "industry": prof.industry_name if prof else None,
                "is_active": inst.is_active,
                "pe": float(ratio.pe) if ratio and ratio.pe is not None else None,
                "pb": float(ratio.pb) if ratio and ratio.pb is not None else None,
                "ps": float(ratio.ps) if ratio and ratio.ps is not None else None,
                "ev_to_ebitda": (
                    float(ratio.ev_to_ebitda)
                    if ratio and ratio.ev_to_ebitda is not None
                    else None
                ),
                "dividend_yield": (
                    float(ratio.dividend_yield)
                    if ratio and ratio.dividend_yield is not None
                    else None
                ),
                "roe": float(ratio.roe) if ratio and ratio.roe is not None else None,
                "roa": float(ratio.roa) if ratio and ratio.roa is not None else None,
                "roic": float(ratio.roic) if ratio and ratio.roic is not None else None,
                "gross_margin": (
                    float(ratio.gross_margin)
                    if ratio and ratio.gross_margin is not None
                    else None
                ),
                "net_margin": (
                    float(ratio.net_margin)
                    if ratio and ratio.net_margin is not None
                    else None
                ),
                "revenue_growth_yoy": (
                    float(ratio.revenue_growth_yoy)
                    if ratio and ratio.revenue_growth_yoy is not None
                    else None
                ),
                "profit_growth_yoy": (
                    float(ratio.net_profit_growth_yoy)
                    if ratio and ratio.net_profit_growth_yoy is not None
                    else None
                ),
                "debt_to_equity": (
                    float(ratio.debt_to_equity)
                    if ratio and ratio.debt_to_equity is not None
                    else None
                ),
                "current_ratio": (
                    float(ratio.current_ratio)
                    if ratio and ratio.current_ratio is not None
                    else None
                ),
                "quick_ratio": (
                    float(ratio.quick_ratio)
                    if ratio and ratio.quick_ratio is not None
                    else None
                ),
                "interest_coverage": (
                    float(ratio.interest_coverage)
                    if ratio and ratio.interest_coverage is not None
                    else None
                ),
                "price": price_val,
                "change_pct": change_val,
                "volume_ma20": vol_val,
                "updated_at": now_utc,
            }

            if snap is None:
                snap = ScreenerSnapshot(**snap_data)
                session.add(snap)
            else:
                for k, v in snap_data.items():
                    setattr(snap, k, v)
                session.add(snap)

            # Idempotent lưu bản ghi lịch sử vintage (ScreenerSnapshotHistorical)
            hist_snap = existing_hist_map.get(inst.id)
            if hist_snap is None:
                hist_snap = ScreenerSnapshotHistorical(
                    **snap_data,
                    as_of=now_utc,
                )
                session.add(hist_snap)
                existing_hist_map[inst.id] = hist_snap
            else:
                # Nếu đã có bản ghi của ngày này, cập nhật các chỉ số mới nhất thay vì nhân bản duplicate
                for k, v in snap_data.items():
                    if k not in ("instrument_id", "snapshot_date"):
                        setattr(hist_snap, k, v)
                hist_snap.as_of = now_utc
                session.add(hist_snap)

            created_count += 1

        session.commit()
        return created_count
