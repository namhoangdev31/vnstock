"""Exceptions for Vnstock Domain package."""


class VnstockServiceError(Exception):
    """Ngoại lệ phát sinh khi tất cả các nguồn dữ liệu vnstock đều thất bại."""


__all__ = ["VnstockServiceError"]
