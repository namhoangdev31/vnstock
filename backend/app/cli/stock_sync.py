"""CLI commands for stock data synchronization.

Usage:
    python -m app.cli.stock_sync symbols
    python -m app.cli.stock_sync backfill --symbol VN30F1M --start 2020-01-01
    python -m app.cli.stock_sync daily
    python -m app.cli.stock_sync status --last 10
"""

from app.cli import app

if __name__ == "__main__":
    app()
