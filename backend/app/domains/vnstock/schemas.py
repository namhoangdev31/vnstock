"""Schemas for Vnstock Domain package."""

from __future__ import annotations

from sqlmodel import SQLModel


class VnstockSymbolResponse(SQLModel):
    symbol: str
    organ_name: str | None = None
    exchange: str | None = None


__all__ = ["VnstockSymbolResponse"]
