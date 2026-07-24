from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from disaster_report.models import SourceReport
    from disaster_report.sources.ercc import ERCCAdapter

from disaster_report.models import ReportPlace

CASSETTE: str = "ercc_daily_maps.yaml"
ERROR_CASSETTE_SLUG: str = "does-not-exist"


class TestERCCAdapter:
    adapter: ERCCAdapter

    def test_fetch_returns_source_reports_from_rss_feed(self) -> None:
        import vcr

        from disaster_report.sources.ercc import ERCCAdapter

        with vcr.use_cassette(f"tests/cassettes/{CASSETTE}"):
            reports = ERCCAdapter().fetch()
        assert len(reports) > 0

    def test_each_source_report_carries_ercc_source_name(self) -> None:
        import vcr

        from disaster_report.sources.ercc import ERCCAdapter

        with vcr.use_cassette(f"tests/cassettes/{CASSETTE}"):
            reports = ERCCAdapter().fetch()
        assert all(report.source == "ERCC" for report in reports)

    def test_incident_type_mapped_from_ercc_eventtypes_never_empty(self) -> None:
        import vcr

        from disaster_report.sources.ercc import ERCCAdapter

        with vcr.use_cassette(f"tests/cassettes/{CASSETTE}"):
            reports = ERCCAdapter().fetch()
        assert all(report.incident_type != "" for report in reports)

    def test_source_report_name_is_non_empty(self) -> None:
        import vcr

        from disaster_report.sources.ercc import ERCCAdapter

        with vcr.use_cassette(f"tests/cassettes/{CASSETTE}"):
            reports = ERCCAdapter().fetch()
        assert first_source_report(reports).name != ""

    def test_report_date_is_iso_parseable(self) -> None:
        import datetime

        import vcr

        from disaster_report.sources.ercc import ERCCAdapter

        with vcr.use_cassette(f"tests/cassettes/{CASSETTE}"):
            reports = ERCCAdapter().fetch()
        datetime.date.fromisoformat(first_source_report(reports).report_date)

    def test_raw_fields_preserve_eventtypes_and_description(self) -> None:
        import vcr

        from disaster_report.sources.ercc import ERCCAdapter

        with vcr.use_cassette(f"tests/cassettes/{CASSETTE}"):
            reports = ERCCAdapter().fetch()
        raw = first_source_report(reports).raw_fields
        assert "eventTypes" in raw
        assert "description" in raw

    def test_source_id_is_the_guid_numeric(self) -> None:
        import vcr

        from disaster_report.sources.ercc import ERCCAdapter

        with vcr.use_cassette(f"tests/cassettes/{CASSETTE}"):
            reports = ERCCAdapter().fetch()
        assert first_source_report(reports).source_id != ""

    def test_derive_keys_returns_strict_and_loose_search_phrases(self) -> None:
        from disaster_report.sources.ercc import ERCCAdapter

        strict, loose = ERCCAdapter().derive_keys(build_ercc_report())
        assert strict == "Earthquake Yumare, Venezuela July 2026", strict
        assert loose == "Earthquake Venezuela 2026", loose

    def test_derive_keys_empty_places_skips_strict(self) -> None:
        from disaster_report.sources.ercc import ERCCAdapter

        strict, loose = ERCCAdapter().derive_keys(build_ercc_report(places=[]))
        assert strict == "", strict
        assert loose == "Earthquake 2026", loose

    def test_fetch_raises_typed_error_on_non_xml(self) -> None:
        import vcr

        from disaster_report.sources.errors import SourceFetchError
        from disaster_report.sources.ercc import ERCCAdapter

        with (
            vcr.use_cassette(f"tests/cassettes/{CASSETTE}"),
            pytest.raises(SourceFetchError),
        ):
            ERCCAdapter(path=ERROR_CASSETTE_SLUG).fetch()


class TestERCCResolveIncidentType:

    def test_single_type_maps_directly(self) -> None:
        from disaster_report.sources.ercc import _resolve_incident_type

        assert _resolve_incident_type("Earthquake") == "Earthquake"

    def test_wild_fire_maps_to_forest_fire(self) -> None:
        from disaster_report.sources.ercc import _resolve_incident_type

        assert _resolve_incident_type("Wild fire") == "Forest Fire"

    def test_heat_wave_maps_to_severe_weather(self) -> None:
        from disaster_report.sources.ercc import _resolve_incident_type

        assert _resolve_incident_type("Heat Wave") == "Severe Weather"

    def test_multi_type_picks_priority_tropical_cyclone_over_flood(self) -> None:
        from disaster_report.sources.ercc import _resolve_incident_type

        assert _resolve_incident_type("Flood, Tropical Cyclone") == "Tropical Cyclone"

    def test_unknown_type_returns_empty(self) -> None:
        from disaster_report.sources.ercc import _resolve_incident_type

        assert _resolve_incident_type("Unknown Hazard") == ""


