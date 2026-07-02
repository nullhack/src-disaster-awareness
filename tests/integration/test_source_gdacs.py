from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime

from disaster_report.sources.gdacs import GDACSAdapter

_NS = {"g": "http://www.gdacs.org"}


def test_gdacs_adapter_parses_captured_fixture(mock_httpx, load_fixture):
    root = ET.fromstring(load_fixture("gdacs_24h.xml"))
    items = root.findall(".//item")
    adapter = GDACSAdapter()
    mock_httpx.register(adapter.url, load_fixture("gdacs_24h.xml"), "application/xml")

    incidents = adapter.fetch()

    assert len(incidents) == len(items)
    assert all(i.source_name == "GDACS" for i in incidents)
    assert all(i.incident_name and i.report_date and i.source_url for i in incidents)
    assert all(i.source_url.startswith("https://www.gdacs.org/") for i in incidents)
    assert incidents[0].incident_name == (items[0].findtext("title") or "").strip()
    assert (
        incidents[0].country
        == (items[0].findtext("g:country", default="", namespaces=_NS) or "").strip()
    )
    assert incidents[0].incident_type != ""
    datetime.fromisoformat(incidents[0].report_date)
    first_item = items[0]
    assert incidents[0].raw_fields["alertlevel"] == (
        first_item.findtext("g:alertlevel", default="", namespaces=_NS) or ""
    )
    assert incidents[0].raw_fields["episodeid"] == (
        first_item.findtext("g:episodeid", default="", namespaces=_NS) or ""
    )
    pop_elt = first_item.find("g:population", namespaces=_NS)
    expected_pop = pop_elt.get("value", "0") if pop_elt is not None else "0"
    assert incidents[0].raw_fields["population"] == expected_pop
    assert incidents[0].raw_fields["alertscore"] == (
        first_item.findtext("g:alertscore", default="0", namespaces=_NS) or "0"
    )
    assert incidents[0].raw_fields["severity"] == (
        first_item.findtext("g:severity", default="", namespaces=_NS) or ""
    )
