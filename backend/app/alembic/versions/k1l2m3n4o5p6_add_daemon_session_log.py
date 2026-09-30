"""Add daemon_session_log table for Phase 3 daemon lifecycle tracking

Revision ID: k1l2m3n4o5p6
Revises: c3d4e5f6a7b8
Create Date: 2026-09-30 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "k1l2m3n4o5p6"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "daemon_session_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("daemon_name", sqlmodel.sql.sqltypes.AutoString(length=80), nullable=False),
        sa.Column("instance_id", sqlmodel.sql.sqltypes.AutoString(length=80), nullable=False),
        sa.Column("status", sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("stopped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_phase", sqlmodel.sql.sqltypes.AutoString(length=40), nullable=True),
        sa.Column("cycle_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failure_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
        sa.Column("metadata_info", postgresql.JSONB(), nullable=True),
    )

    op.create_index(
        "ix_daemon_session_log_daemon_name",
        "daemon_session_log",
        ["daemon_name"]
    )
    op.create_index(
        "ix_daemon_session_log_instance_id",
        "daemon_session_log",
        ["instance_id"]
    )
    op.create_index(
        "ix_daemon_session_log_status",
        "daemon_session_log",
        ["status"]
    )
    op.create_index(
        "ix_daemon_session_log_started_at",
        "daemon_session_log",
        ["started_at"]
    )
    op.create_index(
        "ix_daemon_session_log_status_phase",
        "daemon_session_log",
        ["status", "last_phase"]
    )


def downgrade() -> None:
    op.drop_index("ix_daemon_session_log_status_phase", table_name="daemon_session_log")
    op.drop_index("ix_daemon_session_log_started_at", table_name="daemon_session_log")
    op.drop_index("ix_daemon_session_log_status", table_name="daemon_session_log")
    op.drop_index("ix_daemon_session_log_instance_id", table_name="daemon_session_log")
    op.drop_index("ix_daemon_session_log_daemon_name", table_name="daemon_session_log")
    op.drop_table("daemon_session_log")
