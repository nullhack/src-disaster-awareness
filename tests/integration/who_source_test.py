from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from disaster_report.models import SourceReport
    from disaster_report.sources.who import WHODiseaseOutbreakAdapter

from disaster_report.models import ReportPlace

CASSETTE: str = "who_don.yaml"
ERROR_CASSETTE_ORDERBY: str = "NotAField"


class TestWHODiseaseOutbreakAdapter:
    adapter: WHODiseaseOutbreakAdapter

    def test_fetch_returns_source_reports_from_odata_feed(self) -> None:
        import vcr

        from disaster_report.sources.who import WHODiseaseOutbreakAdapter

        with vcr.use_cassette(f"tests/cassettes/{CASSETTE}"):
            reports = WHODiseaseOutbreakAdapter().fetch()
        assert len(reports) > 0

    def test_each_source_report_carries_who_source_name(self) -> None:
        import vcr

        from disaster_report.sources.who import WHODiseaseOutbreakAdapter

        with vcr.use_cassette(f"tests/cassettes/{CASSETTE}"):
            reports = WHODiseaseOutbreakAdapter().fetch()
        assert all(report.source == "WHO" for report in reports)

    def test_each_source_report_carries_specific_disease_type(self) -> None:
        import vcr

        from disaster_report.sources.who import WHODiseaseOutbreakAdapter

        with vcr.use_cassette(f"tests/cassettes/{CASSETTE}"):
            reports = WHODiseaseOutbreakAdapter().fetch()
        assert all(
            report.incident_type and report.incident_type != "Disease"
            for report in reports
        )

    def test_title_respects_use_override_title_flag(self) -> None:
        import vcr

        from disaster_report.sources.who import WHODiseaseOutbreakAdapter

        with vcr.use_cassette(f"tests/cassettes/{CASSETTE}"):
            reports = WHODiseaseOutbreakAdapter().fetch()
        assert first_source_report(reports).name != ""

    def test_disease_name_extracted_from_title(self) -> None:
        from disaster_report._search_keys import disease_from_title

        assert disease_from_title("Ebola disease caused by Bundibugyo virus") == "Ebola"
        assert disease_from_title("Nipah virus disease - India") == "Nipah"
        assert disease_from_title("Yellow fever - Global") == "Yellow fever"
        assert (
            disease_from_title("Hantavirus outbreak linked to cruise") == "Hantavirus"
        )
        assert disease_from_title("Avian Influenza") == "Avian Influenza"
        assert disease_from_title("") == ""

    def test_disease_name_extracted_from_title_handles_en_dash(self) -> None:
        from disaster_report._search_keys import disease_from_title

        assert disease_from_title("Marburg virus disease \u2013 Ethiopia") == "Marburg"
        assert disease_from_title("Ebola \u2013 Uganda") == "Ebola"
        assert disease_from_title("Cholera \u2013 Global") == "Cholera"

    def test_disease_name_split_on_dash_suffix(self) -> None:
        from disaster_report.sources.who import WHODiseaseOutbreakAdapter

        report = build_who_report(
            name="Nipah virus disease - India",
            places=[
                ReportPlace(country_code="IN", subdivision="", locality=""),
            ],
            report_date="2026-06-25",
        )
        strict, loose = WHODiseaseOutbreakAdapter().derive_keys(report)
        assert strict == "Nipah India June 2026", strict
        assert loose == "Nipah India 2026", loose

    def test_report_date_is_iso_parseable(self) -> None:
        import datetime

        import vcr

        from disaster_report.sources.who import WHODiseaseOutbreakAdapter

        with vcr.use_cassette(f"tests/cassettes/{CASSETTE}"):
            reports = WHODiseaseOutbreakAdapter().fetch()
        datetime.date.fromisoformat(first_source_report(reports).report_date)

    def test_raw_fields_preserve_guid_identity(self) -> None:
        import vcr

        from disaster_report.sources.who import WHODiseaseOutbreakAdapter

        with vcr.use_cassette(f"tests/cassettes/{CASSETTE}"):
            reports = WHODiseaseOutbreakAdapter().fetch()
        raw = first_source_report(reports).raw_fields
        assert "Id" in raw

    def test_derive_keys_include_disease_name(self) -> None:
        from disaster_report.sources.who import WHODiseaseOutbreakAdapter

        strict, loose = WHODiseaseOutbreakAdapter().derive_keys(build_who_report())
        assert strict == "Ebola Uganda July 2026", strict
        assert loose == "Ebola Uganda 2026", loose

    def test_derive_keys_multi_country_skips_strict_disease_in_loose(self) -> None:
        from disaster_report.sources.who import WHODiseaseOutbreakAdapter

        report = build_who_report(
            name="Ebola disease caused by Bundibugyo virus",
            places=[
                ReportPlace(country_code="CD", subdivision="", locality=""),
                ReportPlace(country_code="UG", subdivision="", locality=""),
            ],
            report_date="2026-07-03",
        )
        strict, loose = WHODiseaseOutbreakAdapter().derive_keys(report)
        assert strict == "", strict
        assert loose == "Ebola africa 2026", loose

    def test_derive_keys_global_zero_places_skips_strict(self) -> None:
        from disaster_report.sources.who import WHODiseaseOutbreakAdapter

        report = build_who_report(
            name="Yellow fever - Global",
            places=[],
            report_date="2026-06-24",
        )
        strict, loose = WHODiseaseOutbreakAdapter().derive_keys(report)
        assert strict == "", strict
        assert loose == "Yellow fever 2026", loose

    def test_fetch_raises_on_clean_400_error_path(self) -> None:
        import vcr

        from disaster_report.sources.errors import SourceFetchError
        from disaster_report.sources.who import WHODiseaseOutbreakAdapter

        with (
            vcr.use_cassette(f"tests/cassettes/{CASSETTE}"),
            pytest.raises(SourceFetchError),
        ):
            WHODiseaseOutbreakAdapter(orderby=ERROR_CASSETTE_ORDERBY).fetch()

    def test_derive_keys_drops_disease_kwarg(self) -> None:
        from disaster_report.sources.who import WHODiseaseOutbreakAdapter

        report = build_who_report(name="Ebola disease caused by Bundibugyo virus")
        strict, loose = WHODiseaseOutbreakAdapter().derive_keys(report)
        assert not strict.startswith("Disease "), strict
        assert not loose.startswith("Disease "), loose
        assert "Ebola" in strict
        assert "Ebola" in loose


