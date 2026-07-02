from __future__ import annotations

import pytest

pytest.importorskip("disaster_report.resolver", reason="resolver not implemented")

from disaster_report.resolver import IncidentResolver
from disaster_report.sources.base import RawIncident


def _incident(
    country: str = "Philippines",
    incident_type: str = "Earthquake",
    report_date: str = "2026-06-29T00:00:00Z",
    source: str = "USGS",
    url: str = "https://usgs.example/1",
    raw_fields: dict | None = None,
) -> RawIncident:
    return RawIncident(
        source_name=source,
        incident_name="M5.2 Earthquake near Sarangani",
        country=country,
        incident_type=incident_type,
        report_date=report_date,
        source_url=url,
        raw_fields=raw_fields or {},
    )


def test_resolver_assigns_canonical_deterministic_incident_id():
    resolved = IncidentResolver().resolve([_incident()])

    assert len(resolved) == 1
    assert resolved[0].incident_id == "20260629-PH-EQ"


def test_resolver_collapses_same_key_into_one_incident():
    usgs = _incident(source="USGS", url="https://usgs.example/1")
    gdacs = _incident(source="GDACS", url="https://gdacs.example/1")

    resolved = IncidentResolver().resolve([usgs, gdacs])

    assert len(resolved) == 1
    assert resolved[0].incident_id == "20260629-PH-EQ"


def test_resolver_treats_different_dates_as_different_incidents():
    a = _incident(report_date="2026-06-29T00:00:00Z")
    b = _incident(report_date="2025-06-29T00:00:00Z", url="https://usgs.example/2")

    resolved = IncidentResolver().resolve([a, b])

    assert len(resolved) == 2
    assert {r.incident_id for r in resolved} == {"20260629-PH-EQ", "20250629-PH-EQ"}


def test_resolver_treats_different_countries_as_different_incidents():
    a = _incident(country="Philippines")
    b = _incident(country="Indonesia", url="https://usgs.example/2")

    resolved = IncidentResolver().resolve([a, b])

    assert len(resolved) == 2
    assert {r.incident_id for r in resolved} == {"20260629-PH-EQ", "20260629-ID-EQ"}


def test_resolver_treats_different_types_as_different_incidents():
    a = _incident(incident_type="Earthquake")
    b = _incident(incident_type="Flood", url="https://usgs.example/2")

    resolved = IncidentResolver().resolve([a, b])

    assert len(resolved) == 2
    assert {r.incident_id for r in resolved} == {"20260629-PH-EQ", "20260629-PH-FL"}


def test_resolver_handles_empty_input():
    assert IncidentResolver().resolve([]) == []


def test_resolver_includes_subdivision_for_us_state_place_strings():
    oregon = _incident(country="35 km SSW of Cordova, Alaska", url="https://usgs.example/ak")
    philippines = _incident(country="27 km SSW of Surup, Philippines", url="https://usgs.example/ph")

    resolved = IncidentResolver().resolve([oregon, philippines])

    ids = {r.incident_id for r in resolved}
    assert "20260629-PH-EQ" in ids
    assert any(uid.startswith("20260629-US-") and uid.endswith("-EQ") for uid in ids), ids


def test_resolver_separates_same_country_different_states():
    oregon = _incident(country="Bandon, Oregon", url="https://usgs.example/or")
    alaska = _incident(country="Cordova, Alaska", url="https://usgs.example/ak")

    resolved = IncidentResolver().resolve([oregon, alaska])

    ids = {r.incident_id for r in resolved}
    assert len(ids) == 2, ids
    assert any("-US-OR-" in uid for uid in ids), ids
    assert any("-US-AK-" in uid for uid in ids), ids


def test_resolver_uses_raw_fields_subdivision_when_present():
    arizona = _incident(
        country="United States",
        incident_type="Disease",
        url="https://healthmap.example/az",
        raw_fields={"subdivision": "US-AZ"},
    )

    resolved = IncidentResolver().resolve([arizona])

    assert resolved[0].incident_id == "20260629-US-AZ-EP", resolved[0].incident_id
