import httpx

from disaster_surveillance_reporter.adapters.eonet import EONETAdapter


def _valid_event(eid="EONET_20001", title="Flood in Thailand"):
    return {
        "id": eid,
        "title": title,
        "categories": [{"id": "floods", "title": "Floods"}],
        "sources": [{"id": "EO", "url": "https://example.com"}],
        "geometry": [],
    }


def test_eonet_malformed_records_silently_skipped():
    geojson = {
        "events": [
            _valid_event("EONET_20001", "Flood in Thailand"),
            None,
            "not a dict",
            42,
        ],
    }

    transport = httpx.MockTransport(
        lambda req: httpx.Response(200, json=geojson)
    )
    with httpx.Client(transport=transport) as client:
        adapter = EONETAdapter()
        result = adapter.fetch(client)

    assert len(result) == 1
    assert result[0].raw_fields["id"] == "EONET_20001"


def test_eonet_all_malformed_yields_empty_list():
    geojson = {
        "events": [
            None,
            "not a dict",
            42,
            [],
        ],
    }

    transport = httpx.MockTransport(
        lambda req: httpx.Response(200, json=geojson)
    )
    with httpx.Client(transport=transport) as client:
        adapter = EONETAdapter()
        result = adapter.fetch(client)

    assert result == []
