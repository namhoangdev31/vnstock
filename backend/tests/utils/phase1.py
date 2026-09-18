"""Hermetic SQLite harness for the Phase 1 test suite.

These fixtures are intentionally independent of ``tests/conftest.py``'s
Postgres-backed, session-scoped ``db`` fixture. That lets the Phase 1 tests run
without a database server or network (no Docker, no Supabase), while still
running unchanged inside the full suite — the autouse Postgres fixture simply
also initializes, which is harmless here.
"""

import uuid
from collections.abc import Generator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel

import app.models  # noqa: F401 — register all tables with SQLModel.metadata
from app.api.deps import get_current_user, get_db
from app.core.security import create_access_token
from app.main import app as fastapi_app
from app.models import User


@pytest.fixture
def sqlite_engine():
    """In-memory SQLite with all Phase 1 tables created."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def session(sqlite_engine) -> Generator[Session]:
    with Session(sqlite_engine) as s:
        yield s


@pytest.fixture
def user(session: Session) -> User:
    """A persisted superuser for API tests."""
    u = User(
        email=f"phase1-{uuid.uuid4().hex[:8]}@example.com",
        hashed_password="x",
        is_superuser=True,
        full_name="Phase1 Tester",
    )
    session.add(u)
    session.commit()
    session.refresh(u)
    return u


@pytest.fixture
def api_client(session: Session, user: User) -> Generator[TestClient]:
    """TestClient with deps overridden to the SQLite session + superuser."""

    def _override_db() -> Generator[Session]:
        yield session

    def _override_user() -> User:
        return user

    fastapi_app.dependency_overrides[get_db] = _override_db
    fastapi_app.dependency_overrides[get_current_user] = _override_user
    with TestClient(fastapi_app) as client:
        yield client
    fastapi_app.dependency_overrides.clear()


def auth_headers(user: User) -> dict[str, str]:
    """Real JWT headers (for tests that don't override get_current_user)."""
    token = create_access_token(str(user.id), expires_delta=timedelta(hours=1))
    return {"Authorization": f"Bearer {token}"}


def utc_now() -> datetime:
    return datetime.now(UTC)


def as_utc(value: datetime) -> datetime:
    """Normalize a datetime to UTC for comparison.

    SQLite drops tzinfo on round-trip (naive values are already UTC); Postgres
    TIMESTAMPTZ preserves it. This makes equality assertions dialect-agnostic.
    """
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
