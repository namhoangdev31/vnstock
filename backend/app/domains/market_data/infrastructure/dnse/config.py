"""DNSE WebSocket stream configuration.

Encapsulates authentication and connection parameters for the DNSE WebSocket
market data streaming gateway.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.core.config import settings


@dataclass
class DNSEStreamConfig:
    """Configuration options for DNSE WebSocket streaming."""

    api_key: str = ""
    api_secret: str = ""
    ws_url: str = "wss://ws-openapi.dnse.com.vn"
    symbols: list[str] = field(default_factory=list)
    market_indices: list[str] = field(default_factory=list)
    reconnect_delay: float = 5.0
    max_retries: int = 10
    heartbeat_interval: float = 25.0

    @classmethod
    def from_settings(cls) -> DNSEStreamConfig:
        """Construct configuration instance from application settings."""
        symbols_raw = settings.DNSE_WS_SYMBOLS or ""
        symbols = [s.strip().upper() for s in symbols_raw.split(",") if s.strip()]

        indices_raw = settings.DNSE_WS_MARKET_INDICES or ""
        indices = [i.strip().upper() for i in indices_raw.split(",") if i.strip()]

        return cls(
            api_key=settings.DNSE_API_KEY or "",
            api_secret=settings.DNSE_API_SECRET or "",
            ws_url=settings.DNSE_WS_URL,
            symbols=symbols,
            market_indices=indices,
            reconnect_delay=settings.DNSE_WS_RECONNECT_DELAY,
            max_retries=settings.DNSE_WS_MAX_RETRIES,
            heartbeat_interval=settings.DNSE_WS_HEARTBEAT,
        )

    @property
    def is_configured(self) -> bool:
        """Check whether minimum required credentials (key and secret) are provided."""
        return bool(self.api_key.strip() and self.api_secret.strip())
