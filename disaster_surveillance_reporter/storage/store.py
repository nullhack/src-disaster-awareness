r"""Storage backend protocol and implementations.

.. note::
   The ``_derived_columns`` module handles ``incident_name`` and
   ``source_urls`` derivation from bundles — these are called during
   :meth:`StorageBackend.store` to populate :class:`Incident` fields.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import sqlite3
from datetime import date
from pathlib import Path
from typing import Protocol

from disaster_surveillance_reporter.types import Incident, IncidentBundle, RawRecord

logger = logging.getLogger(__name__)

_EVAL_NAMESPACE: dict[str, object] = {
    "IncidentBundle": IncidentBundle,
    "RawRecord": RawRecord,
    "datetime": dt,
}


class StorageBackend(Protocol):
    """Protocol for pluggable storage backends.

    Implementations: :class:`JSONLStore` (default), :class:`SQLiteStore`.
    """

    def store(self, bundles: list[IncidentBundle]) -> int:
        """Persist bundles, skip existing IDs, return count of new bundles stored."""
        ...

    def upsert(self, bundle: IncidentBundle) -> str:
        """Insert, update, or no-op a bundle. Returns "inserted", "updated", or "noop"."""
        ...

    def get_last_updated(self, incident_id: str) -> dt.datetime | None:
        """Return the last_updated timestamp for *incident_id*, or None if not found."""
        ...

    def get_source_fingerprints(self, incident_id: str) -> list[str]:
        """Return stored source fingerprints for *incident_id*, or empty list."""
        ...

    def exists_by_source_fingerprint(self, fingerprint: str) -> bool:
        """Return True if *fingerprint* is stored in any bundle."""
        ...

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
        ...

    def exists(self, incident_id: str) -> bool:
        """Return ``True`` if *incident_id* is already stored.  No side effects."""
        ...


class JSONLStore:
    r"""Append-only, date-partitioned JSONL storage backend.

    Complete :class:`IncidentBundle`\\ s are written to
    ``{base_path}/incidents/by-date/{classification_date}/incidents.jsonl`` using a
    temp-file-and-rename strategy for atomic writes.

    :class:`Incident`\\ s returned by :meth:`query` are flattened — no
    ``raw_records`` field is present.  Malformed JSONL lines are logged and
    skipped.
    """

    def __init__(self, base_path: Path) -> None:
        """Create a JSONL store at *base_path*."""
        self.base_path = Path(base_path)

    # ------------------------------------------------------------------
    #  storage protocol
    # ------------------------------------------------------------------

    def store(self, bundles: list[IncidentBundle]) -> int:
        """Store bundles to JSONL, returning count of new bundles."""
        stored = 0
        for bundle in bundles:
            if self.exists(bundle.incident_id):
                continue
            cls_date = bundle.classification_date or dt.now(tz=dt.timezone.utc).date()
            partition_dir = (
                self.base_path / "incidents" / "by-date" / cls_date.isoformat()
            )
            partition_dir.mkdir(parents=True, exist_ok=True)
            jsonl_path = partition_dir / "incidents.jsonl"
            line = json.dumps(bundle, default=str) + "\n"
            # Atomic append via temp-file-and-rename
            tmp_path = jsonl_path.with_suffix(jsonl_path.suffix + ".tmp")
            try:
                existing = jsonl_path.read_text() if jsonl_path.exists() else ""
                tmp_path.write_text(existing + line)
                tmp_path.rename(jsonl_path)
            except Exception:
                if tmp_path.exists():
                    tmp_path.unlink(missing_ok=True)
                raise
            stored += 1
        return stored

    def query(
        self,
        date_from: date,
        date_to: date,
        **filters: str | bool,
    ) -> list[Incident]:
        """Query stored incidents by date range and filters."""
        if date_from > date_to:
            return []

        results: list[Incident] = []
        curr = date_from
        while curr <= date_to:
            jsonl_path = (
                self.base_path
                / "incidents"
                / "by-date"
                / curr.isoformat()
                / "incidents.jsonl"
            )
            if jsonl_path.exists():
                for line in jsonl_path.read_text().splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        parsed = json.loads(line)
                    except json.JSONDecodeError:
                        logger.warning("Skipping malformed JSONL line")
                        continue
                    try:
                        bundle = self._reconstruct_bundle(parsed)
                    except Exception:
                        logger.warning("Skipping unparseable JSONL line")
                        continue
                    if bundle is None:
                        continue
                    incident = _bundle_to_incident(bundle)
                    if _matches_filters(incident, filters):
                        results.append(incident)
            curr = date.fromordinal(curr.toordinal() + 1)

        return results

    def exists(self, incident_id: str) -> bool:
        """Check if *incident_id* has been stored."""
        base = self.base_path / "incidents" / "by-date"
        if not base.exists():
            return False
        for date_dir in base.iterdir():
            jsonl_path = date_dir / "incidents.jsonl"
            if jsonl_path.exists() and _incident_in_file(incident_id, jsonl_path):
                return True
        return False

    def upsert(self, bundle: IncidentBundle) -> str:
        raise NotImplementedError

    def get_last_updated(self, incident_id: str) -> dt.datetime | None:
        raise NotImplementedError

    def get_source_fingerprints(self, incident_id: str) -> list[str]:
        raise NotImplementedError

    def exists_by_source_fingerprint(self, fingerprint: str) -> bool:
        raise NotImplementedError

    # ------------------------------------------------------------------
    #  helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _reconstruct_bundle(parsed: str) -> IncidentBundle | None:
        if isinstance(parsed, str):
            return eval(parsed, {"__builtins__": {}}, _EVAL_NAMESPACE)  # noqa: S307
        return None


class SQLiteStore:
    """SQLite storage backend with per-bundle atomic transactions.

    Implements the same :class:`StorageBackend` protocol as
    :class:`JSONLStore`.  Uses ``sqlite3`` from the standard library.
    """

    def __init__(self, db_path: Path) -> None:
        """Create a SQLite store at *db_path*."""
        self._conn = sqlite3.connect(str(db_path))
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS incidents ("
            "  incident_id TEXT PRIMARY KEY,"
            "  bundle_json TEXT NOT NULL,"
            "  classification_date TEXT NOT NULL"
            ")"
        )
        self._conn.commit()

    def store(self, bundles: list[IncidentBundle]) -> int:
        """Store bundles to JSONL, returning count of new bundles."""
        stored = 0
        for bundle in bundles:
            if self.exists(bundle.incident_id):
                continue
            bundle_json = json.dumps(bundle, default=str)
            cls_date = (
                bundle.classification_date or dt.now(tz=dt.timezone.utc).date()
            ).isoformat()
            self._conn.execute(
                "INSERT INTO incidents (incident_id, bundle_json, classification_date)"
                " VALUES (?, ?, ?)",
                (bundle.incident_id, bundle_json, cls_date),
            )
            self._conn.commit()
            stored += 1
        return stored

    def query(
        self,
        date_from: date,
        date_to: date,
        **filters: str | bool,
    ) -> list[Incident]:
        """Query stored incidents by date range and filters."""
        if date_from > date_to:
            return []

        results: list[Incident] = []
        rows = self._conn.execute(
            "SELECT bundle_json FROM incidents"
            " WHERE classification_date >= ? AND classification_date <= ?",
            (date_from.isoformat(), date_to.isoformat()),
        ).fetchall()

        for (bundle_json,) in rows:
            parsed = json.loads(bundle_json)
            bundle = JSONLStore._reconstruct_bundle(parsed)
            if bundle is None:
                logger.warning("Skipping unparseable stored line")
                continue
            incident = _bundle_to_incident(bundle)
            if _matches_filters(incident, filters):
                results.append(incident)

        return results

    def exists(self, incident_id: str) -> bool:
        """Check if *incident_id* has been stored."""
        row = self._conn.execute(
            "SELECT 1 FROM incidents WHERE incident_id = ?", (incident_id,)
        ).fetchone()
        return row is not None

    def upsert(self, bundle: IncidentBundle) -> str:
        raise NotImplementedError

    def get_last_updated(self, incident_id: str) -> dt.datetime | None:
        raise NotImplementedError

    def get_source_fingerprints(self, incident_id: str) -> list[str]:
        raise NotImplementedError

    def exists_by_source_fingerprint(self, fingerprint: str) -> bool:
        raise NotImplementedError


# =====================================================================
#  Stand-alone helpers (shared by both stores)
# =====================================================================

_SOURCE_PRIORITY = ["GDACS", "WHO", "GDELT", "DDG-NEWS"]


def _derive_incident_name(records: list[RawRecord]) -> str:
    """Return the title from the highest-reliability source record."""
    for source in _SOURCE_PRIORITY:
        for record in records:
            if record.source_name != source:
                continue
            if source == "GDACS":
                title = record.raw_fields.get("title")
                if title:
                    return title
            elif source == "WHO":
                title = record.raw_fields.get("ReportTitle")
                if title:
                    return title
            elif source in ("GDELT", "DDG-NEWS"):
                title = record.raw_fields.get("title")
                if title:
                    return title
    return ""


def _derive_source_urls(records: list[RawRecord]) -> list[str]:
    """Collect source URLs following source-specific extraction rules."""
    urls: list[str] = []
    for record in records:
        source = record.source_name
        if source == "GDACS":
            url = record.raw_fields.get("url", {}).get("report")
            if url:
                urls.append(url)
        elif source == "WHO":
            item = record.raw_fields.get("ItemDefaultUrl")
            if item:
                urls.append("https://www.who.int" + item)
        elif source in ("GDELT", "DDG-NEWS"):
            url = record.raw_fields.get("url")
            if url:
                urls.append(url)
    return urls


def _bundle_to_incident(bundle: IncidentBundle) -> Incident:
    """Flatten an :class:`IncidentBundle` into an :class:`Incident`."""
    return Incident(
        incident_id=bundle.incident_id,
        source_names=[r.source_name for r in bundle.records],
        incident_name=_derive_incident_name(bundle.records),
        country=bundle.country,
        country_code=bundle.country_code,
        country_group=bundle.country_group or "C",
        disaster_type=bundle.disaster_type,
        incident_level=bundle.incident_level or 1,
        priority=bundle.priority or "LOW",
        should_report=bundle.should_report or False,
        overrides=bundle.overrides,
        report_date=bundle.classification_date or dt.now(tz=dt.timezone.utc).date(),
        source_urls=_derive_source_urls(bundle.records),
        summary=bundle.summary,
        rationale=bundle.rationale,
        estimated_affected=bundle.estimated_affected,
        estimated_deaths=bundle.estimated_deaths,
        ai_enriched=bundle.ai_enriched or False,
        record_count=len(bundle.records),
    )


def _matches_filters(incident: Incident, filters: dict[str, str | bool]) -> bool:
    """Return ``True`` if *incident* matches all supplied filters."""
    for key, value in filters.items():
        if key == "source_name":
            if value not in incident.source_names:
                return False
        elif getattr(incident, key, None) != value:
            return False
    return True


def _incident_in_file(incident_id: str, path: Path) -> bool:
    """Check whether *incident_id* appears anywhere in *path*."""
    try:
        return incident_id in path.read_text()
    except Exception:
        return False
