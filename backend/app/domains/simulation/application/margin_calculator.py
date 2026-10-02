"""VSDC Margin Calculator for paper trading (isolated, RULE 1 & 2).

Implements Initial Margin (IM), Maintenance Margin (MM), and force-liquidation
thresholds for VN30F1M index futures. Pure functions with no I/O — safe to
reuse in engines, tests, and routers.

Parameters (Vietnam VSDC):
- IM rate: 17%
- MM rate: 13%
- Force liquidation when margin ratio < 10%
- VN30F1M multiplier: 100,000 VND per index point

These are simulation defaults; real brokerages may differ (RULE 4).
"""

from __future__ import annotations

from app.core.enums import DERIVATIVE_MULTIPLIER
from app.domains.simulation.domain.exceptions import SimulationError

INITIAL_MARGIN_RATE = 0.17
MAINTENANCE_MARGIN_RATE = 0.13
FORCE_LIQUIDATION_RATIO = 0.10
VN30F1M_MULTIPLIER = float(DERIVATIVE_MULTIPLIER)  # 100_000.0

STATUS_SAFE = "SAFE"
STATUS_CALL_MARGIN = "CALL_MARGIN"
STATUS_FORCE_LIQUIDATION = "FORCE_LIQUIDATION"


def calculate_required_margin(
    contracts: int, price: float, im_rate: float = INITIAL_MARGIN_RATE
) -> float:
    """Return the required initial margin for a futures position.

    Required = contracts × price × multiplier × im_rate
    """
    if contracts <= 0 or price <= 0:
        return 0.0
    return contracts * price * VN30F1M_MULTIPLIER * im_rate


def calculate_unrealized_pnl(
    side: str, contracts: int, entry_price: float, current_price: float
) -> float:
    """Return unrealized PnL for a futures position.

    LONG: (current − entry); SHORT: (entry − current); multiplied by
    contracts × multiplier. Unknown side raises ``SimulationError``.
    """
    if side in ("LONG", "BUY", "B"):
        direction = 1
    elif side in ("SHORT", "SELL", "S"):
        direction = -1
    else:
        raise SimulationError(f"Unknown position side: {side}")
    diff = (current_price - entry_price) * direction
    return diff * contracts * VN30F1M_MULTIPLIER


def check_margin_status(equity: float, total_position_value: float) -> str:
    """Return the margin status (SAFE / CALL_MARGIN / FORCE_LIQUIDATION).

    ``margin_ratio = equity / total_position_value``.
    - total_pv <= 0 → SAFE (no positions)
    - ratio < 0.10 → FORCE_LIQUIDATION
    - ratio < 0.13 → CALL_MARGIN
    - otherwise → SAFE
    """
    if total_position_value <= 0:
        return STATUS_SAFE
    ratio = equity / total_position_value
    if ratio < FORCE_LIQUIDATION_RATIO:
        return STATUS_FORCE_LIQUIDATION
    if ratio < MAINTENANCE_MARGIN_RATE:
        return STATUS_CALL_MARGIN
    return STATUS_SAFE


def compute_margin_ratio(equity: float, total_position_value: float) -> float | None:
    """Return margin_ratio or None when there is no position value (D8)."""
    if total_position_value <= 0:
        return None
    return equity / total_position_value


def total_derivative_position_value(
    positions: list, multiplier: float = VN30F1M_MULTIPLIER
) -> float:
    """Sum qty × current_price × multiplier over open derivative positions."""
    total = 0.0
    for pos in positions:
        total += pos.quantity * pos.current_price * multiplier
    return total
