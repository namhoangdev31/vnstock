"""normalize financial, institutional flow, and derivatives schemas

Revision ID: g1a2b3c4d5e6
Revises: f6a7b8c9d0e1
Create Date: 2026-09-21
"""

import sqlalchemy as sa
from alembic import op
from sqlmodel.sql.sqltypes import AutoString

# revision identifiers, used by Alembic.
revision = "g1a2b3c4d5e6"
down_revision = "f6a7b8c9d0e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Update stock_ohlcv_daily (derivatives open_interest and basis)
    op.add_column(
        "stock_ohlcv_daily",
        sa.Column("open_interest", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "stock_ohlcv_daily",
        sa.Column("basis", sa.Float(), nullable=True),
    )

    # 2. Update financial_report
    # Add report_scope and is_audited
    op.add_column(
        "financial_report",
        sa.Column(
            "report_scope",
            AutoString(length=20),
            server_default="consolidated",
            nullable=False,
        ),
    )
    op.add_column(
        "financial_report",
        sa.Column(
            "is_audited",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )

    # Add 14 summary financial columns
    op.add_column("financial_report", sa.Column("revenue", sa.Float(), nullable=True))
    op.add_column("financial_report", sa.Column("gross_profit", sa.Float(), nullable=True))
    op.add_column("financial_report", sa.Column("operating_profit", sa.Float(), nullable=True))
    op.add_column("financial_report", sa.Column("net_profit_parent", sa.Float(), nullable=True))
    op.add_column("financial_report", sa.Column("total_assets", sa.Float(), nullable=True))
    op.add_column("financial_report", sa.Column("short_term_assets", sa.Float(), nullable=True))
    op.add_column("financial_report", sa.Column("cash_and_equivalents", sa.Float(), nullable=True))
    op.add_column("financial_report", sa.Column("total_liabilities", sa.Float(), nullable=True))
    op.add_column("financial_report", sa.Column("short_term_debt", sa.Float(), nullable=True))
    op.add_column("financial_report", sa.Column("long_term_debt", sa.Float(), nullable=True))
    op.add_column("financial_report", sa.Column("owners_equity", sa.Float(), nullable=True))
    op.add_column("financial_report", sa.Column("operating_cash_flow", sa.Float(), nullable=True))
    op.add_column("financial_report", sa.Column("investing_cash_flow", sa.Float(), nullable=True))
    op.add_column("financial_report", sa.Column("financing_cash_flow", sa.Float(), nullable=True))

    # Update Unique Constraint for financial_report to include report_scope
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_uqs = inspector.get_unique_constraints("financial_report")
    for uq in existing_uqs:
        cols = set(uq.get("column_names", []))
        if cols == {"symbol", "report_type", "period", "year", "quarter"}:
            uq_name = uq.get("name")
            if uq_name:
                op.drop_constraint(str(uq_name), "financial_report", type_="unique")

    op.create_unique_constraint(
        "uq_financial_report_record",
        "financial_report",
        ["symbol", "report_type", "report_scope", "period", "year", "quarter"],
    )

    # Add lookup index for financial_report
    op.create_index(
        "ix_financial_report_lookup",
        "financial_report",
        ["symbol", "report_type", "report_scope", "year", "quarter"],
    )

    # 3. Update financial_ratio (17 explicit fields and indexes)
    op.add_column("financial_ratio", sa.Column("ev_to_ebitda", sa.Float(), nullable=True))
    op.add_column("financial_ratio", sa.Column("ev_to_ebit", sa.Float(), nullable=True))
    op.add_column("financial_ratio", sa.Column("p_to_fcf", sa.Float(), nullable=True))
    op.add_column("financial_ratio", sa.Column("p_to_ocf", sa.Float(), nullable=True))
    op.add_column("financial_ratio", sa.Column("fcf", sa.Float(), nullable=True))
    op.add_column("financial_ratio", sa.Column("ebit_margin", sa.Float(), nullable=True))
    op.add_column("financial_ratio", sa.Column("ebitda_margin", sa.Float(), nullable=True))
    op.add_column("financial_ratio", sa.Column("asset_turnover", sa.Float(), nullable=True))
    op.add_column("financial_ratio", sa.Column("inventory_turnover", sa.Float(), nullable=True))
    op.add_column("financial_ratio", sa.Column("receivables_turnover", sa.Float(), nullable=True))
    op.add_column("financial_ratio", sa.Column("debt_to_assets", sa.Float(), nullable=True))
    op.add_column("financial_ratio", sa.Column("interest_coverage", sa.Float(), nullable=True))
    op.add_column("financial_ratio", sa.Column("cash_ratio", sa.Float(), nullable=True))
    op.add_column("financial_ratio", sa.Column("revenue_growth_yoy", sa.Float(), nullable=True))
    op.add_column("financial_ratio", sa.Column("net_profit_growth_yoy", sa.Float(), nullable=True))
    op.add_column("financial_ratio", sa.Column("revenue_growth_qoq", sa.Float(), nullable=True))
    op.add_column("financial_ratio", sa.Column("net_profit_growth_qoq", sa.Float(), nullable=True))

    op.create_index(
        "ix_financial_ratio_screener",
        "financial_ratio",
        ["year", "quarter", "pe", "roe"],
    )
    op.create_index(
        "ix_financial_ratio_growth",
        "financial_ratio",
        ["year", "quarter", "revenue_growth_yoy", "net_profit_growth_yoy"],
    )

    # 4. Update institutional_flow
    op.add_column("institutional_flow", sa.Column("foreign_buy_volume", sa.BigInteger(), nullable=True))
    op.add_column("institutional_flow", sa.Column("foreign_sell_volume", sa.BigInteger(), nullable=True))
    op.add_column("institutional_flow", sa.Column("foreign_net_volume", sa.BigInteger(), nullable=True))
    op.add_column("institutional_flow", sa.Column("foreign_room_total", sa.BigInteger(), nullable=True))
    op.add_column("institutional_flow", sa.Column("foreign_room_current", sa.BigInteger(), nullable=True))
    op.add_column("institutional_flow", sa.Column("foreign_room_pct", sa.Float(), nullable=True))
    op.add_column("institutional_flow", sa.Column("prop_buy_volume", sa.BigInteger(), nullable=True))
    op.add_column("institutional_flow", sa.Column("prop_sell_volume", sa.BigInteger(), nullable=True))
    op.add_column("institutional_flow", sa.Column("prop_net_volume", sa.BigInteger(), nullable=True))

    op.create_index(
        "ix_inst_flow_symbol_date",
        "institutional_flow",
        ["symbol", "trading_date"],
    )
    op.create_index(
        "ix_inst_flow_date_net_val",
        "institutional_flow",
        ["trading_date", "foreign_net_value", "prop_net_value"],
    )


def downgrade() -> None:
    # 4. Revert institutional_flow
    op.drop_index("ix_inst_flow_date_net_val", table_name="institutional_flow")
    op.drop_index("ix_inst_flow_symbol_date", table_name="institutional_flow")

    op.drop_column("institutional_flow", "prop_net_volume")
    op.drop_column("institutional_flow", "prop_sell_volume")
    op.drop_column("institutional_flow", "prop_buy_volume")
    op.drop_column("institutional_flow", "foreign_room_pct")
    op.drop_column("institutional_flow", "foreign_room_current")
    op.drop_column("institutional_flow", "foreign_room_total")
    op.drop_column("institutional_flow", "foreign_net_volume")
    op.drop_column("institutional_flow", "foreign_sell_volume")
    op.drop_column("institutional_flow", "foreign_buy_volume")

    # 3. Revert financial_ratio
    op.drop_index("ix_financial_ratio_growth", table_name="financial_ratio")
    op.drop_index("ix_financial_ratio_screener", table_name="financial_ratio")

    for col in [
        "net_profit_growth_qoq",
        "revenue_growth_qoq",
        "net_profit_growth_yoy",
        "revenue_growth_yoy",
        "cash_ratio",
        "interest_coverage",
        "debt_to_assets",
        "receivables_turnover",
        "inventory_turnover",
        "asset_turnover",
        "ebitda_margin",
        "ebit_margin",
        "fcf",
        "p_to_ocf",
        "p_to_fcf",
        "ev_to_ebit",
        "ev_to_ebitda",
    ]:
        op.drop_column("financial_ratio", col)

    # 2. Revert financial_report
    op.drop_index("ix_financial_report_lookup", table_name="financial_report")
    op.drop_constraint("uq_financial_report_record", "financial_report", type_="unique")
    op.create_unique_constraint(
        "financial_report_symbol_report_type_period_year_quarter_key",
        "financial_report",
        ["symbol", "report_type", "period", "year", "quarter"],
    )

    for col in [
        "financing_cash_flow",
        "investing_cash_flow",
        "operating_cash_flow",
        "owners_equity",
        "long_term_debt",
        "short_term_debt",
        "total_liabilities",
        "cash_and_equivalents",
        "short_term_assets",
        "total_assets",
        "net_profit_parent",
        "operating_profit",
        "gross_profit",
        "revenue",
        "is_audited",
        "report_scope",
    ]:
        op.drop_column("financial_report", col)

    # 1. Revert stock_ohlcv_daily
    op.drop_column("stock_ohlcv_daily", "basis")
    op.drop_column("stock_ohlcv_daily", "open_interest")
