from __future__ import annotations

import json
from datetime import datetime

from disaster_report.sources.usgs import USGSEarthquakesAdapter


def test_usgs_adapter_parses_captured_fixture(mock_httpx, load_fixture):
    features = json.loads(load_fixture("usgs_earthquakes.geojson"))["features"]
    adapter = USGSEarthquakesAdapter()
    mock_httpx.register(
        adapter.url, load_fixture("usgs_earthquakes.geojson"), "application/json"
    )

    incidents = adapter.fetch()

    assert len(incidents) == len(features)
    assert all(i.source_name == "USGS Earthquakes" for i in incidents)
    assert all(i.incident_type == "Earthquake" for i in incidents)
    assert all(i.incident_name and i.report_date and i.source_url for i in incidents)
    assert all(
        i.source_url.startswith("https://earthquake.usgs.gov/") for i in incidents
    )
    assert incidents[0].incident_name == features[0]["properties"]["title"]
    datetime.fromisoformat(incidents[0].report_date)
    first_geom = (features[0].get("geometry") or {}).get("coordinates") or []
    expected_depth = first_geom[2] if len(first_geom) > 2 else 0
    assert incidents[0].raw_fields["depth"] == expected_depth
    assert incidents[0].raw_fields["mag"] == features[0]["properties"]["mag"]
    assert incidents[0].raw_fields["place"] == features[0]["properties"]["place"]
