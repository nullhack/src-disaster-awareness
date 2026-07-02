"""Deterministic derivation of incident display fields from structured facts.

These replace the AI-authored ``canonical_name`` and ``search_keys`` so that:
  * every incident has usable, date-anchored keys immediately at ingest (even
    when the AI digest fails or is deferred), and
  * the date is ALWAYS present in the search keys (no reliance on the model
    choosing to include it).

AI is now reserved for judgment (classification) and prose (summary). The
identity/display strings are pure functions of (type, country, event_date,
disease, place).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from disaster_report.classification import is_disease_type
from disaster_report.countries import is_known_country


@dataclass(frozen=True)
class DeriveInput:
    incident_type: str
    country: str
    event_date: date | None
    disease: str = ""
    place: str = ""


def _clean_country(country: str) -> str:
    """Country token for display/keys, or '' when unknown/multi-country.

    WHO multi-country DONs normalize to country "Unknown". Emitting that token
    pollutes search keys ("Disease Unknown outbreak 2026") — DDG returns nothing
    and the literal "unknown" appears in no real article, so it is dropped.
    """
    return country.strip() if is_known_country(country) else ""


def _clean_place(place: str) -> str:
    """Reduce a raw USGS-style place string to its distinguishing locality.

    "near Sarangani, Philippines"  ->  "Sarangani"
    "of the coast of Honshu, Japan" ->  "Honshu"
    """
    if not place:
        return ""
    first = place.split(",", 1)[0]
    # Recursively strip leading filler words ("near ", "of the ", "of ", "the ")
    # so "of the coast of Honshu" -> "coast of Honshu" is reduced further on the
    # next pass until no filler prefix remains.
    prefixes = ("near ", "of the ", "of ", "the ")
    changed = True
    while changed:
        changed = False
        low = first.lower()
        for prefix in prefixes:
            if low.startswith(prefix):
                first = first[len(prefix):]
                low = first.lower()
                changed = True
                break
    return first.strip(" ,.")


def _month_year(event_date: date) -> str:
    return event_date.strftime("%B %Y")  # "June 2026"


def _year(event_date: date) -> str:
    return event_date.strftime("%Y")


def _disease_keys(inputs: DeriveInput, disease: str, country: str) -> list[str]:
    """Disease-track phrases: "{disease} {country} outbreak {YYYY}",
    "{disease} {country} {Month YYYY}", then the generic catch-all."""
    keys: list[str] = []
    if inputs.event_date:
        keys.append(f"{disease} {country} outbreak {_year(inputs.event_date)}".strip())
        keys.append(f"{disease} {country} {_month_year(inputs.event_date)}".strip())
    else:
        keys.append(f"{disease} {country} outbreak".strip())
    keys.append(f"{disease} outbreak cases deaths")
    return keys


def _physical_keys(
    inputs: DeriveInput, country: str, place: str, type_lower: str
) -> list[str]:
    """Physical-track phrases anchored on place/country + the incident type."""
    keys: list[str] = []
    if not inputs.event_date:
        if place:
            keys.append(f"{place} {type_lower}")
        keys.append(f"{country} {type_lower}".strip())
        return keys
    month = _month_year(inputs.event_date)
    year = _year(inputs.event_date)
    if place:
        keys.append(f"{place} {type_lower} {month}")
    keys.append(f"{country} {type_lower} {month}".strip())
    if place:
        keys.append(f"{place} {type_lower} {year}")
    else:
        keys.append(f"{country} {type_lower} {year}".strip())
    return keys


def _dedupe(keys: list[str], limit: int = 3) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for key in keys:
        collapsed = " ".join(key.split())  # collapse internal whitespace
        if collapsed and collapsed not in seen:
            seen.add(collapsed)
            out.append(collapsed)
    return out[:limit]


def derive_search_keys(inputs: DeriveInput) -> list[str]:
    """Three DDG-friendly phrases, most specific first.

    Date always present when ``event_date`` is known; de-duplicated; capped at 3.
    """
    country = _clean_country(inputs.country)
    place = _clean_place(inputs.place)
    type_lower = inputs.incident_type.strip().lower()
    if is_disease_type(inputs.incident_type) and inputs.disease:
        keys = _disease_keys(inputs, inputs.disease.strip(), country)
    else:
        keys = _physical_keys(inputs, country, place, type_lower)
    return _dedupe(keys)


def derive_canonical_name(inputs: DeriveInput) -> str:
    """Short display name: "{Type} {place} {Month YYYY}" / "{Disease} outbreak {country} {Month YYYY}"."""
    country = _clean_country(inputs.country)
    if is_disease_type(inputs.incident_type):
        base = (
            f"{inputs.disease} outbreak {country}".strip()
            if inputs.disease
            else f"{inputs.incident_type} {country}".strip()
        )
    else:
        place = _clean_place(inputs.place) or country
        base = f"{inputs.incident_type} {place}".strip()
    if inputs.event_date:
        base = f"{base} {_month_year(inputs.event_date)}".strip()
    return base[:120]
