"""Storage backend protocol and implementations.

.. note::
   The ``_derived_columns`` module handles ``incident_name`` and
   ``source_urls`` derivation from bundles — these are called during
   :meth:`StorageBackend.store` to populate :class:`Incident` fields.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Protocol

from disaster_surveillance_reporter.types import Incident, IncidentBundle


class StorageBackend(Protocol):
    """Protocol for pluggable storage backends.

    Implementations: :class:`JSONLStore` (default), :class:`SQLiteStore`.
    """

    def store(self, bundles: list[IncidentBundle]) -> int:
        """Persist bundles, skip existing IDs, return count of new bundles stored."""
        raise NotImplementedError

    def query(
        self,
        date_from: date,
        date_to: date,
        **filters: str | bool,
    ) -> list[Incident]:
        """Return flattened :class:`Incident` records matching date range and filters.

        Filters: ``country_group``, ``disaster_type``, ``priority``,
        ``should_report``, ``source_name``.  When *date_from > date_to*, return
        an empty list without error.
        """
        raise NotImplementedError

    def exists(self, incident_id: str) -> bool:
        """Return ``True`` if *incident_id* is already stored.  No side effects."""
        raise NotImplementedError


class JSONLStore:
    """Append-only, date-partitioned JSONL storage backend.

    Complete :class:`IncidentBundle`\\ s are written to
    ``{base_path}/by-date/{classification_date}/incidents.jsonl`` using a
    temp-file-and-rename strategy for atomic writes.

    :class:`Incident`\\ s returned by :meth:`query` are flattened — no
    ``raw_records`` field is present.  Malformed JSONL lines are logged and
    skipped.
    """

    def __init__(self, base_path: Path) -> None:
        raise NotImplementedError

    def store(self, bundles: list[IncidentBundle]) -> int:
        raise NotImplementedError

    def query(
        self,
        date_from: date,
        date_to: date,
        **filters: str | bool,
    ) -> list[Incident]:
        raise NotImplementedError

    def exists(self, incident_id: str) -> bool:
        raise NotImplementedError


class SQLiteStore:
    """SQLite storage backend with per-bundle atomic transactions.

    Implements the same :class:`StorageBackend` protocol as
    :class:`JSONLStore`.  Uses ``sqlite3`` from the standard library.
    """

    def __init__(self, db_path: Path) -> None:
        raise NotImplementedError

    def store(self, bundles: list[IncidentBundle]) -> int:
        raise NotImplementedError

    def query(
        self,
        date_from: date,
        date_to: date,
        **filters: str | bool,
    ) -> list[Incident]:
        raise NotImplementedError

    def exists(self, incident_id: str) -> bool:
        raise NotImplementedError
