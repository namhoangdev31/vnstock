"""Read-only, source-backed projections for the Phase 6 trading cockpit.

This router intentionally never calls the signal-generation endpoint.  It reads
the persisted quant tables and the existing market-data services, so refreshing
the cockpit cannot create a forecast-journal entry.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

import numpy as np
from fastapi import APIRouter, Query
from sqlmodel import col, select

from app.api.deps import CurrentUser, SessionDep
from app.core.models_base import VN_TZ
from app.domains.market_data.application.iboard_service import IBoardService
from app.domains.market_data.domain.models import StockOHLCVDaily
from app.domains.quant.application.engines.flow_engine import FlowLiquidityEngine
from app.domains.quant.application.engines.quant_ml_engine import QuantMLEngine
from app.domains.quant.application.engines.technical_engine import TechnicalEngine
from app.domains.quant.domain.models import (
    ForecastJournal,
    InstitutionalFlow,
    MacroIndicator,
    MarketBreadth,
    SignalLog,
    TickFlowAggregated,
)

router = APIRouter(prefix="/quant/cockpit", tags=["quant-cockpit"])


def _availability(value: Any, reason: str = "") -> dict[str, Any]:
    return {"available": value is not None, "reason": reason if value is None else None}


def _latest_price(session: Any, symbol: str) -> float | None:
    bar = session.exec(
        select(StockOHLCVDaily)
        .where(StockOHLCVDaily.symbol == symbol.upper())
        .order_by(col(StockOHLCVDaily.trading_date).desc())
        .limit(1)
    ).first()
    return float(bar.close) if bar is not None else None


def _monte_carlo_histogram(
    current: float | None, volatility: float
) -> list[dict[str, float]]:
    if current is None or current <= 0:
        return []
    simulations = 10_000
    steps = 8
    effective_volatility = max(0.05, min(0.60, volatility or 0.20))
    rng = np.random.default_rng(42)
    increments = np.exp(
        (-0.5 * effective_volatility**2) / (252 * steps)
        + effective_volatility
        / np.sqrt(252 * steps)
        * rng.standard_normal((simulations, steps))
    )
    paths = current * np.cumprod(increments, axis=1)
    finals = np.clip(paths[:, -1], current * 0.93, current * 1.07)
    counts, edges = np.histogram(
        finals, bins=20, range=(current * 0.93, current * 1.07)
    )
    total = float(counts.sum())
    return [
        {
            "price": float((edges[index] + edges[index + 1]) / 2),
            "probability": float(count / total),
        }
        for index, count in enumerate(counts)
    ]


@router.get("/derivatives")
def derivatives_snapshot(
    session: SessionDep,
    _current_user: CurrentUser,
    symbol: str = Query(default="VN30F1M", min_length=1, max_length=20),
    timeframe: str = Query(default="1m", pattern="^(1m|5m|15m)$"),
    limit: int = Query(default=120, ge=20, le=300),
) -> dict[str, Any]:
    symbol = symbol.upper()
    bars = IBoardService.get_candles(session, symbol, timeframe, limit)
    futures = _latest_price(session, symbol)
    spot = _latest_price(session, "VN30")
    technical = TechnicalEngine(session=session).analyze(symbol=symbol)
    quant = QuantMLEngine(session=session).analyze(
        symbol=symbol,
        futures_price=futures or 0.0,
        spot_index_price=spot or 0.0,
    )
    tick_rows = session.exec(
        select(TickFlowAggregated)
        .where(TickFlowAggregated.symbol == symbol)
        .order_by(col(TickFlowAggregated.interval_start).desc())
        .limit(limit)
    ).all()
    signal = session.exec(
        select(SignalLog)
        .where(SignalLog.symbol == symbol)
        .order_by(col(SignalLog.created_at).desc())
        .limit(1)
    ).first()
    latest_bar = session.exec(
        select(StockOHLCVDaily)
        .where(StockOHLCVDaily.symbol == symbol)
        .order_by(col(StockOHLCVDaily.trading_date).desc())
        .limit(1)
    ).first()
    reference = float(latest_bar.close) if latest_bar is not None else None
    return {
        "symbol": symbol,
        "as_of": datetime.now(VN_TZ),
        "session_phase": quant.session_phase,
        "quote": {
            "price": futures,
            "reference": reference,
            "change": (futures - reference)
            if futures is not None and reference
            else None,
            "change_percent": ((futures / reference) - 1) * 100
            if futures and reference
            else None,
            "ceiling": reference * 1.07 if reference else None,
            "floor": reference * 0.93 if reference else None,
        },
        "basis": {
            "value": quant.basis_value,
            "zscore": quant.basis_zscore,
            "spot": spot,
        },
        "technical": {
            "vwap": technical.vwap,
            "bollinger": technical.macd,
            "rsi": technical.rsi,
            "atr": technical.camarilla_levels.get("atr"),
        },
        "candles": [bar.model_dump() for bar in bars],
        "orderflow": [
            {
                "time": row.interval_start,
                "buy_volume": row.aggressive_buy_volume,
                "sell_volume": row.aggressive_sell_volume,
                "delta": row.volume_delta,
                "vwap": row.vwap,
            }
            for row in reversed(tick_rows)
        ],
        "signal": (
            {
                "direction": signal.signal_type,
                "entry": signal.action_price,
                "stop_loss": signal.stop_loss,
                "take_profit": signal.take_profit,
                "trailing_stop": signal.metadata_info.get("trailing_stop"),
                "confidence": signal.strength,
                "created_at": signal.created_at,
            }
            if signal is not None
            else None
        ),
        "disclaimer": "Dữ liệu phục vụ nghiên cứu và mô phỏng, không phải khuyến nghị đầu tư.",
    }


@router.get("/flow-radar")
def flow_radar_snapshot(
    session: SessionDep,
    _current_user: CurrentUser,
) -> dict[str, Any]:
    today = date.today()
    flows = session.exec(
        select(InstitutionalFlow)
        .where(InstitutionalFlow.trading_date >= today - timedelta(days=30))
        .order_by(col(InstitutionalFlow.trading_date))
    ).all()
    latest_breadth = session.exec(
        select(MarketBreadth)
        .where(MarketBreadth.exchange == "HOSE")
        .order_by(col(MarketBreadth.trading_date).desc())
        .limit(1)
    ).first()
    macro_rows = session.exec(
        select(MacroIndicator)
        .order_by(col(MacroIndicator.recorded_date).desc())
        .limit(20)
    ).all()
    engine = FlowLiquidityEngine(session=session).analyze()
    return {
        "as_of": datetime.now(VN_TZ),
        "engine": engine.model_dump(),
        "flows": [row.model_dump() for row in flows],
        "breadth": latest_breadth.model_dump() if latest_breadth else None,
        "macro": [row.model_dump() for row in macro_rows],
        "availability": {
            "flows": _availability(flows, "Chưa có dữ liệu dòng tiền tổ chức"),
            "breadth": _availability(latest_breadth, "Chưa có dữ liệu độ rộng HOSE"),
            "macro": _availability(macro_rows, "Chưa có dữ liệu tỷ giá hoặc vàng"),
        },
    }


@router.get("/prediction")
def prediction_snapshot(
    session: SessionDep,
    _current_user: CurrentUser,
    symbol: str = Query(default="VN30F1M", min_length=1, max_length=20),
) -> dict[str, Any]:
    symbol = symbol.upper()
    current = _latest_price(session, symbol)
    quant = QuantMLEngine(session=session).analyze(
        symbol=symbol, futures_price=current or 0.0
    )
    targets = quant.monte_carlo_targets or {}
    forecast_rows = session.exec(
        select(ForecastJournal)
        .where(ForecastJournal.symbol == symbol)
        .order_by(col(ForecastJournal.predicted_at).desc())
        .limit(50)
    ).all()
    return {
        "symbol": symbol,
        "as_of": datetime.now(VN_TZ),
        "current_price": current,
        "price_limits": {
            "floor": current * 0.93 if current else None,
            "ceiling": current * 1.07 if current else None,
        },
        "atc": {"available": False, "reason": "ATC imbalance feed chưa được persisted"},
        "monte_carlo": {
            "available": bool(targets),
            "simulations": 10000,
            "p10": targets.get("p05"),
            "p50": targets.get("p50"),
            "p90": targets.get("p95"),
            "histogram": _monte_carlo_histogram(current, quant.historical_vol),
            "reason": None if targets else "Chưa có kết quả mô phỏng",
        },
        "ledger": [row.model_dump() for row in forecast_rows],
        "disclaimer": "Dải xác suất chỉ phục vụ nghiên cứu mô phỏng và không bảo đảm kết quả thực tế.",
    }
