import httpx

from disaster_surveillance_reporter.adapters.gdelt import GDELTAdapter


def test_malformed_records_are_silently_skipped():
    valid_article = {
        "url": "https://example.com/article1",
        "url_mobile": "",
        "title": "Flooding devastates Bangladesh",
        "seendate": "20250510T120000Z",
        "socialimage": "",
        "domain": "example.com",
        "language": "English",
        "sourcecountry": "Bangladesh",
    }
    api_response = {
        "articles": [
            valid_article,
            None,
        ],
    }

    transport = httpx.MockTransport(
        lambda req: httpx.Response(200, json=api_response)
    )

    with httpx.Client(transport=transport) as client:
        adapter = GDELTAdapter()
        result = adapter.fetch(client)

    assert len(result) == 1
    assert result[0].raw_fields["title"] == "Flooding devastates Bangladesh"


def test_all_malformed_yields_empty_list():
    api_response = {
        "articles": [
            None,
            "not-a-dict",
            123,
            [],
        ],
    }

    transport = httpx.MockTransport(
        lambda req: httpx.Response(200, json=api_response)
    )

    with httpx.Client(transport=transport) as client:
        adapter = GDELTAdapter()
        result = adapter.fetch(client)

    assert result == []
