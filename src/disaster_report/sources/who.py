from __future__ import annotations

import re

import httpx

from disaster_report.sources._dates import parse_date
from disaster_report.sources.base import RawIncident, json_list

_DEFAULT_URL = (
    "https://www.who.int/api/news/diseaseoutbreaknews"
    "?$orderby=PublicationDateAndTime%20desc&$top=25"
)
_GUID_RE = re.compile(r"/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})", re.IGNORECASE)


# WHO DON titles separate the disease from the place with an en-dash, em-dash,
# ASCII hyphen (with or without surrounding spaces), or sometimes a comma.
# Normalize all dash variants to "-" first, then split. Comma is a fallback only
# when no dash is present (so disease names containing commas are not over-split).
_DASH_SPLIT_RE = re.compile(r"\s*-\s*")

# Place tokens in DON titles that are NOT a country. These are global/regional
# sitreps with no single country to anchor on -> empty so the deriver drops the
# country token from search keys instead of producing a misleading "Unknown".
_NON_COUNTRY_PLACES: frozenset[str] = frozenset(
    {
        "global",
        "worldwide",
        "international",
        "multi",
        "multi-location",
        "multi-locations",
        "multi-location(s)",
        "multiple locations",
        "multi-country",
        "multi-countries",
        "region",
        "regional",
    }
)


def _split_title(title: str) -> list[str]:
    normalized = title.replace("\u2013", "-").replace("\u2014", "-")
    parts = [p.strip() for p in _DASH_SPLIT_RE.split(normalized) if p.strip()]
    if len(parts) >= 2:
        return parts
    comma = [p.strip() for p in title.split(",") if p.strip()]
    return comma if len(comma) >= 2 else parts


def _normalize_country(place: str) -> str:
    """Reduce a DON title's place field to a single country name.

    WHO multi-country sitreps use the form "Disease, Country A & Country B";
    we keep the FIRST (primary) country so country_info can resolve it. Sentinels
    like "Global"/"Multi-locations" become "" (no country) rather than a bogus
    "Unknown". Compound names containing " and " (e.g. "Bosnia and Herzegovina")
    are intentionally NOT split.
    """
    s = (place or "").strip()
    if not s:
        return ""
    low = s.lower()
    if low in _NON_COUNTRY_PLACES or low.startswith("multi"):
        return ""
    if " & " in s:
        s = s.split(" & ")[0].strip()
    return s


def _to_iso(s: str) -> str:
    parsed = parse_date(s)
    return parsed.isoformat() if parsed is not None else s


class WHODiseaseOutbreakAdapter:
    source_name = "WHO Disease Outbreak News"

    def __init__(self, url: str = _DEFAULT_URL, timeout: float = 30.0) -> None:
        self.url = url
        self.timeout = timeout

    def fetch(self) -> list[RawIncident]:
        response = httpx.get(self.url, timeout=self.timeout, follow_redirects=True)
        response.raise_for_status()
        out: list[RawIncident] = []
        for item in json_list(response, "value"):
            title = (
                (item.get("OverrideTitle") or item.get("Title") or "")
                if item.get("UseOverrideTitle")
                else (item.get("Title") or "")
            )
            parts = _split_title(title)
            country = _normalize_country(parts[-1]) if len(parts) > 1 else ""
            disease_name = parts[0].strip() if len(parts) > 1 else ""
            path = item.get("ItemDefaultUrl", "") or ""
            source_url = ("https://www.who.int" + path) if path else ""
            guid_match = _GUID_RE.search(path)
            event_id = guid_match.group(1) if guid_match else path
            raw_fields = dict(item)
            raw_fields["event_id"] = event_id
            raw_fields["disease"] = disease_name
            out.append(
                RawIncident(
                    source_name=self.source_name,
                    incident_name=title,
                    country=country,
                    disaster_type="Disease",
                    report_date=_to_iso(item.get("PublicationDateAndTime", "") or ""),
                    source_url=source_url,
                    raw_fields=raw_fields,
                )
            )
        return out
