"""Dynamic symbol registry for multi-asset daemon polling.

Manages the set of active symbols the daemon polls, partitioned by asset class:
- DERIVATIVES: VN30F1M (T+0), always active during derivatives session
- EQUITY: user-registered watchlists and index constituents (T+2)

Rules (AGENTS.md §6):
- Derivatives: VN30F1M always in registry; session 08:45-14:45.
- Equities: polling respects T+2 settlement; intraday 09:00-14:45.
- Rate-limit budget: <=60 req/min total -> tier symbols by polling priority.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from app.core.models_base import VN_TZ

logger = logging.getLogger(__name__)

AssetClass = Literal["DERIVATIVE", "EQUITY", "MACRO"]

# Hard-coded tier priorities (lower = polled more frequently)
_DEFAULT_PRIORITY: dict[str, int] = {
    "DERIVATIVE": 1,
    "EQUITY": 2,
    "MACRO": 3,
}

# Symbols that are always registered regardless of user preferences
_ALWAYS_ON: list[tuple[str, str]] = [
    ("VN30F1M", "DERIVATIVE"),
]


@dataclass
class SymbolEntry:
    symbol: str
    asset_class: str
    priority: int = 2
    added_at: datetime = field(default_factory=lambda: datetime.now(VN_TZ))
    source: str = "system"  # "system" | "user" | "index"

    def __hash__(self) -> int:
        return hash(self.symbol)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, SymbolEntry):
            return self.symbol == other.symbol
        return NotImplemented


class SymbolRegistry:
    """Thread-safe registry of symbols the daemon should poll.

    The registry is populated from multiple sources:
    1. ``_ALWAYS_ON`` -- hard-coded system symbols (VN30F1M)
    2. ``register()`` -- dynamic additions (equity watchlists, index constituents)
    3. ``set_equity_universe()`` -- bulk update from VN30/VNINDEX listings

    ``get_active_symbols()`` returns an ordered list respecting priority tiers,
    capped by ``max_symbols`` to stay within the 60 req/min rate-limit budget.
    """

    def __init__(self, max_symbols: int = 40) -> None:
        self._lock = threading.Lock()
        self._entries: dict[str, SymbolEntry] = {}
        self.max_symbols = max_symbols
        self._bootstrap()

    def _bootstrap(self) -> None:
        for symbol, asset_class in _ALWAYS_ON:
            entry = SymbolEntry(
                symbol=symbol,
                asset_class=asset_class,
                priority=_DEFAULT_PRIORITY.get(asset_class, 2),
                source="system",
            )
            self._entries[symbol] = entry
        logger.debug(
            "SymbolRegistry bootstrapped with %d always-on symbols",
            len(self._entries),
        )

    # ------------------------------------------------------------------
    # Public write API
    # ------------------------------------------------------------------

    def register(
        self,
        symbol: str,
        asset_class: str = "EQUITY",
        priority: int | None = None,
        source: str = "system",
    ) -> None:
        """Register a single symbol. No-op if already registered."""
        resolved_priority = (
            priority if priority is not None else _DEFAULT_PRIORITY.get(asset_class, 2)
        )
        with self._lock:
            if symbol not in self._entries:
                self._entries[symbol] = SymbolEntry(
                    symbol=symbol,
                    asset_class=asset_class,
                    priority=resolved_priority,
                    source=source,
                )
                logger.debug("SymbolRegistry: registered %s (%s)", symbol, asset_class)

    def unregister(self, symbol: str) -> bool:
        """Remove a symbol. System symbols cannot be removed. Returns True if removed."""
        with self._lock:
            entry = self._entries.get(symbol)
            if entry is None:
                return False
            if entry.source == "system":
                logger.warning(
                    "SymbolRegistry: attempted to unregister system symbol %s -- ignored",
                    symbol,
                )
                return False
            del self._entries[symbol]
            logger.debug("SymbolRegistry: unregistered %s", symbol)
            return True

    def set_equity_universe(
        self,
        symbols: list[str],
        source: str = "index",
        priority: int = 2,
    ) -> None:
        """Bulk-replace the equity universe (non-system symbols) with *symbols*.

        System symbols (VN30F1M, etc.) are never removed.
        """
        with self._lock:
            # Remove stale non-system equity entries
            stale = [
                sym
                for sym, entry in self._entries.items()
                if entry.source != "system" and entry.asset_class == "EQUITY"
            ]
            for sym in stale:
                del self._entries[sym]

            # Add new ones
            for sym in symbols:
                if sym not in self._entries:
                    self._entries[sym] = SymbolEntry(
                        symbol=sym,
                        asset_class="EQUITY",
                        priority=priority,
                        source=source,
                    )
        logger.info(
            "SymbolRegistry: equity universe updated -- %d symbols (source=%s)",
            len(symbols),
            source,
        )

    # ------------------------------------------------------------------
    # Public read API
    # ------------------------------------------------------------------

    def get_active_symbols(
        self,
        asset_class: str | None = None,
        max_count: int | None = None,
    ) -> list[str]:
        """Return active symbols ordered by priority (lowest first).

        Args:
            asset_class: Filter by asset class. None = all classes.
            max_count: Cap on number of symbols (defaults to self.max_symbols).
        """
        cap = max_count if max_count is not None else self.max_symbols
        with self._lock:
            entries = list(self._entries.values())

        if asset_class is not None:
            entries = [e for e in entries if e.asset_class == asset_class]

        # Sort: priority ASC, then symbol name for determinism
        entries.sort(key=lambda e: (e.priority, e.symbol))
        return [e.symbol for e in entries[:cap]]

    def get_derivatives(self) -> list[str]:
        """Shortcut: return all registered derivatives symbols."""
        return self.get_active_symbols(asset_class="DERIVATIVE")

    def get_equities(self) -> list[str]:
        """Shortcut: return equity symbols within rate-limit budget."""
        n_derivatives = len(self.get_derivatives())
        return self.get_active_symbols(
            asset_class="EQUITY",
            max_count=max(0, self.max_symbols - n_derivatives),
        )

    def summary(self) -> dict[str, int]:
        """Return count by asset class."""
        with self._lock:
            counts: dict[str, int] = {}
            for entry in self._entries.values():
                counts[entry.asset_class] = counts.get(entry.asset_class, 0) + 1
        return counts

    def __len__(self) -> int:
        with self._lock:
            return len(self._entries)

    def __repr__(self) -> str:
        return f"SymbolRegistry(symbols={len(self)}, max={self.max_symbols})"
