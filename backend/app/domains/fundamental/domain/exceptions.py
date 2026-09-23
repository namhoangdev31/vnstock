"""Domain exceptions for Fundamental & Corporate Analysis."""


class FundamentalError(Exception):
    """Base exception for all Fundamental domain errors."""


class ScreenerError(FundamentalError):
    """Exception raised when an error occurs during stock screening execution."""


class FinancialRevisionError(FundamentalError):
    """Exception raised when an error occurs during financial report revision or restatement processing."""
