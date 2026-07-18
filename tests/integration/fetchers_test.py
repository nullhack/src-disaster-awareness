from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

if TYPE_CHECKING:

    pass


CNN_HTML = """<!doctype html><html><head>
<title>People are making wildfire bets on prediction markets</title>
<meta name="author" content="Laura Paddison">
<meta name="description" content="As catastrophic wildfires raged, people placed bets on how far they would spread.">
<meta property="og:site_name" content="CNN">
<meta property="article:published_time" content="2026-07-17T10:00:00Z">
</head><body><p>Wildfire prediction markets are growing fast.</p></body></html>"""


class TestFetchArticle:
    def test_returns_fetched_article_on_success(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from disaster_report import fetchers

        fake_resp = MagicMock()
        fake_resp.text = CNN_HTML
        fake_resp.raise_for_status = MagicMock()
        monkeypatch.setattr("disaster_report.fetchers.httpx.get", lambda *a, **kw: fake_resp)

        result = fetchers.fetch_article("https://example.com/wildfire-bets")
        assert result is not None
        assert result.url == "https://example.com/wildfire-bets"
        assert result.author == "Laura Paddison"
        assert result.sitename == "CNN"
        assert result.published_date.startswith("2026-07-17")
        assert "wildfire" in result.description.lower() or result.title

    def test_returns_none_on_http_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import httpx

        from disaster_report import fetchers

        def raise_err(*args: object, **kwargs: object) -> object:
            raise httpx.ConnectError("connection refused")

        monkeypatch.setattr("disaster_report.fetchers.httpx.get", raise_err)
        assert fetchers.fetch_article("https://no.example.com/x") is None

    def test_returns_none_on_empty_body(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from disaster_report import fetchers

        fake_resp = MagicMock()
        fake_resp.text = ""
        fake_resp.raise_for_status = MagicMock()
        monkeypatch.setattr("disaster_report.fetchers.httpx.get", lambda *a, **kw: fake_resp)
        assert fetchers.fetch_article("https://example.com/empty") is None

    def test_default_timeout_is_10_seconds(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from disaster_report import fetchers

        captured: dict[str, object] = {}

        def spy(url: str, timeout: float = 5.0, **kw: object) -> object:
            captured["timeout"] = timeout
            fake = MagicMock()
            fake.text = CNN_HTML
            fake.raise_for_status = MagicMock()
            return fake

        monkeypatch.setattr("disaster_report.fetchers.httpx.get", spy)
        fetchers.fetch_article("https://example.com/x")
        assert captured["timeout"] == 10.0
