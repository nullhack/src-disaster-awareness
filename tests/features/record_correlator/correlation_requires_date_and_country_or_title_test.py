import pytest

from hypothesis import given, example, strategies as st

@pytest.mark.skip(reason="not implemented")
@example(other_date="2026-05-14", other_country="Philippines", other_title="Quake hits Philippines", grouping="are grouped into one bundle")
@example(other_date="2026-05-14", other_country="Japan", other_title="Earthquake in Philippines", grouping="are grouped into one bundle")
@example(other_date="2026-05-14", other_country="Japan", other_title="Typhoon warning Japan", grouping="remain in separate bundles")
@example(other_date="2026-05-16", other_country="Philippines", other_title="Earthquake in Philippines", grouping="remain in separate bundles")
@given(other_date=st.text(), other_country=st.text(), other_title=st.text(), grouping=st.text())
def test_date_plus_country_or_title_determines_grouping(other_date, other_country, other_title, grouping):
    ...

@pytest.mark.skip(reason="not implemented")
def test_sole_criterion_correlates_records_alone():
    ...

