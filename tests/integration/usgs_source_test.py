from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from disaster_report.models import SourceReport
    from disaster_report.sources.usgs import USGSAdapter

from disaster_report.models import ReportPlace

CASSETTE: str = "usgs_summary_feed.yaml"
ERROR_CASSETTE_SLUG: str = "99_day.geojson"
SOFT_404_BODY: str = "404 File Not Found"


class TestUSGSAdapter:
    adapter: USGSAdapter

    def test_fetch_returns_source_reports_from_summary_feed(self) -> None:
        import vcr

        from disaster_report.sources.usgs import USGSAdapter

        with vcr.use_cassette(f"tests/cassettes/{CASSETTE}"):
            reports = USGSAdapter().fetch()
        assert len(reports) > 0

    def test_each_source_report_carries_usgs_source_name(self) -> None:
        import vcr

        from disaster_report.sources.usgs import USGSAdapter

        with vcr.use_cassette(f"tests/cassettes/{CASSETTE}"):
            reports = USGSAdapter().fetch()
        assert all(report.source == "USGS" for report in reports)

    def test_each_source_report_is_typed_earthquake(self) -> None:
        import vcr

        from disaster_report.sources.usgs import USGSAdapter

        with vcr.use_cassette(f"tests/cassettes/{CASSETTE}"):
            reports = USGSAdapter().fetch()
        assert all(report.incident_type == "Earthquake" for report in reports)

    def test_source_report_name_matches_feature_title(self) -> None:
        import vcr

        from disaster_report.sources.usgs import USGSAdapter

        with vcr.use_cassette(f"tests/cassettes/{CASSETTE}"):
            reports = USGSAdapter().fetch()
        assert first_source_report(reports).name != ""

    def test_report_date_is_iso_parseable(self) -> None:
        import datetime

        import vcr

        from disaster_report.sources.usgs import USGSAdapter

        with vcr.use_cassette(f"tests/cassettes/{CASSETTE}"):
            reports = USGSAdapter().fetch()
        report = first_source_report(reports)
        datetime.date.fromisoformat(report.report_date)

    def test_raw_fields_preserve_magnitude_place_and_depth(self) -> None:
        import vcr

        from disaster_report.sources.usgs import USGSAdapter

        with vcr.use_cassette(f"tests/cassettes/{CASSETTE}"):
            reports = USGSAdapter().fetch()
        raw = first_source_report(reports).raw_fields
        assert "mag" in raw
        assert "place" in raw
        assert "depth" in raw
        assert "geometry" in raw

    def test_each_source_report_carries_standardized_places(self) -> None:
        import vcr

        from disaster_report.sources.usgs import USGSAdapter

        with vcr.use_cassette(f"tests/cassettes/{CASSETTE}"):
            reports = USGSAdapter().fetch()
        for report in reports:
            for place in report.places:
                assert isinstance(place, ReportPlace)
                if place.locality == "Ocean":
                    assert place.country_code == ""
                    assert place.subdivision == ""
                else:
                    assert place.country_code != ""

    def test_source_id_is_the_usgs_eventid(self) -> None:
        import vcr

        from disaster_report.sources.usgs import USGSAdapter

        with vcr.use_cassette(f"tests/cassettes/{CASSETTE}"):
            reports = USGSAdapter().fetch()
        assert first_source_report(reports).source_id != ""

    def test_should_monitor_keeps_significant_events(self) -> None:
        from disaster_report.sources.usgs import USGSAdapter

        adapter = USGSAdapter()
        kept = build_kept_report()
        dropped = build_kept_report(raw_fields={"mag": 1.0})
        assert adapter.should_monitor(kept) is True
        assert adapter.should_monitor(dropped) is False

    def test_derive_keys_returns_strict_and_loose_search_phrases(self) -> None:
        from disaster_report.sources.usgs import USGSAdapter

        strict, loose = USGSAdapter().derive_keys(build_kept_report())
        assert strict == "Earthquake Town, United States July 2026", strict
        assert loose == "Earthquake United States 2026", loose

    def test_derive_keys_empty_locality_degrades_to_country_only(self) -> None:
        from disaster_report.models import SourceReport
        from disaster_report.sources.usgs import USGSAdapter

        report = SourceReport(
            source="USGS",
            source_id="x",
            incident_type="Earthquake",
            name="M 5.0 - region",
            places=[
                ReportPlace(country_code="CN", subdivision="Sichuan", locality=""),
            ],
            report_date="2026-07-05",
            raw_fields={"mag": 5.0},
        )
        strict, loose = USGSAdapter().derive_keys(report)
        assert strict == "Earthquake China July 2026", strict
        assert loose == "Earthquake China 2026", loose

    def test_derive_keys_offshore_no_places_skips_strict(self) -> None:
        from disaster_report.models import SourceReport
        from disaster_report.sources.usgs import USGSAdapter

        report = SourceReport(
            source="USGS",
            source_id="x",
            incident_type="Earthquake",
            name="west of Macquarie Island",
            places=[],
            report_date="2026-07-05",
            raw_fields={"mag": 5.4},
        )
        strict, loose = USGSAdapter().derive_keys(report)
        assert strict == "", strict
        assert loose == "Earthquake 2026", loose

    def test_fetch_raises_typed_error_on_soft_404(self) -> None:
        import vcr

        from disaster_report.sources.errors import SourceFetchError
        from disaster_report.sources.usgs import USGSAdapter

        with (
            vcr.use_cassette(f"tests/cassettes/{CASSETTE}"),
            pytest.raises(SourceFetchError),
        ):
            USGSAdapter(slug=ERROR_CASSETTE_SLUG).fetch()


def first_source_report(reports: list[SourceReport]) -> SourceReport:
    return reports[0]


def build_kept_report(
    *,
    source: str = "USGS",
    source_id: str = "us7000abcd",
    incident_type: str = "Earthquake",
    name: str = "M 5.6 - 10 km S of Town",
    places: list[ReportPlace] | None = None,
    report_date: str = "2026-07-04",
    raw_fields: dict[str, object] | None = None,
) -> SourceReport:
    from disaster_report.models import SourceReport

    defaults: dict[str, object] = {
        "mag": 5.6,
        "place": "10 km S of Town",
        "depth": 10.0,
    }
    return SourceReport(
        source=source,
        source_id=source_id,
        incident_type=incident_type,
        name=name,
        places=places
        if places is not None
        else [
            ReportPlace(country_code="US", subdivision="", locality="10 km S of Town"),
        ],
        report_date=report_date,
        raw_fields=raw_fields if raw_fields is not None else defaults,
    )
