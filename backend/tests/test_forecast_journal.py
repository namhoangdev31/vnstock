"""ForecastJournalService tests — TEST-JRN-01/02/03 (RULE 3 audit ledger)."""

from datetime import datetime, timedelta

import pytest

from app.core.enums import ForecastDirection, ForecastHorizon, ForecastStatus
from app.domains.quant.application.forecast_journal_service import (
    ForecastJournalError,
    ForecastJournalService,
)
from tests.utils.phase1 import as_utc as _as_utc  # noqa: F401
from tests.utils.phase1 import session, sqlite_engine, utc_now  # noqa: F401


def test_record_defaults_to_pending_with_required_fields(session) -> None:  # noqa: F811
    """TEST-JRN-01: status=pending; predicted_at/engine_weights/model_version set."""
    svc = ForecastJournalService(session)
    entry = svc.record(
        symbol="VN30F1M",
        predicted_at=utc_now(),
        model_version="v1.0.0-alpha",
        horizon=ForecastHorizon.ATC,
        predicted_value=1350.0,
        predicted_direction=ForecastDirection.BULLISH,
        engine_weights={"e1": 0.5, "e2": 0.3, "e3": 0.2},
    )
    assert entry.status == ForecastStatus.PENDING
    assert entry.model_version == "v1.0.0-alpha"
    assert entry.engine_weights["e1"] == 0.5
    assert entry.actual_value is None
    assert entry.score is None


def test_record_rejects_naive_predicted_at(session) -> None:  # noqa: F811
    """RULE 3 / TEST-DB-03: naive predicted_at must be rejected."""
    svc = ForecastJournalService(session)
    with pytest.raises(ForecastJournalError, match="timezone-aware"):
        svc.record(
            symbol="VN30F1M",
            predicted_at=datetime(2026, 9, 17, 10, 0, 0),  # naive
            model_version="v1",
        )


def test_resolve_preserves_predicted_at(session) -> None:  # noqa: F811
    """TEST-JRN-02: resolve sets actual_* + realized_at, never touches predicted_at."""
    svc = ForecastJournalService(session)
    predicted_at = utc_now() - timedelta(hours=1)
    entry = svc.record(
        symbol="VN30F1M",
        predicted_at=predicted_at,
        model_version="v1",
        predicted_value=1300.0,
        predicted_direction=ForecastDirection.BULLISH,
    )
    resolved = svc.resolve(
        entry.id, actual_value=1310.0, actual_direction=ForecastDirection.BULLISH
    )
    assert resolved.status == ForecastStatus.RESOLVED
    assert resolved.actual_value == 1310.0
    assert resolved.realized_at is not None
    # No-look-ahead anchor unchanged. Compare on UTC instants because some
    # dialects (SQLite) drop tzinfo on round-trip; Postgres preserves it.
    assert _as_utc(resolved.predicted_at) == _as_utc(predicted_at)
    assert resolved.predicted_value == 1300.0


def test_resolve_blocks_when_already_scored(session) -> None:  # noqa: F811
    svc = ForecastJournalService(session)
    entry = svc.record(
        symbol="FPT",
        predicted_at=utc_now(),
        model_version="v1",
        predicted_value=100.0,
        predicted_direction=ForecastDirection.BULLISH,
    )
    svc.resolve(
        entry.id, actual_value=105.0, actual_direction=ForecastDirection.BULLISH
    )
    svc.score(entry.id)
    with pytest.raises(ForecastJournalError, match="already scored"):
        svc.resolve(entry.id, actual_value=110.0, actual_direction="BULLISH")


def test_score_computes_mae_and_direction(session) -> None:  # noqa: F811
    """TEST-JRN-03: MAE = |predicted - actual|; directional accuracy computed."""
    svc = ForecastJournalService(session)
    entry = svc.record(
        symbol="VN30F1M",
        predicted_at=utc_now(),
        model_version="v1",
        predicted_value=1300.0,
        predicted_direction=ForecastDirection.BULLISH,
    )
    svc.resolve(entry.id, actual_value=1310.0, actual_direction="BULLISH")
    scored = svc.score(entry.id)
    assert scored.status == ForecastStatus.SCORED
    assert scored.error == pytest.approx(10.0)  # MAE
    assert scored.score == pytest.approx(1.0)  # correct direction


def test_score_before_resolve_is_blocked(session) -> None:  # noqa: F811
    svc = ForecastJournalService(session)
    entry = svc.record(symbol="FPT", predicted_at=utc_now(), model_version="v1")
    with pytest.raises(ForecastJournalError, match="still pending"):
        svc.score(entry.id)


def test_aggregate_across_scored(session) -> None:  # noqa: F811
    """Aggregate MAE + directional accuracy over multiple scored forecasts."""
    svc = ForecastJournalService(session)
    # Two correct-direction, one wrong-direction
    for sym, pred, actual, pdir, adir in [
        ("A", 100.0, 110.0, "BULLISH", "BULLISH"),
        ("B", 200.0, 190.0, "BEARISH", "BEARISH"),
        ("C", 300.0, 310.0, "BEARISH", "BULLISH"),
    ]:
        e = svc.record(
            symbol=sym,
            predicted_at=utc_now(),
            model_version="v1",
            predicted_value=pred,
            predicted_direction=pdir,
        )
        svc.resolve(e.id, actual_value=actual, actual_direction=adir)
        svc.score(e.id)
    agg = svc.aggregate()
    assert agg["count"] == 3
    assert agg["mae"] == pytest.approx(10.0)  # (10+10+10)/3
    assert agg["directional_accuracy"] == pytest.approx(2 / 3)
