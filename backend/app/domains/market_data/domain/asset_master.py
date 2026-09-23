"""Mô hình quản lý danh mục tài sản chuẩn hóa (Canonical Asset Master) theo thời gian.

Cung cấp các thực thể cốt lõi theo AGENTS §1.1:
- LegalEntity: Pháp nhân phát hành
- Instrument: Thực thể công cụ tài chính chuẩn (canonical identity via UUID)
- InstrumentAlias: Quản lý Ticker, Alias và Continuous Rolling contract theo thời gian
- InstrumentRelation: Mối quan hệ giữa các công cụ tài chính (CW -> Underlying, Bond -> Issuer, v.v.)
"""

import uuid
from datetime import date, datetime

from sqlalchemy import CheckConstraint, DateTime, Index, text
from sqlmodel import Field, Relationship

from app.core.models_base import AwareSQLModel, get_datetime_utc


class LegalEntity(AwareSQLModel, table=True):
    """Pháp nhân phát hành hoặc tổ chức niêm yết (Doanh nghiệp, Quỹ, CTCK)."""

    __tablename__ = "legal_entity"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    legal_name: str = Field(max_length=255, index=True)
    short_name: str | None = Field(default=None, max_length=100)
    tax_id: str | None = Field(default=None, max_length=50, unique=True)
    headquarters_address: str | None = Field(default=None, max_length=500)
    created_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    updated_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )

    instruments: list["Instrument"] = Relationship(back_populates="legal_entity")


class Instrument(AwareSQLModel, table=True):
    """Thực thể công cụ tài chính chuẩn (Canonical Instrument).

    Mỗi công cụ tài chính (Cổ phiếu, Phái sinh, Chứng quyền, Trái phiếu, Chỉ số)
    sở hữu đúng một UUID duy nhất trên toàn bộ fact table.
    """

    __tablename__ = "instrument"
    __table_args__ = (
        Index("ix_instrument_type_active", "instrument_type", "is_active"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    legal_entity_id: uuid.UUID | None = Field(
        default=None, foreign_key="legal_entity.id", index=True
    )
    instrument_type: str = Field(
        max_length=30, index=True
    )  # EQUITY, FUTURES, COVERED_WARRANT, CORPORATE_BOND, INDEX
    canonical_code: str = Field(
        max_length=50, unique=True, index=True
    )  # e.g. "EQUITY:VNM", "FUTURES:VN30F2610", "FUTURES:VN30F1M:CONTINUOUS", "INDEX:VN30"
    isin: str | None = Field(default=None, max_length=20, unique=True, index=True)
    figi: str | None = Field(default=None, max_length=20, unique=True, index=True)
    exchange: str = Field(max_length=20, index=True)  # HOSE, HNX, UPCOM, VNFE
    currency: str = Field(default="VND", max_length=10)
    roll_rule: str | None = Field(
        default=None, max_length=100
    )  # e.g. "THIRD_THURSDAY", "EXPIRATION_MINUS_1D"
    is_active: bool = Field(default=True, index=True)
    created_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    updated_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )

    legal_entity: LegalEntity | None = Relationship(back_populates="instruments")
    aliases: list["InstrumentAlias"] = Relationship(back_populates="instrument")
    source_relations: list["InstrumentRelation"] = Relationship(
        back_populates="source_instrument",
        sa_relationship_kwargs={
            "foreign_keys": "InstrumentRelation.source_instrument_id"
        },
    )
    target_relations: list["InstrumentRelation"] = Relationship(
        back_populates="target_instrument",
        sa_relationship_kwargs={
            "foreign_keys": "InstrumentRelation.target_instrument_id"
        },
    )


class InstrumentAlias(AwareSQLModel, table=True):
    """Quản lý Ticker và Alias theo thời gian (Temporal Alias)."""

    __tablename__ = "instrument_alias"
    __table_args__ = (
        Index("ix_instrument_alias_lookup", "alias", "valid_from", "valid_to"),
        CheckConstraint(
            "valid_from <= coalesce(valid_to, '9999-12-31')",
            name="ck_instrument_alias_valid_dates",
        ),
        Index(
            "uix_instrument_alias_active",
            "alias",
            unique=True,
            postgresql_where=text("valid_to IS NULL"),
            sqlite_where=text("valid_to IS NULL"),
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    instrument_id: uuid.UUID = Field(foreign_key="instrument.id", index=True)
    alias: str = Field(max_length=30, index=True)  # e.g. "VNM", "VN30F1M", "VN30F2610"
    alias_type: str = Field(
        default="TICKER", max_length=30
    )  # TICKER, LOCAL_CODE, CONTINUOUS_ROLLING
    valid_from: date = Field(default_factory=lambda: date(2000, 1, 1), index=True)
    valid_to: date | None = Field(default=None, index=True)
    created_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )

    instrument: Instrument | None = Relationship(back_populates="aliases")


class InstrumentRelation(AwareSQLModel, table=True):
    """Mối quan hệ giữa các công cụ tài chính theo thời gian."""

    __tablename__ = "instrument_relation"
    __table_args__ = (
        Index(
            "ix_instrument_relation_lookup",
            "source_instrument_id",
            "relation_type",
            "valid_from",
            "valid_to",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    source_instrument_id: uuid.UUID = Field(foreign_key="instrument.id", index=True)
    target_instrument_id: uuid.UUID = Field(foreign_key="instrument.id", index=True)
    relation_type: str = Field(
        max_length=50, index=True
    )  # UNDERLYING_OF_CW, UNDERLYING_OF_FUTURES, ISSUED_BY, CONSTITUENT_OF_INDEX
    weight: float | None = None
    valid_from: date = Field(default_factory=lambda: date(2000, 1, 1))
    valid_to: date | None = None
    created_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )

    source_instrument: Instrument | None = Relationship(
        back_populates="source_relations",
        sa_relationship_kwargs={
            "foreign_keys": "InstrumentRelation.source_instrument_id"
        },
    )
    target_instrument: Instrument | None = Relationship(
        back_populates="target_relations",
        sa_relationship_kwargs={
            "foreign_keys": "InstrumentRelation.target_instrument_id"
        },
    )


__all__ = [
    "Instrument",
    "InstrumentAlias",
    "InstrumentRelation",
    "LegalEntity",
]
