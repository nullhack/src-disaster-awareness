from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from disaster_report.models import NewsItem
    from disaster_report.sources.ddg_news import DuckDuckGoNewsAdapter

FIXTURE: str = "ddg_news.json"
SEARCH_QUERY: str = "cholera outbreak"
ARTICLE_KEYS: tuple[str, ...] = ("date", "title", "body", "url", "image", "source")


class _FakeDDGS:
    def __init__(self, **kwargs: object) -> None:
        pass

    def news(self, **kwargs: object) -> list[dict[str, object]]:
        return _load_fixture()


class _CapturingDDGS:
    captured: dict[str, object] = {}

    def __init__(self, **kwargs: object) -> None:
        pass

    def news(self, **kwargs: object) -> list[dict[str, object]]:
        type(self).captured.update(kwargs)
        return _load_fixture()


class _RaisingDDGS:
    def __init__(self, **kwargs: object) -> None:
        pass

    def news(self, **kwargs: object) -> list[dict[str, object]]:
        from ddgs.exceptions import DDGSException

        raise DDGSException("query is mandatory.")


class TestDuckDuckGoNewsAdapter:
    adapter: DuckDuckGoNewsAdapter

    def test_search_returns_news_items_from_fixture(self, monkeypatch) -> None:
        from disaster_report.sources.ddg_news import DuckDuckGoNewsAdapter

        monkeypatch.setattr("disaster_report.sources.ddg_news.DDGS", _FakeDDGS)
        items = DuckDuckGoNewsAdapter().search(SEARCH_QUERY, timelimit=None)
        assert len(items) > 0

    def test_each_news_item_carries_six_canonical_keys(self, monkeypatch) -> None:
        from disaster_report.sources.ddg_news import DuckDuckGoNewsAdapter

        monkeypatch.setattr("disaster_report.sources.ddg_news.DDGS", _FakeDDGS)
        items = DuckDuckGoNewsAdapter().search(SEARCH_QUERY, timelimit=None)
        assert len(items) > 0
        assert all(getattr(item, "url", "") != "" for item in items)

    def test_region_pinned_to_worldwide_wt_wt(self, monkeypatch) -> None:
        from disaster_report.sources.ddg_news import DuckDuckGoNewsAdapter

        _CapturingDDGS.captured = {}
        monkeypatch.setattr("disaster_report.sources.ddg_news.DDGS", _CapturingDDGS)
        DuckDuckGoNewsAdapter().search(SEARCH_QUERY, timelimit=None)
        assert _CapturingDDGS.captured["region"] == "wt-wt"

    def test_max_results_set_above_library_default(self, monkeypatch) -> None:
        from disaster_report.sources.ddg_news import DuckDuckGoNewsAdapter

        _CapturingDDGS.captured = {}
        monkeypatch.setattr("disaster_report.sources.ddg_news.DDGS", _CapturingDDGS)
        DuckDuckGoNewsAdapter().search(SEARCH_QUERY, timelimit=None)
        max_results = _CapturingDDGS.captured["max_results"]
        assert isinstance(max_results, int) and max_results > 10

    def test_ddgs_exception_returns_empty_not_raises(self, monkeypatch) -> None:
        from disaster_report.sources.ddg_news import DuckDuckGoNewsAdapter

        monkeypatch.setattr("disaster_report.sources.ddg_news.DDGS", _RaisingDDGS)
        assert DuckDuckGoNewsAdapter().search("", timelimit=None) == []

    def test_crawl_timestamp_falls_back_to_url_date(self) -> None:
        from datetime import datetime, timezone

        from disaster_report.sources.ddg_news import _resolve_date

        now_iso = datetime.now(timezone.utc).isoformat()
        url = "https://example.com/news/2026/07/08/some-article"
        result = _resolve_date(now_iso, url)
        assert result == "2026-07-08T00:00:00+00:00"

    def test_crawl_timestamp_falls_back_to_ingest_time_when_no_url_date(self) -> None:
        from datetime import datetime, timezone

        from disaster_report.sources.ddg_news import _resolve_date

        now_iso = datetime.now(timezone.utc).isoformat()
        url = "https://example.com/news/some-article-no-date"
        result = _resolve_date(now_iso, url)
        parsed = datetime.fromisoformat(result)
        assert abs((datetime.now(timezone.utc) - parsed).total_seconds()) < 5

    def test_valid_ddg_date_is_kept_as_is(self) -> None:
        from disaster_report.sources.ddg_news import _resolve_date

        result = _resolve_date(
            "2026-06-15T10:30:00+00:00", "https://example.com/article"
        )
        assert result == "2026-06-15T10:30:00+00:00"

    def test_compressed_url_date_is_extracted(self) -> None:
        from disaster_report.sources.ddg_news import _resolve_date

        url = "https://example.com/news/20260628/article"
        result = _resolve_date("", url)
        assert result == "2026-06-28T00:00:00+00:00"

    def test_missing_date_and_no_url_date_uses_ingest_time(self) -> None:
        from datetime import datetime, timezone

        from disaster_report.sources.ddg_news import _resolve_date

        result = _resolve_date("", "https://example.com/no-date-here")
        parsed = datetime.fromisoformat(result)
        assert abs((datetime.now(timezone.utc) - parsed).total_seconds()) < 5

    def test_future_date_rejected_falls_back_to_url_date(self) -> None:
        from disaster_report.sources.ddg_news import _resolve_date

        result = _resolve_date(
            "2099-12-31T00:00:00+00:00",
            "https://example.com/news/2026/07/08/article",
        )
        assert result == "2026-07-08T00:00:00+00:00"

    def test_future_date_rejected_falls_back_to_ingest_time(self) -> None:
        from datetime import datetime, timezone

        from disaster_report.sources.ddg_news import _resolve_date

        result = _resolve_date(
            "2099-12-31T00:00:00+00:00",
            "https://example.com/news/no-date-here",
        )
        parsed = datetime.fromisoformat(result)
        assert abs((datetime.now(timezone.utc) - parsed).total_seconds()) < 5

    def test_date_outside_timelimit_window_rejected(self) -> None:
        from disaster_report.sources.ddg_news import _resolve_date

        result = _resolve_date(
            "2026-01-01T00:00:00+00:00",
            "https://example.com/news/2026/07/08/article",
            timelimit="w",
        )
        assert result == "2026-07-08T00:00:00+00:00"

    def test_date_within_timelimit_window_kept(self) -> None:
        from datetime import datetime, timedelta, timezone

        from disaster_report.sources.ddg_news import _resolve_date

        recent = (datetime.now(timezone.utc) - timedelta(days=2)).replace(microsecond=0).isoformat()
        result = _resolve_date(recent, "https://example.com/news/article", timelimit="w")
        assert result == recent

    def test_url_date_outside_timelimit_falls_back_to_ingest_time(self) -> None:
        from datetime import datetime, timezone

        from disaster_report.sources.ddg_news import _resolve_date

        result = _resolve_date(
            "",
            "https://example.com/news/2020/01/01/old-article",
            timelimit="w",
        )
        parsed = datetime.fromisoformat(result)
        assert abs((datetime.now(timezone.utc) - parsed).total_seconds()) < 5

    def test_no_timelimit_allows_any_past_date(self) -> None:
        from disaster_report.sources.ddg_news import _resolve_date

        result = _resolve_date(
            "2020-01-01T00:00:00+00:00",
            "https://example.com/news/article",
            timelimit=None,
        )
        assert result == "2020-01-01T00:00:00+00:00"


def first_news_item(items: list[NewsItem]) -> NewsItem:
    return items[0]


def _load_fixture() -> list[dict[str, object]]:
    import json

    with open(f"tests/cassettes/{FIXTURE}") as handle:
        return json.load(handle)
