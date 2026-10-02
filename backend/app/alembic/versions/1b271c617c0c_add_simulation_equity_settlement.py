"""add_simulation_equity_settlement

Revision ID: 1b271c617c0c
Revises: o1a2b3c4d5e6
Create Date: 2026-10-02 11:22:55.357837

"""

from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes

# revision identifiers, used by Alembic.
revision = "1b271c617c0c"
down_revision = "o1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "simulation_equity_settlement",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("portfolio_id", sa.Uuid(), nullable=False),
        sa.Column("symbol", sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
        sa.Column("side", sqlmodel.sql.sqltypes.AutoString(length=10), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("bought_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("settlement_due", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["portfolio_id"], ["simulation_portfolio.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_simulation_equity_settlement_portfolio_id"),
        "simulation_equity_settlement",
        ["portfolio_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_simulation_equity_settlement_settlement_due"),
        "simulation_equity_settlement",
        ["settlement_due"],
        unique=False,
    )
    op.create_index(
        op.f("ix_simulation_equity_settlement_status"),
        "simulation_equity_settlement",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_simulation_equity_settlement_symbol"),
        "simulation_equity_settlement",
        ["symbol"],
        unique=False,
    )


def downgrade():
    op.drop_index(
        op.f("ix_simulation_equity_settlement_symbol"),
        table_name="simulation_equity_settlement",
    )
    op.drop_index(
        op.f("ix_simulation_equity_settlement_status"),
        table_name="simulation_equity_settlement",
    )
    op.drop_index(
        op.f("ix_simulation_equity_settlement_settlement_due"),
        table_name="simulation_equity_settlement",
    )
    op.drop_index(
        op.f("ix_simulation_equity_settlement_portfolio_id"),
        table_name="simulation_equity_settlement",
    )
    op.drop_table("simulation_equity_settlement")
