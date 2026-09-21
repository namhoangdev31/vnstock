"""optimize screener snapshot partial composite indexes

Revision ID: m1a2b3c4d5e6
Revises: l1a2b3c4d5e6
Create Date: 2026-09-21
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "m1a2b3c4d5e6"
down_revision = "l1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    # Drop existing indexes from k1
    op.execute("DROP INDEX IF EXISTS ix_screener_snapshot_roe_inst;")
    op.execute("DROP INDEX IF EXISTS ix_screener_snapshot_pe_inst;")

    if is_postgres:
        op.execute(
            """
            CREATE INDEX ix_screener_snapshot_roe_inst
            ON screener_snapshot (roe DESC NULLS LAST, instrument_id ASC)
            WHERE is_active = true;
            """
        )
        op.execute(
            """
            CREATE INDEX ix_screener_snapshot_pe_inst
            ON screener_snapshot (pe ASC NULLS LAST, instrument_id ASC)
            WHERE is_active = true;
            """
        )
    else:
        op.execute(
            """
            CREATE INDEX ix_screener_snapshot_roe_inst
            ON screener_snapshot (roe DESC, instrument_id ASC)
            WHERE is_active = 1;
            """
        )
        op.execute(
            """
            CREATE INDEX ix_screener_snapshot_pe_inst
            ON screener_snapshot (pe ASC, instrument_id ASC)
            WHERE is_active = 1;
            """
        )


def downgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    op.execute("DROP INDEX IF EXISTS ix_screener_snapshot_roe_inst;")
    op.execute("DROP INDEX IF EXISTS ix_screener_snapshot_pe_inst;")

    if is_postgres:
        op.create_index(
            "ix_screener_snapshot_roe_inst",
            "screener_snapshot",
            ["roe", "instrument_id"],
            postgresql_where=sa.text("is_active = true"),
        )
        op.create_index(
            "ix_screener_snapshot_pe_inst",
            "screener_snapshot",
            ["pe", "instrument_id"],
            postgresql_where=sa.text("is_active = true"),
        )
    else:
        op.create_index(
            "ix_screener_snapshot_roe_inst",
            "screener_snapshot",
            ["roe", "instrument_id"],
            sqlite_where=sa.text("is_active = 1"),
        )
        op.create_index(
            "ix_screener_snapshot_pe_inst",
            "screener_snapshot",
            ["pe", "instrument_id"],
            sqlite_where=sa.text("is_active = 1"),
        )
