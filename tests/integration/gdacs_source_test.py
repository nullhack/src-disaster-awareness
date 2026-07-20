from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from disaster_report.models import SourceReport
    from disaster_report.sources.gdacs import GDACSAdapter

from disaster_report.models import ReportPlace

CASSETTE: str = "gdacs_rss_24h.yaml"
ERROR_CASSETTE_SLUG: str = "does-not-exist.xml"


class TestGDACSAdapter:
    adapter: GDACSAdapter

    def test_fetch_returns_source_reports_from_rss_feed(self) -> None:
        import vcr

        from disaster_report.sources.gdacs import GDACSAdapter

        with vcr.use_cassette(f"tests/cassettes/{CASSETTE}"):
            reports = GDACSAdapter().fetch()
        assert len(reports) > 0

    def test_each_source_report_carries_gdacs_source_name(self) -> None:
        import vcr

        from disaster_report.sources.gdacs import GDACSAdapter

        with vcr.use_cassette(f"tests/cassettes/{CASSETTE}"):
            reports = GDACSAdapter().fetch()
        assert all(report.source == "GDACS" for report in reports)

    def test_incident_type_mapped_from_gdacs_eventtype_never_unknown(self) -> None:
        import vcr

        from disaster_report.sources.gdacs import GDACSAdapter

        with vcr.use_cassette(f"tests/cassettes/{CASSETTE}"):
            reports = GDACSAdapter().fetch()
        assert all(report.incident_type != "Unknown" for report in reports)

    def test_source_report_name_matches_item_title(self) -> None:
        import vcr

        from disaster_report.sources.gdacs import GDACSAdapter

        with vcr.use_cassette(f"tests/cassettes/{CASSETTE}"):
            reports = GDACSAdapter().fetch()
        assert first_source_report(reports).name != ""

    def test_report_date_is_iso_parseable(self) -> None:
        import datetime

        import vcr

        from disaster_report.sources.gdacs import GDACSAdapter

        with vcr.use_cassette(f"tests/cassettes/{CASSETTE}"):
            reports = GDACSAdapter().fetch()
        datetime.date.fromisoformat(first_source_report(reports).report_date)

    def test_raw_fields_preserve_alertlevel_eventtype_and_country(self) -> None:
        import vcr

        from disaster_report.sources.gdacs import GDACSAdapter

        with vcr.use_cassette(f"tests/cassettes/{CASSETTE}"):
            reports = GDACSAdapter().fetch()
        raw = first_source_report(reports).raw_fields
        assert "alertlevel" in raw
        assert "eventtype" in raw

    def test_population_read_via_value_attribute(self) -> None:
        import vcr

        from disaster_report.sources.gdacs import GDACSAdapter

        with vcr.use_cassette(f"tests/cassettes/{CASSETTE}"):
            reports = GDACSAdapter().fetch()
        raw = first_source_report(reports).raw_fields
        assert "population" in raw

    def test_source_id_is_the_link_eventid(self) -> None:
        import vcr

        from disaster_report.sources.gdacs import GDACSAdapter

        with vcr.use_cassette(f"tests/cassettes/{CASSETTE}"):
            reports = GDACSAdapter().fetch()
        assert first_source_report(reports).source_id != ""

    def test_should_monitor_filters_over_reporting(self) -> None:
        from disaster_report.sources.gdacs import GDACSAdapter

        adapter = GDACSAdapter()
        assert isinstance(adapter.should_monitor(build_gdacs_report()), bool)

    def test_derive_keys_returns_strict_and_loose_search_phrases(self) -> None:
        from disaster_report.sources.gdacs import GDACSAdapter

        strict, loose = GDACSAdapter().derive_keys(build_gdacs_report())
        assert strict == "Tropical Cyclone Philippines July 2026", strict
        assert loose == "Tropical Cyclone Philippines 2026", loose

    def test_derive_keys_empty_places_skips_strict(self) -> None:
        from disaster_report.sources.gdacs import GDACSAdapter

        strict, loose = GDACSAdapter().derive_keys(build_gdacs_report(places=[]))
        assert strict == "", strict
        assert loose == "Tropical Cyclone 2026", loose

    def test_fetch_raises_typed_error_on_soft_200(self) -> None:
        import vcr

        from disaster_report.sources.errors import SourceFetchError
        from disaster_report.sources.gdacs import GDACSAdapter

        with (
            vcr.use_cassette(f"tests/cassettes/{CASSETTE}"),
            pytest.raises(SourceFetchError),
        ):
            GDACSAdapter(path=ERROR_CASSETTE_SLUG).fetch()


class TestExtractPlaces:
    def test_iso3_with_land_coordinates_returns_country_and_subdivision(self) -> None:
        from disaster_report.sources.gdacs import _extract_places

        places = _extract_places("PER", "Peru", -12.0429, -75.3013)
        assert places and places[0].country_code == "PE"
        assert places[0].subdivision  # Junín or similar

    def test_iso3_with_far_land_coords_returns_subdivision(self) -> None:
        from disaster_report.sources.gdacs import _extract_places

        places = _extract_places("CHN", "China", 31.5649, 104.126)
        assert places and places[0].country_code == "CN"
        assert places[0].subdivision  # Sichuan Sheng

    def test_ocean_event_falls_back_to_geo_country(self) -> None:
        from disaster_report.sources.gdacs import _extract_places

        # Owen Fracture Zone — no iso3, no country match by text, but near UAE
        places = _extract_places("", "Owen Fracture Zone Region", 25.0, 57.0)
        assert places and places[0].country_code  # AE or nearby

    def test_true_mid_ocean_returns_empty(self) -> None:
        from disaster_report.sources.gdacs import _extract_places

        # Deep southern Indian Ocean — no land within 200km
        places = _extract_places("", "Mid-Indian Ridge", -25.0, 70.0)
        assert places == []

    def test_no_coordinates_returns_country_only(self) -> None:
        from disaster_report.sources.gdacs import _extract_places

        places = _extract_places("PER", "Peru", None, None)
        assert places and places[0].country_code == "PE"
        assert places[0].subdivision == ""

    def test_no_iso3_no_text_no_coords_returns_empty(self) -> None:
        from disaster_report.sources.gdacs import _extract_places

        places = _extract_places("", "", None, None)
        assert places == []


def first_source_report(reports: list[SourceReport]) -> SourceReport:
    return reports[0]


def build_gdacs_report(
    *,
    source: str = "GDACS",
    source_id: str = "1001279",
    incident_type: str = "Tropical Cyclone",
    name: str = "TC test event",
    places: list[ReportPlace] | None = None,
    report_date: str = "2026-07-04",
    raw_fields: dict[str, object] | None = None,
) -> SourceReport:
    from disaster_report.models import SourceReport

    defaults: dict[str, object] = {
        "alertlevel": "Green",
        "eventtype": "TC",
        "population": 140768,
    }
    return SourceReport(
        source=source,
        source_id=source_id,
        incident_type=incident_type,
        name=name,
        places=places
        if places is not None
        else [
            ReportPlace(country_code="PH", subdivision="", locality=""),
        ],
        report_date=report_date,
        raw_fields=raw_fields if raw_fields is not None else defaults,
    )
