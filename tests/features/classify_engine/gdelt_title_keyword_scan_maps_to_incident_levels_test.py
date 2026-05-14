import pytest

from hypothesis import given, example, strategies as st

@pytest.mark.skip(reason="not implemented")
@example(keyword="major", level=3)
@example(keyword="catastrophic", level=3)
@example(keyword="deadly", level=3)
@example(keyword="massive", level=3)
@example(keyword="devastating", level=4)
@example(keyword="hundreds dead", level=4)
@example(keyword="thousands displaced", level=4)
@example(keyword="PHEIC", level=4)
@given(keyword=st.text(), level=st.integers())
def test_gdelt_title_keyword_to_incident_level_mapping(keyword, level):
    ...

@pytest.mark.skip(reason="not implemented")
def test_gdelt_record_with_no_severity_keyword_defaults_to_level_2():
    ...

