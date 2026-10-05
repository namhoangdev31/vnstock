"""DNSE WebSocket integration infrastructure package."""

from __future__ import annotations

from app.domains.market_data.infrastructure.dnse.config import DNSEStreamConfig
from app.domains.market_data.infrastructure.dnse.stream_manager import DNSEStreamManager
from app.domains.market_data.infrastructure.dnse.tick_handler import TickNormalizer

_stream_manager: DNSEStreamManager | None = None


def get_dnse_stream_manager() -> DNSEStreamManager:
    """Return singleton instance of DNSEStreamManager initialized from current settings."""
    global _stream_manager
    if _stream_manager is None:
        cfg = DNSEStreamConfig.from_settings()
        _stream_manager = DNSEStreamManager(config=cfg)
    return _stream_manager


class _LazyStreamManagerProxy:
    """Lazy proxy allowing import of dnse_stream_manager before settings are fully initialized."""

    def __getattr__(self, name: str):
        return getattr(get_dnse_stream_manager(), name)


dnse_stream_manager = _LazyStreamManagerProxy()  # type: ignore[assignment]

__all__ = [
    "DNSEStreamConfig",
    "DNSEStreamManager",
    "TickNormalizer",
    "dnse_stream_manager",
    "get_dnse_stream_manager",
]
