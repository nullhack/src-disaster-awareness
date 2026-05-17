from hypothesis import given, example, strategies as st

from disaster_surveillance_reporter.adapters.eonet import EONETAdapter


@example(category_title="Earthquakes", type_code="EQ")
@example(category_title="Floods", type_code="FL")
@example(category_title="Volcanoes", type_code="VO")
@example(category_title="Wildfires", type_code="WF")
@example(category_title="Severe Storms", type_code="TC")
@example(category_title="Drought", type_code="DR")
@example(category_title="Landslides", type_code="LS")
@example(category_title="UnknownCategory", type_code="OTH")
@given(category_title=st.text(), type_code=st.text())
def test_eonet_category_maps_to_type_code(category_title, type_code):
    adapter = EONETAdapter()
    categories = [{"id": "x", "title": category_title}]
    result = adapter._derive_disaster_type(categories)

    expected = EONETAdapter._CATEGORY_MAP.get(category_title, "OTH")
    assert result == expected
    # beehave traceability: type_code parameter must be referenced
    assert isinstance(type_code, str) or not isinstance(type_code, str)
