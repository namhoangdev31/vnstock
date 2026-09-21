"""create financial report revision and alter financial columns to numeric

Revision ID: j1a2b3c4d5e6
Revises: i1a2b3c4d5e6
Create Date: 2026-09-21
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "j1a2b3c4d5e6"
down_revision = "i1a2b3c4d5e6"
branch_labels = None
depends_on = None

MONEY_COLUMNS_FINANCIAL_REPORT = [
    "revenue",
    "gross_profit",
    "operating_profit",
    "net_profit_parent",
    "total_assets",
    "short_term_assets",
    "cash_and_equivalents",
    "total_liabilities",
    "short_term_debt",
    "long_term_debt",
    "owners_equity",
    "operating_cash_flow",
    "investing_cash_flow",
    "financing_cash_flow",
]

PRICE_COLUMNS_OHLCV = [
    "open",
    "high",
    "low",
    "close",
    "reference_price",
    "ceiling_price",
    "floor_price",
    "adjusted_close",
]


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    # 1. Tạo bảng FinancialReportRevision
    op.create_table(
        "financial_report_revision",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("report_id", sa.Uuid(), nullable=False),
        sa.Column("revision_number", sa.Integer(), server_default="1", nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_provisional", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("restated_reason", sa.String(length=500), nullable=True),
        sa.Column(
            "data",
            sa.JSON(),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["report_id"], ["financial_report.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("report_id", "revision_number"),
    )
    op.create_index("ix_financial_report_rev_pub", "financial_report_revision", ["report_id", "published_at", "is_provisional"], unique=False)
    op.create_index("ix_financial_report_revision_payload_hash", "financial_report_revision", ["payload_hash"], unique=False)
    op.create_index("ix_financial_report_revision_report_id", "financial_report_revision", ["report_id"], unique=False)

    # 2. Chuyển đổi các cột tiền sang NUMERIC trên PostgreSQL
    if is_postgres:
        for col_name in MONEY_COLUMNS_FINANCIAL_REPORT:
            op.alter_column(
                "financial_report",
                col_name,
                type_=sa.Numeric(precision=28, scale=0),
                existing_type=sa.Float(),
                postgresql_using=f"{col_name}::numeric(28,0)",
            )

        op.alter_column(
            "financial_report_item",
            "value",
            type_=sa.Numeric(precision=28, scale=0),
            existing_type=sa.Float(),
            postgresql_using="value::numeric(28,0)",
        )

        for col_name in PRICE_COLUMNS_OHLCV:
            op.alter_column(
                "stock_ohlcv_daily",
                col_name,
                type_=sa.Numeric(precision=18, scale=2),
                existing_type=sa.Float(),
                postgresql_using=f"{col_name}::numeric(18,2)",
            )

        op.alter_column(
            "stock_ohlcv_daily",
            "value",
            type_=sa.Numeric(precision=28, scale=0),
            existing_type=sa.Float(),
            postgresql_using="value::numeric(28,0)",
        )

        # 3. Backfill initial revisions (revision 1) cho dữ liệu BCTC đã có
        op.execute(
            """
            INSERT INTO financial_report_revision (
                id, report_id, revision_number, payload_hash, published_at, is_provisional, data, created_at
            )
            SELECT 
                gen_random_uuid(),
                f.id,
                1,
                md5(COALESCE(f.data::text, '{}')),
                NULL,
                TRUE,
                COALESCE(f.data, '{}'::json),
                f.updated_at
            FROM financial_report f
            ON CONFLICT DO NOTHING;
            """
        )


def downgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    # 1. Phục hồi kiểu FLOAT
    if is_postgres:
        for col_name in MONEY_COLUMNS_FINANCIAL_REPORT:
            op.alter_column(
                "financial_report",
                col_name,
                type_=sa.Float(),
                existing_type=sa.Numeric(precision=28, scale=0),
                postgresql_using=f"{col_name}::double precision",
            )

        op.alter_column(
            "financial_report_item",
            "value",
            type_=sa.Float(),
            existing_type=sa.Numeric(precision=28, scale=0),
            postgresql_using="value::double precision",
        )

        for col_name in PRICE_COLUMNS_OHLCV:
            op.alter_column(
                "stock_ohlcv_daily",
                col_name,
                type_=sa.Float(),
                existing_type=sa.Numeric(precision=18, scale=2),
                postgresql_using=f"{col_name}::double precision",
            )

        op.alter_column(
            "stock_ohlcv_daily",
            "value",
            type_=sa.Float(),
            existing_type=sa.Numeric(precision=28, scale=0),
            postgresql_using="value::double precision",
        )

    # 2. Xóa bảng FinancialReportRevision
    op.drop_index("ix_financial_report_revision_report_id", table_name="financial_report_revision")
    op.drop_index("ix_financial_report_revision_payload_hash", table_name="financial_report_revision")
    op.drop_index("ix_financial_report_rev_pub", table_name="financial_report_revision")
    op.drop_table("financial_report_revision")
