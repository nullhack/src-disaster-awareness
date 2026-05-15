from unittest.mock import MagicMock, patch

from hypothesis import example, given, strategies as st

from disaster_surveillance_reporter.adapters.news import NewsSearcher


@example(failure_kind="network error")
@example(failure_kind="HTTP server error")
@example(failure_kind="unexpected exception")
@given(failure_kind=st.text())
def test_ddg_news_search_failure_returns_empty_list(failure_kind):
    _placeholder = "<failure_kind>"

    mock_ddgs = MagicMock()
    mock_ddgs.return_value.news.side_effect = Exception(failure_kind)

    with patch("disaster_surveillance_reporter.adapters.news.DDGS", mock_ddgs):
        adapter = NewsSearcher()
        result = adapter.search(
            "test query", region="asiapacific", timelimit="7d", max_results=5
        )

    assert result == []
