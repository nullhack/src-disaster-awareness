
import httpx

from disaster_surveillance_reporter.adapters.gdacs import GDACSAdapter


def test_geojson_properties_preserved_verbatim():
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [121, 14]},
                "properties": {
                    "eventtype": "EQ",
                    "alertlevel": "Orange",
                    "country": "Philippines",
                    "fromdate": "2026-05-13T00:00:00",
                    "todate": "2026-05-14T00:00:00",
                    "name": "M6.2 Luzon",
                    "eventid": 12345,
                    "severitydata": {"severity": 3},
                    "url": {
                        "report": "https://gdacs.org/report/123",
                        "details": "https://gdacs.org/detail/123",
                        "geometry": "https://gdacs.org/geo/123",
                    },
                },
            }
        ],
    }

    transport = httpx.MockTransport(
        lambda req: httpx.Response(200, json=geojson)
    )

    with httpx.Client(transport=transport) as client:
        adapter = GDACSAdapter()
        result = adapter.fetch(client)

    assert len(result) == 1
    raw = result[0].raw_fields
    assert raw["eventtype"] == "EQ"
    assert raw["alertlevel"] == "Orange"
    assert raw["country"] == "Philippines"
    assert raw["eventid"] == 12345
    assert raw["url"]["report"] == "https://gdacs.org/report/123"
    assert raw["severitydata"]["severity"] == 3
    assert raw is result[0].raw_fields
