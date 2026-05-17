import httpx

from disaster_surveillance_reporter.adapters.gdelt import GDELTAdapter


def test_gdelt_api_response_is_preserved():
    article = {
        "url": "https://example.com/quake-report",
        "url_mobile": "https://m.example.com/quake-report",
        "title": "Magnitude 7.2 earthquake strikes Indonesia",
        "seendate": "20250512T080000Z",
        "socialimage": "https://example.com/img.jpg",
        "domain": "example.com",
        "language": "English",
        "sourcecountry": "Indonesia",
    }
    api_response = {"articles": [article]}

    transport = httpx.MockTransport(
        lambda req: httpx.Response(200, json=api_response)
    )

    with httpx.Client(transport=transport) as client:
        adapter = GDELTAdapter()
        result = adapter.fetch(client)

    assert len(result) == 1
    raw = result[0].raw_fields
    assert raw["url"] == "https://example.com/quake-report"
    assert raw["url_mobile"] == "https://m.example.com/quake-report"
    assert raw["title"] == "Magnitude 7.2 earthquake strikes Indonesia"
    assert raw["seendate"] == "20250512T080000Z"
    assert raw["socialimage"] == "https://example.com/img.jpg"
    assert raw["domain"] == "example.com"
    assert raw["language"] == "English"
    assert raw["sourcecountry"] == "Indonesia"
    assert raw is result[0].raw_fields
