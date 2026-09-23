"""Application Service: Symbol & Index Management.

Quản lý danh mục mã chứng khoán (HOSE, HNX, UPCOM, Phái sinh, Index, ETF),
nhóm chỉ số (VN30, VN100, VNFINLEAD), và các thành phần cấu thành rổ chỉ số.
"""

from __future__ import annotations

import uuid

from sqlmodel import Session, col, func, select

from app.core.cache import metadata_cache
from app.domains.market_data.application.schemas import (
    IndexConstituentPublic,
    IndexConstituentsResponse,
    StockSymbolPublic,
    StockSymbolsPublic,
)
from app.domains.market_data.domain.exceptions import SymbolNotFoundError
from app.domains.market_data.domain.models import IndexConstituent, StockSymbol
from app.domains.market_data.infrastructure.vnstock_adapter import (
    VnstockServiceError,
    vnstock_service,
)
from app.domains.quant.application.schemas import SymbolGroupResponse


class SymbolService:
    """Dịch vụ nghiệp vụ quản lý thông tin tham chiếu mã chứng khoán."""

    @staticmethod
    def list_symbols(
        session: Session,
        skip: int = 0,
        limit: int = 100,
        exchange: str | None = None,
        asset_type: str | None = None,
        search: str | None = None,
    ) -> StockSymbolsPublic:
        """Liệt kê danh sách mã chứng khoán có phân trang và bộ lọc."""
        query = select(StockSymbol).where(col(StockSymbol.is_active).is_(True))

        if exchange:
            query = query.where(StockSymbol.exchange == exchange)
        if asset_type:
            query = query.where(StockSymbol.asset_type == asset_type)
        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                (col(StockSymbol.symbol).ilike(search_pattern))
                | (col(StockSymbol.organ_name).ilike(search_pattern))
            )

        count_query = select(func.count()).select_from(query.subquery())
        total_count = session.exec(count_query).one()

        paginated_query = (
            query.order_by(col(StockSymbol.symbol)).offset(skip).limit(limit)
        )
        symbols = session.exec(paginated_query).all()

        return StockSymbolsPublic(
            data=[StockSymbolPublic.model_validate(s) for s in symbols],
            count=total_count,
        )

    @staticmethod
    def get_symbol_by_id(
        session: Session,
        symbol_id: uuid.UUID,
    ) -> StockSymbolPublic:
        """Lấy thông tin chi tiết một mã chứng khoán qua UUID."""
        sym = session.exec(
            select(StockSymbol).where(StockSymbol.id == symbol_id)
        ).first()
        if not sym:
            raise SymbolNotFoundError(str(symbol_id))
        return StockSymbolPublic.model_validate(sym)

    @staticmethod
    def get_symbol_group(group: str) -> SymbolGroupResponse:
        """Lấy danh sách mã thuộc nhóm/rổ chỉ số với bộ đệm metadata 24h."""
        grp_code = group.strip().upper()
        cache_key = f"symbols_group:{grp_code}"
        cached = metadata_cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            symbols = vnstock_service.fetch_group_symbols(group=grp_code)
        except VnstockServiceError as e:
            raise VnstockServiceError(
                f"Symbol group {grp_code} unavailable from all data sources: {e}"
            ) from e

        result = SymbolGroupResponse(
            group=grp_code, count=len(symbols), symbols=symbols
        )
        metadata_cache.set(cache_key, result)
        return result

    @staticmethod
    def get_index_constituents(
        session: Session,
        group: str,
    ) -> IndexConstituentsResponse:
        """Lấy danh sách thành phần và tỷ trọng rổ chỉ số (VN30, VN100, VNFINLEAD)."""
        grp_code = group.strip().upper()
        rows = session.exec(
            select(IndexConstituent)
            .where(IndexConstituent.index_code == grp_code)
            .order_by(col(IndexConstituent.symbol).asc())
        ).all()

        if not rows:
            from app.domains.market_data.application.sync_service import DataSyncManager

            try:
                manager = DataSyncManager(session, vnstock_service)
                log = manager.sync_index_constituents(group=grp_code)
                if log.status == "success":
                    rows = session.exec(
                        select(IndexConstituent)
                        .where(IndexConstituent.index_code == grp_code)
                        .order_by(col(IndexConstituent.symbol).asc())
                    ).all()
            except VnstockServiceError:
                pass

        data = [
            IndexConstituentPublic(
                id=r.id,
                index_code=r.index_code,
                symbol=r.symbol,
                weight=r.weight,
                free_float_shares=r.free_float_shares,
                effective_date=r.effective_date,
            )
            for r in rows
        ]
        return IndexConstituentsResponse(
            index_code=grp_code, count=len(data), data=data
        )


__all__ = ["SymbolService"]
