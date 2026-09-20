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
from sqlmodel import Session
from starlette.middleware.cors import CORSMiddleware

from app.api.main import api_router
from app.core.config import settings
from app.core.db import engine, init_db

FRONTEND_DIR = Path(__file__).parent / "frontend"
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        backend_dir = Path(__file__).parent.parent
        alembic_ini_path = backend_dir / "alembic.ini"
        if not alembic_ini_path.is_file():
            alembic_ini_path = Path(__file__).parent.parent.parent / "alembic.ini"

        logger.info(
            f"[LIFESPAN] Alembic ini path: {alembic_ini_path}, exists: {alembic_ini_path.is_file()}"
        )
        if alembic_ini_path.is_file():
            try:
                alembic_cfg = Config(str(alembic_ini_path))
                command.upgrade(alembic_cfg, "head")
                logger.info("[LIFESPAN] Alembic migrations executed successfully.")
            except Exception as alembic_err:
                logger.warning(
                    f"[LIFESPAN] Alembic failed: {alembic_err}, running SQLModel.metadata.create_all..."
                )
                from sqlmodel import SQLModel

                import app.models  # noqa: F401

                SQLModel.metadata.create_all(engine)
        else:
            from sqlmodel import SQLModel

            import app.models  # noqa: F401

            SQLModel.metadata.create_all(engine)
            logger.info("[LIFESPAN] Created tables via SQLModel.metadata.create_all.")

        with Session(engine) as session:
            init_db(session)
            logger.info("[LIFESPAN] Initial DB seed executed successfully.")
    except Exception as e:
        logger.error(f"[LIFESPAN ERROR] Migration/seed error: {e}", exc_info=True)
    yield


def custom_generate_unique_id(route: APIRoute) -> str:
    return f"{route.tags[0]}-{route.name}"


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

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_HOST],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)
if FRONTEND_DIR.is_dir():
    app.frontend("/", directory=FRONTEND_DIR)
