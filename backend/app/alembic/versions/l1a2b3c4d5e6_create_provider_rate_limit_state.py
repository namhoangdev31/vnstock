"""create provider_rate_limit_state table

Revision ID: l1a2b3c4d5e6
Revises: k1a2b3c4d5e6
Create Date: 2026-09-21
"""

from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa
from app.cron.scheduler import VN_TZ
# revision identifiers, used by Alembic.
revision = "l1a2b3c4d5e6"
down_revision = "k1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "provider_rate_limit_state",
        sa.Column("provider", sa.String(length=20), primary_key=True, nullable=False),
        sa.Column("last_request_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consecutive_failures", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("circuit_state", sa.String(length=20), nullable=False, server_default="closed"),
        sa.Column("circuit_open_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # Seed initial rows for default providers
    now = datetime.now(VN_TZ)
    provider_table = sa.table(
        "provider_rate_limit_state",
        sa.column("provider", sa.String),
        sa.column("last_request_at", sa.DateTime),
        sa.column("consecutive_failures", sa.Integer),
        sa.column("circuit_state", sa.String),
        sa.column("circuit_open_until", sa.DateTime),
        sa.column("updated_at", sa.DateTime),
    )

    op.bulk_insert(
        provider_table,
        [
            {
                "provider": p,
                "last_request_at": now,
                "consecutive_failures": 0,
                "circuit_state": "closed",
                "circuit_open_until": None,
                "updated_at": now,
            }
            for p in ["VCI", "KBS", "MSN", "TCBS"]
        ],
    )


def downgrade() -> None:
    op.drop_table("provider_rate_limit_state")
