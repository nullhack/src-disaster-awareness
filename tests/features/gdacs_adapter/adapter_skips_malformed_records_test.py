
import httpx

from disaster_surveillance_reporter.adapters.gdacs import GDACSAdapter


def test_malformed_records_are_skipped():
    valid1 = {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [121, 14]},
        "properties": {
            "eventtype": "EQ",
            "alertlevel": "Orange",
            "country": "Philippines",
            "fromdate": "2026-05-13",
            "todate": "2026-05-14",
        },
    }
    valid2 = {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [139, 35]},
        "properties": {
            "eventtype": "EQ",
            "alertlevel": "Green",
            "country": "Japan",
            "fromdate": "2026-05-13",
            "todate": "2026-05-14",
        },
    }
    geojson = {
        "type": "FeatureCollection",
        "features": [
            valid1,
            None,
            valid2,
        ],
    }

    transport = httpx.MockTransport(
        lambda req: httpx.Response(200, json=geojson)
    )

    with httpx.Client(transport=transport) as client:
        adapter = GDACSAdapter()
        result = adapter.fetch(client)

    assert len(result) == 2
    assert result[0].raw_fields["country"] == "Philippines"
    assert result[1].raw_fields["country"] == "Japan"
