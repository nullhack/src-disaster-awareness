import httpx

from disaster_surveillance_reporter.adapters.gdacs import GDACSAdapter


def test_all_records_have_exact_source_name():
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
                    "fromdate": "2026-05-13",
                    "todate": "2026-05-14",
                },
            },
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [139, 35]},
                "properties": {
                    "eventtype": "EQ",
                    "alertlevel": "Green",
                    "country": "Japan",
                    "fromdate": "2026-05-13",
                    "todate": "2026-05-14",
                },
            },
        ],
    }

    transport = httpx.MockTransport(
        lambda req: httpx.Response(200, json=geojson)
    )

    with httpx.Client(transport=transport) as client:
        adapter = GDACSAdapter()
        result = adapter.fetch(client)

    assert len(result) == 2
    for record in result:
        assert record.source_name == "GDACS"
