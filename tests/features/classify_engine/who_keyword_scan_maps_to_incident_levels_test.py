import pytest

from hypothesis import given, example, strategies as st

@pytest.mark.skip(reason="not implemented")
@example(keyword="pandemic", level=4)
@example(keyword="PHEIC", level=4)
@example(keyword="epidemic", level=3)
@example(keyword="widespread", level=3)
@example(keyword="cluster", level=2)
@example(keyword="cases reported", level=2)
@example(keyword="isolated case", level=1)
@given(keyword=st.text(), level=st.integers())
def test_who_keyword_to_incident_level_mapping(keyword, level):
    ...

@pytest.mark.skip(reason="not implemented")
def test_who_record_with_no_level_keyword_defaults_to_level_2():
    ...

