from __future__ import annotations

import json
from datetime import datetime

from disaster_report.sources.who import WHODiseaseOutbreakAdapter


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
