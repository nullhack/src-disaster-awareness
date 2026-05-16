import httpx
from hypothesis import given, example, strategies as st

from disaster_surveillance_reporter.adapters.eonet import EONETAdapter


def _make_event(eid, title):
    return {
        "id": eid,
        "title": title,
        "categories": [{"id": "wildfires", "title": "Wildfires"}],
        "sources": [{"id": "EO", "url": "https://example.com"}],
        "geometry": [],
    }


@example(fire_pattern="Prescribed Fire")
@example(fire_pattern="RX Burn Project")
@example(fire_pattern="rx")
@given(fire_pattern=st.text())
def test_eonet_prescribed_fire_is_filtered(fire_pattern):
    geojson = {"events": [_make_event("EONET_40001", fire_pattern)]}

    transport = httpx.MockTransport(
        lambda req: httpx.Response(200, json=geojson)
    )
    with httpx.Client(transport=transport) as client:
        adapter = EONETAdapter()
        result = adapter.fetch(client)

    should_filter = (
        "prescribed fire" in fire_pattern.lower()
        or "rx" in fire_pattern.lower()
    )
    if should_filter:
        assert result == []
    else:
        assert len(result) == 1


def test_eonet_wildfire_event_returns_normally():
    geojson = {"events": [_make_event("EONET_40002", "Wildfire in California")]}

    transport = httpx.MockTransport(
        lambda req: httpx.Response(200, json=geojson)
    )
    with httpx.Client(transport=transport) as client:
        adapter = EONETAdapter()
        result = adapter.fetch(client)

    assert len(result) == 1
    assert result[0].raw_fields["title"] == "Wildfire in California"
