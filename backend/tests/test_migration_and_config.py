"""Automated tests for Alembic migration determinism and fail-fast database URL validation."""

import pytest

from app.core.config import Settings


def test_database_url_rejects_unencoded_at_symbol():
    """Verify that unencoded '@' in password fails fast per RFC 3986."""
    with pytest.raises(ValueError, match="unencoded '@' in credentials"):
        Settings._validate_and_normalize_postgres_url(
            "postgresql://user:pass@word@localhost:5432/dbname",
            "DATABASE_URL",
        )


def test_database_url_accepts_percent_encoded_at_symbol():
    """Verify that percent-encoded '%40' in password succeeds."""
    res = Settings._validate_and_normalize_postgres_url(
        "postgresql://user:pass%40word@localhost:5432/dbname",
        "DATABASE_URL",
    )
    assert res is not None
    assert "pass%40word" in res
    assert res.startswith("postgresql+psycopg://")


def test_database_url_rejects_unknown_query_parameters():
    """Verify that unknown query parameters like pgbouncer=true are rejected fail-fast."""
    with pytest.raises(ValueError, match="invalid psycopg connection parameter"):
        Settings._validate_and_normalize_postgres_url(
            "postgresql://user:password@localhost:5432/dbname?pgbouncer=true",
            "DATABASE_URL",
        )


def test_database_url_accepts_allow_listed_parameters():
    """Verify that valid libpq parameters pass through."""
    res = Settings._validate_and_normalize_postgres_url(
        "postgresql://user:password@localhost:5432/dbname?connect_timeout=5&sslmode=prefer",
        "DATABASE_URL",
    )
    assert res is not None
    assert "connect_timeout=5" in res
    assert "sslmode=prefer" in res


def test_alembic_g1a2b3c4d5e6_uses_year_and_quarter():
    """Verify that the g1a2b3c4d5e6 migration file does not contain fiscal_year or fiscal_quarter."""
    from pathlib import Path

    migration_path = (
        Path(__file__).parent.parent
        / "app"
        / "alembic"
        / "versions"
        / "g1a2b3c4d5e6_normalize_financial_and_institutional_schema.py"
    )
    content = migration_path.read_text()
    assert "fiscal_year" not in content, "Found invalid column fiscal_year in migration"
    assert "fiscal_quarter" not in content, (
        "Found invalid column fiscal_quarter in migration"
    )
    assert "except Exception:" not in content, (
        "Found non-deterministic except Exception in migration"
    )
