from __future__ import annotations

import json
from datetime import datetime

import pytest

from disaster_report.sources.base import RawArticle
from disaster_report.sources.ddg_news import DdgNewsAdapter


def test_ddg_news_adapter_parses_captured_fixture(monkeypatch, load_fixture):
    items = json.loads(load_fixture("ddg_news.json"))
    captured: list[dict] = []

    class FakeDDGS:
        def __init__(self, *args, **kwargs):
            pass

        def news(self, **kwargs):
            captured.append(kwargs)
            return items

    monkeypatch.setattr("disaster_report.sources.ddg_news.DDGS", FakeDDGS)

    adapter = DdgNewsAdapter(query="earthquake", max_results=10)
    articles = adapter.fetch()

    assert len(articles) == len(items)
    assert all(isinstance(a, RawArticle) for a in articles)
    assert all(a.source_name == "DuckDuckGo News" for a in articles)
    assert all(a.headline and a.url and a.outlet for a in articles)

    assert articles[0].headline == items[0]["title"]
    assert articles[0].url == items[0]["url"]
    assert articles[0].outlet == items[0]["source"]
    assert articles[0].body == items[0]["body"]
    datetime.fromisoformat(articles[0].published_date)

    assert captured[0]["query"] == "earthquake"
    assert captured[0]["max_results"] == 10


def test_ddg_news_search_passes_query_and_timelimit_to_sdk(monkeypatch, load_fixture):
    items = json.loads(load_fixture("ddg_news.json"))
    captured: dict = {}

    class FakeDDGS:
        def __init__(self, *args, **kwargs):
            pass

        def news(self, **kwargs):
            captured.update(kwargs)
            return items

    monkeypatch.setattr("disaster_report.sources.ddg_news.DDGS", FakeDDGS)

    adapter = DdgNewsAdapter()
    articles = adapter.search(query="Sarangani earthquake", timelimit="d")

    assert len(articles) == len(items)
    assert all(isinstance(a, RawArticle) for a in articles)
    assert captured["query"] == "Sarangani earthquake"
    assert captured["timelimit"] == "d"


def test_ddg_news_search_returns_empty_when_ddgs_raises_no_results(monkeypatch):
    from ddgs.exceptions import DDGSException

    calls = {"n": 0}

    class RaisingDDGS:
        def __init__(self, *args, **kwargs):
            pass

        def news(self, **kwargs):
            calls["n"] += 1
            raise DDGSException("No results found.")

    monkeypatch.setattr("disaster_report.sources.ddg_news.DDGS", RaisingDDGS)
    monkeypatch.setattr("disaster_report.sources.ddg_news.time.sleep", lambda _s: None)

    adapter = DdgNewsAdapter()

    assert adapter.search("unlikely-query-with-zero-results") == []
    assert adapter.fetch() == []
    # retries are exhausted, not abandoned on the first failure
    assert calls["n"] >= 2


def test_ddg_news_search_retries_empty_then_returns_results(monkeypatch, load_fixture):
    """A transient empty result (the yahoo IndexError burst pattern) is retried
    and the call eventually returns the articles from a later attempt."""
    items = json.loads(load_fixture("ddg_news.json"))

    attempts = {"n": 0}

    class FlakyDDGS:
        def __init__(self, *args, **kwargs):
            pass

        def news(self, **kwargs):
            attempts["n"] += 1
            return [] if attempts["n"] == 1 else items

    monkeypatch.setattr("disaster_report.sources.ddg_news.DDGS", FlakyDDGS)
    monkeypatch.setattr("disaster_report.sources.ddg_news.time.sleep", lambda _s: None)

    adapter = DdgNewsAdapter()
    articles = adapter.search("Nipah India outbreak 2026", timelimit="m")

    assert articles  # recovered
    assert attempts["n"] == 2
