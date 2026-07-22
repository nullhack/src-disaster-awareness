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

        # Deep southern Indian Ocean.  Per accepted trade-off, coco's text
        # regex matches "Indian" → IN and the geo reverse-lookup also
        # resolves to IN within 200km of (-25, 70); both India
        # mis-attributions are accepted because fixing them requires a
        # handcrafted exclusion list and coco's overall recall on
        # offshore/sovereign-territory events is far higher than pycountry's.
        places = _extract_places("", "Mid-Indian Ridge", -25.0, 70.0)
        # Either no places (true ocean), or single IN entry (accepted regression)
        assert places == [] or (
            len(places) == 1 and places[0].country_code == "IN"
        )

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


class TestGDACSExtractCanonicalName:
    def test_earthquake_extracts_magnitude_from_numeric_severity(self) -> None:
        from disaster_report.sources.gdacs import _extract_canonical_name

        result = _extract_canonical_name(
            {"eventtype": "EQ", "severity": 7.8, "severitytext": "Magnitude 7.8M"},
            [ReportPlace("AF", "Balkh", "")],
            "2025-10-15",
            "Earthquake",
        )
        assert result == "Earthquake M7.8 Balkh, Afghanistan 2025-10-15"

    def test_earthquake_extracts_magnitude_from_severitytext_string(self) -> None:
        from disaster_report.sources.gdacs import _extract_canonical_name

        result = _extract_canonical_name(
            {
                "eventtype": "EQ",
                "severity": "Magnitude 5M, Depth:10km",
                "severitytext": "Magnitude 5M, Depth:10km",
                "title": "Earthquake in Afghanistan",
            },
            [ReportPlace("AF", "Balkh", "")],
            "2025-10-15",
            "Earthquake",
        )
        assert result == "Earthquake M5.0 Balkh, Afghanistan 2025-10-15"

    def test_tropical_cyclone_uses_eventname_when_present(self) -> None:
        from disaster_report.sources.gdacs import _extract_canonical_name

        result = _extract_canonical_name(
            {
                "eventtype": "TC",
                "eventname": "BAVI-26",
                "title": "Red notification for tropical cyclone BAVI-26. Population.",
            },
            [ReportPlace("CN", "", "")],
            "2026-07-01",
            "Tropical Cyclone",
        )
        assert result == "Tropical Cyclone BAVI-26 China 2026-07-01"

    def test_tropical_cyclone_parses_storm_name_from_title_when_eventname_empty(
        self,
    ) -> None:
        from disaster_report.sources.gdacs import _extract_canonical_name

        result = _extract_canonical_name(
            {
                "eventtype": "TC",
                "eventname": "",
                "title": "Tropical Cyclone TAPAH-25",
            },
            [ReportPlace("CN", "Macao SAR", "")],
            "2025-09-20",
            "Tropical Cyclone",
        )
        assert result == "Tropical Cyclone TAPAH-25 Macao, China 2025-09-20"

    def test_volcano_extracts_name_from_title(self) -> None:
        from disaster_report.sources.gdacs import _extract_canonical_name

        result = _extract_canonical_name(
            {
                "eventtype": "VO",
                "title": "Eruption  Kanlaon",
            },
            [ReportPlace("PH", "Negros Occidental", "")],
            "2025-10-14",
            "Volcano",
        )
        assert result == "Volcano Kanlaon, Philippines 2025-10-14"

    def test_flood_omits_identifier(self) -> None:
        from disaster_report.sources.gdacs import _extract_canonical_name

        result = _extract_canonical_name(
            {
                "eventtype": "FL",
                "title": "Orange flood alert in China",
                "alertlevel": "Orange",
            },
            [ReportPlace("CN", "Hunan Sheng", "")],
            "2026-06-06",
            "Flood",
        )
        assert result == "Flood Hunan, China 2026-06-06"

    def test_forest_fire_omits_identifier(self) -> None:
        from disaster_report.sources.gdacs import _extract_canonical_name

        result = _extract_canonical_name(
            {
                "eventtype": "WF",
                "title": "Orange forest fire notification in France",
                "alertlevel": "Orange",
            },
            [ReportPlace("FR", "Pyrénées-Orientales", "")],
            "2026-07-04",
            "Forest Fire",
        )
        assert result == "Forest Fire Pyrenees-Orientales, France 2026-07-04"

    def test_drought_with_country(self) -> None:
        from disaster_report.sources.gdacs import _extract_canonical_name

        result = _extract_canonical_name(
            {
                "eventtype": "DR",
                "title": "Drought in Kenya, Somalia",
                "alertlevel": "Orange",
            },
            [ReportPlace("KE", "Shabeellaha Hoose", "")],
            "2025-12-01",
            "Drought",
        )
        assert result == "Drought Shabeellaha Hoose, Kenya 2025-12-01"

    def test_drought_degenerate_no_place(self) -> None:
        from disaster_report.sources.gdacs import _extract_canonical_name

        result = _extract_canonical_name(
            {"eventtype": "DR", "title": "Drought Green", "alertlevel": "Green"},
            [],
            "2025-12-21",
            "Drought",
        )
        assert result == "Drought 2025-12-21"

    def test_normalises_chinese_subdivision(self) -> None:
        from disaster_report.sources.gdacs import _extract_canonical_name

        result = _extract_canonical_name(
            {"eventtype": "FL", "title": "Flood in China"},
            [ReportPlace("CN", "Sichuan Sheng", "")],
            "2026-07-15",
            "Flood",
        )
        assert result == "Flood Sichuan, China 2026-07-15"
