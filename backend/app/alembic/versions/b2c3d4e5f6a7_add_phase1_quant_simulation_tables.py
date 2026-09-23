"""add phase 1 quant & simulation tables

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-09-17
"""

import sqlalchemy as sa
from alembic import op
from sqlmodel.sql.sqltypes import AutoString

from app.core.models_base import JSONBVariant

# revision identifiers, used by Alembic.
revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- forecast_journal (RULE 3 audit ledger) ---
    op.create_table(
        "forecast_journal",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("symbol", AutoString(length=20), nullable=False),
        sa.Column(
            "horizon",
            AutoString(length=20),
            nullable=False,
            server_default="T_PLUS_1",
        ),
        sa.Column("predicted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("predicted_value", sa.Float(), nullable=True),
        sa.Column(
            "predicted_direction",
            AutoString(length=10),
            nullable=False,
            server_default="NEUTRAL",
        ),
        sa.Column("engine_weights", JSONBVariant, nullable=False),
        sa.Column("model_version", AutoString(length=40), nullable=False),
        sa.Column("parameter_snapshot", JSONBVariant, nullable=False),
        sa.Column("actual_value", sa.Float(), nullable=True),
        sa.Column("actual_direction", AutoString(length=10), nullable=True),
        sa.Column("realized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Float(), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column(
            "status",
            AutoString(length=10),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "symbol", "horizon", "predicted_at", name="uq_forecast_journal_signal"
        ),
    )
    op.create_index(
        "ix_forecast_journal_symbol", "forecast_journal", ["symbol"]
    )
    op.create_index(
        "ix_forecast_journal_predicted_at", "forecast_journal", ["predicted_at"]
    )
    op.create_index(
        "ix_forecast_journal_status", "forecast_journal", ["status"]
    )

    # --- macro_indicator ---
    op.create_table(
        "macro_indicator",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("recorded_date", sa.Date(), nullable=False),
        sa.Column("indicator_code", AutoString(length=30), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("change_pct", sa.Float(), nullable=True),
        sa.Column("source", AutoString(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "indicator_code",
            "recorded_date",
            "source",
            name="uq_macro_indicator",
        ),
    )
    op.create_index(
        "ix_macro_indicator_recorded_date", "macro_indicator", ["recorded_date"]
    )
    op.create_index(
        "ix_macro_indicator_indicator_code", "macro_indicator", ["indicator_code"]
    )

    # --- tick_flow_aggregated ---
    op.create_table(
        "tick_flow_aggregated",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("symbol", AutoString(length=20), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "aggressive_buy_volume",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "aggressive_sell_volume",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "volume_delta", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "trade_count", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column("vwap", sa.Float(), nullable=True),
        sa.Column("source", AutoString(length=20), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "symbol", "timestamp", name="uq_tick_flow_aggregated"
        ),
    )
    op.create_index(
        "ix_tick_flow_aggregated_symbol", "tick_flow_aggregated", ["symbol"]
    )
    op.create_index(
        "ix_tick_flow_aggregated_timestamp", "tick_flow_aggregated", ["timestamp"]
    )

    # --- institutional_flow (schema only — no Phase 1 sync source) ---
    op.create_table(
        "institutional_flow",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("trading_date", sa.Date(), nullable=False),
        sa.Column("symbol", AutoString(length=20), nullable=False),
        sa.Column("foreign_buy_value", sa.Float(), nullable=True),
        sa.Column("foreign_sell_value", sa.Float(), nullable=True),
        sa.Column("foreign_net_value", sa.Float(), nullable=True),
        sa.Column("prop_buy_value", sa.Float(), nullable=True),
        sa.Column("prop_sell_value", sa.Float(), nullable=True),
        sa.Column("prop_net_value", sa.Float(), nullable=True),
        sa.Column("source", AutoString(length=20), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "trading_date", "symbol", "source", name="uq_institutional_flow"
        ),
    )
    op.create_index(
        "ix_institutional_flow_trading_date", "institutional_flow", ["trading_date"]
    )
    op.create_index(
        "ix_institutional_flow_symbol", "institutional_flow", ["symbol"]
    )

    # --- market_breadth (schema only — no Phase 1 sync source) ---
    op.create_table(
        "market_breadth",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("trading_date", sa.Date(), nullable=False),
        sa.Column("exchange", AutoString(length=10), nullable=False),
        sa.Column(
            "advancers", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "decliners", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "unchanged", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "ceiling_count", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "floor_count", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "total_volume", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "total_value", sa.Float(), nullable=False, server_default=sa.text("0")
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "trading_date", "exchange", name="uq_market_breadth"
        ),
    )
    op.create_index(
        "ix_market_breadth_trading_date", "market_breadth", ["trading_date"]
    )

    # --- simulation_portfolio (RULE 1/2: isolated paper account) ---
    op.create_table(
        "simulation_portfolio",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", AutoString(length=255), nullable=False),
        sa.Column(
            "initial_balance",
            sa.Float(),
            nullable=False,
            server_default=sa.text("100000000.0"),
        ),
        sa.Column(
            "cash_balance",
            sa.Float(),
            nullable=False,
            server_default=sa.text("100000000.0"),
        ),
        sa.Column(
            "equity", sa.Float(), nullable=False, server_default=sa.text("100000000.0")
        ),
        sa.Column(
            "margin_used", sa.Float(), nullable=False, server_default=sa.text("0.0")
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["user.id"], ondelete="CASCADE"
        ),
    )
    op.create_index(
        "ix_simulation_portfolio_user_id", "simulation_portfolio", ["user_id"]
    )

    # --- simulation_order ---
    op.create_table(
        "simulation_order",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("portfolio_id", sa.Uuid(), nullable=False),
        sa.Column("symbol", AutoString(length=20), nullable=False),
        sa.Column("side", AutoString(length=10), nullable=False, server_default="BUY"),
        sa.Column(
            "order_type",
            AutoString(length=10),
            nullable=False,
            server_default="MARKET",
        ),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("stop_price", sa.Float(), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column(
            "filled_quantity",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("filled_price", sa.Float(), nullable=True),
        sa.Column("fee", sa.Float(), nullable=False, server_default=sa.text("0.0")),
        sa.Column("tax", sa.Float(), nullable=False, server_default=sa.text("0.0")),
        sa.Column(
            "status",
            AutoString(length=10),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("reject_reason", AutoString(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["portfolio_id"], ["simulation_portfolio.id"], ondelete="CASCADE"
        ),
    )
    op.create_index(
        "ix_simulation_order_portfolio_id", "simulation_order", ["portfolio_id"]
    )
    op.create_index("ix_simulation_order_symbol", "simulation_order", ["symbol"])
    op.create_index("ix_simulation_order_status", "simulation_order", ["status"])

    # --- simulation_position ---
    op.create_table(
        "simulation_position",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("portfolio_id", sa.Uuid(), nullable=False),
        sa.Column("symbol", AutoString(length=20), nullable=False),
        sa.Column(
            "side", AutoString(length=10), nullable=False, server_default="LONG"
        ),
        sa.Column(
            "quantity", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "entry_price", sa.Float(), nullable=False, server_default=sa.text("0.0")
        ),
        sa.Column(
            "current_price", sa.Float(), nullable=False, server_default=sa.text("0.0")
        ),
        sa.Column(
            "unrealized_pnl", sa.Float(), nullable=False, server_default=sa.text("0.0")
        ),
        sa.Column(
            "realized_pnl", sa.Float(), nullable=False, server_default=sa.text("0.0")
        ),
        sa.Column(
            "margin_required", sa.Float(), nullable=False, server_default=sa.text("0.0")
        ),
        sa.Column("settlement_date", sa.Date(), nullable=True),
        sa.Column(
            "status", AutoString(length=10), nullable=False, server_default="OPEN"
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["portfolio_id"], ["simulation_portfolio.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint(
            "portfolio_id", "symbol", "side", name="uq_position_symbol"
        ),
    )
    op.create_index(
        "ix_simulation_position_portfolio_id",
        "simulation_position",
        ["portfolio_id"],
    )
    op.create_index(
        "ix_simulation_position_symbol", "simulation_position", ["symbol"]
    )
    op.create_index(
        "ix_simulation_position_status", "simulation_position", ["status"]
    )

    # --- simulation_trade ---
    op.create_table(
        "simulation_trade",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("portfolio_id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=True),
        sa.Column("symbol", AutoString(length=20), nullable=False),
        sa.Column("side", AutoString(length=10), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("fee", sa.Float(), nullable=False, server_default=sa.text("0.0")),
        sa.Column("tax", sa.Float(), nullable=False, server_default=sa.text("0.0")),
        sa.Column(
            "realized_pnl", sa.Float(), nullable=False, server_default=sa.text("0.0")
        ),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["portfolio_id"], ["simulation_portfolio.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["order_id"], ["simulation_order.id"]),
    )
    op.create_index(
        "ix_simulation_trade_portfolio_id", "simulation_trade", ["portfolio_id"]
    )
    op.create_index("ix_simulation_trade_order_id", "simulation_trade", ["order_id"])
    op.create_index("ix_simulation_trade_symbol", "simulation_trade", ["symbol"])


def downgrade() -> None:
    op.drop_index("ix_simulation_trade_symbol", table_name="simulation_trade")
    op.drop_index("ix_simulation_trade_order_id", table_name="simulation_trade")
    op.drop_index("ix_simulation_trade_portfolio_id", table_name="simulation_trade")
    op.drop_table("simulation_trade")
    op.drop_index("ix_simulation_position_status", table_name="simulation_position")
    op.drop_index("ix_simulation_position_symbol", table_name="simulation_position")
    op.drop_index(
        "ix_simulation_position_portfolio_id", table_name="simulation_position"
    )
    op.drop_table("simulation_position")
    op.drop_index("ix_simulation_order_status", table_name="simulation_order")
    op.drop_index("ix_simulation_order_symbol", table_name="simulation_order")
    op.drop_index("ix_simulation_order_portfolio_id", table_name="simulation_order")
    op.drop_table("simulation_order")
    op.drop_index(
        "ix_simulation_portfolio_user_id", table_name="simulation_portfolio"
    )
    op.drop_table("simulation_portfolio")
    op.drop_index("ix_market_breadth_trading_date", table_name="market_breadth")
    op.drop_table("market_breadth")
    op.drop_index("ix_institutional_flow_symbol", table_name="institutional_flow")
    op.drop_index(
        "ix_institutional_flow_trading_date", table_name="institutional_flow"
    )
    op.drop_table("institutional_flow")
    op.drop_index(
        "ix_tick_flow_aggregated_timestamp", table_name="tick_flow_aggregated"
    )
    op.drop_index("ix_tick_flow_aggregated_symbol", table_name="tick_flow_aggregated")
    op.drop_table("tick_flow_aggregated")
    op.drop_index("ix_macro_indicator_indicator_code", table_name="macro_indicator")
    op.drop_index("ix_macro_indicator_recorded_date", table_name="macro_indicator")
    op.drop_table("macro_indicator")
    op.drop_index("ix_forecast_journal_status", table_name="forecast_journal")
    op.drop_index("ix_forecast_journal_predicted_at", table_name="forecast_journal")
    op.drop_index("ix_forecast_journal_symbol", table_name="forecast_journal")
    op.drop_table("forecast_journal")
