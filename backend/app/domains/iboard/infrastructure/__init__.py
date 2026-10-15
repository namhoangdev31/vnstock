"""Infrastructure layer for iBoard."""

from app.domains.iboard.infrastructure.external_indices import (
    IBoardDataGateway,
    IndexSparklineGateway,
)

__all__ = [
    "IBoardDataGateway",
    "IndexSparklineGateway",
]
