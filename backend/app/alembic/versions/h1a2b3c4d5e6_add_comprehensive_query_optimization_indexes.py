"""add comprehensive query optimization composite indexes

Revision ID: h1a2b3c4d5e6
Revises: g1a2b3c4d5e6
Create Date: 2026-09-21
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "h1a2b3c4d5e6"
down_revision = "g1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. StockSymbol composite filter indexes
    op.create_index(
        "ix_stock_symbol_active_exchange",
        "stock_symbol",
        ["is_active", "exchange", "asset_type"],
        unique=False,
    )
    op.create_index(
        "ix_stock_symbol_active_group",
        "stock_symbol",
        ["index_group", "is_active"],
        unique=False,
    )

    # 2. StockOHLCVDaily composite indexes
    op.create_index(
        "ix_stock_ohlcv_daily_sym_date",
        "stock_ohlcv_daily",
        ["symbol", "trading_date"],
        unique=False,
    )
    op.create_index(
        "ix_stock_ohlcv_daily_date_val",
        "stock_ohlcv_daily",
        ["trading_date", "value"],
        unique=False,
    )

    # 3. StockOHLCVIntraday multi-timeframe composite index
    op.create_index(
        "ix_stock_ohlcv_intraday_sym_int_time",
        "stock_ohlcv_intraday",
        ["symbol", "interval", "timestamp"],
        unique=False,
    )

    # 4. StockTickIntraday tick lookup index
    op.create_index(
        "ix_stock_tick_intraday_sym_time",
        "stock_tick_intraday",
        ["symbol", "timestamp"],
        unique=False,
    )

    # 5. CorporateEvent lookup index
    op.create_index(
        "ix_corporate_event_sym_exdate",
        "corporate_event",
        ["symbol", "ex_date"],
        unique=False,
    )

    # 6. IndexConstituent composition query index
    op.create_index(
        "ix_index_constituent_code_eff",
        "index_constituent",
        ["index_code", "effective_date"],
        unique=False,
    )

    # 7. CoveredWarrant active underlying index
    op.create_index(
        "ix_covered_warrant_underlying_active",
        "covered_warrant",
        ["underlying_symbol", "is_active"],
        unique=False,
    )

    # 8. BondSpecification issuer and type active indexes
    op.create_index(
        "ix_bond_spec_issuer_active",
        "bond_specification",
        ["issuer_symbol", "is_active"],
        unique=False,
    )
    op.create_index(
        "ix_bond_spec_type_active",
        "bond_specification",
        ["bond_type", "is_active"],
        unique=False,
    )

    # 9. DataSyncLog audit indexes
    op.create_index(
        "ix_data_sync_log_type_date",
        "data_sync_log",
        ["sync_type", "started_at"],
        unique=False,
    )
    op.create_index(
        "ix_data_sync_log_symbol_date",
        "data_sync_log",
        ["symbol", "started_at"],
        unique=False,
    )

    # 10. ForecastJournal learning loop index
    op.create_index(
        "ix_forecast_journal_status_pred",
        "forecast_journal",
        ["status", "predicted_at"],
        unique=False,
    )


def downgrade() -> None:
    # Reverse all indexes created in upgrade()
    op.drop_index("ix_forecast_journal_status_pred", table_name="forecast_journal")
    op.drop_index("ix_data_sync_log_symbol_date", table_name="data_sync_log")
    op.drop_index("ix_data_sync_log_type_date", table_name="data_sync_log")
    op.drop_index("ix_bond_spec_type_active", table_name="bond_specification")
    op.drop_index("ix_bond_spec_issuer_active", table_name="bond_specification")
    op.drop_index("ix_covered_warrant_underlying_active", table_name="covered_warrant")
    op.drop_index("ix_index_constituent_code_eff", table_name="index_constituent")
    op.drop_index("ix_corporate_event_sym_exdate", table_name="corporate_event")
    op.drop_index("ix_stock_tick_intraday_sym_time", table_name="stock_tick_intraday")
    op.drop_index("ix_stock_ohlcv_intraday_sym_int_time", table_name="stock_ohlcv_intraday")
    op.drop_index("ix_stock_ohlcv_daily_date_val", table_name="stock_ohlcv_daily")
    op.drop_index("ix_stock_ohlcv_daily_sym_date", table_name="stock_ohlcv_daily")
    op.drop_index("ix_stock_symbol_active_group", table_name="stock_symbol")
    op.drop_index("ix_stock_symbol_active_exchange", table_name="stock_symbol")