def first_source_report(reports: list[SourceReport]) -> SourceReport:
    return reports[0]


def build_who_report(
    *,
    source: str = "WHO",
    source_id: str = "2026-DON612",
    incident_type: str | None = None,
    name: str = "Ebola disease caused by Bundibugyo virus",
    places: list[ReportPlace] | None = None,
    report_date: str = "2026-07-04",
    raw_fields: dict[str, object] | None = None,
) -> SourceReport:
    from disaster_report._search_keys import disease_from_title
    from disaster_report.models import SourceReport

    if incident_type is None:
        incident_type = disease_from_title(name) or "Disease"
    defaults: dict[str, object] = {
        "Id": "608d728d-b078-4614-9ccf-682229ebfee8",
        "disease": "Ebola",
    }
    return SourceReport(
        source=source,
        source_id=source_id,
        incident_type=incident_type,
        name=name,
        places=places
        if places is not None
        else [
            ReportPlace(country_code="UG", subdivision="", locality=""),
        ],
        report_date=report_date,
        raw_fields=raw_fields if raw_fields is not None else defaults,
    )


class TestWHOExtractCanonicalName:
    def test_disease_with_country_only(self) -> None:
        from disaster_report.sources.who import _extract_canonical_name

        result = _extract_canonical_name(
            {},
            [ReportPlace("UG", "", "")],
            "2025-09-05",
            "Ebola",
        )
        assert result == "Ebola Uganda 2025-09-05"

    def test_disease_global_no_places_uses_Global(self) -> None:
        from disaster_report.sources.who import _extract_canonical_name

        result = _extract_canonical_name(
            {},
            [],
            "2025-05-28",
            "COVID-19",
        )
        assert result == "COVID-19 Global 2025-05-28"

    def test_disease_uses_subdivision_when_available(self) -> None:
        from disaster_report.sources.who import _extract_canonical_name

        result = _extract_canonical_name(
            {},
            [ReportPlace("CD", "Kinshasa", "")],
            "2025-09-05",
            "Ebola",
        )
        assert result == "Ebola Kinshasa, DR Congo 2025-09-05"

    def test_disease_normalises_messy_incident_type(self) -> None:
        from disaster_report.sources.who import _extract_canonical_name

        result = _extract_canonical_name(
            {},
            [ReportPlace("US", "", "")],
            "2025-04-01",
            "Avian Influenza A(H5N1)",
        )
        assert result == "Avian Influenza United States 2025-04-01"

    def test_disease_unknown_falls_back_to_first_word(self) -> None:
        from disaster_report.sources.who import _extract_canonical_name

        result = _extract_canonical_name(
            {},
            [ReportPlace("UG", "", "")],
            "2025-09-05",
            "Mysterious Novel Pathogen X",
        )
        assert result == "Mysterious Uganda 2025-09-05"

    def test_disease_normalises_long_country_name(self) -> None:
        from disaster_report.sources.who import _extract_canonical_name

        result = _extract_canonical_name(
            {},
            [ReportPlace("CD", "", "")],
            "2025-09-05",
            "Ebola",
        )
        assert "DR Congo" in result
        assert "Democratic Republic" not in result

    def test_title_suffix_country_overrides_body_scan_places(self) -> None:
        from disaster_report.sources.who import _extract_canonical_name

        result = _extract_canonical_name(
            {"title": "Marburg virus disease - Ethiopia"},
            [
                ReportPlace("AO", "", ""),
                ReportPlace("CD", "", ""),
                ReportPlace("ET", "", ""),
                ReportPlace("UG", "", ""),
            ],
            "2025-09-05",
            "Marburg",
        )
        assert result == "Marburg Ethiopia 2025-09-05"

    def test_title_global_suffix_overrides_places(self) -> None:
        from disaster_report.sources.who import _extract_canonical_name

        result = _extract_canonical_name(
            {"title": "Yellow fever - Global situation"},
            [ReportPlace("BR", "", ""), ReportPlace("CO", "", "")],
            "2025-06-24",
            "Yellow fever",
        )
        assert result == "Yellow fever Global 2025-06-24"

    def test_title_country_match_uses_subdivision_when_available(self) -> None:
        from disaster_report.sources.who import _extract_canonical_name

        result = _extract_canonical_name(
            {"title": "Ebola virus disease – Democratic Republic of the Congo"},
            [
                ReportPlace("CD", "Kinshasa", ""),
                ReportPlace("UG", "Bundibugyo", ""),
            ],
            "2025-09-05",
            "Ebola",
        )
        assert result == "Ebola Kinshasa, DR Congo 2025-09-05"

    def test_title_without_suffix_falls_back_to_places(self) -> None:
        from disaster_report.sources.who import _extract_canonical_name

        result = _extract_canonical_name(
            {"title": "Ebola disease caused by Bundibugyo virus"},
            [ReportPlace("UG", "", "")],
            "2025-09-05",
            "Ebola",
        )
        assert result == "Ebola Uganda 2025-09-05"
