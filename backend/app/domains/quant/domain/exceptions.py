"""Quant domain exceptions."""


class QuantEngineError(Exception):
    """Raised on invalid quant engine calculation or missing input."""


class ForecastJournalError(Exception):
    """Raised on invalid forecast-journal operations."""
