"""add subsidiary, insider trading, and capital history tables, and ratio data column

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-09-21
"""

import sqlalchemy as sa
from alembic import op
from sqlmodel.sql.sqltypes import AutoString

from app.models.base import JSONBVariant

# revision identifiers, used by Alembic.
revision = "f6a7b8c9d0e1"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add columns to existing tables
    op.add_column(
        "company_profile",
        sa.Column("ceo_name", AutoString(length=255), nullable=True),
    )
    op.add_column(
        "company_profile",
        sa.Column("auditor", AutoString(length=255), nullable=True),
    )
    op.add_column(
        "financial_ratio",
        sa.Column("data", JSONBVariant, nullable=True),
    )

    # 2. company_subsidiary table
    op.create_table(
        "company_subsidiary",
        sa.Column(
            "id",
            sa.Uuid(),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("symbol", AutoString(length=20), nullable=False),
        sa.Column("sub_organ_code", AutoString(length=50), nullable=False),
        sa.Column("organ_name", AutoString(length=500), nullable=False),
        sa.Column(
            "ownership_percent",
            sa.Float(),
            nullable=False,
            server_default="0.0",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["symbol"],
            ["stock_symbol.symbol"],
            name="fk_company_subsidiary_symbol",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "symbol",
            "sub_organ_code",
            name="uq_company_subsidiary_symbol_sub_code",
        ),
    )
    op.create_index(
        "ix_company_subsidiary_symbol",
        "company_subsidiary",
        ["symbol"],
    )
    op.create_index(
        "ix_company_subsidiary_sub_organ_code",
        "company_subsidiary",
        ["sub_organ_code"],
    )

    # 3. insider_trading table
    op.create_table(
        "insider_trading",
        sa.Column(
            "id",
            sa.Uuid(),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("symbol", AutoString(length=20), nullable=False),
        sa.Column("officer_name", AutoString(length=255), nullable=False),
        sa.Column("officer_position", AutoString(length=255), nullable=True),
        sa.Column("deal_action", AutoString(length=50), nullable=False),
        sa.Column("deal_quantity", sa.Float(), nullable=True),
        sa.Column("deal_price", sa.Float(), nullable=True),
        sa.Column("deal_ratio", sa.Float(), nullable=True),
        sa.Column("deal_announce_date", sa.Date(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["symbol"],
            ["stock_symbol.symbol"],
            name="fk_insider_trading_symbol",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "symbol",
            "officer_name",
            "deal_action",
            "deal_announce_date",
            name="uq_insider_trading_record",
        ),
    )
    op.create_index(
        "ix_insider_trading_symbol",
        "insider_trading",
        ["symbol"],
    )
    op.create_index(
        "ix_insider_trading_officer_name",
        "insider_trading",
        ["officer_name"],
    )
    op.create_index(
        "ix_insider_trading_deal_announce_date",
        "insider_trading",
        ["deal_announce_date"],
    )

    # 4. capital_history table
    op.create_table(
        "capital_history",
        sa.Column(
            "id",
            sa.Uuid(),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("symbol", AutoString(length=20), nullable=False),
        sa.Column("issue_date", sa.Date(), nullable=True),
        sa.Column("charter_capital", sa.Float(), nullable=True),
        sa.Column("shares_issued", sa.Float(), nullable=True),
        sa.Column("description", AutoString(length=500), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["symbol"],
            ["stock_symbol.symbol"],
            name="fk_capital_history_symbol",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "symbol",
            "issue_date",
            "charter_capital",
            name="uq_capital_history_record",
        ),
    )
    op.create_index(
        "ix_capital_history_symbol",
        "capital_history",
        ["symbol"],
    )
    op.create_index(
        "ix_capital_history_issue_date",
        "capital_history",
        ["issue_date"],
    )


def downgrade() -> None:
    op.drop_table("capital_history")
    op.drop_table("insider_trading")
    op.drop_table("company_subsidiary")
    op.drop_column("financial_ratio", "data")
    op.drop_column("company_profile", "auditor")
    op.drop_column("company_profile", "ceo_name")
