from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    pass


class TestEnrichNewsItems:
    def test_enriches_title_body_author_sitename_when_fetch_succeeds(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from disaster_report import pipeline
        from disaster_report.models import FetchedArticle, NewsItem

        fetched = FetchedArticle(
            url="https://x.com/a",
            title="New Title",
            description="New description.",
            body="long body",
            published_date="2026-07-17",
            author="Jane Doe",
            sitename="X",
        )
        monkeypatch.setattr(pipeline, "fetch_article", lambda url: fetched)

        original = NewsItem(
            url="https://x.com/a",
            title="old",
            body="old body",
            published_date="2020-01-01",
            source="ddg",
            domain="x.com",
            image="",
        )
        result = pipeline._enrich_news_items([original])
        assert len(result) == 1
        assert result[0].title == "New Title"
        assert result[0].body == "New description."
        assert result[0].published_date == "2026-07-17"
        assert result[0].author == "Jane Doe"
        assert result[0].sitename == "X"

    def test_keeps_original_when_fetch_returns_none(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from disaster_report import pipeline
        from disaster_report.models import NewsItem

        monkeypatch.setattr(pipeline, "fetch_article", lambda url: None)

        original = NewsItem(
            url="https://x.com/a",
            title="orig title",
            body="orig body",
            published_date="2024-01-01",
            source="ddg",
            domain="x.com",
            image="",
        )
        result = pipeline._enrich_news_items([original])
        assert result == [original]

    def test_partial_enrichment_when_fetched_field_is_empty(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from disaster_report import pipeline
        from disaster_report.models import FetchedArticle, NewsItem

        fetched = FetchedArticle(
            url="https://x.com/a",
            title="",
            description="",
            body="",
            published_date="",
            author="Author Only",
            sitename="Site",
        )
        monkeypatch.setattr(pipeline, "fetch_article", lambda url: fetched)

        original = NewsItem(
            url="https://x.com/a",
            title="keep me",
            body="keep body",
            published_date="2024-01-01",
            source="ddg",
            domain="x.com",
            image="",
        )
        result = pipeline._enrich_news_items([original])[0]
        assert result.title == "keep me"
        assert result.body == "keep body"
        assert result.published_date == "2024-01-01"
        assert result.author == "Author Only"
        assert result.sitename == "Site"

    def test_empty_list_passes_through(self) -> None:
        from disaster_report import pipeline

        assert pipeline._enrich_news_items([]) == []
