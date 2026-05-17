from disaster_surveillance_reporter.adapters.news import NewsSearcher


def test_ddg_news_worst_case_query_default_template():
    query = NewsSearcher._build_query()
    assert query == "disaster incident disaster emergency latest news"


def test_ddg_news_partial_info_query_includes_fallbacks():
    query = NewsSearcher._build_query(title="Earthquake detected")
    assert query == "Earthquake detected disaster emergency latest news"
