"""FastAPI router for autonomous quant session daemon management."""

from typing import Any

from fastapi import APIRouter

from app.api.deps import CurrentSuperuser
from app.domains.quant.application.daemon import quant_daemon_controller

router = APIRouter(prefix="/quant/daemon", tags=["quant-daemon"])


@router.get("/status", summary="Get daemon operational status and market phase")
def get_daemon_status(current_user: CurrentSuperuser) -> dict[str, Any]:  # noqa: ARG001
    return quant_daemon_controller.status()


@router.post("/pause", summary="Pause background daemon loop")
def pause_daemon(current_user: CurrentSuperuser) -> dict[str, Any]:  # noqa: ARG001
    return quant_daemon_controller.pause()


@router.post(
    "/resume", summary="Resume background daemon loop and reset circuit breaker"
)
def resume_daemon(current_user: CurrentSuperuser) -> dict[str, Any]:  # noqa: ARG001
    return quant_daemon_controller.resume()


@router.post("/trigger", summary="Trigger a single execution cycle off-schedule")
@router.post(
    "/trigger_once",
    summary="Trigger a single execution cycle off-schedule (alias)",
)
async def trigger_daemon_cycle(current_user: CurrentSuperuser) -> dict[str, Any]:  # noqa: ARG001
    return await quant_daemon_controller.trigger_once()


@router.post("/start", summary="Start daemon background worker task")
async def start_daemon(current_user: CurrentSuperuser) -> dict[str, Any]:  # noqa: ARG001
    await quant_daemon_controller.start()
    return quant_daemon_controller.status()


@router.post("/stop", summary="Stop daemon background worker task")
async def stop_daemon(current_user: CurrentSuperuser) -> dict[str, Any]:  # noqa: ARG001
    await quant_daemon_controller.stop()
    return quant_daemon_controller.status()
