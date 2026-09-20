"""add covered warrant and bond specification tables

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-09-21
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. covered_warrant table
    op.create_table(
        "covered_warrant",
        sa.Column(
            "id",
            sa.Uuid(),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("underlying_symbol", sa.String(length=20), nullable=False),
        sa.Column("issuer_name", sa.String(length=255), nullable=True),
        sa.Column(
            "warrant_type",
            sa.String(length=10),
            nullable=False,
            server_default="call",
        ),
        sa.Column("exercise_price", sa.Float(), nullable=True),
        sa.Column("conversion_ratio", sa.String(length=20), nullable=True),
        sa.Column("exercise_ratio", sa.Float(), nullable=True),
        sa.Column("issue_date", sa.Date(), nullable=True),
        sa.Column("maturity_date", sa.Date(), nullable=True),
        sa.Column("last_trading_date", sa.Date(), nullable=True),
        sa.Column(
            "settlement_type",
            sa.String(length=20),
            nullable=True,
            server_default="cash",
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
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
            name="fk_covered_warrant_symbol",
        ),
        sa.ForeignKeyConstraint(
            ["underlying_symbol"],
            ["stock_symbol.symbol"],
            name="fk_covered_warrant_underlying_symbol",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("symbol", name="uq_covered_warrant_symbol"),
    )
    op.create_index(
        "ix_covered_warrant_symbol", "covered_warrant", ["symbol"], unique=True
    )
    op.create_index(
        "ix_covered_warrant_underlying_symbol",
        "covered_warrant",
        ["underlying_symbol"],
    )
    op.create_index(
        "ix_covered_warrant_maturity_date", "covered_warrant", ["maturity_date"]
    )

    # 2. bond_specification table
    op.create_table(
        "bond_specification",
        sa.Column(
            "id",
            sa.Uuid(),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("bond_type", sa.String(length=20), nullable=False),
        sa.Column("issuer_symbol", sa.String(length=20), nullable=True),
        sa.Column("issuer_name", sa.String(length=255), nullable=True),
        sa.Column(
            "par_value",
            sa.Float(),
            nullable=False,
            server_default="100000.0",
        ),
        sa.Column("coupon_rate", sa.Float(), nullable=True),
        sa.Column(
            "coupon_type",
            sa.String(length=20),
            nullable=True,
            server_default="fixed",
        ),
        sa.Column("tenor_years", sa.Float(), nullable=True),
        sa.Column("issue_date", sa.Date(), nullable=True),
        sa.Column("maturity_date", sa.Date(), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
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
            name="fk_bond_specification_symbol",
        ),
        sa.ForeignKeyConstraint(
            ["issuer_symbol"],
            ["stock_symbol.symbol"],
            name="fk_bond_specification_issuer_symbol",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("symbol", name="uq_bond_specification_symbol"),
    )
    op.create_index(
        "ix_bond_specification_symbol",
        "bond_specification",
        ["symbol"],
        unique=True,
    )
    op.create_index(
        "ix_bond_specification_bond_type",
        "bond_specification",
        ["bond_type"],
    )
    op.create_index(
        "ix_bond_specification_issuer_symbol",
        "bond_specification",
        ["issuer_symbol"],
    )
    op.create_index(
        "ix_bond_specification_maturity_date",
        "bond_specification",
        ["maturity_date"],
    )


def downgrade() -> None:
    op.drop_table("bond_specification")
    op.drop_table("covered_warrant")
