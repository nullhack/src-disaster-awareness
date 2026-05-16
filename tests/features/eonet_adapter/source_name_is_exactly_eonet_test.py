import httpx

from disaster_surveillance_reporter.adapters.eonet import EONETAdapter


def test_eonet_source_name_is_exact():
    geojson = {
        "events": [
            {
                "id": "EONET_20001",
                "title": "Flood in Thailand",
                "categories": [{"id": "floods", "title": "Floods"}],
                "sources": [{"id": "EO", "url": "https://example.com"}],
                "geometry": [],
            },
            {
                "id": "EONET_20002",
                "title": "Earthquake in Japan",
                "categories": [{"id": "earthquakes", "title": "Earthquakes"}],
                "sources": [{"id": "EO", "url": "https://example.com"}],
                "geometry": [],
            },
        ],
    }

    transport = httpx.MockTransport(
        lambda req: httpx.Response(200, json=geojson)
    )
    with httpx.Client(transport=transport) as client:
        adapter = EONETAdapter()
        result = adapter.fetch(client)

    assert len(result) == 2
    for record in result:
        assert record.source_name == "EONET"
