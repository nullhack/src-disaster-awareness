from __future__ import annotations

from disaster_report._title_format import (
    format_place,
    format_title,
    normalise_country,
    normalise_subdivision,
    smallest_place,
)
from disaster_report.models import ReportPlace


class TestFormatTitle:
    def test_joins_non_empty_parts_with_single_spaces(self) -> None:
        assert (
            format_title("Earthquake", "M7.5", "Yumare, Venezuela", "2026-06-24")
            == "Earthquake M7.5 Yumare, Venezuela 2026-06-24"
        )

    def test_skips_empty_parts(self) -> None:
        assert format_title("Flood", "", "Hunan, China", "2026-06-06") == "Flood Hunan, China 2026-06-06"

    def test_returns_empty_when_all_parts_empty(self) -> None:
        assert format_title("", "", "") == ""

    def test_strips_whitespace_around_parts(self) -> None:
        assert format_title("  Earthquake  ", " M7.5 ") == "Earthquake M7.5"


class TestNormaliseSubdivision:
    def test_strips_chinese_sheng_suffix(self) -> None:
        assert normalise_subdivision("Hunan Sheng") == "Hunan"

    def test_strips_hong_kong_sar_suffix(self) -> None:
        assert normalise_subdivision("Hong Kong SAR") == "Hong Kong"

    def test_strips_guangxi_zhuangzu_zizhiqu_suffix(self) -> None:
        assert normalise_subdivision("Guangxi Zhuangzu Zizhiqu") == "Guangxi"

    def test_strips_accents(self) -> None:
        assert normalise_subdivision("Pyrénées-Orientales") == "Pyrenees-Orientales"

    def test_no_change_for_plain_name(self) -> None:
        assert normalise_subdivision("Yaracuy") == "Yaracuy"

    def test_returns_empty_for_empty_input(self) -> None:
        assert normalise_subdivision("") == ""

    def test_case_insensitive_suffix_match(self) -> None:
        assert normalise_subdivision("Taiwan sheng") == "Taiwan"


class TestNormaliseCountry:
    def test_dr_congo_alias(self) -> None:
        assert normalise_country("Democratic Republic of the Congo") == "DR Congo"

    def test_uk_alias(self) -> None:
        assert normalise_country("United Kingdom") == "UK"

    def test_passes_through_short_form_unchanged(self) -> None:
        assert normalise_country("Venezuela") == "Venezuela"

    def test_returns_empty_for_empty_input(self) -> None:
        assert normalise_country("") == ""


class TestSmallestPlace:
    def test_locality_wins_over_subdivision(self) -> None:
        assert smallest_place([ReportPlace("VE", "Yaracuy", "Yumare")]) == ("Yumare", "Venezuela")

    def test_subdivision_used_when_no_locality(self) -> None:
        assert smallest_place([ReportPlace("CN", "Hunan Sheng", "")]) == ("Hunan", "China")

    def test_country_fallback_when_no_locality_or_subdivision(self) -> None:
        assert smallest_place([ReportPlace("CN", "", "")]) == ("China", "China")

    def test_returns_empty_pair_for_empty_places(self) -> None:
        assert smallest_place([]) == ("", "")

    def test_uses_first_place_only(self) -> None:
        places = [ReportPlace("PH", "Sarangani", "Glan"), ReportPlace("VE", "Yaracuy", "Yumare")]
        assert smallest_place(places) == ("Glan", "Philippines")

    def test_subdivision_normalised(self) -> None:
        assert smallest_place([ReportPlace("FR", "Pyrénées-Orientales", "")]) == (
            "Pyrenees-Orientales",
            "France",
        )

    def test_strips_locality_offset_when_present(self) -> None:
        assert smallest_place([ReportPlace("VE", "", "20 km ESE of Yumare")]) == ("Yumare", "Venezuela")


class TestFormatPlace:
    def test_smallest_with_country(self) -> None:
        assert format_place("Yumare", "Venezuela") == "Yumare, Venezuela"

    def test_smallest_equals_country(self) -> None:
        assert format_place("China", "China") == "China"

    def test_empty_smallest_keeps_country(self) -> None:
        assert format_place("", "China") == "China"

    def test_both_empty_returns_empty(self) -> None:
        assert format_place("", "") == ""

    def test_empty_country_keeps_smallest(self) -> None:
        assert format_place("Banda Sea", "") == "Banda Sea"
