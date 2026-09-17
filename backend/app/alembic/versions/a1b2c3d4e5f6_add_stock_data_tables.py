"""add stock data tables

Revision ID: a1b2c3d4e5f6
Revises: fe56fa70289e
Create Date: 2026-09-17
"""

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = "fe56fa70289e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # stock_symbol
    op.create_table(
        "stock_symbol",
        sa.Column("symbol", sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
        sa.Column("organ_name", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
        sa.Column("exchange", sqlmodel.sql.sqltypes.AutoString(length=10), nullable=True),
        sa.Column("industry", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True),
        sa.Column("asset_type", sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("symbol"),
    )

    # stock_ohlcv_daily
    op.create_table(
        "stock_ohlcv_daily",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("symbol", sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
        sa.Column("trading_date", sa.Date(), nullable=False),
        sa.Column("open", sa.Float(), nullable=False),
        sa.Column("high", sa.Float(), nullable=False),
        sa.Column("low", sa.Float(), nullable=False),
        sa.Column("close", sa.Float(), nullable=False),
        sa.Column("volume", sa.Integer(), nullable=False),
        sa.Column("value", sa.Float(), nullable=True),
        sa.Column("source", sqlmodel.sql.sqltypes.AutoString(length=10), nullable=False),
        sa.ForeignKeyConstraint(["symbol"], ["stock_symbol.symbol"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("symbol", "trading_date"),
    )
    op.create_index("ix_stock_ohlcv_daily_symbol", "stock_ohlcv_daily", ["symbol"])
    op.create_index("ix_stock_ohlcv_daily_trading_date", "stock_ohlcv_daily", ["trading_date"])

    # stock_ohlcv_intraday
    op.create_table(
        "stock_ohlcv_intraday",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("symbol", sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("interval", sqlmodel.sql.sqltypes.AutoString(length=5), nullable=False),
        sa.Column("open", sa.Float(), nullable=False),
        sa.Column("high", sa.Float(), nullable=False),
        sa.Column("low", sa.Float(), nullable=False),
        sa.Column("close", sa.Float(), nullable=False),
        sa.Column("volume", sa.Integer(), nullable=False),
        sa.Column("source", sqlmodel.sql.sqltypes.AutoString(length=10), nullable=False),
        sa.ForeignKeyConstraint(["symbol"], ["stock_symbol.symbol"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("symbol", "timestamp", "interval"),
    )
    op.create_index("ix_stock_ohlcv_intraday_symbol", "stock_ohlcv_intraday", ["symbol"])
    op.create_index("ix_stock_ohlcv_intraday_timestamp", "stock_ohlcv_intraday", ["timestamp"])

    # company_profile
    op.create_table(
        "company_profile",
        sa.Column("symbol", sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
        sa.Column("company_name", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
        sa.Column("short_name", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
        sa.Column("industry_name", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
        sa.Column("established_date", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("listed_date", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("charter_capital", sa.Float(), nullable=True),
        sa.Column("outstanding_shares", sa.Float(), nullable=True),
        sa.Column("market_cap", sa.Float(), nullable=True),
        sa.Column("website", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
        sa.Column("description", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["symbol"], ["stock_symbol.symbol"]),
        sa.PrimaryKeyConstraint("symbol"),
    )

    # financial_report
    op.create_table(
        "financial_report",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("symbol", sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
        sa.Column("report_type", sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
        sa.Column("period", sqlmodel.sql.sqltypes.AutoString(length=10), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("quarter", sa.Integer(), nullable=True),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("source", sqlmodel.sql.sqltypes.AutoString(length=10), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["symbol"], ["stock_symbol.symbol"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("symbol", "report_type", "period", "year", "quarter"),
    )
    op.create_index("ix_financial_report_symbol", "financial_report", ["symbol"])

    # data_sync_log
    op.create_table(
        "data_sync_log",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("sync_type", sqlmodel.sql.sqltypes.AutoString(length=30), nullable=False),
        sa.Column("symbol", sqlmodel.sql.sqltypes.AutoString(length=20), nullable=True),
        sa.Column("source", sqlmodel.sql.sqltypes.AutoString(length=10), nullable=False),
        sa.Column("status", sqlmodel.sql.sqltypes.AutoString(length=15), nullable=False),
        sa.Column("rows_synced", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("error_message", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("data_sync_log")
    op.drop_table("financial_report")
    op.drop_table("company_profile")
    op.drop_index("ix_stock_ohlcv_intraday_timestamp", table_name="stock_ohlcv_intraday")
    op.drop_index("ix_stock_ohlcv_intraday_symbol", table_name="stock_ohlcv_intraday")
    op.drop_table("stock_ohlcv_intraday")
    op.drop_index("ix_stock_ohlcv_daily_trading_date", table_name="stock_ohlcv_daily")
    op.drop_index("ix_stock_ohlcv_daily_symbol", table_name="stock_ohlcv_daily")
    op.drop_table("stock_ohlcv_daily")
    op.drop_table("stock_symbol")
