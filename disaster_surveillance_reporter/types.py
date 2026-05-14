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


def generate_incident_id(
    records: list[RawRecord],
    country: str | None,
    disaster_type: str | None,
) -> str:
    """Generate a stable incident identifier in YYYYMMDD-CC-TTT format.

    - Date: earliest ``fetched_at`` from *records*, falling back to UTC today.
    - CC: ISO 3166-1 alpha-2 country code.  Unknown → ``"UNX"``.
    - TTT: disaster type code.  Unknown → ``"OTH"``.
    """
    if records:
        earliest = min(r.fetched_at.date() for r in records)
        date_part = earliest.strftime("%Y%m%d")
    else:
        date_part = datetime.now(tz=timezone.utc).strftime("%Y%m%d")

    cc = _country_to_alpha2(country)
    ttt = _DISASTER_TYPE_CODE.get(disaster_type or "", "OTH")

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
