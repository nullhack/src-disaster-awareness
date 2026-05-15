import httpx

from disaster_surveillance_reporter.adapters.gdelt import GDELTAdapter


def test_source_name_is_always_gdelt():
    article1 = {
        "url": "https://example.com/quake1",
        "url_mobile": "",
        "title": "Earthquake in Japan",
        "seendate": "20250510T120000Z",
        "socialimage": "",
        "domain": "example.com",
        "language": "English",
        "sourcecountry": "Japan",
    }
    article2 = {
        "url": "https://example.com/flood1",
        "url_mobile": "",
        "title": "Flooding in Thailand",
        "seendate": "20250511T090000Z",
        "socialimage": "",
        "domain": "example.org",
        "language": "English",
        "sourcecountry": "Thailand",
    }
    api_response = {"articles": [article1, article2]}

    transport = httpx.MockTransport(
        lambda req: httpx.Response(200, json=api_response)
    )

    with httpx.Client(transport=transport) as client:
        adapter = GDELTAdapter()
        result = adapter.fetch(client)

    assert len(result) == 2
    for record in result:
        assert record.source_name == "GDELT"
