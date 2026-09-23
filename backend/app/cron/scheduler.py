"""Bộ lập lịch in-process background scheduler (Facade adapter).

Delegates directly to app.core.scheduler.
"""

from __future__ import annotations

from app.core.scheduler import (
    VN_TZ,
    get_next_schedule_delay,
    run_daily_market_scheduler_loop,
    run_inprocess_scheduler,
    run_quarterly_financials_scheduler_loop,
    run_symbols_scheduler_loop,
    run_tick_purge_scheduler_loop,
    start_scheduler_task,
)
from app.domains.fundamental.application.jobs import run_sync_quarterly_financials_job
from app.domains.market_data.application.jobs import (
    run_purge_ticks_job,
    run_sync_daily_market_job,
    run_sync_symbols_job,
)

__all__ = [
    "VN_TZ",
    "get_next_schedule_delay",
    "run_daily_market_scheduler_loop",
    "run_inprocess_scheduler",
    "run_purge_ticks_job",
    "run_quarterly_financials_scheduler_loop",
    "run_sync_daily_market_job",
    "run_sync_quarterly_financials_job",
    "run_sync_symbols_job",
    "run_symbols_scheduler_loop",
    "run_tick_purge_scheduler_loop",
    "start_scheduler_task",
]
