import httpx

from disaster_surveillance_reporter.adapters.eonet import EONETAdapter


def _make_event(eid, title, source_id):
    return {
        "id": eid,
        "title": title,
        "categories": [{"id": "wildfires", "title": "Wildfires"}],
        "sources": [{"id": source_id, "url": "https://example.com"}],
        "geometry": [],
    }


def test_eonet_event_with_gdacs_source_is_skipped():
    geojson = {
        "events": [
            _make_event("EONET_30001", "GDACS-linked fire", "GDACS"),
        ],
    }

    transport = httpx.MockTransport(
        lambda req: httpx.Response(200, json=geojson)
    )
    with httpx.Client(transport=transport) as client:
        adapter = EONETAdapter()
        result = adapter.fetch(client)

    assert result == []


def test_eonet_non_gdacs_event_returns_normally():
    geojson = {
        "events": [
            _make_event("EONET_30002", "Regular fire", "EO"),
        ],
    }

    transport = httpx.MockTransport(
        lambda req: httpx.Response(200, json=geojson)
    )
    with httpx.Client(transport=transport) as client:
        adapter = EONETAdapter()
        result = adapter.fetch(client)

    assert len(result) == 1
    assert result[0].raw_fields["id"] == "EONET_30002"
