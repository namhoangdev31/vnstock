"""Add durable idempotency key for daemon-generated paper orders."""

from alembic import op
import sqlalchemy as sa


revision = "o1a2b3c4d5e6"
down_revision = "k1l2m3n4o5p6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("simulation_order")}
    if "source_signal_id" not in columns:
        op.add_column(
            "simulation_order",
            sa.Column("source_signal_id", sa.String(length=100), nullable=True),
        )
    indexes = {index["name"] for index in inspector.get_indexes("simulation_order")}
    if "ix_simulation_order_source_signal_id" not in indexes:
        op.create_index(
            "ix_simulation_order_source_signal_id",
            "simulation_order",
            ["source_signal_id"],
        )
    constraints = {
        constraint["name"]
        for constraint in inspector.get_unique_constraints("simulation_order")
    }
    if "uq_order_signal" not in constraints:
        op.create_unique_constraint(
            "uq_order_signal", "simulation_order", ["portfolio_id", "source_signal_id"]
        )


def downgrade() -> None:
    op.drop_constraint("uq_order_signal", "simulation_order", type_="unique")
    op.drop_index("ix_simulation_order_source_signal_id", table_name="simulation_order")
    op.drop_column("simulation_order", "source_signal_id")