class TestERCCExtractCanonicalName:

    def test_earthquake_extracts_magnitude(self) -> None:
        from disaster_report.sources.ercc import _extract_canonical_name

        raw: dict[str, object] = {"description": "Peru | 5.5 M Earthquake of 19 July"}
        places = [ReportPlace(country_code="PE", subdivision="", locality="")]
        name = _extract_canonical_name(raw, places, "2026-07-20", "Earthquake")
        assert name == "Earthquake M5.5 Peru 2026-07-20", name

    def test_earthquake_takes_first_magnitude_when_multiple(self) -> None:
        from disaster_report.sources.ercc import _extract_canonical_name

        raw: dict[str, object] = {"description": "Venezuela | 7.5 M and 7.2 M earthquakes"}
        places = [ReportPlace(country_code="VE", subdivision="", locality="")]
        name = _extract_canonical_name(raw, places, "2026-07-16", "Earthquake")
        assert name == "Earthquake M7.5 Venezuela 2026-07-16", name

    def test_tropical_cyclone_extracts_storm_name(self) -> None:
        from disaster_report.sources.ercc import _extract_canonical_name

        raw: dict[str, object] = {"description": "Philippines, China, Taiwan, Japan | Tropical cyclone BAVI"}
        places = [ReportPlace(country_code="PH", subdivision="", locality="")]
        name = _extract_canonical_name(raw, places, "2026-07-13", "Tropical Cyclone")
        assert name == "Tropical Cyclone BAVI Philippines 2026-07-13", name

    def test_severe_weather_no_identifier(self) -> None:
        from disaster_report.sources.ercc import _extract_canonical_name

        raw: dict[str, object] = {"description": "Europe | Ongoing heatwave"}
        places: list[ReportPlace] = []
        name = _extract_canonical_name(raw, places, "2026-07-09", "Severe Weather")
        assert name == "Severe Weather 2026-07-09", name

    def test_conflict_with_country(self) -> None:
        from disaster_report.sources.ercc import _extract_canonical_name

        raw: dict[str, object] = {"description": "Russia's War on Ukraine | Generators offered"}
        places = [ReportPlace(country_code="UA", subdivision="", locality="")]
        name = _extract_canonical_name(raw, places, "2026-07-15", "Conflict")
        assert name == "Conflict Ukraine 2026-07-15", name

    def test_global_no_places_omits_place(self) -> None:
        from disaster_report.sources.ercc import _extract_canonical_name

        raw: dict[str, object] = {"description": "World | Temperature anomalies in June 2026"}
        places: list[ReportPlace] = []
        name = _extract_canonical_name(raw, places, "2026-07-17", "Severe Weather")
        assert name == "Severe Weather 2026-07-17", name


class TestERCCExtractPlaces:

    def test_main_country_resolves_to_iso2(self) -> None:
        from disaster_report.sources.ercc import _extract_places

        places = _extract_places("Peru", "")
        assert len(places) == 1
        assert places[0].country_code == "PE"

    def test_countries_iso3_list_resolves(self) -> None:
        from disaster_report.sources.ercc import _extract_places

        places = _extract_places("", "ESP, FRA")
        assert len(places) == 2
        assert places[0].country_code == "ES"
        assert places[1].country_code == "FR"

    def test_both_present_dedupes(self) -> None:
        from disaster_report.sources.ercc import _extract_places

        places = _extract_places("Spain", "ESP, FRA")
        codes = [p.country_code for p in places]
        assert codes == ["ES", "FR"]

    def test_neither_returns_empty(self) -> None:
        from disaster_report.sources.ercc import _extract_places

        assert _extract_places("", "") == []


class TestERCCDeriveRepollKeys:

    def test_with_places_delegates_to_shared(self) -> None:
        from disaster_report.sources.ercc import ERCCAdapter

        keys = ERCCAdapter().derive_repoll_keys(build_ercc_report())
        assert keys, keys
        assert any("Venezuela" in k for k in keys)

    def test_empty_places_countryless_keys(self) -> None:
        from disaster_report.sources.ercc import ERCCAdapter

        keys = ERCCAdapter().derive_repoll_keys(build_ercc_report(places=[]))
        assert keys == ["Earthquake latest 2026", "Earthquake 2026"], keys


def first_source_report(reports: list[SourceReport]) -> SourceReport:
    return reports[0]


def build_ercc_report(
    *,
    source: str = "ERCC",
    source_id: str = "5730",
    incident_type: str = "Earthquake",
    name: str = "Earthquake M7.5 Venezuela 2026-07-16",
    places: list[ReportPlace] | None = None,
    report_date: str = "2026-07-16",
    raw_fields: dict[str, object] | None = None,
) -> SourceReport:
    from disaster_report.models import SourceReport

    if places is None:
        places = [ReportPlace(country_code="VE", subdivision="", locality="Yumare")]
    if raw_fields is None:
        raw_fields = {"description": "Venezuela | 7.5 M Earthquake"}
    return SourceReport(
        source=source,
        source_id=source_id,
        incident_type=incident_type,
        name=name,
        places=places,
        report_date=report_date,
        raw_fields=raw_fields,
    )
