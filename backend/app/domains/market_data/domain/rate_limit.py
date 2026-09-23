"""Mô hình dữ liệu trạng thái Rate Limit và Circuit Breaker phân tán (ProviderRateLimitState).

Quản lý trạng thái throttle và circuit breaker cho từng external data provider (VCI, KBS, MSN, TCBS)
trên toàn bộ cụm worker / API threads qua PostgreSQL.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime
from sqlmodel import Field

from app.core.models_base import AwareSQLModel, get_datetime_utc


class ProviderRateLimitState(AwareSQLModel, table=True):
    """Trạng thái rate limit và circuit breaker của từng nguồn dữ liệu bên ngoài."""

    __tablename__ = "provider_rate_limit_state"

    provider: str = Field(primary_key=True, max_length=20)
    last_request_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    consecutive_failures: int = Field(default=0)
    circuit_state: str = Field(
        default="closed", max_length=20
    )  # closed, open, half_open
    circuit_open_until: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    updated_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


__all__ = ["ProviderRateLimitState"]
