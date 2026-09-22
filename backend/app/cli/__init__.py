"""CLI commands for stock data synchronization.

Usage:
    python -m app.cli.stock_sync symbols
    python -m app.cli.stock_sync backfill --symbol VN30F1M --start 2020-01-01
    python -m app.cli.stock_sync daily
    python -m app.cli.stock_sync daily --symbols VNM,FPT,VN30F1M
    python -m app.cli.stock_sync intraday --symbol VN30F1M --interval 1m
    python -m app.cli.stock_sync purge-ticks --retention-days 30
    python -m app.cli.stock_sync status --last 10
"""

from datetime import date

import typer
from sqlmodel import Session, col, select

from app.core.db import engine
from app.cron.purge_ticks import run_purge_ticks_job
from app.models.models_stock import DataSyncLog
from app.services.data_sync import DataSyncManager

app = typer.Typer(help="Stock data sync CLI for Quant Trading system.")


@app.command()
def symbols() -> None:
    """Sync all stock symbols from vnstock to PostgreSQL."""
    with Session(engine) as session:
        manager = DataSyncManager(session)
        log = manager.sync_symbols()
        typer.echo(f"Status: {log.status} | Rows: {log.rows_synced}")
        if log.error_message:
            typer.echo(f"Error: {log.error_message}", err=True)
            raise typer.Exit(code=1)


@app.command()
def backfill(
    symbol: str = typer.Option(help="Stock symbol (e.g. VNM, VN30F1M)"),
    start: str = typer.Option(help="Start date (YYYY-MM-DD)"),
    end: str = typer.Option(
        default=None, help="End date (YYYY-MM-DD), defaults to today"
    ),
) -> None:
    """Backfill historical daily OHLCV data for a symbol."""
    start_date = date.fromisoformat(start)
    end_date = date.fromisoformat(end) if end else date.today()

    with Session(engine) as session:
        manager = DataSyncManager(session)
        log = manager.backfill_daily(symbol, start_date, end_date)
        typer.echo(f"Symbol: {symbol} | Status: {log.status} | Rows: {log.rows_synced}")
        if log.error_message:
            typer.echo(f"Error: {log.error_message}", err=True)
            raise typer.Exit(code=1)


@app.command()
def daily(
    symbols: str = typer.Option(
        default=None,
        help="Comma-separated symbols (e.g. VNM,FPT). Defaults to all active.",
    ),
) -> None:
    """Incremental daily sync for active symbols."""
    symbol_list = symbols.split(",") if symbols else None

    with Session(engine) as session:
        manager = DataSyncManager(session)
        logs = manager.sync_daily_incremental(symbol_list)
        for log in logs:
            typer.echo(f"{log.symbol}: {log.status} ({log.rows_synced} rows)")


@app.command()
def intraday(
    symbol: str = typer.Option(help="Stock symbol"),
    interval: str = typer.Option(default="1m", help="Interval: 1m, 5m, 15m"),
    count_back: int = typer.Option(default=300, help="Number of bars to fetch"),
) -> None:
    """Collect intraday bars for a symbol."""
    with Session(engine) as session:
        manager = DataSyncManager(session)
        log = manager.collect_intraday(symbol, interval=interval, count_back=count_back)
        typer.echo(f"Symbol: {symbol} | Status: {log.status} | Rows: {log.rows_synced}")
        if log.error_message:
            typer.echo(f"Error: {log.error_message}", err=True)
            raise typer.Exit(code=1)


@app.command()
def profile(
    symbol: str = typer.Option(help="Stock symbol"),
) -> None:
    """Sync company profile for a symbol."""
    with Session(engine) as session:
        manager = DataSyncManager(session)
        log = manager.sync_company_profile(symbol)
        typer.echo(f"Symbol: {symbol} | Status: {log.status}")
        if log.error_message:
            typer.echo(f"Error: {log.error_message}", err=True)
            raise typer.Exit(code=1)


@app.command()
def financials(
    symbol: str = typer.Option(help="Stock symbol"),
    report_type: str = typer.Option(
        default="income_statement",
        help="Report type: income_statement, balance_sheet, cash_flow",
    ),
    period: str = typer.Option(default="quarterly", help="Period: quarterly, annual"),
) -> None:
    """Sync financial reports for a symbol."""
    with Session(engine) as session:
        manager = DataSyncManager(session)
        log = manager.sync_financials(symbol, report_type=report_type, period=period)
        typer.echo(f"Symbol: {symbol} | Status: {log.status} | Rows: {log.rows_synced}")
        if log.error_message:
            typer.echo(f"Error: {log.error_message}", err=True)
            raise typer.Exit(code=1)


@app.command(name="purge-ticks")
def purge_ticks(
    retention_days: int = typer.Option(
        default=30, help="Số ngày lưu trữ tick (mặc định 30 ngày theo AGENTS §7.2)"
    ),
    force: bool = typer.Option(
        default=False, help="Bỏ qua Safe Purge Gate (chỉ dùng khi bắt buộc)"
    ),
) -> None:
    """Dọn dẹp dữ liệu tick cũ hơn N ngày qua Safe Purge Gate."""
    with Session(engine) as session:
        log = run_purge_ticks_job(
            session=session, retention_days=retention_days, force=force
        )
        typer.echo(f"Status: {log.status} | Ticks purged: {log.rows_synced}")
        if log.error_message:
            typer.echo(f"Error: {log.error_message}", err=True)
            raise typer.Exit(code=1)


@app.command()
def status(
    last: int = typer.Option(default=10, help="Number of recent sync logs to show"),
) -> None:
    """Show recent sync log entries."""
    with Session(engine) as session:
        logs = session.exec(
            select(DataSyncLog).order_by(col(DataSyncLog.started_at).desc()).limit(last)
        ).all()

        if not logs:
            typer.echo("No sync logs found.")
            return

        typer.echo(
            f"{'Type':<15} {'Symbol':<12} {'Status':<10} {'Rows':<8} {'Started':<20} {'Error'}"
        )
        typer.echo("-" * 90)
        for log in logs:
            typer.echo(
                f"{log.sync_type:<15} "
                f"{(log.symbol or '-'):<12} "
                f"{log.status:<10} "
                f"{log.rows_synced:<8} "
                f"{str(log.started_at)[:19]:<20} "
                f"{(log.error_message or '')[:30]}"
            )


if __name__ == "__main__":
    app()
