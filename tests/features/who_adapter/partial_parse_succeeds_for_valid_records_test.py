import httpx

from disaster_surveillance_reporter.adapters.who import WHOAdapter


def test_malformed_records_are_silently_skipped():
    valid_article = {
        "Id": 1,
        "Title": "Ebola outbreak in DRC",
        "Overview": "An outbreak of Ebola virus disease...",
        "ItemDefaultUrl": "/emergencies/disease-outbreak-news/item/2025-DON123",
        "PublicationDate": "2026-05-10T00:00:00Z",
    }
    odata_response = {
        "@odata.context": (
            "https://wesalute.azurewebsites.net/api/"
            "$metadata#DiseaseOutbreakNews"
        ),
        "value": [
            valid_article,
            None,
        ],
    }

    transport = httpx.MockTransport(
        lambda req: httpx.Response(200, json=odata_response)
    )

    with httpx.Client(transport=transport) as client:
        adapter = WHOAdapter()
        result = adapter.fetch(client)

    assert len(result) == 1
    assert result[0].raw_fields["Title"] == "Ebola outbreak in DRC"


def test_all_malformed_yields_empty_list():
    odata_response = {
        "@odata.context": (
            "https://wesalute.azurewebsites.net/api/"
            "$metadata#DiseaseOutbreakNews"
        ),
        "value": [
            None,
            "not-a-dict",
            123,
            [],
        ],
    }

    transport = httpx.MockTransport(
        lambda req: httpx.Response(200, json=odata_response)
    )

    with httpx.Client(transport=transport) as client:
        adapter = WHOAdapter()
        result = adapter.fetch(client)

    assert result == []
