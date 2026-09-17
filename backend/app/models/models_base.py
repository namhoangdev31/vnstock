"""Shared model foundations for the Phase 1 quant & simulation tables.

Provides:
- ``AwareSQLModel``: a non-table base that rejects timezone-naive datetimes at
  construction time (RULE 3 — every timestamp must be UTC-aware). SQLAlchemy's
  ORM load path bypasses Pydantic validation, so reading rows from a database
  that returns naive datetimes (e.g. SQLite in tests) is unaffected.
- ``JSONBVariant``: a JSON column type that maps to native ``JSONB`` on
  PostgreSQL and plain ``JSON`` on other dialects.
- ``get_datetime_utc``: the canonical aware-UTC timestamp factory.
"""

from datetime import UTC, datetime
from typing import Any

from pydantic import field_validator
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import SQLModel
from sqlmodel.main import SQLModelConfig


def get_datetime_utc() -> datetime:
    return datetime.now(UTC)


# Native JSONB on PostgreSQL (per spec); plain JSON elsewhere (SQLite in tests).
JSONBVariant = JSON().with_variant(JSONB, "postgresql")


class AwareSQLModel(SQLModel):
    """Base for new table models that enforces timezone-aware datetimes.

    The validator runs on construction and assignment. It deliberately does not
    fire on ORM row loads, which keeps database reads fast and dialect-agnostic.
    """

    model_config = SQLModelConfig(validate_assignment=True)

    @field_validator("*", mode="before")
    @classmethod
    def _reject_naive_datetime(cls, value: Any) -> Any:
        if isinstance(value, datetime) and value.tzinfo is None:
            raise ValueError(
                "timezone-naive datetime is not allowed; provide a UTC-aware datetime"
            )
        return value
