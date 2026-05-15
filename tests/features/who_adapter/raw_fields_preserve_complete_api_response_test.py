import httpx

from disaster_surveillance_reporter.adapters.who import WHOAdapter


def test_complete_api_response_is_preserved():
    article = {
        "Id": 1,
        "Title": "Dengue fever in Brazil",
        "Overview": "Brazil has reported an increase in dengue cases...",
        "ItemDefaultUrl": "/emergencies/disease-outbreak-news/item/2025-DON456",
        "PublicationDate": "2025-05-12T00:00:00Z",
        "Disease": "Dengue",
        "Country": "Brazil",
        "Region": "Americas",
    }
    odata_response = {
        "@odata.context": (
            "https://wesalute.azurewebsites.net/api/"
            "$metadata#DiseaseOutbreakNews"
        ),
        "value": [article],
    }

    transport = httpx.MockTransport(
        lambda req: httpx.Response(200, json=odata_response)
    )

    with httpx.Client(transport=transport) as client:
        adapter = WHOAdapter()
        result = adapter.fetch(client)

    assert len(result) == 1
    raw = result[0].raw_fields
    assert raw["Id"] == 1
    assert raw["Title"] == "Dengue fever in Brazil"
    assert raw["Overview"] == "Brazil has reported an increase in dengue cases..."
    assert raw["ItemDefaultUrl"] == (
        "/emergencies/disease-outbreak-news/item/2025-DON456"
    )
    assert raw["PublicationDate"] == "2025-05-12T00:00:00Z"
    assert raw["Disease"] == "Dengue"
    assert raw["Country"] == "Brazil"
    assert raw["Region"] == "Americas"
    assert raw is result[0].raw_fields
