from __future__ import annotations


from disaster_report._countries import (
    extract_places_from_text,
    scan_countries,
    scan_subdivision,
)


class TestScanCountries:
    def test_drc_with_the_resolves_to_cd_not_cg(self) -> None:
        names = [
            code
            for _, code in scan_countries(
                "outbreak in the Democratic Republic of the Congo"
            )
        ]
        assert "CD" in names
        assert "CG" not in names

    def test_drc_without_the_resolves_to_cd_not_cg(self) -> None:
        names = [
            code
            for _, code in scan_countries(
                "reported from the Democratic Republic of Congo"
            )
        ]
        assert "CD" in names
        assert "CG" not in names

    def test_drc_short_alias_resolves_to_cd(self) -> None:
        names = [code for _, code in scan_countries("DRC outbreak")]
        assert names == ["CD"]

    def test_congo_alone_resolves_to_cg(self) -> None:
        names = [code for _, code in scan_countries("cases in Congo")]
        assert names == ["CG"]

    def test_south_georgia_does_not_match_georgia(self) -> None:
        names = [
            code
            for _, code in scan_countries("endemic in South Georgia and nearby islands")
        ]
        assert "GE" not in names

    def test_georgia_alone_matches_ge(self) -> None:
        names = [code for _, code in scan_countries("outbreak in Georgia")]
        assert names == ["GE"]

    def test_longest_first_drc_beats_congo_substring(self) -> None:
        text = "Democratic Republic of the Congo and Congo both reported"
        names = [code for _, code in scan_countries(text)]
        assert names == ["CD", "CG"]

    def test_uninhabited_territories_dropped(self) -> None:
        names = [code for _, code in scan_countries("Antarctica and Bouvet Island")]
        assert names == []

    def test_hong_kong_resolves_to_hk_not_cn(self) -> None:
        names = [code for _, code in scan_countries("cases in Hong Kong")]
        assert names == ["HK"]

    def test_dedupes_repeated_country(self) -> None:
        names = [code for _, code in scan_countries("Uganda and Uganda again")]
        assert names == ["UG"]


class TestScanSubdivision:
    def test_kerala_resolves_under_india(self) -> None:
        assert scan_subdivision("outbreak in Kerala state", "IN") == "Kerala"

    def test_kinshasa_resolves_under_drc(self) -> None:
        assert scan_subdivision("cases in Kinshasa province", "CD") == "Kinshasa"

    def test_rwampara_resolves_under_uganda_not_sri_lanka(self) -> None:
        assert scan_subdivision("Rwampara reported", "UG") == "Rwampara"

    def test_rwampara_does_not_resolve_under_sri_lanka(self) -> None:
        assert scan_subdivision("Rwampara reported", "LK") == ""

    def test_tristan_da_cunha_does_not_resolve_under_uk(self) -> None:
        assert scan_subdivision("Tristan da Cunha island", "GB") == ""

    def test_city_not_admin1_returns_empty(self) -> None:
        assert scan_subdivision("cases in Jinka town", "ET") == ""

    def test_case_insensitive_match(self) -> None:
        assert scan_subdivision("outbreak in kerala state", "IN") == "Kerala"

    def test_no_subdivision_in_text_returns_empty(self) -> None:
        assert scan_subdivision("no places here", "IN") == ""

    def test_unknown_country_returns_empty(self) -> None:
        assert scan_subdivision("anything", "ZZ") == ""


class TestExtractPlacesFromText:
    def test_global_title_short_circuits_to_empty(self) -> None:
        places = extract_places_from_text(
            title="Yellow fever - Global",
            body_sections={"Summary": "cases in Brazil and Peru"},
        )
        assert places == []

    def test_global_case_insensitive(self) -> None:
        places = extract_places_from_text(
            title="Disease - GLOBAL",
            body_sections={"Summary": "cases in Brazil"},
        )
        assert places == []

    def test_multi_country_not_short_circuited(self) -> None:
        places = extract_places_from_text(
            title="Hantavirus - Multi-country",
            body_sections={"Summary": "cases in United Kingdom and Netherlands"},
        )
        names = [p["name"] for p in places]
        assert "UK" in names
        assert "Netherlands" in names

    def test_places_carry_four_keys(self) -> None:
        places = extract_places_from_text(
            title="Marburg virus",
            body_sections={"Summary": "outbreak in Uganda"},
        )
        assert places
        for place in places:
            assert set(place.keys()) == {
                "name",
                "country_code",
                "subdivision",
                "locality",
                "region",
            }

    def test_place_region_from_un_m49(self) -> None:
        places = extract_places_from_text(
            title="Marburg virus",
            body_sections={"Summary": "outbreak in Uganda"},
        )
        assert places[0]["region"] == "Eastern Africa"

    def test_place_subdivision_resolved(self) -> None:
        places = extract_places_from_text(
            title="Nipah virus",
            body_sections={"Summary": "outbreak in Kerala, India"},
        )
        india = next(p for p in places if p["name"] == "India")
        assert india["subdivision"] == "Kerala"
        assert india["region"] == "Southern Asia"

    def test_drc_not_canonicalized_to_cg(self) -> None:
        places = extract_places_from_text(
            title="Ebola",
            body_sections={
                "Summary": "Democratic Republic of the Congo reported cases"
            },
        )
        names = [p["name"] for p in places]
        assert "DR Congo" in names
        assert not any(p["name"] == "Congo" for p in places)

    def test_locality_always_empty(self) -> None:
        places = extract_places_from_text(
            title="Disease",
            body_sections={"Summary": "outbreak in Uganda and India"},
        )
        for place in places:
            assert place["locality"] == ""

    def test_html_stripped_from_body(self) -> None:
        places = extract_places_from_text(
            title="Disease",
            body_sections={"Summary": "<p>outbreak in <b>Uganda</b></p>"},
        )
        assert any(p["name"] == "Uganda" for p in places)
