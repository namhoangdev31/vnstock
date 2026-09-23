"""Market Data Application Job: Sync Symbols & Derivatives.

Đồng bộ danh mục mã chứng khoán (HOSE, HNX, UPCOM) và các hợp đồng phái sinh.
"""

from __future__ import annotations

import logging

from sqlmodel import Session

from app.core.db import engine
from app.domains.market_data.application.sync_service import DataSyncManager
from app.domains.market_data.domain.models import DataSyncLog
from app.domains.market_data.infrastructure.vnstock_adapter import (
    VnstockService,
    vnstock_service,
)

logger = logging.getLogger(__name__)


def run_sync_symbols_job(
    session: Session | None = None,
    service: VnstockService | None = None,
) -> DataSyncLog:
    """Thực thi tác vụ đồng bộ danh mục mã chứng khoán & hợp đồng phái sinh."""
    svc = service if service is not None else vnstock_service
    if session is not None:
        manager = DataSyncManager(session, svc)
        return manager.sync_symbols()

    with Session(engine) as db_session:
        manager = DataSyncManager(db_session, svc)
        return manager.sync_symbols()
