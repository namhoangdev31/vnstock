"""add vnstock v4 comprehensive tables & columns

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-09-20
"""

import sqlalchemy as sa
from alembic import op
from sqlmodel.sql.sqltypes import AutoString

from app.models.base import JSONBVariant

# revision identifiers, used by Alembic.
revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # =========================================================================
    # 1. Bổ sung các cột mới vào các bảng Stock hiện có
    # =========================================================================

    # 1.1. stock_symbol
    op.add_column(
        "stock_symbol",
        sa.Column(
            "icb_code",
            AutoString(length=20),
            nullable=True,
        ),
    )
    op.add_column(
        "stock_symbol",
        sa.Column(
            "icb_name",
            AutoString(length=255),
            nullable=True,
        ),
    )
    op.add_column(
        "stock_symbol",
        sa.Column(
            "index_group",
            AutoString(length=50),
            nullable=True,
        ),
    )
    op.add_column(
        "stock_symbol",
        sa.Column(
            "lot_size",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("100"),
        ),
    )

    # 1.2. stock_ohlcv_daily
    op.add_column(
        "stock_ohlcv_daily",
        sa.Column("change", sa.Float(), nullable=True),
    )
    op.add_column(
        "stock_ohlcv_daily",
        sa.Column("change_pct", sa.Float(), nullable=True),
    )
    op.add_column(
        "stock_ohlcv_daily",
        sa.Column("reference_price", sa.Float(), nullable=True),
    )
    op.add_column(
        "stock_ohlcv_daily",
        sa.Column("ceiling_price", sa.Float(), nullable=True),
    )
    op.add_column(
        "stock_ohlcv_daily",
        sa.Column("floor_price", sa.Float(), nullable=True),
    )
    op.add_column(
        "stock_ohlcv_daily",
        sa.Column("adjusted_close", sa.Float(), nullable=True),
    )
    op.add_column(
        "stock_ohlcv_daily",
        sa.Column("buy_volume", sa.Integer(), nullable=True),
    )
    op.add_column(
        "stock_ohlcv_daily",
        sa.Column("sell_volume", sa.Integer(), nullable=True),
    )
    op.add_column(
        "stock_ohlcv_daily",
        sa.Column("foreign_buy_volume", sa.Integer(), nullable=True),
    )
    op.add_column(
        "stock_ohlcv_daily",
        sa.Column("foreign_sell_volume", sa.Integer(), nullable=True),
    )
    op.add_column(
        "stock_ohlcv_daily",
        sa.Column("foreign_net_volume", sa.Integer(), nullable=True),
    )

    # 1.3. stock_ohlcv_intraday
    op.add_column(
        "stock_ohlcv_intraday",
        sa.Column("value", sa.Float(), nullable=True),
    )
    op.add_column(
        "stock_ohlcv_intraday",
        sa.Column("buy_volume", sa.Integer(), nullable=True),
    )
    op.add_column(
        "stock_ohlcv_intraday",
        sa.Column("sell_volume", sa.Integer(), nullable=True),
    )
    op.add_column(
        "stock_ohlcv_intraday",
        sa.Column("volume_delta", sa.Integer(), nullable=True),
    )
    op.add_column(
        "stock_ohlcv_intraday",
        sa.Column("vwap", sa.Float(), nullable=True),
    )

    # 1.4. company_profile
    op.add_column(
        "company_profile",
        sa.Column("free_float_pct", sa.Float(), nullable=True),
    )
    op.add_column(
        "company_profile",
        sa.Column("foreign_ownership_pct", sa.Float(), nullable=True),
    )
    op.add_column(
        "company_profile",
        sa.Column("max_foreign_ownership_pct", sa.Float(), nullable=True),
    )
    op.add_column(
        "company_profile",
        sa.Column("employee_count", sa.Integer(), nullable=True),
    )
    op.add_column(
        "company_profile",
        sa.Column("address", AutoString(length=500), nullable=True),
    )

    # =========================================================================
    # 2. Tạo các bảng mới cho hệ sinh thái vnstock v4
    # =========================================================================

    # 2.1. derivative_contract (Đặc tả hợp đồng phái sinh)
    op.create_table(
        "derivative_contract",
        sa.Column("symbol", AutoString(length=20), nullable=False),
        sa.Column(
            "underlying_symbol",
            AutoString(length=20),
            nullable=False,
            server_default="VN30",
        ),
        sa.Column(
            "multiplier",
            sa.Float(),
            nullable=False,
            server_default="100000.0",
        ),
        sa.Column("first_trading_date", sa.Date(), nullable=True),
        sa.Column("last_trading_date", sa.Date(), nullable=True),
        sa.Column("expiration_date", sa.Date(), nullable=False),
        sa.Column("settlement_price", sa.Float(), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("symbol"),
    )
    op.create_index(
        "ix_derivative_contract_expiration_date",
        "derivative_contract",
        ["expiration_date"],
    )

    # 2.2. stock_tick_intraday (Tick khớp lệnh Quote.intraday)
    op.create_table(
        "stock_tick_intraday",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("symbol", AutoString(length=20), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("volume", sa.Integer(), nullable=False),
        sa.Column("match_type", AutoString(length=10), nullable=False),
        sa.Column("accumulated_volume", sa.Integer(), nullable=True),
        sa.Column("accumulated_value", sa.Float(), nullable=True),
        sa.Column(
            "sequence_number",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("source", AutoString(length=10), nullable=False),
        sa.ForeignKeyConstraint(["symbol"], ["stock_symbol.symbol"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("symbol", "timestamp", "sequence_number"),
    )
    op.create_index(
        "ix_stock_tick_intraday_symbol",
        "stock_tick_intraday",
        ["symbol"],
    )
    op.create_index(
        "ix_stock_tick_intraday_timestamp",
        "stock_tick_intraday",
        ["timestamp"],
    )

    # 2.3. financial_report_item (Chuẩn hóa dòng chỉ tiêu BCTC chi tiết)
    op.create_table(
        "financial_report_item",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("report_id", sa.Uuid(), nullable=False),
        sa.Column("item_code", AutoString(length=100), nullable=False),
        sa.Column("item_name", AutoString(length=255), nullable=False),
        sa.Column("value", sa.Float(), nullable=True),
        sa.Column(
            "order_index",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.ForeignKeyConstraint(["report_id"], ["financial_report.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("report_id", "item_code"),
    )
    op.create_index(
        "ix_financial_report_item_report_id",
        "financial_report_item",
        ["report_id"],
    )
    op.create_index(
        "ix_financial_report_item_item_code",
        "financial_report_item",
        ["item_code"],
    )

    # 2.4. financial_ratio (Chỉ số tài chính P/E, P/B, ROE, ROA, EPS,...)
    op.create_table(
        "financial_ratio",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("symbol", AutoString(length=20), nullable=False),
        sa.Column("period", AutoString(length=10), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("quarter", sa.Integer(), nullable=True),
        sa.Column("pe", sa.Float(), nullable=True),
        sa.Column("pb", sa.Float(), nullable=True),
        sa.Column("ps", sa.Float(), nullable=True),
        sa.Column("roe", sa.Float(), nullable=True),
        sa.Column("roa", sa.Float(), nullable=True),
        sa.Column("roic", sa.Float(), nullable=True),
        sa.Column("eps", sa.Float(), nullable=True),
        sa.Column("bvps", sa.Float(), nullable=True),
        sa.Column("gross_margin", sa.Float(), nullable=True),
        sa.Column("net_margin", sa.Float(), nullable=True),
        sa.Column("debt_to_equity", sa.Float(), nullable=True),
        sa.Column("quick_ratio", sa.Float(), nullable=True),
        sa.Column("current_ratio", sa.Float(), nullable=True),
        sa.Column("dividend_yield", sa.Float(), nullable=True),
        sa.Column("source", AutoString(length=10), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["symbol"], ["stock_symbol.symbol"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("symbol", "period", "year", "quarter"),
    )
    op.create_index(
        "ix_financial_ratio_symbol",
        "financial_ratio",
        ["symbol"],
    )

    # 2.5. corporate_event (Sự kiện doanh nghiệp & cổ tức)
    op.create_table(
        "corporate_event",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("symbol", AutoString(length=20), nullable=False),
        sa.Column("event_type", AutoString(length=30), nullable=False),
        sa.Column("event_title", AutoString(length=500), nullable=False),
        sa.Column("ex_date", sa.Date(), nullable=True),
        sa.Column("record_date", sa.Date(), nullable=True),
        sa.Column("effective_date", sa.Date(), nullable=True),
        sa.Column("cash_rate", sa.Float(), nullable=True),
        sa.Column("stock_rate", sa.Float(), nullable=True),
        sa.Column("ratio_string", AutoString(length=50), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("details", JSONBVariant, nullable=False),
        sa.Column("source", AutoString(length=10), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["symbol"], ["stock_symbol.symbol"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("symbol", "event_type", "ex_date"),
    )
    op.create_index(
        "ix_corporate_event_symbol",
        "corporate_event",
        ["symbol"],
    )
    op.create_index(
        "ix_corporate_event_ex_date",
        "corporate_event",
        ["ex_date"],
    )

    # 2.6. company_shareholder (Cơ cấu cổ đông lớn)
    op.create_table(
        "company_shareholder",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("symbol", AutoString(length=20), nullable=False),
        sa.Column("shareholder_name", AutoString(length=255), nullable=False),
        sa.Column(
            "share_count",
            sa.Float(),
            nullable=False,
            server_default="0.0",
        ),
        sa.Column(
            "ownership_pct",
            sa.Float(),
            nullable=False,
            server_default="0.0",
        ),
        sa.Column(
            "is_institutional",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "is_foreign",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "is_state",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["symbol"], ["stock_symbol.symbol"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("symbol", "shareholder_name"),
    )
    op.create_index(
        "ix_company_shareholder_symbol",
        "company_shareholder",
        ["symbol"],
    )

    # 2.7. company_officer (Ban lãnh đạo, HĐQT)
    op.create_table(
        "company_officer",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("symbol", AutoString(length=20), nullable=False),
        sa.Column("officer_name", AutoString(length=255), nullable=False),
        sa.Column("position", AutoString(length=255), nullable=False),
        sa.Column("share_count", sa.Float(), nullable=True),
        sa.Column("ownership_pct", sa.Float(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["symbol"], ["stock_symbol.symbol"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("symbol", "officer_name", "position"),
    )
    op.create_index(
        "ix_company_officer_symbol",
        "company_officer",
        ["symbol"],
    )

    # 2.8. index_constituent (Thành phần rổ chỉ số VN30, VN100)
    op.create_table(
        "index_constituent",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("index_code", AutoString(length=20), nullable=False),
        sa.Column("symbol", AutoString(length=20), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("free_float_shares", sa.Float(), nullable=True),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["symbol"], ["stock_symbol.symbol"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("index_code", "symbol", "effective_date"),
    )
    op.create_index(
        "ix_index_constituent_index_code",
        "index_constituent",
        ["index_code"],
    )
    op.create_index(
        "ix_index_constituent_symbol",
        "index_constituent",
        ["symbol"],
    )
    op.create_index(
        "ix_index_constituent_effective_date",
        "index_constituent",
        ["effective_date"],
    )

    # 2.9. signal_log (Sổ cái tín hiệu chiến lược định lượng)
    op.create_table(
        "signal_log",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("strategy_name", AutoString(length=50), nullable=False),
        sa.Column("symbol", AutoString(length=20), nullable=False),
        sa.Column("signal_type", AutoString(length=10), nullable=False),
        sa.Column("action_price", sa.Float(), nullable=False),
        sa.Column("stop_loss", sa.Float(), nullable=True),
        sa.Column("take_profit", sa.Float(), nullable=True),
        sa.Column(
            "timeframe",
            AutoString(length=10),
            nullable=False,
            server_default="1m",
        ),
        sa.Column(
            "strength",
            sa.Float(),
            nullable=False,
            server_default="1.0",
        ),
        sa.Column("metadata_info", JSONBVariant, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_signal_log_strategy_name", "signal_log", ["strategy_name"])
    op.create_index("ix_signal_log_symbol", "signal_log", ["symbol"])
    op.create_index("ix_signal_log_created_at", "signal_log", ["created_at"])


def downgrade() -> None:
    # Drop các bảng mới theo thứ tự phụ thuộc
    op.drop_index("ix_signal_log_created_at", table_name="signal_log")
    op.drop_index("ix_signal_log_symbol", table_name="signal_log")
    op.drop_index("ix_signal_log_strategy_name", table_name="signal_log")
    op.drop_table("signal_log")

    op.drop_index(
        "ix_index_constituent_effective_date", table_name="index_constituent"
    )
    op.drop_index("ix_index_constituent_symbol", table_name="index_constituent")
    op.drop_index("ix_index_constituent_index_code", table_name="index_constituent")
    op.drop_table("index_constituent")

    op.drop_index("ix_company_officer_symbol", table_name="company_officer")
    op.drop_table("company_officer")

    op.drop_index("ix_company_shareholder_symbol", table_name="company_shareholder")
    op.drop_table("company_shareholder")

    op.drop_index("ix_corporate_event_ex_date", table_name="corporate_event")
    op.drop_index("ix_corporate_event_symbol", table_name="corporate_event")
    op.drop_table("corporate_event")

    op.drop_index("ix_financial_ratio_symbol", table_name="financial_ratio")
    op.drop_table("financial_ratio")

    op.drop_index(
        "ix_financial_report_item_item_code", table_name="financial_report_item"
    )
    op.drop_index(
        "ix_financial_report_item_report_id", table_name="financial_report_item"
    )
    op.drop_table("financial_report_item")

    op.drop_index(
        "ix_stock_tick_intraday_timestamp", table_name="stock_tick_intraday"
    )
    op.drop_index("ix_stock_tick_intraday_symbol", table_name="stock_tick_intraday")
    op.drop_table("stock_tick_intraday")

    op.drop_index(
        "ix_derivative_contract_expiration_date",
        table_name="derivative_contract",
    )
    op.drop_table("derivative_contract")

    # Drop các cột đã add vào các bảng cũ
    op.drop_column("company_profile", "address")
    op.drop_column("company_profile", "employee_count")
    op.drop_column("company_profile", "max_foreign_ownership_pct")
    op.drop_column("company_profile", "foreign_ownership_pct")
    op.drop_column("company_profile", "free_float_pct")

    op.drop_column("stock_ohlcv_intraday", "vwap")
    op.drop_column("stock_ohlcv_intraday", "volume_delta")
    op.drop_column("stock_ohlcv_intraday", "sell_volume")
    op.drop_column("stock_ohlcv_intraday", "buy_volume")
    op.drop_column("stock_ohlcv_intraday", "value")

    op.drop_column("stock_ohlcv_daily", "foreign_net_volume")
    op.drop_column("stock_ohlcv_daily", "foreign_sell_volume")
    op.drop_column("stock_ohlcv_daily", "foreign_buy_volume")
    op.drop_column("stock_ohlcv_daily", "sell_volume")
    op.drop_column("stock_ohlcv_daily", "buy_volume")
    op.drop_column("stock_ohlcv_daily", "adjusted_close")
    op.drop_column("stock_ohlcv_daily", "floor_price")
    op.drop_column("stock_ohlcv_daily", "ceiling_price")
    op.drop_column("stock_ohlcv_daily", "reference_price")
    op.drop_column("stock_ohlcv_daily", "change_pct")
    op.drop_column("stock_ohlcv_daily", "change")

    op.drop_column("stock_symbol", "lot_size")
    op.drop_column("stock_symbol", "index_group")
    op.drop_column("stock_symbol", "icb_name")
    op.drop_column("stock_symbol", "icb_code")
