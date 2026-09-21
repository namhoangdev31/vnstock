"""create asset master and refactor fact tables with canonical instrument_id

Revision ID: i1a2b3c4d5e6
Revises: h1a2b3c4d5e6
Create Date: 2026-09-21
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "i1a2b3c4d5e6"
down_revision = "h1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    # 1. Bảng LegalEntity
    op.create_table(
        "legal_entity",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("legal_name", sa.String(length=255), nullable=False),
        sa.Column("short_name", sa.String(length=100), nullable=True),
        sa.Column("tax_id", sa.String(length=50), nullable=True),
        sa.Column("headquarters_address", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tax_id"),
    )
    op.create_index("ix_legal_entity_legal_name", "legal_entity", ["legal_name"], unique=False)
    op.create_index("ix_legal_entity_tax_id", "legal_entity", ["tax_id"], unique=False)

    # 2. Bảng Instrument
    op.create_table(
        "instrument",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("legal_entity_id", sa.Uuid(), nullable=True),
        sa.Column("instrument_type", sa.String(length=30), nullable=False),
        sa.Column("canonical_code", sa.String(length=50), nullable=False),
        sa.Column("isin", sa.String(length=20), nullable=True),
        sa.Column("figi", sa.String(length=20), nullable=True),
        sa.Column("exchange", sa.String(length=20), nullable=False),
        sa.Column("currency", sa.String(length=10), server_default="VND", nullable=False),
        sa.Column("roll_rule", sa.String(length=100), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["legal_entity_id"], ["legal_entity.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("canonical_code"),
        sa.UniqueConstraint("isin"),
        sa.UniqueConstraint("figi"),
    )
    op.create_index("ix_instrument_canonical_code", "instrument", ["canonical_code"], unique=True)
    op.create_index("ix_instrument_type_active", "instrument", ["instrument_type", "is_active"], unique=False)
    op.create_index("ix_instrument_exchange", "instrument", ["exchange"], unique=False)
    op.create_index("ix_instrument_legal_entity_id", "instrument", ["legal_entity_id"], unique=False)

    # 3. Bảng InstrumentAlias
    op.create_table(
        "instrument_alias",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("instrument_id", sa.Uuid(), nullable=False),
        sa.Column("alias", sa.String(length=30), nullable=False),
        sa.Column("alias_type", sa.String(length=30), server_default="TICKER", nullable=False),
        sa.Column("valid_from", sa.Date(), server_default="2000-01-01", nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("valid_from <= coalesce(valid_to, '9999-12-31'::date)", name="ck_instrument_alias_valid_dates"),
        sa.ForeignKeyConstraint(["instrument_id"], ["instrument.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_instrument_alias_instrument_id", "instrument_alias", ["instrument_id"], unique=False)
    op.create_index("ix_instrument_alias_lookup", "instrument_alias", ["alias", "valid_from", "valid_to"], unique=False)

    # Partial unique index cho active alias
    if is_postgres:
        op.create_index(
            "uix_instrument_alias_active",
            "instrument_alias",
            ["alias"],
            unique=True,
            postgresql_where=sa.text("valid_to IS NULL"),
        )
    else:
        op.create_index(
            "uix_instrument_alias_active",
            "instrument_alias",
            ["alias"],
            unique=True,
            sqlite_where=sa.text("valid_to IS NULL"),
        )

    # 4. Bảng InstrumentRelation
    op.create_table(
        "instrument_relation",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_instrument_id", sa.Uuid(), nullable=False),
        sa.Column("target_instrument_id", sa.Uuid(), nullable=False),
        sa.Column("relation_type", sa.String(length=50), nullable=False),
        sa.Column("weight", sa.Float(), nullable=True),
        sa.Column("valid_from", sa.Date(), server_default="2000-01-01", nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["source_instrument_id"], ["instrument.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_instrument_id"], ["instrument.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_instrument_relation_lookup",
        "instrument_relation",
        ["source_instrument_id", "relation_type", "valid_from", "valid_to"],
        unique=False,
    )

    # 5. Thêm instrument_id vào các Fact Tables
    op.add_column("stock_ohlcv_daily", sa.Column("instrument_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_stock_ohlcv_daily_instrument_id",
        "stock_ohlcv_daily",
        "instrument",
        ["instrument_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_stock_ohlcv_daily_instrument_id", "stock_ohlcv_daily", ["instrument_id"], unique=False)

    op.add_column("financial_report", sa.Column("instrument_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_financial_report_instrument_id",
        "financial_report",
        "instrument",
        ["instrument_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_financial_report_instrument_id", "financial_report", ["instrument_id"], unique=False)

    op.add_column("financial_ratio", sa.Column("instrument_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_financial_ratio_instrument_id",
        "financial_ratio",
        "instrument",
        ["instrument_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_financial_ratio_instrument_id", "financial_ratio", ["instrument_id"], unique=False)

    # 6. Backfill Data từ stock_symbol vào Asset Master
    if is_postgres:
        op.execute(
            """
            -- 1. Tạo LegalEntity cho các mã hiện có trong stock_symbol
            INSERT INTO legal_entity (id, legal_name, short_name, created_at, updated_at)
            SELECT 
                gen_random_uuid(),
                COALESCE(s.organ_name, s.symbol),
                s.symbol,
                NOW(),
                NOW()
            FROM stock_symbol s
            WHERE s.symbol IS NOT NULL
            ON CONFLICT DO NOTHING;

            -- 2. Tạo Instrument cho toàn bộ mã trong stock_symbol
            INSERT INTO instrument (
                id, legal_entity_id, instrument_type, canonical_code, exchange, currency, is_active, created_at, updated_at
            )
            SELECT 
                gen_random_uuid(),
                le.id,
                CASE 
                    WHEN s.asset_type = 'DERIVATIVE' OR s.symbol LIKE 'VN30F%' THEN 'FUTURES'
                    WHEN s.symbol LIKE 'C%' AND LENGTH(s.symbol) = 8 THEN 'COVERED_WARRANT'
                    WHEN s.symbol IN ('VN30', 'VN100', 'VNINDEX', 'HNXINDEX', 'UPCOMINDEX') THEN 'INDEX'
                    ELSE 'EQUITY'
                END,
                CASE 
                    WHEN s.asset_type = 'DERIVATIVE' OR s.symbol LIKE 'VN30F%' THEN 'FUTURES:' || s.symbol
                    WHEN s.symbol LIKE 'C%' AND LENGTH(s.symbol) = 8 THEN 'COVERED_WARRANT:' || s.symbol
                    WHEN s.symbol IN ('VN30', 'VN100', 'VNINDEX', 'HNXINDEX', 'UPCOMINDEX') THEN 'INDEX:' || s.symbol
                    ELSE 'EQUITY:' || s.symbol
                END,
                COALESCE(s.exchange, 'HOSE'),
                'VND',
                COALESCE(s.is_active, TRUE),
                NOW(),
                NOW()
            FROM stock_symbol s
            LEFT JOIN legal_entity le ON le.short_name = s.symbol
            ON CONFLICT (canonical_code) DO NOTHING;

            -- 3. Tạo Instrument liên tục (Continuous Rolling) cho VN30F1M
            INSERT INTO instrument (
                id, legal_entity_id, instrument_type, canonical_code, exchange, currency, roll_rule, is_active, created_at, updated_at
            )
            VALUES (
                gen_random_uuid(),
                NULL,
                'FUTURES',
                'FUTURES:VN30F1M:CONTINUOUS',
                'VNFE',
                'VND',
                'THIRD_THURSDAY',
                TRUE,
                NOW(),
                NOW()
            )
            ON CONFLICT (canonical_code) DO NOTHING;

            -- 4. Tạo InstrumentAlias cho tất cả Instrument
            INSERT INTO instrument_alias (
                id, instrument_id, alias, alias_type, valid_from, valid_to, created_at
            )
            SELECT 
                gen_random_uuid(),
                i.id,
                s.symbol,
                CASE 
                    WHEN s.symbol = 'VN30F1M' THEN 'CONTINUOUS_ROLLING'
                    ELSE 'TICKER'
                END,
                '2000-01-01'::date,
                NULL,
                NOW()
            FROM stock_symbol s
            JOIN instrument i ON i.canonical_code = (
                CASE 
                    WHEN s.symbol = 'VN30F1M' THEN 'FUTURES:VN30F1M:CONTINUOUS'
                    WHEN s.asset_type = 'DERIVATIVE' OR s.symbol LIKE 'VN30F%' THEN 'FUTURES:' || s.symbol
                    WHEN s.symbol LIKE 'C%' AND LENGTH(s.symbol) = 8 THEN 'COVERED_WARRANT:' || s.symbol
                    WHEN s.symbol IN ('VN30', 'VN100', 'VNINDEX', 'HNXINDEX', 'UPCOMINDEX') THEN 'INDEX:' || s.symbol
                    ELSE 'EQUITY:' || s.symbol
                END
            )
            ON CONFLICT DO NOTHING;

            -- 5. Backfill instrument_id vào stock_ohlcv_daily
            UPDATE stock_ohlcv_daily d
            SET instrument_id = ia.instrument_id
            FROM instrument_alias ia
            WHERE d.symbol = ia.alias AND ia.valid_to IS NULL AND d.instrument_id IS NULL;

            -- 6. Backfill instrument_id vào financial_report
            UPDATE financial_report f
            SET instrument_id = ia.instrument_id
            FROM instrument_alias ia
            WHERE f.symbol = ia.alias AND ia.valid_to IS NULL AND f.instrument_id IS NULL;

            -- 7. Backfill instrument_id vào financial_ratio
            UPDATE financial_ratio r
            SET instrument_id = ia.instrument_id
            FROM instrument_alias ia
            WHERE r.symbol = ia.alias AND ia.valid_to IS NULL AND r.instrument_id IS NULL;
            """
        )


def downgrade() -> None:
    # 1. Gỡ bỏ instrument_id khỏi Fact Tables
    op.drop_index("ix_financial_ratio_instrument_id", table_name="financial_ratio")
    op.drop_constraint("fk_financial_ratio_instrument_id", "financial_ratio", type_="foreignkey")
    op.drop_column("financial_ratio", "instrument_id")

    op.drop_index("ix_financial_report_instrument_id", table_name="financial_report")
    op.drop_constraint("fk_financial_report_instrument_id", "financial_report", type_="foreignkey")
    op.drop_column("financial_report", "instrument_id")

    op.drop_index("ix_stock_ohlcv_daily_instrument_id", table_name="stock_ohlcv_daily")
    op.drop_constraint("fk_stock_ohlcv_daily_instrument_id", "stock_ohlcv_daily", type_="foreignkey")
    op.drop_column("stock_ohlcv_daily", "instrument_id")

    # 2. Xóa bảng InstrumentRelation
    op.drop_index("ix_instrument_relation_lookup", table_name="instrument_relation")
    op.drop_table("instrument_relation")

    # 3. Xóa bảng InstrumentAlias
    op.drop_index("uix_instrument_alias_active", table_name="instrument_alias")
    op.drop_index("ix_instrument_alias_lookup", table_name="instrument_alias")
    op.drop_index("ix_instrument_alias_instrument_id", table_name="instrument_alias")
    op.drop_table("instrument_alias")

    # 4. Xóa bảng Instrument
    op.drop_index("ix_instrument_legal_entity_id", table_name="instrument")
    op.drop_index("ix_instrument_exchange", table_name="instrument")
    op.drop_index("ix_instrument_type_active", table_name="instrument")
    op.drop_index("ix_instrument_canonical_code", table_name="instrument")
    op.drop_table("instrument")

    # 5. Xóa bảng LegalEntity
    op.drop_index("ix_legal_entity_tax_id", table_name="legal_entity")
    op.drop_index("ix_legal_entity_legal_name", table_name="legal_entity")
    op.drop_table("legal_entity")
