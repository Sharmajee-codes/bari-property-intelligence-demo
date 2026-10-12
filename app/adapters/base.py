from typing import Protocol

from app.schemas import Snapshot


class TransientSourceError(Exception):
    """Retryable acquisition failure, distinct from invalid source content."""


class SourceAdapter(Protocol):
    def collect(self) -> Snapshot:
        """Return a scoped snapshot; mark completeness only when independently established."""
        ...
