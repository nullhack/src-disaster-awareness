from hypothesis import given, example, strategies as st

@example(failure_kind="network error")
@example(failure_kind="HTTP server error")
@example(failure_kind="unexpected exception")
@given(failure_kind=st.text())
def test_ddg_news_search_failure_returns_empty_list(failure_kind):
    ...

