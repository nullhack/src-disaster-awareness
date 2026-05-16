"""Domain types for the disaster surveillance reporter."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import ClassVar

import pycountry

_DISASTER_TYPE_CODE: dict[str, str] = {
    "Earthquake": "EQ",
    "Flood": "FL",
    "Cyclone": "TC",
    "Volcano": "VO",
    "Tsunami": "TS",
    "Drought": "DR",
    "Wildfire": "WF",
}


def _country_to_alpha2(name: str | None) -> str:
    if not name or name == "unknown":
        return "UNX"
    lookup = name.strip()
    try:
        return pycountry.countries.lookup(lookup).alpha_2
    except LookupError:
        return "UNX"


def _extract_source_date(record: RawRecord) -> datetime | None:
    """Extract the source-provided date from a RawRecord's raw_fields.

    Source date fields: GDACS fromdate, WHO PublicationDate,
    GDELT seendate, DDG-NEWS date.  Returns ``None`` if no
    source date is available or the date cannot be parsed.
    """
    source = record.source_name
    raw = record.raw_fields

    if source == "GDACS":
        date_str = raw.get("fromdate")
    elif source == "WHO":
        date_str = raw.get("PublicationDate")
    elif source == "GDELT":
        date_str = raw.get("seendate")
    elif source == "DDG-NEWS":
        date_str = raw.get("date")
    else:
        return None

    if not date_str:
        return None

    date_str = str(date_str)
    try:
        if source == "GDELT":
            return datetime.strptime(date_str, "%Y%m%dT%H%M%Sz")
        return datetime.fromisoformat(date_str)
    except (ValueError, TypeError):
        return None


def generate_source_fingerprint(record: RawRecord) -> str:
    """Generate ``{SOURCE_NAME}:{native_id}`` for a single source record.

    native_id is source-specific: GDACS uses eventid, WHO uses Id or DonId,
    GDELT uses url, DDG-NEWS uses url.
    """
    source = record.source_name
    raw = record.raw_fields

    if source == "GDACS":
        native_id = raw.get("eventid")
    elif source == "WHO":
        native_id = raw.get("Id") or raw.get("DonId")
    elif source in ("GDELT", "DDG-NEWS"):
        native_id = raw.get("url")
    elif source == "EONET":
        native_id = raw.get("id")
    else:
        raise ValueError(f"Unknown source: {source}")

    if native_id is None:
        raise ValueError(
            f"No native identifier for source {source} in raw_fields"
        )

    return f"{source}:{native_id}"


def generate_incident_id(
    records: list[RawRecord],
    country: str | None,
    disaster_type: str | None,
) -> str:
    """Generate a stable incident identifier in YYYYMMDD-CC-TTT format.

    - Date: earliest source-provided date from *records*, falling back to
      ``fetched_at`` if no source date is available, then to UTC today.
    - CC: ISO 3166-1 alpha-2 country code.  Unknown → ``"UNX"``.
    - TTT: disaster type code.  Unknown → ``"OTH"``.
    """
    if records:
        source_dates = []
        for r in records:
            sd = _extract_source_date(r)
            if sd is not None:
                source_dates.append(sd.date())
        if source_dates:
            date_part = min(source_dates).strftime("%Y%m%d")
        else:
            date_part = min(r.fetched_at.date() for r in records).strftime("%Y%m%d")
    else:
        date_part = datetime.now(tz=timezone.utc).strftime("%Y%m%d")

    cc = _country_to_alpha2(country)

    dt = disaster_type or ""
    if dt in _DISASTER_TYPE_CODE.values():
        ttt = dt
    else:
        ttt = _DISASTER_TYPE_CODE.get(dt, "OTH")

    return f"{date_part}-{cc}-{ttt}"


@dataclass(frozen=True)
class RawRecord:
    """A single raw record fetched from an external data source."""

    source_name: str
    fetched_at: datetime
    raw_fields: dict


@dataclass
class IncidentBundle:
    """A correlated group of raw records representing one disaster incident."""

    incident_id: str
    records: list[RawRecord]
    country: str | None = None
    country_code: str | None = None
    country_group: str | None = None
    disaster_type: str | None = None
    incident_level: int | None = None
    priority: str | None = None
    should_report: bool = False
    overrides: list[str] = field(default_factory=list)
    summary: str | None = None
    rationale: str | None = None
    estimated_affected: int | None = None
    estimated_deaths: int | None = None
    ai_enriched: bool = False
    enrichment_failed: bool = False
    classified_at: datetime | None = None
    classification_date: date | None = None
    last_updated: datetime | None = None
    source_fingerprints: list[str] = field(default_factory=list)

    _AI_FIELDS: ClassVar[tuple[str, ...]] = (
        "summary",
        "rationale",
        "estimated_affected",
        "estimated_deaths",
    )

    def __post_init__(self) -> None:
        """Validate invariants after initialisation."""
        if not self.records:
            raise ValueError("IncidentBundle must contain at least one RawRecord")
        if not self.ai_enriched:
            for field_name in self._AI_FIELDS:
                if getattr(self, field_name) is not None:
                    raise ValueError(
                        f"IncidentBundle with ai_enriched=False must not have "
                        f"{field_name} set, got {getattr(self, field_name)!r}"
                    )

    def is_active(self, reference_time: datetime | None = None) -> bool:
        """Return True if the bundle was updated within the last 7 days.

        A bundle with ``last_updated`` within 7 days of *reference_time*
        is ACTIVE; otherwise it is STALE.
        """
        if self.last_updated is None:
            return False
        if reference_time is None:
            reference_time = datetime.now(tz=timezone.utc)
        last = self.last_updated
        if reference_time.tzinfo is None and last.tzinfo is not None:
            reference_time = reference_time.replace(tzinfo=timezone.utc)
        elif reference_time.tzinfo is not None and last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        return (reference_time - last).days <= 7


@dataclass(frozen=True)
class Incident:
    """A deduplicated incident ready for reporting."""

    incident_id: str
    source_names: list[str]
    incident_name: str
    country: str | None = None
    country_code: str | None = None
    country_group: str = "C"
    disaster_type: str | None = None
    incident_level: int = 1
    priority: str = "LOW"
    should_report: bool = False
    overrides: list[str] = field(default_factory=list)
    report_date: date = field(default_factory=date.today)
    source_urls: list[str] = field(default_factory=list)
    summary: str | None = None
    rationale: str | None = None
    estimated_affected: int | None = None
    estimated_deaths: int | None = None
    ai_enriched: bool = False
    record_count: int = 0
