from __future__ import annotations

import json
from datetime import datetime

import pytest

from disaster_report.sources.who import WHODiseaseOutbreakAdapter, _normalize_country


def test_who_adapter_parses_captured_fixture(mock_httpx, load_fixture):
    items = json.loads(load_fixture("who_don.json"))["value"]
    adapter = WHODiseaseOutbreakAdapter()
    mock_httpx.register(adapter.url, load_fixture("who_don.json"), "application/json")

    incidents = adapter.fetch()

    assert len(incidents) == len(items)
    assert all(i.source_name == "WHO Disease Outbreak News" for i in incidents)
    assert all(i.incident_name and i.report_date for i in incidents)
    assert all(i.source_url.startswith("https://www.who.int/") for i in incidents)
    assert (
        incidents[0].source_url
        == "https://www.who.int" + items[0]["ItemDefaultUrl"]
    )
    datetime.fromisoformat(incidents[0].report_date)


def _who_item(title: str, don_id: str) -> dict:
    return {
        "Title": title,
        "UseOverrideTitle": False,
        "ItemDefaultUrl": f"/{don_id}",
        "PublicationDateAndTime": "2026-06-25T18:00:00Z",
    }


@pytest.mark.parametrize(
    "title, expect_disease, expect_country",
    [
        ("Ebola virus disease - DRC", "Ebola virus disease", "DRC"),
        ("Marburg virus disease- Ethiopia", "Marburg virus disease", "Ethiopia"),
        ("Ebola virus disease \u2013 DRC", "Ebola virus disease", "DRC"),
        ("Avian Influenza A(H5N5)\u2014 United States", "Avian Influenza A(H5N5)", "United States"),
        ("Ebola disease caused by Bundibugyo virus, DRC & Uganda", "Ebola disease caused by Bundibugyo virus", "DRC"),
    ],
)
def test_who_adapter_splits_title_across_separators(
    mock_httpx, title, expect_disease, expect_country
):
    payload = json.dumps({"value": [_who_item(title, "DON-SEP-1")]})
    adapter = WHODiseaseOutbreakAdapter()
    mock_httpx.register(adapter.url, payload, "application/json")

    incident = adapter.fetch()[0]

    assert incident.raw_fields["disease"] == expect_disease
    assert incident.country == expect_country


@pytest.mark.parametrize(
    "raw, expect",
    [
        ("Global", ""),
        ("Multi-locations", ""),
        ("Multi-location", ""),
        ("Worldwide", ""),
        ("International", ""),
        ("Region", ""),
        ("DRC & Uganda", "DRC"),
        ("Democratic Republic of the Congo & Uganda", "Democratic Republic of the Congo"),
        ("India", "India"),
        ("", ""),
        ("  ", ""),
    ],
)
def test_normalize_country_handles_sentinels_and_compounds(raw, expect):
    assert _normalize_country(raw) == expect


def test_normalize_country_preserves_compound_country_names():
    # "Bosnia and Herzegovina" is a single country - must NOT split on " and ".
    assert _normalize_country("Bosnia and Herzegovina") == "Bosnia and Herzegovina"
