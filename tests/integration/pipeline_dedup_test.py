from __future__ import annotations

from pathlib import Path


from disaster_report.models import ReportPlace, SourceReport
from disaster_report.pipeline import (
    _find_existing_incident,
    _normalize_incident_name,
    _parse_usgs_ids,
)
from disaster_report.store.content import ContentStore


def _build_report(
    *,
    source: str = "USGS",
    source_id: str = "us7000xyz",
    incident_type: str = "Earthquake",
    name: str = "M 6.0 - 90 km SW of Puerto Madero, Mexico",
    country_code: str = "GT",
    report_date: str = "2026-07-17",
    raw_fields: dict | None = None,
) -> SourceReport:
    return SourceReport(
        source=source,
        source_id=source_id,
        incident_type=incident_type,
        name=name,
        places=[ReportPlace(country_code=country_code, subdivision="", locality="")],
        report_date=report_date,
        raw_fields=raw_fields or {},
    )


class TestNormalizeIncidentName:
    def test_strips_usgs_magnitude_prefix(self) -> None:
        assert (
            _normalize_incident_name("M 6.0 - 90 km SW of Puerto Madero, Mexico")
            == "90 km SW of Puerto Madero, Mexico"
        )

    def test_strips_magnitude_word_prefix(self) -> None:
        assert (
            _normalize_incident_name("Magnitude 7.3 - offshore Guatemala")
            == "offshore Guatemala"
        )

    def test_keeps_name_without_prefix(self) -> None:
        assert _normalize_incident_name("Ebola outbreak - DRC") == "Ebola outbreak - DRC"

    def test_falls_back_when_strip_empties(self) -> None:
        assert _normalize_incident_name("M 6.0") == "M 6.0"


class TestParseUsgsIds:
    def test_parses_comma_separated(self) -> None:
        assert _parse_usgs_ids("us7000t1cc,us7000t1bu,  us7000abc ") == {
            "us7000t1cc",
            "us7000t1bu",
            "us7000abc",
        }

    def test_returns_empty_for_none(self) -> None:
        assert _parse_usgs_ids(None) == set()

    def test_returns_empty_for_empty_string(self) -> None:
        assert _parse_usgs_ids("") == set()


class TestFindExistingIncidentUsgsFamily:
    def test_usgs_event_id_family_matches(self, tmp_path: Path) -> None:
        store = ContentStore(tmp_path)
        existing_report = _build_report(
            source_id="us7000t1bu",
            name="M 7.3 - 58 km WSW of Puerto Madero",
            raw_fields={"ids": "us7000t1bu,us7000t1cc"},
        )
        rid = store.ingest_source_report(existing_report)
        store.ingest_report_places(rid, existing_report.places)
        inc_id = "abc123"
        store.add_report_incident(rid, inc_id)

        new_report = _build_report(
            source_id="us7000t1cc",
            name="M 6.0 - 90 km SW of Puerto Madero",
            raw_fields={"ids": "us7000t1cc,us7000t1bu"},
        )
        match = _find_existing_incident(store, new_report)
        assert match == inc_id

    def test_no_usgs_ids_returns_none_quickly(self, tmp_path: Path) -> None:
        store = ContentStore(tmp_path)
        new_report = _build_report(raw_fields={})
        assert _find_existing_incident(store, new_report) is None


class TestFindExistingIncidentWindow:
    def test_matches_same_type_country_within_14d(self, tmp_path: Path) -> None:
        store = ContentStore(tmp_path)
        existing = _build_report(
            source_id="us7000aaa",
            name="M 7.3 - offshore",
            report_date="2026-07-10",
            raw_fields={"ids": "us7000aaa"},
        )
        rid = store.ingest_source_report(existing)
        store.ingest_report_places(rid, existing.places)
        store.add_report_incident(rid, "incident_v1")
        new_report = _build_report(
            source_id="us7000bbb",
            name="M 6.0 - same area",
            report_date="2026-07-15",
            raw_fields={"ids": "us7000bbb"},
        )
        match = _find_existing_incident(store, new_report)
        assert match == "incident_v1"

    def test_rejects_different_country(self, tmp_path: Path) -> None:
        store = ContentStore(tmp_path)
        existing = _build_report(
            source_id="us7000aaa",
            country_code="GT",
            report_date="2026-07-10",
            raw_fields={"ids": "us7000aaa"},
        )
        rid = store.ingest_source_report(existing)
        store.ingest_report_places(rid, existing.places)
        store.add_report_incident(rid, "gt_incident")
        new_report = _build_report(
            source_id="us7000bbb",
            country_code="JP",
            report_date="2026-07-12",
            raw_fields={"ids": "us7000bbb"},
        )
        assert _find_existing_incident(store, new_report) is None

    def test_rejects_outside_window(self, tmp_path: Path) -> None:
        store = ContentStore(tmp_path)
        existing = _build_report(
            source_id="us7000aaa",
            report_date="2026-07-01",
            raw_fields={"ids": "us7000aaa"},
        )
        rid = store.ingest_source_report(existing)
        store.ingest_report_places(rid, existing.places)
        store.add_report_incident(rid, "old_incident")
        new_report = _build_report(
            source_id="us7000bbb",
            report_date="2026-07-25",
            raw_fields={"ids": "us7000bbb"},
        )
        assert _find_existing_incident(store, new_report) is None

    def test_rejects_different_incident_type(self, tmp_path: Path) -> None:
        store = ContentStore(tmp_path)
        existing = _build_report(
            source_id="us7000aaa",
            incident_type="Earthquake",
            report_date="2026-07-10",
            raw_fields={"ids": "us7000aaa"},
        )
        rid = store.ingest_source_report(existing)
        store.ingest_report_places(rid, existing.places)
        store.add_report_incident(rid, "quake_incident")
        new_report = _build_report(
            source_id="who123",
            source="WHO",
            incident_type="Ebola",
            name="Ebola outbreak",
            country_code="GT",
            report_date="2026-07-12",
        )
        assert _find_existing_incident(store, new_report) is None
