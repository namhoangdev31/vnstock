"""Alpha Screener - multi-horizon equity basket selection (paper-only).

Implements three screening horizons:
- Weekly: volume surge + price action + liquidity
- Monthly: RS rating + sector flow + VCP (volatility contraction)
- Quarterly: growth + financial health + Piotroski F-Score + P/E

All criteria derived from DB models (StockOHLCVDaily, FinancialRatio, etc.).
RULE 3: missing data → criterion failed / symbol skipped (never invented).

Outputs are simulation baskets for educational analysis (RULE 4).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from statistics import fmean
from typing import Any

from sqlmodel import Session, col, select

from app.core.models_base import VN_TZ
from app.domains.fundamental.domain.models import FinancialRatio, FinancialReport
from app.domains.market_data.domain.models import (
    StockOHLCVDaily,
    StockSymbol,
)
from app.domains.quant.domain.indicators import compute_sma
from app.domains.quant.domain.models import InstitutionalFlow

# Weekly thresholds
WEEKLY_VOL_SURGE_MULT = 2.0
WEEKLY_MIN_AVG_VALUE_VND = 15e9  # 15 billion VND

# Monthly thresholds
MONTHLY_RS_MIN = 80
MONTHLY_RS_WINDOW = 60  # days
MONTHLY_SECTOR_TOP_N = 3
MONTHLY_SECTOR_LOOKBACK_TRADING_DAYS = 10
MONTHLY_VCP_MAX_RANGE = 0.08  # 8%

# Quarterly thresholds
QUARTERLY_GROWTH_MIN = 20.0  # % YoY
QUARTERLY_ROE_MIN = 15.0  # %
QUARTERLY_DE_MAX = 1.5
QUARTERLY_FSCORE_MIN = 7
PE_HISTORY_QUARTERS = 12


@dataclass
class Criterion:
    """Single screening criterion evaluation."""

    key: str
    label: str
    passed: bool
    value: float | None
    threshold: float | None


@dataclass
class ScreenedTicker:
    """A ticker that passed screening for a horizon."""

    symbol: str
    horizon: str
    alpha_score: float  # 0-100, weighted pass rate
    criteria: list[Criterion]


def _get_active_equities(session: Session) -> list[str]:
    """Fetch active equity symbols from StockSymbol (HOSE/HNX/UPCOM)."""
    from app.core.enums import Exchange

    symbols = session.exec(
        select(StockSymbol.symbol)
        .where(
            (StockSymbol.asset_type == "stock") | (StockSymbol.asset_type == "EQUITY")
        )
        .where(
            col(StockSymbol.exchange).in_([Exchange.HOSE, Exchange.HNX, Exchange.UPCOM])
        )
        .where(col(StockSymbol.is_active).is_(True))
    ).all()
    return list(symbols)


def _get_stock_bars(
    session: Session,
    symbol: str,
    lookback_days: int,
    as_of: date | None = None,
) -> list[StockOHLCVDaily]:
    """Fetch recent OHLCV bars for a symbol up to as_of date."""
    end_date = as_of or datetime.now(VN_TZ).date()
    cutoff = end_date - timedelta(days=lookback_days)
    bars = session.exec(
        select(StockOHLCVDaily)
        .where(StockOHLCVDaily.symbol == symbol)
        .where(col(StockOHLCVDaily.trading_date) >= cutoff)
        .where(col(StockOHLCVDaily.trading_date) <= end_date)
        .order_by(col(StockOHLCVDaily.trading_date).asc())
    ).all()
    return list(bars)


def _screen_weekly(
    session: Session, symbol: str, as_of: date | None = None
) -> ScreenedTicker | None:
    """Weekly screen: volume surge + price above SMA + liquidity."""
    bars = _get_stock_bars(session, symbol, lookback_days=120, as_of=as_of)
    if len(bars) < 50:
        return None

    volumes = [bar.volume for bar in bars if bar.volume is not None]
    closes = [bar.close for bar in bars if bar.close is not None]
    values = [
        bar.value
        if bar.value is not None
        else (bar.close * bar.volume if bar.close and bar.volume else None)
        for bar in bars
    ]
    valid_values = [v for v in values if v is not None]

    if len(volumes) < 20 or len(closes) < 50 or len(valid_values) < 20:
        return None

    sma20_vol = compute_sma(volumes, 20)
    sma20_close = compute_sma(closes, 20)
    sma50_close = compute_sma(closes, 50)
    avg_value_20d = fmean(valid_values[-20:])

    criteria = [
        Criterion(
            key="volume_surge",
            label=(
                f"Volume {volumes[-1]:,.0f} >= {WEEKLY_VOL_SURGE_MULT}×SMA20={sma20_vol:,.0f}"
                if sma20_vol
                else "Volume surge"
            ),
            passed=volumes[-1] >= WEEKLY_VOL_SURGE_MULT * (sma20_vol or 0),
            value=volumes[-1],
            threshold=WEEKLY_VOL_SURGE_MULT * (sma20_vol or 0) if sma20_vol else None,
        ),
        Criterion(
            key="price_above_sma20",
            label=(
                f"Close {closes[-1]:,.2f} > SMA20={sma20_close:,.2f}"
                if sma20_close
                else "Price > SMA20"
            ),
            passed=closes[-1] > (sma20_close or 0) if sma20_close else False,
            value=closes[-1],
            threshold=sma20_close,
        ),
        Criterion(
            key="price_above_sma50",
            label=(
                f"Close {closes[-1]:,.2f} > SMA50={sma50_close:,.2f}"
                if sma50_close
                else "Price > SMA50"
            ),
            passed=closes[-1] > (sma50_close or 0) if sma50_close else False,
            value=closes[-1],
            threshold=sma50_close,
        ),
        Criterion(
            key="liquidity",
            label=f"AvgValue20D={avg_value_20d / 1e9:.2f}B >= {WEEKLY_MIN_AVG_VALUE_VND / 1e9}B",
            passed=avg_value_20d >= WEEKLY_MIN_AVG_VALUE_VND,
            value=avg_value_20d,
            threshold=WEEKLY_MIN_AVG_VALUE_VND,
        ),
    ]

    passed_count = sum(1 for c in criteria if c.passed)
    alpha_score = 100.0 * passed_count / len(criteria)

    return ScreenedTicker(
        symbol=symbol,
        horizon="weekly",
        alpha_score=alpha_score,
        criteria=criteria,
    )


def _screen_monthly(
    session: Session,
    symbol: str,
    sector_top_icb: list[str],
    as_of: date | None = None,
) -> ScreenedTicker | None:
    """Monthly screen: RS rating + sector momentum + VCP."""
    end_date = as_of or datetime.now(VN_TZ).date()
    bars = _get_stock_bars(session, symbol, lookback_days=180, as_of=end_date)
    if len(bars) < 60:
        return None

    closes = [bar.close for bar in bars if bar.close is not None]
    highs = [bar.high for bar in bars if bar.high is not None]
    lows = [bar.low for bar in bars if bar.low is not None]

    if len(closes) < 60 or len(highs) < 5 or len(lows) < 5:
        return None

    # RS: 60-day ROC residualized by VNINDEX bars when present
    roc_symbol = (
        ((closes[-1] - closes[-60]) / closes[-60]) * 100 if closes[-60] > 0 else 0.0
    )

    vn_bars = session.exec(
        select(StockOHLCVDaily)
        .where(col(StockOHLCVDaily.symbol).in_(["VNINDEX", "VN-INDEX"]))
        .where(col(StockOHLCVDaily.trading_date) <= end_date)
        .order_by(col(StockOHLCVDaily.trading_date).asc())
    ).all()

    if len(vn_bars) >= 60:
        vn_closes = [b.close for b in vn_bars if b.close is not None]
        if len(vn_closes) >= 60 and vn_closes[-60] > 0:
            roc_bench = ((vn_closes[-1] - vn_closes[-60]) / vn_closes[-60]) * 100
            # Residualized score: baseline 50 + (roc_symbol - roc_bench) clamped to [0, 100]
            rs_score = min(100.0, max(0.0, 50.0 + (roc_symbol - roc_bench)))
        else:
            rs_score = min(100.0, max(0.0, roc_symbol))
    else:
        rs_score = min(100.0, max(0.0, roc_symbol))

    rs_passed = rs_score >= MONTHLY_RS_MIN

    # Sector: check if symbol's ICB is in top sectors
    symbol_meta = session.exec(
        select(StockSymbol).where(StockSymbol.symbol == symbol)
    ).first()
    icb_code = symbol_meta.icb_code if symbol_meta else None
    sector_passed = icb_code in sector_top_icb if icb_code else False

    # VCP: max (high-low)/close over last 5 bars < 8%
    last_5_ranges = []
    for i in range(-5, 0):
        if closes[i] > 0:
            last_5_ranges.append((highs[i] - lows[i]) / closes[i])
    max_range = max(last_5_ranges) if last_5_ranges else None
    vcp_passed = max_range is not None and max_range < MONTHLY_VCP_MAX_RANGE

    criteria = [
        Criterion(
            key="rs_rating",
            label=f"RS Rating={rs_score:.1f} >= {MONTHLY_RS_MIN}",
            passed=rs_passed,
            value=rs_score,
            threshold=float(MONTHLY_RS_MIN),
        ),
        Criterion(
            key="sector_momentum",
            label=f"ICB {icb_code} in top-{MONTHLY_SECTOR_TOP_N}",
            passed=sector_passed,
            value=None,
            threshold=None,
        ),
        Criterion(
            key="vcp_contraction",
            label=(
                f"MaxRange={max_range * 100:.2f}% < {MONTHLY_VCP_MAX_RANGE * 100:.0f}%"
                if max_range is not None
                else "VCP contraction"
            ),
            passed=vcp_passed,
            value=(max_range * 100 if max_range is not None else None),
            threshold=MONTHLY_VCP_MAX_RANGE * 100,
        ),
    ]

    passed_count = sum(1 for c in criteria if c.passed)
    alpha_score = 100.0 * passed_count / len(criteria)

    return ScreenedTicker(
        symbol=symbol,
        horizon="monthly",
        alpha_score=alpha_score,
        criteria=criteria,
    )


def _compute_piotroski_fscore(
    session: Session, symbol: str, current_ratio: FinancialRatio | None
) -> float:
    """Compute Piotroski F-Score (0-9) from available financial data.

    Missing data → signal fails (0). Only signals with sufficient data count.
    """
    if current_ratio is None:
        return 0.0

    # Find prior year financial ratio for YoY comparison (same quarter of prior year preferred)
    prior_ratio = session.exec(
        select(FinancialRatio)
        .where(FinancialRatio.symbol == symbol)
        .where(FinancialRatio.year == current_ratio.year - 1)
        .where(FinancialRatio.quarter == current_ratio.quarter)
    ).first()
    if prior_ratio is None:
        prior_ratio = session.exec(
            select(FinancialRatio)
            .where(FinancialRatio.symbol == symbol)
            .where(FinancialRatio.year < current_ratio.year)
            .order_by(
                col(FinancialRatio.year).desc(), col(FinancialRatio.quarter).desc()
            )
            .limit(1)
        ).first()

    # Query matching FinancialReport rows
    current_report = session.exec(
        select(FinancialReport)
        .where(FinancialReport.symbol == symbol)
        .where(FinancialReport.year == current_ratio.year)
        .where(FinancialReport.quarter == current_ratio.quarter)
    ).first()

    prior_report = None
    if prior_ratio is not None:
        prior_report = session.exec(
            select(FinancialReport)
            .where(FinancialReport.symbol == symbol)
            .where(FinancialReport.year == prior_ratio.year)
            .where(FinancialReport.quarter == prior_ratio.quarter)
        ).first()

    fscore = 0.0

    # F1: ROA > 0
    if current_ratio.roa is not None and current_ratio.roa > 0:
        fscore += 1
    elif (
        current_report
        and current_report.net_profit_parent is not None
        and current_report.total_assets
        and current_report.total_assets > 0
        and (current_report.net_profit_parent / current_report.total_assets) > 0
    ):
        fscore += 1

    # F2: OCF > 0
    if current_report and current_report.operating_cash_flow is not None:
        if current_report.operating_cash_flow > 0:
            fscore += 1

    # F3: ROA improving YoY
    if current_ratio.roa is not None and prior_ratio and prior_ratio.roa is not None:
        if current_ratio.roa > prior_ratio.roa:
            fscore += 1

    # F4: Accruals (OCF / Total Assets > ROA or improved)
    if (
        current_report
        and current_report.operating_cash_flow is not None
        and current_report.total_assets
        and current_report.total_assets > 0
    ):
        curr_ocf_scaled = (
            current_report.operating_cash_flow / current_report.total_assets
        )
        curr_roa_frac = (current_ratio.roa or 0.0) / 100.0
        if curr_ocf_scaled > curr_roa_frac:
            fscore += 1

    # F5: LTD/TotalAssets decreased
    if (
        current_report
        and prior_report
        and current_report.total_assets
        and prior_report.total_assets
        and current_report.total_assets > 0
        and prior_report.total_assets > 0
    ):
        curr_ltd_ratio = (
            current_report.long_term_debt or 0.0
        ) / current_report.total_assets
        prior_ltd_ratio = (
            prior_report.long_term_debt or 0.0
        ) / prior_report.total_assets
        if curr_ltd_ratio < prior_ltd_ratio:
            fscore += 1

    # F6: Current ratio improved
    if (
        current_ratio.current_ratio is not None
        and prior_ratio
        and prior_ratio.current_ratio is not None
    ):
        if current_ratio.current_ratio > prior_ratio.current_ratio:
            fscore += 1

    # F7: No new share issuance (skip/0 if no event data)

    # F8: Gross margin improved
    if (
        current_ratio.gross_margin is not None
        and prior_ratio
        and prior_ratio.gross_margin is not None
    ):
        if current_ratio.gross_margin > prior_ratio.gross_margin:
            fscore += 1

    # F9: Asset turnover increased
    if (
        current_ratio.asset_turnover is not None
        and prior_ratio
        and prior_ratio.asset_turnover is not None
    ):
        if current_ratio.asset_turnover > prior_ratio.asset_turnover:
            fscore += 1

    return fscore


def _screen_quarterly(
    session: Session, symbol: str, as_of: date | None = None
) -> ScreenedTicker | None:
    """Quarterly screen: growth + ROE/D/E + Piotroski + P/E vs history."""
    query = select(FinancialRatio).where(FinancialRatio.symbol == symbol)
    if as_of is not None:
        as_of_year = as_of.year
        as_of_quarter = (as_of.month - 1) // 3 + 1
        query = query.where(
            (col(FinancialRatio.year) < as_of_year)
            | (
                (col(FinancialRatio.year) == as_of_year)
                & (col(FinancialRatio.quarter) <= as_of_quarter)
            )
        )
    current_ratio = session.exec(
        query.order_by(
            col(FinancialRatio.year).desc(), col(FinancialRatio.quarter).desc()
        ).limit(1)
    ).first()

    if current_ratio is None:
        return None

    # Revenue/Profit growth YoY
    growth_passed = (
        current_ratio.revenue_growth_yoy is not None
        and current_ratio.revenue_growth_yoy >= QUARTERLY_GROWTH_MIN
        and current_ratio.net_profit_growth_yoy is not None
        and current_ratio.net_profit_growth_yoy >= QUARTERLY_GROWTH_MIN
    )

    # ROE >= 15% and D/E < 1.5
    health_passed = (
        current_ratio.roe is not None
        and current_ratio.roe >= QUARTERLY_ROE_MIN
        and current_ratio.debt_to_equity is not None
        and current_ratio.debt_to_equity < QUARTERLY_DE_MAX
    )

    # Piotroski F-Score >= 7
    fscore = _compute_piotroski_fscore(session, symbol, current_ratio)
    fscore_passed = fscore >= QUARTERLY_FSCORE_MIN

    # P/E < 3-year average (use 12-quarter history)
    pe_history = session.exec(
        select(FinancialRatio.pe)
        .where(FinancialRatio.symbol == symbol)
        .where(col(FinancialRatio.pe).is_not(None))
        .order_by(col(FinancialRatio.year).desc(), col(FinancialRatio.quarter).desc())
        .limit(PE_HISTORY_QUARTERS)
    ).all()
    pe_history_clean = [pe for pe in pe_history if pe is not None and pe > 0]

    pe_passed = False
    pe_avg = None
    if len(pe_history_clean) >= 4 and current_ratio.pe is not None:
        pe_avg = fmean(pe_history_clean)
        pe_passed = current_ratio.pe < pe_avg

    criteria = [
        Criterion(
            key="growth_yoy",
            label=f"Rev+Profit Growth >= {QUARTERLY_GROWTH_MIN}%",
            passed=growth_passed,
            value=(current_ratio.revenue_growth_yoy or 0)
            + (current_ratio.net_profit_growth_yoy or 0),
            threshold=QUARTERLY_GROWTH_MIN * 2,
        ),
        Criterion(
            key="financial_health",
            label=f"ROE >= {QUARTERLY_ROE_MIN}% & D/E < {QUARTERLY_DE_MAX}",
            passed=health_passed,
            value=current_ratio.roe,
            threshold=QUARTERLY_ROE_MIN,
        ),
        Criterion(
            key="piotroski_fscore",
            label=f"F-Score {fscore:.0f}/9 >= {QUARTERLY_FSCORE_MIN}",
            passed=fscore_passed,
            value=fscore,
            threshold=QUARTERLY_FSCORE_MIN,
        ),
        Criterion(
            key="pe_discount",
            label=(
                f"P/E {current_ratio.pe} < Avg{pe_avg:.1f}"
                if pe_avg
                else "P/E < 3Y Avg"
            ),
            passed=pe_passed,
            value=current_ratio.pe,
            threshold=pe_avg,
        ),
    ]

    passed_count = sum(1 for c in criteria if c.passed)
    alpha_score = 100.0 * passed_count / len(criteria)

    return ScreenedTicker(
        symbol=symbol,
        horizon="quarterly",
        alpha_score=alpha_score,
        criteria=criteria,
    )


def record_screener_forecasts(
    session: Session,
    baskets: dict[str, list[ScreenedTicker]],
    *,
    as_of: date | None = None,
    model_version: str = "alpha_screener_v1",
) -> list[Any]:
    """Persist screened tickers into ForecastJournal as pending forecasts (RULE 3 / AGENTS §9.1)."""
    from app.core.enums import ForecastDirection, ForecastHorizon, ForecastStatus
    from app.domains.quant.domain.models import ForecastJournal

    as_of_date = as_of or datetime.now(VN_TZ).date()
    now_vn = datetime.now(VN_TZ)
    pred_time = datetime.combine(as_of_date, datetime.min.time()).replace(
        hour=15, minute=0, tzinfo=VN_TZ
    )
    if pred_time > now_vn + timedelta(seconds=5):
        pred_time = now_vn

    horizon_map = {
        "weekly": ForecastHorizon.WEEKLY,
        "monthly": ForecastHorizon.MONTHLY,
        "quarterly": ForecastHorizon.QUARTERLY,
    }

    recorded: list[ForecastJournal] = []

    for horizon_key, tickers in baskets.items():
        horizon_enum = horizon_map.get(horizon_key)
        if not horizon_enum:
            continue

        for ticker in tickers:
            existing = session.exec(
                select(ForecastJournal).where(
                    ForecastJournal.symbol == ticker.symbol,
                    ForecastJournal.horizon == horizon_enum,
                    col(ForecastJournal.predicted_at) == pred_time,
                )
            ).first()
            if existing is not None:
                recorded.append(existing)
                continue

            last_bar = session.exec(
                select(StockOHLCVDaily)
                .where(StockOHLCVDaily.symbol == ticker.symbol)
                .where(col(StockOHLCVDaily.trading_date) <= as_of_date)
                .order_by(col(StockOHLCVDaily.trading_date).desc())
                .limit(1)
            ).first()
            predicted_value = last_bar.close if last_bar else None

            entry = ForecastJournal(
                symbol=ticker.symbol,
                horizon=horizon_enum,
                predicted_at=pred_time,
                predicted_value=predicted_value,
                predicted_direction=ForecastDirection.BULLISH,
                engine_weights={
                    "technical": 0.35,
                    "flow_liquidity": 0.35,
                    "fundamental": 0.30,
                },
                model_version=model_version,
                parameter_snapshot={
                    "alpha_score": ticker.alpha_score,
                    "criteria": {
                        c.key: {
                            "passed": c.passed,
                            "value": c.value,
                            "threshold": c.threshold,
                        }
                        for c in ticker.criteria
                    },
                },
                status=ForecastStatus.PENDING,
            )
            session.add(entry)
            recorded.append(entry)

    if recorded:
        session.commit()
    return recorded


def screen(
    session: Session,
    horizon: str = "all",
    as_of: date | None = None,
    *,
    record_journal: bool = False,
    model_version: str = "alpha_screener_v1",
) -> dict[str, list[ScreenedTicker]]:
    """Run multi-horizon screening and return baskets by horizon.

    Args:
        session: SQLAlchemy session
        horizon: "weekly", "monthly", "quarterly", or "all"
        as_of: As-of date for screening (default: today)
        record_journal: If True, persist screened tickers to ForecastJournal
        model_version: Model calibration identifier for audit ledger

    Returns:
        Dict mapping horizon → list of ScreenedTicker (passing criteria only).

    RULE 3: missing data → criterion failed; never invent prices or metrics.
    """
    as_of_date = as_of or datetime.now(VN_TZ).date()

    if horizon not in ("weekly", "monthly", "quarterly", "all"):
        raise ValueError(f"Invalid horizon: {horizon}")

    symbols = _get_active_equities(session)
    results: dict[str, list[ScreenedTicker]] = {
        "weekly": [],
        "monthly": [],
        "quarterly": [],
    }

    # Pre-compute top sectors for monthly screen
    sector_top_icb: list[str] = []
    if horizon in ("monthly", "all"):
        cutoff = as_of_date - timedelta(days=MONTHLY_SECTOR_LOOKBACK_TRADING_DAYS * 3)
        flow_rows = session.exec(
            select(InstitutionalFlow)
            .where(col(InstitutionalFlow.trading_date) <= as_of_date)
            .where(col(InstitutionalFlow.trading_date) >= cutoff)
            .order_by(col(InstitutionalFlow.trading_date).desc())
        ).all()
        # Find distinct last 10 trading dates present in InstitutionalFlow
        distinct_dates = sorted({row.trading_date for row in flow_rows}, reverse=True)[
            :MONTHLY_SECTOR_LOOKBACK_TRADING_DAYS
        ]

        recent_flows = [r for r in flow_rows if r.trading_date in distinct_dates]

        icb_totals: dict[str, float] = {}
        flow_symbols = list({row.symbol for row in recent_flows})
        symbol_metas = {
            meta.symbol: meta
            for meta in session.exec(
                select(StockSymbol).where(col(StockSymbol.symbol).in_(flow_symbols))
            ).all()
        }
        for row in recent_flows:
            meta = symbol_metas.get(row.symbol)
            if meta and meta.icb_code:
                net = (row.foreign_net_value or 0) + (row.prop_net_value or 0)
                icb_totals[meta.icb_code] = icb_totals.get(meta.icb_code, 0) + net
        sorted_icb = sorted(icb_totals.items(), key=lambda x: x[1], reverse=True)
        sector_top_icb = [icb for icb, _ in sorted_icb[:MONTHLY_SECTOR_TOP_N]]

    for symbol in symbols:
        if horizon in ("weekly", "all"):
            screened = _screen_weekly(session, symbol, as_of=as_of_date)
            if screened and screened.alpha_score >= 75:  # 3/4 criteria passed
                results["weekly"].append(screened)

        if horizon in ("monthly", "all"):
            screened = _screen_monthly(
                session, symbol, sector_top_icb, as_of=as_of_date
            )
            if screened and screened.alpha_score >= 66:  # 2/3 criteria passed
                results["monthly"].append(screened)

        if horizon in ("quarterly", "all"):
            screened = _screen_quarterly(session, symbol, as_of=as_of_date)
            if screened and screened.alpha_score >= 75:  # 3/4 criteria passed
                results["quarterly"].append(screened)

    # Sort each basket by alpha_score descending
    for key in results:
        results[key].sort(key=lambda t: t.alpha_score, reverse=True)

    if record_journal:
        record_screener_forecasts(
            session, results, as_of=as_of_date, model_version=model_version
        )

    return results
