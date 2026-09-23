"""Application Service: Price Data & Multi-Asset Relationships.

Cung cấp dữ liệu giá nến lịch sử ngày (OHLCV Daily), giá thời gian thực (Realtime Price)
kèm in-memory TTL caching, mạng lưới tài sản liên kết chéo (Related Assets Graph),
và danh mục chứng quyền / trái phiếu.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlmodel import Session, col, select

from app.core.cache import realtime_cache
from app.domains.fundamental.application.schemas import CompanyOverviewPublic
from app.domains.fundamental.domain.models import CompanyProfile
from app.domains.market_data.application.schemas import (
    BondSpecificationPublic,
    CoveredWarrantPublic,
    DerivativeContractPublic,
    OHLCVRecord,
    PriceHistoryResponse,
    RelatedAssetsResponse,
    StockSymbolPublic,
)
from app.domains.market_data.domain.exceptions import SymbolNotFoundError
from app.domains.market_data.domain.models import (
    BondSpecification,
    CoveredWarrant,
    DerivativeContract,
    StockOHLCVDaily,
    StockSymbol,
)
from app.domains.market_data.infrastructure.vnstock_adapter import (
    VnstockServiceError,
    vnstock_service,
)


class PriceService:
    """Dịch vụ nghiệp vụ truy xuất dữ liệu giá và mạng lưới tài sản."""

    @staticmethod
    def get_daily_price(
        session: Session,
        symbol: str,
        start: date,
        end: date,
    ) -> PriceHistoryResponse:
        """Lấy lịch sử nến ngày từ PostgreSQL. Nếu thiếu dữ liệu, tự động backfill từ vnstock."""
        sym_code = symbol.strip().upper()

        # 1. Truy vấn PostgreSQL trước (DB-first policy)
        rows = session.exec(
            select(StockOHLCVDaily)
            .where(StockOHLCVDaily.symbol == sym_code)
            .where(StockOHLCVDaily.trading_date >= start)
            .where(StockOHLCVDaily.trading_date <= end)
            .order_by(col(StockOHLCVDaily.trading_date))
        ).all()

        # 2. Nếu DB chưa có dữ liệu, thử backfill từ vnstock
        if not rows:
            from app.domains.market_data.application.sync_service import DataSyncManager

            try:
                manager = DataSyncManager(session, vnstock_service)
                log = manager.backfill_daily(sym_code, start, end)
                if log.status == "success" and log.rows_synced > 0:
                    rows = session.exec(
                        select(StockOHLCVDaily)
                        .where(StockOHLCVDaily.symbol == sym_code)
                        .where(StockOHLCVDaily.trading_date >= start)
                        .where(StockOHLCVDaily.trading_date <= end)
                        .order_by(col(StockOHLCVDaily.trading_date))
                    ).all()
            except VnstockServiceError as e:
                raise VnstockServiceError(
                    f"No data available for {sym_code} and external source is unavailable: {e}"
                ) from e

        data = [
            OHLCVRecord(
                trading_date=str(r.trading_date),
                open=r.open,
                high=r.high,
                low=r.low,
                close=r.close,
                volume=r.volume,
                value=r.value,
                open_interest=r.open_interest,
                basis=r.basis,
            )
            for r in rows
        ]

        return PriceHistoryResponse(
            symbol=sym_code,
            interval="1D",
            count=len(data),
            data=data,
        )

    @staticmethod
    def get_realtime_price(symbol: str) -> dict[str, Any]:
        """Lấy giá thời gian thực gần nhất với bộ đệm in-memory TTL (3-5 giây)."""
        sym_code = symbol.strip().upper()
        cache_key = f"realtime:{sym_code}"
        cached = realtime_cache.get(cache_key)
        if cached:
            return cached

        try:
            df = vnstock_service.fetch_intraday(sym_code, interval="1m", count_back=1)
            if df is not None and not df.empty:
                row = df.iloc[-1]
                result: dict[str, Any] = {
                    "symbol": sym_code,
                    "open": float(row.get("open", 0)),
                    "high": float(row.get("high", 0)),
                    "low": float(row.get("low", 0)),
                    "close": float(row.get("close", 0)),
                    "volume": int(row.get("volume", 0)),
                    "time": str(row.get("time", row.get("date", ""))),
                }
                realtime_cache.set(cache_key, result)
                return result
        except VnstockServiceError:
            pass

        raise VnstockServiceError(
            f"Không thể lấy dữ liệu giá thời gian thực cho mã {sym_code}"
        )

    @staticmethod
    def get_related_assets(session: Session, symbol: str) -> RelatedAssetsResponse:
        """Truy xuất mạng lưới tài sản liên kết chéo của một mã chứng khoán."""
        sym_code = symbol.strip().upper()
        sym = session.exec(
            select(StockSymbol).where(StockSymbol.symbol == sym_code)
        ).first()
        if not sym:
            raise SymbolNotFoundError(sym_code)

        # 1. Profile (truy vấn độc lập ở tầng Application)
        db_prof = session.exec(
            select(CompanyProfile).where(CompanyProfile.symbol == sym_code)
        ).first()
        profile_dto = CompanyOverviewPublic.model_validate(db_prof) if db_prof else None

        # 2. Covered Warrants có cơ sở là mã này
        cw_rows = session.exec(
            select(CoveredWarrant).where(CoveredWarrant.underlying_symbol == sym_code)
        ).all()
        cws_dto = [CoveredWarrantPublic.model_validate(w) for w in cw_rows]

        # 3. Trái phiếu do mã này phát hành
        bond_rows = session.exec(
            select(BondSpecification).where(BondSpecification.issuer_symbol == sym_code)
        ).all()
        bonds_dto = [BondSpecificationPublic.model_validate(b) for b in bond_rows]

        # 4. Hợp đồng phái sinh dựa trên chỉ số này (e.g. VN30)
        deriv_rows = session.exec(
            select(DerivativeContract).where(
                DerivativeContract.underlying_symbol == sym_code
            )
        ).all()
        derivs_dto = [DerivativeContractPublic.model_validate(d) for d in deriv_rows]

        # 5. Nếu bản thân mã là Chứng quyền -> truy xuất ngược về cổ phiếu cơ sở
        underlying_asset_dto = None
        if sym.asset_type == "covered_warrant":
            cw_spec = session.exec(
                select(CoveredWarrant).where(CoveredWarrant.symbol == sym_code)
            ).first()
            if cw_spec and cw_spec.underlying_symbol:
                underlying_sym = session.exec(
                    select(StockSymbol).where(
                        StockSymbol.symbol == cw_spec.underlying_symbol
                    )
                ).first()
                if underlying_sym:
                    underlying_asset_dto = StockSymbolPublic.model_validate(
                        underlying_sym
                    )

        # 6. Nếu bản thân mã là Phái sinh -> truy xuất ngược về chỉ số cơ sở (VN30)
        elif sym.asset_type == "derivative":
            deriv_spec = session.exec(
                select(DerivativeContract).where(DerivativeContract.symbol == sym_code)
            ).first()
            if deriv_spec and deriv_spec.underlying_symbol:
                underlying_sym = session.exec(
                    select(StockSymbol).where(
                        StockSymbol.symbol == deriv_spec.underlying_symbol
                    )
                ).first()
                if underlying_sym:
                    underlying_asset_dto = StockSymbolPublic.model_validate(
                        underlying_sym
                    )

        # 7. Nếu bản thân mã là Trái phiếu -> truy xuất ngược về tổ chức phát hành
        issuer_asset_dto = None
        if sym.asset_type in ("corporate_bond", "government_bond"):
            bond_spec = session.exec(
                select(BondSpecification).where(BondSpecification.symbol == sym_code)
            ).first()
            if bond_spec and bond_spec.issuer_symbol:
                issuer_sym = session.exec(
                    select(StockSymbol).where(
                        StockSymbol.symbol == bond_spec.issuer_symbol
                    )
                ).first()
                if issuer_sym:
                    issuer_asset_dto = StockSymbolPublic.model_validate(issuer_sym)

        return RelatedAssetsResponse(
            symbol=sym.symbol,
            asset_type=sym.asset_type,
            organ_name=sym.organ_name,
            exchange=sym.exchange,
            profile=profile_dto,
            covered_warrants=cws_dto,
            issued_bonds=bonds_dto,
            derivative_contracts=derivs_dto,
            underlying_asset=underlying_asset_dto,
            issuer_asset=issuer_asset_dto,
        )

    @staticmethod
    def list_covered_warrants(
        session: Session,
        underlying_symbol: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[CoveredWarrantPublic]:
        """Danh sách các chứng quyền có bảo đảm kèm bộ lọc theo mã cổ phiếu cơ sở."""
        query = select(CoveredWarrant).where(col(CoveredWarrant.is_active).is_(True))
        if underlying_symbol:
            query = query.where(
                CoveredWarrant.underlying_symbol == underlying_symbol.strip().upper()
            )

        warrants = session.exec(
            query.order_by(col(CoveredWarrant.symbol)).offset(skip).limit(limit)
        ).all()
        return [CoveredWarrantPublic.model_validate(w) for w in warrants]

    @staticmethod
    def list_bonds(
        session: Session,
        bond_type: str | None = None,
        issuer_symbol: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[BondSpecificationPublic]:
        """Danh sách trái phiếu doanh nghiệp & trái phiếu chính phủ kèm bộ lọc."""
        query = select(BondSpecification).where(
            col(BondSpecification.is_active).is_(True)
        )
        if bond_type:
            query = query.where(BondSpecification.bond_type == bond_type.lower())
        if issuer_symbol:
            query = query.where(
                BondSpecification.issuer_symbol == issuer_symbol.strip().upper()
            )

        bonds = session.exec(
            query.order_by(col(BondSpecification.symbol)).offset(skip).limit(limit)
        ).all()
        return [BondSpecificationPublic.model_validate(b) for b in bonds]


__all__ = ["PriceService"]
