"""Storage backends for incident data.

This module provides pluggable storage backends for persisting
:class:`~disaster_surveillance_reporter.types.IncidentBundle`\\ s and
querying flattened :class:`~disaster_surveillance_reporter.types.Incident`
records.
"""

from .store import JSONLStore, SQLiteStore, StorageBackend, get_storage_backend  # noqa: F401
