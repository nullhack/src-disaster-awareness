import httpx

from disaster_surveillance_reporter.adapters.who import WHOAdapter


def test_source_name_is_always_who():
    article1 = {
        "Id": 1,
        "Title": "Ebola outbreak in DRC",
        "Overview": "...",
        "ItemDefaultUrl": "/emergencies/disease-outbreak-news/item/2025-DON123",
        "PublicationDate": "2026-05-10T00:00:00Z",
    }
    article2 = {
        "Id": 2,
        "Title": "Cholera in Haiti",
        "Overview": "...",
        "ItemDefaultUrl": "/emergencies/disease-outbreak-news/item/2025-DON789",
        "PublicationDate": "2026-05-11T00:00:00Z",
    }
    odata_response = {
        "@odata.context": (
            "https://wesalute.azurewebsites.net/api/"
            "$metadata#DiseaseOutbreakNews"
        ),
        "value": [article1, article2],
    }

    transport = httpx.MockTransport(
        lambda req: httpx.Response(200, json=odata_response)
    )

    with httpx.Client(transport=transport) as client:
        adapter = WHOAdapter()
        result = adapter.fetch(client)

    assert len(result) == 2
    for record in result:
        assert record.source_name == "WHO"
