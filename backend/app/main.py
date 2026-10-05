import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path

# Enforce Vietnam Timezone (UTC+7) across the application runtime
os.environ["TZ"] = "Asia/Ho_Chi_Minh"
if hasattr(time, "tzset"):
    time.tzset()

import sentry_sdk
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session
from starlette.middleware.cors import CORSMiddleware

from app.api.main import api_router
from app.core.config import settings
from app.core.db import engine, init_db
from app.domains.quant.application.daemon import quant_daemon_controller

FRONTEND_DIR = Path(__file__).parent / "frontend"
logger = logging.getLogger(__name__)


def _run_migrations_and_seed() -> bool:
    try:
        backend_dir = Path(__file__).parent.parent
        alembic_ini_path = backend_dir / "alembic.ini"
        if not alembic_ini_path.is_file():
            alembic_ini_path = Path(__file__).parent.parent.parent / "alembic.ini"

        logger.info(
            f"[LIFESPAN] Alembic ini path: {alembic_ini_path}, exists: {alembic_ini_path.is_file()}"
        )

        max_retries = 5
        migration_success = False

        if alembic_ini_path.is_file():
            alembic_cfg = Config(str(alembic_ini_path))
            script_dir = backend_dir / "app" / "alembic"
            if not script_dir.is_dir():
                script_dir = Path(__file__).parent / "alembic"
            alembic_cfg.set_main_option("script_location", str(script_dir.resolve()))

            for attempt in range(1, max_retries + 1):
                try:
                    command.upgrade(alembic_cfg, "head")
                    logger.info("[LIFESPAN] Alembic migrations executed successfully.")
                    migration_success = True
                    break
                except Exception as alembic_err:
                    if attempt < max_retries:
                        wait_time = attempt * 2 + 1
                        logger.info(
                            f"[LIFESPAN] Database/DNS đang khởi động ({alembic_err}). Thử lại sau {wait_time}s (lần {attempt}/{max_retries})..."
                        )
                        time.sleep(wait_time)
                    else:
                        logger.warning(
                            f"[LIFESPAN] Alembic migration chưa thành công sau {max_retries} lần thử: {alembic_err}. Bỏ qua DB seed."
                        )
                        return False
        else:
            try:
                from sqlmodel import SQLModel

                import app.domains.fundamental.domain.models  # noqa: F401
                import app.domains.identity.domain.models  # noqa: F401
                import app.domains.market_data.domain.asset_master  # noqa: F401
                import app.domains.market_data.domain.models  # noqa: F401
                import app.domains.market_data.domain.rate_limit  # noqa: F401
                import app.domains.quant.domain.models  # noqa: F401
                import app.domains.simulation.domain.models  # noqa: F401

                SQLModel.metadata.create_all(engine)
                logger.info(
                    "[LIFESPAN] Created tables via SQLModel.metadata.create_all."
                )
                migration_success = True
            except Exception as create_err:
                logger.warning(
                    f"[LIFESPAN] SQLModel.metadata.create_all failed: {create_err}"
                )
                return False

        if migration_success:
            try:
                with Session(engine) as session:
                    init_db(session)
                    logger.info("[LIFESPAN] Initial DB seed executed successfully.")
            except Exception as seed_err:
                logger.warning(f"[LIFESPAN] Initial DB seed failed: {seed_err}")
        return migration_success
    except Exception as e:
        logger.warning(f"[LIFESPAN] Unexpected error in background migration/seed: {e}")
        return False


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if os.getenv("TESTING") == "1" or "PYTEST_CURRENT_TEST" in os.environ:
        yield
        return
    migration_task = asyncio.create_task(asyncio.to_thread(_run_migrations_and_seed))
    try:
        from app.domains.market_data.infrastructure.vnstock import (
            VnstockService,
        )

        tier_info = VnstockService.get_tier_info()
        logger.info(
            f"[LIFESPAN] vnstock initialized (tier: {tier_info.get('tier')}, "
            f"limits: {tier_info.get('limits')}, has_api_key: {tier_info.get('has_api_key')})"
        )
    except Exception as tier_err:
        logger.warning(f"[LIFESPAN] Failed to detect vnstock tier: {tier_err}")

    migrations_ready = await migration_task
    if migrations_ready:
        await quant_daemon_controller.start()
        if settings.DNSE_WS_ENABLED:
            try:
                from app.domains.market_data.infrastructure.dnse import (
                    dnse_stream_manager,
                )

                await dnse_stream_manager.start()
            except Exception as dnse_err:
                logger.warning(
                    f"[LIFESPAN] Failed to start DNSE stream manager: {dnse_err}"
                )
    else:
        logger.error("[LIFESPAN] Daemon withheld because database setup failed")
    try:
        yield
    finally:
        if migrations_ready:
            if settings.DNSE_WS_ENABLED:
                try:
                    from app.domains.market_data.infrastructure.dnse import (
                        dnse_stream_manager,
                    )

                    await dnse_stream_manager.stop()
                except Exception as dnse_err:
                    logger.warning(
                        f"[LIFESPAN] Error stopping DNSE stream manager: {dnse_err}"
                    )
            await quant_daemon_controller.stop()
        if not migration_task.done():
            migration_task.cancel()


def custom_generate_unique_id(route: APIRoute) -> str:
    tag = route.tags[0] if route.tags else "default"
    return f"{tag}-{route.name}"


if settings.SENTRY_DSN and settings.FASTAPI_ENV != "development":
    sentry_sdk.init(dsn=str(settings.SENTRY_DSN), enable_tracing=True)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    generate_unique_id_function=custom_generate_unique_id,
    lifespan=lifespan,
    swagger_ui_parameters={
        "persistAuthorization": True,
        "displayRequestDuration": True,
        "filter": True,
        "tryItOutEnabled": True,
        "syntaxHighlight.theme": "obsidian",
        "docExpansion": "list",
        "defaultModelsExpandDepth": 2,
        "defaultModelExpandDepth": 2,
    },
)

cors_origins = [
    settings.FRONTEND_HOST,
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://vnstock.fastapicloud.dev",
]
cors_origins = list(dict.fromkeys(cors_origins))

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:[0-9]+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)
if FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
else:

    @app.get("/", include_in_schema=False)
    async def root():
        return {
            "project": settings.PROJECT_NAME,
            "status": "online",
            "docs": f"{settings.API_V1_STR}/docs",
        }
