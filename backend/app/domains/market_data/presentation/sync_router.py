"""Market Data Presentation: Sync & Ingestion Routes.

Cung cấp các endpoints đồng bộ dữ liệu thủ công, đồng bộ hàng loạt (batch sync),
các webhook cron tự động (sync-symbols, sync-daily-market, sync-quarterly-financials, purge-ticks),
và nhật ký kiểm toán đồng bộ dữ liệu.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Header, HTTPException, Query
from sqlmodel import col, select

from app.api.deps import CurrentUser, SessionDep
from app.core.config import settings
from app.domains.fundamental.application.jobs import run_sync_quarterly_financials_job
from app.domains.market_data.application.jobs import (
    run_purge_ticks_job,
    run_sync_daily_market_job,
)
from app.domains.market_data.application.schemas import SyncStatusPublic
from app.domains.market_data.application.sync_service import DataSyncManager
from app.domains.market_data.domain.models import DataSyncLog
from app.domains.market_data.infrastructure.vnstock_adapter import vnstock_service

router = APIRouter()


@router.post("/sync/{sync_type}", response_model=SyncStatusPublic)
def trigger_sync(
    session: SessionDep,
    current_user: CurrentUser,
    sync_type: str,
    symbol: str | None = Query(default=None),
    start: str | None = Query(default=None),
    end: str | None = Query(default=None),
    report_type: str = Query(default="income_statement"),
    period: str = Query(default="quarterly"),
) -> Any:
    """Trigger a manual data sync (SuperUser only)."""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough privileges")

    manager = DataSyncManager(session, vnstock_service)

    match sync_type:
        case "symbols":
            log = manager.sync_symbols()
        case "daily":
            if not symbol:
                raise HTTPException(
                    status_code=400, detail="symbol is required for daily sync"
                )
            start_date = date.fromisoformat(start) if start else date(2024, 1, 1)
            end_date = date.fromisoformat(end) if end else date.today()
            log = manager.backfill_daily(symbol, start_date, end_date)
        case "intraday":
            if not symbol:
                raise HTTPException(
                    status_code=400, detail="symbol is required for intraday sync"
                )
            log = manager.collect_intraday(symbol)
        case "profile":
            if not symbol:
                raise HTTPException(
                    status_code=400, detail="symbol is required for profile sync"
                )
            log = manager.sync_company_profile(symbol)
        case "financials":
            if not symbol:
                raise HTTPException(
                    status_code=400, detail="symbol is required for financials sync"
                )
            log = manager.sync_financials(
                symbol, report_type=report_type, period=period
            )
        case "ratios":
            if not symbol:
                raise HTTPException(
                    status_code=400, detail="symbol is required for ratios sync"
                )
            clean_period = "quarter" if "quarter" in period else "year"
            log = manager.sync_financial_ratios(symbol, period=clean_period)
        case "shareholders":
            if not symbol:
                raise HTTPException(
                    status_code=400, detail="symbol is required for shareholders sync"
                )
            log = manager.sync_company_shareholders(symbol)
        case "officers":
            if not symbol:
                raise HTTPException(
                    status_code=400, detail="symbol is required for officers sync"
                )
            log = manager.sync_company_officers(symbol)
        case "events":
            if not symbol:
                raise HTTPException(
                    status_code=400, detail="symbol is required for events sync"
                )
            log = manager.sync_corporate_events(symbol)
        case "subsidiaries":
            if not symbol:
                raise HTTPException(
                    status_code=400, detail="symbol is required for subsidiaries sync"
                )
            log = manager.sync_company_subsidiaries(symbol)
        case "insider_trading":
            if not symbol:
                raise HTTPException(
                    status_code=400,
                    detail="symbol is required for insider_trading sync",
                )
            log = manager.sync_insider_trading(symbol)
        case "capital_history":
            if not symbol:
                raise HTTPException(
                    status_code=400,
                    detail="symbol is required for capital_history sync",
                )
            log = manager.sync_capital_history(symbol)
        case "constituents":
            target_group = symbol or "VN30"
            log = manager.sync_index_constituents(group=target_group)
        case "screener":
            log = manager.sync_screener_snapshots()
        case _:
            raise HTTPException(
                status_code=400, detail=f"Unknown sync type: {sync_type}"
            )

    return SyncStatusPublic.model_validate(log)


@router.post("/sync/batch", response_model=dict[str, Any])
def trigger_batch_sync(
    session: SessionDep,
    current_user: CurrentUser,
    symbols: list[str] = Query(..., description="Danh sách mã cổ phiếu cần đồng bộ"),
    sync_types: list[str] = Query(
        default=[
            "profile",
            "financials",
            "ratios",
            "events",
            "subsidiaries",
            "insider_trading",
            "capital_history",
        ],
        description="Các loại dữ liệu cần đồng bộ",
    ),
    delay_sec: float = Query(
        default=0.3, ge=0.1, le=5.0, description="Độ trễ giữa các mã (giây)"
    ),
) -> Any:
    """Trigger bulk synchronization for multiple symbols (SuperUser only)."""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough privileges")

    manager = DataSyncManager(session, vnstock_service)
    return manager.sync_batch_symbols_data(
        symbols=symbols, sync_types=sync_types, delay_sec=delay_sec
    )


@router.post("/cron/sync-symbols", response_model=SyncStatusPublic)
def cron_sync_symbols(
    session: SessionDep,
    x_cron_secret: Annotated[str | None, Header(alias="X-Cron-Secret")] = None,
    secret_key: str | None = Query(default=None),
) -> Any:
    """Kích hoạt đồng bộ danh mục mã qua Cronjob (GitHub Actions hoặc Scheduled Webhook)."""
    valid_secret = settings.CRON_SECRET_KEY or settings.SECRET_KEY
    provided_secret = x_cron_secret or secret_key

    if not provided_secret or provided_secret != valid_secret:
        raise HTTPException(
            status_code=403,
            detail="Mã bảo mật Cron (X-Cron-Secret) không hợp lệ",
        )

    manager = DataSyncManager(session, vnstock_service)
    log = manager.sync_symbols()
    return SyncStatusPublic.model_validate(log)


@router.post("/cron/sync-daily-market", response_model=list[SyncStatusPublic])
def cron_sync_daily_market(
    session: SessionDep,
    x_cron_secret: Annotated[str | None, Header(alias="X-Cron-Secret")] = None,
    secret_key: str | None = Query(default=None),
) -> Any:
    """Kích hoạt đồng bộ nến ngày cho các chỉ số và rổ VN30 sau phiên ATC (15:15)."""
    valid_secret = settings.CRON_SECRET_KEY or settings.SECRET_KEY
    provided_secret = x_cron_secret or secret_key

    if not provided_secret or provided_secret != valid_secret:
        raise HTTPException(
            status_code=403,
            detail="Mã bảo mật Cron (X-Cron-Secret) không hợp lệ",
        )

    logs = run_sync_daily_market_job(session=session)
    return [SyncStatusPublic.model_validate(log) for log in logs]


@router.post("/cron/sync-quarterly-financials", response_model=list[SyncStatusPublic])
def cron_sync_quarterly_financials(
    session: SessionDep,
    x_cron_secret: Annotated[str | None, Header(alias="X-Cron-Secret")] = None,
    secret_key: str | None = Query(default=None),
    group: str = Query(
        default="VN30", description="Nhóm chỉ số cần đồng bộ (VN30, VN100,...)"
    ),
) -> Any:
    """Kích hoạt đồng bộ báo cáo tài chính & chỉ số quý cho rổ chỉ số (VN30 mặc định)."""
    valid_secret = settings.CRON_SECRET_KEY or settings.SECRET_KEY
    provided_secret = x_cron_secret or secret_key

    if not provided_secret or provided_secret != valid_secret:
        raise HTTPException(
            status_code=403,
            detail="Mã bảo mật Cron (X-Cron-Secret) không hợp lệ",
        )

    logs = run_sync_quarterly_financials_job(session=session, group=group)
    return [SyncStatusPublic.model_validate(log) for log in logs]


@router.post("/cron/purge-ticks", response_model=SyncStatusPublic)
def cron_purge_ticks(
    session: SessionDep,
    x_cron_secret: Annotated[str | None, Header(alias="X-Cron-Secret")] = None,
    secret_key: str | None = Query(default=None),
    retention_days: int = Query(
        default=30, ge=1, le=365, description="Số ngày lưu trữ tick (mặc định 30 ngày)"
    ),
    force: bool = Query(
        default=False, description="Bỏ qua Safe Purge Gate (chỉ dùng khi bắt buộc)"
    ),
) -> Any:
    """Kích hoạt dọn dẹp tick cũ hơn retention_days ngày qua Safe Purge Gate."""
    valid_secret = settings.CRON_SECRET_KEY or settings.SECRET_KEY
    provided_secret = x_cron_secret or secret_key

    if not provided_secret or provided_secret != valid_secret:
        raise HTTPException(
            status_code=403,
            detail="Mã bảo mật Cron (X-Cron-Secret) không hợp lệ",
        )

    log = run_purge_ticks_job(
        session=session, retention_days=retention_days, force=force
    )
    return SyncStatusPublic.model_validate(log)


@router.get("/sync/status", response_model=list[SyncStatusPublic])
def get_sync_status(
    session: SessionDep,
    current_user: CurrentUser,
    last: int = Query(default=10, ge=1, le=100),
) -> Any:
    """Get recent data sync logs (SuperUser only)."""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough privileges")

    logs = session.exec(
        select(DataSyncLog).order_by(col(DataSyncLog.started_at).desc()).limit(last)
    ).all()

    return [SyncStatusPublic.model_validate(log) for log in logs]
