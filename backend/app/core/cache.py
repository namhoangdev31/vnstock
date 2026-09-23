"""Simple TTL (Time-To-Live) in-memory cache for core system.

Designed for realtime price data caching (3-5s TTL) and metadata caching.
Can be swapped to Redis later for multi-instance deployments.
"""

from __future__ import annotations

import time
from typing import Any


class TTLCache:
    """Thread-safe in-memory cache with per-key TTL."""

    def __init__(self, default_ttl: int = 5) -> None:
        self._store: dict[str, tuple[Any, float]] = {}
        self.default_ttl = default_ttl

    def get(self, key: str) -> Any | None:
        """Return cached value if exists and not expired, else None."""
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if time.monotonic() > expires_at:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Store a value with optional custom TTL (seconds)."""
        effective_ttl = ttl if ttl is not None else self.default_ttl
        self._store[key] = (value, time.monotonic() + effective_ttl)

    def invalidate(self, key: str) -> None:
        """Remove a specific key from cache."""
        self._store.pop(key, None)

    def clear(self) -> None:
        """Remove all entries."""
        self._store.clear()

    def cleanup(self) -> int:
        """Remove all expired entries. Returns count of removed entries."""
        now = time.monotonic()
        expired_keys = [k for k, (_, exp) in self._store.items() if now > exp]
        for k in expired_keys:
            del self._store[k]
        return len(expired_keys)


# Singleton instances for different cache tiers
realtime_cache = TTLCache(default_ttl=5)  # 3-5 seconds for realtime prices
metadata_cache = TTLCache(default_ttl=86400)  # 24 hours for metadata
