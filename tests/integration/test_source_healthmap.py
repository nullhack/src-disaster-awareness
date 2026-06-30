from __future__ import annotations

import html
import json
import re
from datetime import datetime

from disaster_report.sources.healthmap import HealthMapAdapter

_TAG = re.compile(r"<[^>]+>")


def _strip(s: str) -> str:
    return html.unescape(_TAG.sub("", s or "")).strip()


def test_healthmap_adapter_parses_captured_fixture(mock_httpx, load_fixture):
    rows = json.loads(load_fixture("healthmap_alerts.json"))["listview"]
    adapter = HealthMapAdapter()
    mock_httpx.register(
        adapter.url, load_fixture("healthmap_alerts.json"), "application/json"
    )

    incidents = adapter.fetch()

    assert len(incidents) == len(rows)
    assert all(i.source_name == "HealthMap" for i in incidents)
    assert all(i.incident_name for i in incidents)
    assert incidents[0].source_url.startswith("https://www.healthmap.org/ai.php?")
    assert incidents[0].incident_name == _strip(rows[0][2])
    datetime.fromisoformat(incidents[0].report_date)


def test_healthmap_adapter_extracts_us_state_subdivision_from_headline(mock_httpx, load_fixture):
    fixture = json.dumps({
        "listview": [
            [
                "1",
                "22 Jun 2026",
                "Arizona: Maricopa County reports increase in West Nile virus cases",
                "West Nile Virus",
                "United States",
                "https://www.healthmap.org/ai.php?12345",
            ]
        ]
    })
    adapter = HealthMapAdapter()
    mock_httpx.register(adapter.url, fixture, "application/json")

    incidents = adapter.fetch()

    assert len(incidents) == 1
    sub = incidents[0].raw_fields.get("subdivision")
    assert sub == "US-AZ", f"expected US-AZ subdivision, got {sub!r}"
