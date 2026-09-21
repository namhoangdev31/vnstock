"""create screener snapshot and screener snapshot historical tables

Revision ID: k1a2b3c4d5e6
Revises: j1a2b3c4d5e6
Create Date: 2026-09-21
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "k1a2b3c4d5e6"
down_revision = "j1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"
    uuid_type = postgresql.UUID(as_uuid=True) if is_postgres else sa.Uuid()

    # 1. Bảng screener_snapshot (snapshot hiện tại)
    op.create_table(
        "screener_snapshot",
        sa.Column("instrument_id", uuid_type, sa.ForeignKey("instrument.id"), primary_key=True, nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False, index=True),
        sa.Column("symbol", sa.String(length=20), nullable=False, index=True),
        sa.Column("exchange", sa.String(length=20), nullable=False, index=True),
        sa.Column("industry", sa.String(length=100), nullable=True, index=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True, index=True),
        sa.Column("version", sa.Integer(), nullable=False, default=1),
        # 1. Định giá (Valuation)
        sa.Column("pe", sa.Float(), nullable=True),
        sa.Column("pb", sa.Float(), nullable=True),
        sa.Column("ps", sa.Float(), nullable=True),
        sa.Column("ev_to_ebitda", sa.Float(), nullable=True),
        sa.Column("dividend_yield", sa.Float(), nullable=True),
        # 2. Sinh lời (Profitability)
        sa.Column("roe", sa.Float(), nullable=True),
        sa.Column("roa", sa.Float(), nullable=True),
        sa.Column("roic", sa.Float(), nullable=True),
        sa.Column("gross_margin", sa.Float(), nullable=True),
        sa.Column("net_margin", sa.Float(), nullable=True),
        # 3. Tăng trưởng (Growth)
        sa.Column("revenue_growth_yoy", sa.Float(), nullable=True),
        sa.Column("profit_growth_yoy", sa.Float(), nullable=True),
        sa.Column("revenue_growth_qoq", sa.Float(), nullable=True),
        sa.Column("profit_growth_qoq", sa.Float(), nullable=True),
        # 4. Sức khỏe tài chính & Đòn bẩy (Leverage & Liquidity)
        sa.Column("debt_to_equity", sa.Float(), nullable=True),
        sa.Column("current_ratio", sa.Float(), nullable=True),
        sa.Column("quick_ratio", sa.Float(), nullable=True),
        sa.Column("interest_coverage", sa.Float(), nullable=True),
        # 5. Kỹ thuật & Giá (Technical & Price Momentum)
        sa.Column("price", sa.Float(), nullable=True),
        sa.Column("change_pct", sa.Float(), nullable=True),
        sa.Column("volume_ma20", sa.Float(), nullable=True),
        sa.Column("rsi_14", sa.Float(), nullable=True),
        sa.Column("macd_histogram", sa.Float(), nullable=True),
        sa.Column("bollinger_bandwidth", sa.Float(), nullable=True),
        # 6. Dòng tiền & Thanh khoản (Institutional Flow & Liquidity)
        sa.Column("foreign_net_val_5d", sa.Float(), nullable=True),
        sa.Column("foreign_room_pct", sa.Float(), nullable=True),
        sa.Column("t2_pressure_score", sa.Float(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # Partial indexes for ScreenerSnapshot with exact ordering to prevent TEMP B-TREE sorts
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


    # 2. Bảng screener_snapshot_historical (lịch sử snapshot Point-in-Time)
    op.create_table(
        "screener_snapshot_historical",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("instrument_id", uuid_type, sa.ForeignKey("instrument.id"), nullable=False, index=True),
        sa.Column("snapshot_date", sa.Date(), nullable=False, index=True),
        sa.Column("symbol", sa.String(length=20), nullable=False, index=True),
        sa.Column("exchange", sa.String(length=20), nullable=False, index=True),
        sa.Column("industry", sa.String(length=100), nullable=True, index=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True, index=True),
        sa.Column("version", sa.Integer(), nullable=False, default=1),
        # 1. Định giá (Valuation)
        sa.Column("pe", sa.Float(), nullable=True),
        sa.Column("pb", sa.Float(), nullable=True),
        sa.Column("ps", sa.Float(), nullable=True),
        sa.Column("ev_to_ebitda", sa.Float(), nullable=True),
        sa.Column("dividend_yield", sa.Float(), nullable=True),
        # 2. Sinh lời (Profitability)
        sa.Column("roe", sa.Float(), nullable=True),
        sa.Column("roa", sa.Float(), nullable=True),
        sa.Column("roic", sa.Float(), nullable=True),
        sa.Column("gross_margin", sa.Float(), nullable=True),
        sa.Column("net_margin", sa.Float(), nullable=True),
        # 3. Tăng trưởng (Growth)
        sa.Column("revenue_growth_yoy", sa.Float(), nullable=True),
        sa.Column("profit_growth_yoy", sa.Float(), nullable=True),
        sa.Column("revenue_growth_qoq", sa.Float(), nullable=True),
        sa.Column("profit_growth_qoq", sa.Float(), nullable=True),
        # 4. Sức khỏe tài chính & Đòn bẩy (Leverage & Liquidity)
        sa.Column("debt_to_equity", sa.Float(), nullable=True),
        sa.Column("current_ratio", sa.Float(), nullable=True),
        sa.Column("quick_ratio", sa.Float(), nullable=True),
        sa.Column("interest_coverage", sa.Float(), nullable=True),
        # 5. Kỹ thuật & Giá (Technical & Price Momentum)
        sa.Column("price", sa.Float(), nullable=True),
        sa.Column("change_pct", sa.Float(), nullable=True),
        sa.Column("volume_ma20", sa.Float(), nullable=True),
        sa.Column("rsi_14", sa.Float(), nullable=True),
        sa.Column("macd_histogram", sa.Float(), nullable=True),
        sa.Column("bollinger_bandwidth", sa.Float(), nullable=True),
        # 6. Dòng tiền & Thanh khoản (Institutional Flow & Liquidity)
        sa.Column("foreign_net_val_5d", sa.Float(), nullable=True),
        sa.Column("foreign_room_pct", sa.Float(), nullable=True),
        sa.Column("t2_pressure_score", sa.Float(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("as_of", sa.DateTime(timezone=True), nullable=False, default=sa.func.now(), index=True),
        sa.UniqueConstraint("snapshot_date", "instrument_id", "as_of", name="uq_screener_hist_date_instrument_as_of"),
    )

    op.create_index(
        "ix_screener_hist_date_roe",
        "screener_snapshot_historical",
        ["snapshot_date", "roe"],
    )
    op.create_index(
        "ix_screener_hist_inst_as_of",
        "screener_snapshot_historical",
        ["instrument_id", "as_of"],
    )


def downgrade() -> None:
    op.drop_index("ix_screener_hist_inst_as_of", table_name="screener_snapshot_historical")
    op.drop_index("ix_screener_hist_date_roe", table_name="screener_snapshot_historical")
    op.drop_table("screener_snapshot_historical")
    op.drop_index("ix_screener_snapshot_pe_inst", table_name="screener_snapshot")
    op.drop_index("ix_screener_snapshot_roe_inst", table_name="screener_snapshot")
    op.drop_table("screener_snapshot")
