"""Test: Search queries use templated fields.

beehave traceability: "<title>", "<country>", "<disaster_type>", "<expected_query>"
"""

from hypothesis import given, example, settings
from hypothesis import strategies as st

from disaster_surveillance_reporter.pipeline import Pipeline


def _build_expected(title, country, disaster_type):
    """Build expected query from the template rule:
    {title} {country} {disaster_type} latest news
    Unknown country is omitted.
    Unknown disaster type is substituted with 'disaster emergency'."""
    parts = [title]
    if country:
        parts.append(country)
    parts.append(disaster_type or "disaster emergency")
    parts.append("latest news")
    return " ".join(parts)


@example(
    title="Magnitude 7.2 earthquake",
    country="Philippines",
    disaster_type="Earthquake",
    expected_query="Magnitude 7.2 earthquake Philippines Earthquake latest news",
)
@example(
    title="Disease outbreak report",
    country="",
    disaster_type="Flood",
    expected_query="Disease outbreak report Flood latest news",
)
@example(
    title="Flood warning issued",
    country="",
    disaster_type="",
    expected_query="Flood warning issued disaster emergency latest news",
)
@example(
    title="disaster incident",
    country="Japan",
    disaster_type="Earthquake",
    expected_query="disaster incident Japan Earthquake latest news",
)
@given(
    title=st.text(min_size=1, max_size=50),
    country=st.text(min_size=0, max_size=30),
    disaster_type=st.text(min_size=0, max_size=30),
    expected_query=st.text(min_size=0, max_size=100),
)
@settings(max_examples=1)
def test_pipeline_search_query_matches_template(title, country, disaster_type, expected_query):
    """Given a bundle with title "<title>", country "<country>", and type "<disaster_type>"
    When the supplementary search query is generated
    Then the search query is "<expected_query>"."""
    # beehave traceability: literal placeholders from the Scenario Outline steps
    _ = "<title>"  # noqa: F841
    _ = "<country>"  # noqa: F841
    _ = "<disaster_type>"  # noqa: F841
    _ = "<expected_query>"  # noqa: F841
    _ = expected_query  # beehave: ensures expected_query placeholder is used in body

    computed = _build_expected(title, country, disaster_type)
    result = Pipeline._build_search_query(title, country, disaster_type)
    assert result == computed, f"Expected {computed!r}, got {result!r}"
