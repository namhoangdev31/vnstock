"""add missing schema columns for instrument, screener_snapshot_historical, and tick_flow_aggregated

Revision ID: n1a2b3c4d5e6
Revises: m1a2b3c4d5e6
Create Date: 2026-09-21 17:42:00
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "n1a2b3c4d5e6"
down_revision: Union[str, None] = "m1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)

    # 1. instrument table: roll_rule column
    inst_cols = {c["name"] for c in insp.get_columns("instrument")}
    if "roll_rule" not in inst_cols:
        op.add_column(
            "instrument",
            sa.Column("roll_rule", sa.String(length=100), nullable=True),
        )

    # 2. screener_snapshot_historical: as_of column
    hist_cols = {c["name"] for c in insp.get_columns("screener_snapshot_historical")}
    if "as_of" not in hist_cols:
        op.add_column(
            "screener_snapshot_historical",
            sa.Column(
                "as_of",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
        )
        op.create_index(
            "ix_screener_snapshot_historical_as_of",
            "screener_snapshot_historical",
            ["as_of"],
        )
        op.create_index(
            "ix_screener_hist_inst_as_of",
            "screener_snapshot_historical",
            ["instrument_id", "as_of"],
        )

    # 3. tick_flow_aggregated table: interval_start, open, high, low, close, volume
    if "tick_flow_aggregated" in insp.get_table_names():
        tick_cols = {c["name"] for c in insp.get_columns("tick_flow_aggregated")}
        if "timestamp" in tick_cols and "interval_start" not in tick_cols:
            op.alter_column(
                "tick_flow_aggregated",
                "timestamp",
                new_column_name="interval_start",
            )
        elif "interval_start" not in tick_cols:
            op.add_column(
                "tick_flow_aggregated",
                sa.Column(
                    "interval_start",
                    sa.DateTime(timezone=True),
                    server_default=sa.text("now()"),
                    nullable=False,
                ),
            )

        for col_name, col_type in [
            ("open", sa.Float()),
            ("high", sa.Float()),
            ("low", sa.Float()),
            ("close", sa.Float()),
            ("volume", sa.Integer()),
        ]:
            if col_name not in tick_cols:
                op.add_column(
                    "tick_flow_aggregated",
                    sa.Column(
                        col_name,
                        col_type,
                        server_default=sa.text("0"),
                        nullable=False,
                    ),
                )


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)

    # 1. instrument
    inst_cols = {c["name"] for c in insp.get_columns("instrument")}
    if "roll_rule" in inst_cols:
        op.drop_column("instrument", "roll_rule")

    # 2. screener_snapshot_historical
    hist_cols = {c["name"] for c in insp.get_columns("screener_snapshot_historical")}
    if "as_of" in hist_cols:
        op.drop_index("ix_screener_hist_inst_as_of", table_name="screener_snapshot_historical")
        op.drop_index("ix_screener_snapshot_historical_as_of", table_name="screener_snapshot_historical")
        op.drop_column("screener_snapshot_historical", "as_of")

    # 3. tick_flow_aggregated
    if "tick_flow_aggregated" in insp.get_table_names():
        tick_cols = {c["name"] for c in insp.get_columns("tick_flow_aggregated")}
        for col_name in ["open", "high", "low", "close", "volume"]:
            if col_name in tick_cols:
                op.drop_column("tick_flow_aggregated", col_name)
        if "interval_start" in tick_cols:
            op.alter_column(
                "tick_flow_aggregated",
                "interval_start",
                new_column_name="timestamp",
            )
