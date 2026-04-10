"""Storage backends for incident data.

This module provides pluggable storage backends for persisting incident records.
"""

from typing import Protocol


class StorageBackend(Protocol):
    """Protocol for storage backends."""

    def write(self, incidents: list[dict]) -> None:
        """Write incidents to storage."""
        raise NotImplementedError

    def read(self) -> list[dict]:
        """Read all incidents from storage."""
        raise NotImplementedError

    def append(self, incidents: list[dict]) -> None:
        """Append new incidents to existing storage."""
        raise NotImplementedError


# Import backends
from .jsonl import JSONLBackend  # noqa: F401
from .google_sheets import GoogleSheetsBackend  # noqa: F401
from .email_reporter import EmailReporter  # noqa: F401
