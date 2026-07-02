from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from disaster_report.countries import country_from_place
from disaster_report.sources._dates import parse_date
from disaster_report.sources.base import RawIncident

_TYPE_CODES: dict[str, str] = {
    "earthquake": "EQ",
    "flood": "FL",
    "storm": "ST",
    "cyclone": "CY",
    "typhoon": "CY",
    "hurricane": "CY",
    "volcano": "VO",
    "volcanic eruption": "VO",
    "drought": "DR",
    "wildfire": "WF",
    "fire": "WF",
    "landslide": "LS",
    "tsunami": "TS",
    "disease": "EP",
    "epidemic": "EP",
    "outbreak": "EP",
    "epidemics": "EP",
}


def _type_code(disaster_type: str) -> str:
    key = (disaster_type or "").strip().lower()
    if key in _TYPE_CODES:
        return _TYPE_CODES[key]
    cleaned = "".join(ch for ch in key if ch.isalnum())
    if len(cleaned) >= 2:
        return cleaned[:2].upper()
    return (cleaned or "OT").upper().ljust(2, "X")[:2]


def _date_stamp(report_date: str) -> str:
    parsed = parse_date(report_date)
    if parsed is None:
        raise ValueError(f"unparseable report_date: {report_date!r}")
    return parsed.strftime("%Y%m%d")


@dataclass(frozen=True)
class ResolvedIncident:
    incident_id: str
    incidents: tuple[RawIncident, ...] = field(default_factory=tuple)

    @property
    def primary(self) -> RawIncident:
        """The representative source record (first / earliest by fetch order)."""
        return self.incidents[0]

    def is_today(self, today: date) -> bool:
        """True when the primary record's report_date is ``today``."""
        return parse_date(self.primary.report_date) == today


class IncidentResolver:
    def resolve(self, raw_incidents: list[RawIncident]) -> list[ResolvedIncident]:
        groups: dict[str, list[RawIncident]] = {}
        order: list[str] = []
        for raw in raw_incidents:
            stamp = _date_stamp(raw.report_date)
            explicit_sub = str(raw.raw_fields.get("subdivision") or "")
            if explicit_sub and "-" in explicit_sub:
                cc, sub = explicit_sub.split("-", 1)
                cc = cc.upper()
                sub = sub.upper()
            else:
                cc, sub = country_from_place(raw.country)
            code = _type_code(raw.disaster_type)
            incident_id = (
                f"{stamp}-{cc}-{sub}-{code}" if sub else f"{stamp}-{cc}-{code}"
            )
            if incident_id not in groups:
                groups[incident_id] = []
                order.append(incident_id)
            groups[incident_id].append(raw)
        return [
            ResolvedIncident(incident_id=incident_id, incidents=tuple(groups[incident_id]))
            for incident_id in order
        ]
