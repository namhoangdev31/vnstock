"""Shared-kernel base utilities for SQLModel entities (timezone, JSONB, aware model).

Cung cấp các lớp cơ sở (AwareSQLModel, JSONBVariant) và tiện ích múi giờ dùng chung
giữa các bounded contexts trong kiến trúc Domain-Driven Design (DDD).
"""

from datetime import datetime
from typing import Any, ClassVar
from zoneinfo import ZoneInfo

from pydantic import field_validator
from sqlalchemy import JSON, Table
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import SQLModel
from sqlmodel.main import SQLModelConfig

VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")


def get_datetime_utc() -> datetime:
    """Trả về thời gian hiện tại có múi giờ chuẩn UTC+7 (giờ Việt Nam)."""
    return datetime.now(VN_TZ)


def get_datetime_vn() -> datetime:
    """Trả về thời gian hiện tại có múi giờ chuẩn UTC+7 (giờ Việt Nam)."""
    return datetime.now(VN_TZ)


# Kiểu cột JSONB trên PostgreSQL; fallback JSON thông thường trên SQLite khi kiểm thử
JSONBVariant = JSON().with_variant(JSONB, "postgresql")


class AwareSQLModel(SQLModel):
    """Lớp cơ sở bắt buộc kiểm tra datetime có múi giờ hợp lệ, chống lỗi timezone-naive."""

    model_config = SQLModelConfig(validate_assignment=True)
    __table__: ClassVar[Table]
    __tablename__: ClassVar[str]

    @field_validator("*", mode="before")
    @classmethod
    def _reject_naive_datetime(cls, value: Any) -> Any:
        if isinstance(value, datetime) and value.tzinfo is None:
            raise ValueError(
                "timezone-naive datetime is not allowed; "
                "không chấp nhận datetime không có múi giờ (naive), vui lòng cung cấp datetime có múi giờ hợp lệ"
            )
        return value
