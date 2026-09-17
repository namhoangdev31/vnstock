"""Domain enumerations and market constants for the quant & simulation layer.

Using ``str``-backed ``StrEnum`` lets SQLModel persist the value as a short
varchar while keeping the valid set explicit and type-checked. Internal field
names follow standard domain terminology (RULE 2) — no redundant prefixes.
"""

from enum import StrEnum


class ForecastHorizon(StrEnum):
    ATC = "ATC"
    T_PLUS_1 = "T_PLUS_1"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"


class ForecastDirection(StrEnum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


class ForecastStatus(StrEnum):
    PENDING = "pending"
    RESOLVED = "resolved"
    SCORED = "scored"


class OrderSide(StrEnum):
    BUY = "BUY"
    SELL = "SELL"
    LONG = "LONG"
    SHORT = "SHORT"


class OrderType(StrEnum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"


class OrderStatus(StrEnum):
    PENDING = "PENDING"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class PositionSide(StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"


class PositionStatus(StrEnum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class Exchange(StrEnum):
    HOSE = "HOSE"
    HNX = "HNX"
    UPCOM = "UPCOM"


class MacroIndicatorCode(StrEnum):
    USD_VND = "USD_VND"
    SJC_GOLD_BUY = "SJC_GOLD_BUY"
    SJC_GOLD_SELL = "SJC_GOLD_SELL"
    WORLD_GOLD = "WORLD_GOLD"


# --- Vietnamese market constants (AGENTS.md Section 6) ---

# VN30F1M index-futures contract multiplier (VND per index point).
DERIVATIVE_MULTIPLIER = 100_000

# Default simulated starting balance (VND).
DEFAULT_INITIAL_BALANCE = 100_000_000.0

# Settlement cycles: equities T+2, derivatives T+0 (intraday round-trip allowed).
EQUITY_SETTLEMENT_DAYS = 2
DERIVATIVE_SETTLEMENT_DAYS = 0
