"""add uuid id to master stock tables

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-09-21
"""

import sqlalchemy as sa
from alembic import op

revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "stock_symbol",
        sa.Column(
            "id",
            sa.Uuid(),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
    )
    op.create_index("ix_stock_symbol_id", "stock_symbol", ["id"], unique=True)

    op.add_column(
        "company_profile",
        sa.Column(
            "id",
            sa.Uuid(),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
    )
    op.create_index(
        "ix_company_profile_id", "company_profile", ["id"], unique=True
    )

    op.add_column(
        "derivative_contract",
        sa.Column(
            "id",
            sa.Uuid(),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
    )
    op.create_index(
        "ix_derivative_contract_id", "derivative_contract", ["id"], unique=True
    )


def downgrade() -> None:
    op.drop_index("ix_derivative_contract_id", table_name="derivative_contract")
    op.drop_column("derivative_contract", "id")

    op.drop_index("ix_company_profile_id", table_name="company_profile")
    op.drop_column("company_profile", "id")

    op.drop_index("ix_stock_symbol_id", table_name="stock_symbol")
    op.drop_column("stock_symbol", "id")
