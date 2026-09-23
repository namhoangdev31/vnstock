import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, delete

import app.domains.fundamental.domain.models  # noqa: F401
import app.domains.identity.domain.models  # noqa: F401
import app.domains.market_data.domain.asset_master  # noqa: F401
import app.domains.market_data.domain.models  # noqa: F401
import app.domains.market_data.domain.rate_limit  # noqa: F401
import app.domains.quant.domain.models  # noqa: F401
import app.domains.simulation.domain.models  # noqa: F401
from app.api.deps import get_db
from app.core.config import settings
from app.core.db import init_db
from app.domains.identity.domain.models import Item, User
from app.main import app as fastapi_app
from tests.utils.user import authentication_token_from_email
from tests.utils.utils import get_superuser_token_headers

# Cấu hình Isolated Test Engine: mặc định dùng In-memory SQLite với StaticPool (nhanh, an toàn, offline 100%)
_test_db_url = os.getenv("TEST_DATABASE_URL")
if not _test_db_url and os.getenv("USE_POSTGRES_TESTS") != "1":
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
elif _test_db_url:
    test_engine = create_engine(_test_db_url)
else:
    from app.core.db import engine as postgres_engine

    test_engine = postgres_engine


def _override_get_db() -> Generator[Session, None, None]:
    with Session(test_engine) as session:
        yield session


# Override get_db toàn cục cho TestClient
fastapi_app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture(autouse=True)
def ensure_db_override() -> Generator[None, None, None]:
    fastapi_app.dependency_overrides[get_db] = _override_get_db
    yield
    fastapi_app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture(scope="session")
def db() -> Generator[Session, None, None]:
    SQLModel.metadata.create_all(test_engine)
    with Session(test_engine) as session:
        init_db(session)
        yield session
        statement = delete(Item)
        session.exec(statement)
        statement = delete(User)
        session.exec(statement)
        session.commit()


@pytest.fixture(scope="module")
def client(db: Session) -> Generator[TestClient, None, None]:  # noqa: ARG001
    with TestClient(fastapi_app) as c:
        yield c


@pytest.fixture(scope="module")
def superuser_token_headers(client: TestClient) -> dict[str, str]:
    return get_superuser_token_headers(client)


@pytest.fixture(scope="module")
def normal_user_token_headers(client: TestClient, db: Session) -> dict[str, str]:
    return authentication_token_from_email(
        client=client, email=settings.EMAIL_TEST_USER, db=db
    )
