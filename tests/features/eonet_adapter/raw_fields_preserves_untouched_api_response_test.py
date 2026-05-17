import httpx

from disaster_surveillance_reporter.adapters.eonet import EONETAdapter


def test_eonet_api_response_preserved_verbatim():
    event = {
        "id": "EONET_20104",
        "title": "Wildfire in California",
        "categories": [{"id": "wildfires", "title": "Wildfires"}],
        "sources": [{"id": "EO", "url": "https://eonet.gsfc.nasa.gov/"}],
        "geometry": [
            {
                "date": "2026-05-01T00:00:00Z",
                "type": "Point",
                "coordinates": [-120.0, 37.0],
            }
        ],
        "description": "A wildfire is burning in California.",
        "link": "https://eonet.gsfc.nasa.gov/api/v3/events/EONET_20104",
    }

    geojson = {"events": [event]}
    transport = httpx.MockTransport(
        lambda req: httpx.Response(200, json=geojson)
    )
    with httpx.Client(transport=transport) as client:
        adapter = EONETAdapter()
        result = adapter.fetch(client)

    assert len(result) == 1
    raw = result[0].raw_fields
    assert raw["id"] == "EONET_20104"
    assert raw["title"] == "Wildfire in California"
    assert raw["categories"][0]["title"] == "Wildfires"
    assert raw["sources"][0]["id"] == "EO"
    assert raw["geometry"][0]["coordinates"] == [-120.0, 37.0]
    assert raw["description"] == "A wildfire is burning in California."
