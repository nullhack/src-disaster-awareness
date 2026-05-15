from unittest.mock import MagicMock, patch

from disaster_surveillance_reporter.adapters.news import NewsSearcher


def test_ddg_news_records_source_name_verified():
    mock_articles = [
        {"title": "Article 1", "url": "https://example.com/1"},
        {"title": "Article 2", "url": "https://example.com/2"},
    ]

    mock_ddgs = MagicMock()
    mock_ddgs.return_value.news.return_value = mock_articles

    with patch("disaster_surveillance_reporter.adapters.news.DDGS", mock_ddgs):
        adapter = NewsSearcher()
        result = adapter.search(
            "test query", region="asiapacific", timelimit="7d", max_results=5
        )

    assert len(result) == 2
    for record in result:
        assert record.source_name == "DDG-NEWS"
