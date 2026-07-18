from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

if TYPE_CHECKING:
    from pathlib import Path

    from disaster_report.ai.base import SubmissionClassification
    from disaster_report.models import FetchedArticle


def _make_issue(
    number: int = 1,
    body: str = "Saw this: https://cnn.com/article",
    title: str = "Wildfire article",
    author: str = "alice",
) -> dict:
    return {
        "number": number,
        "title": title,
        "body": body,
        "author": {"login": author},
        "createdAt": "2026-07-17T08:00:00Z",
        "url": f"https://github.com/nullhack/src-disaster-awareness/issues/{number}",
    }


def _make_classification(
    is_disaster: bool = True,
    incident_type: str = "Wildfire",
    country_code: str = "US",
    country_name: str = "United States",
    summary: str = "Major wildfire burning.",
    event_date: str = "2026-07-17",
) -> "SubmissionClassification":
    from disaster_report.ai.base import SubmissionClassification

    return SubmissionClassification(
        is_disaster=is_disaster,
        incident_type=incident_type,
        country_code=country_code,
        country_name=country_name,
        summary=summary,
        event_date=event_date,
    )


def _make_fetched(
    url: str = "https://cnn.com/article",
    title: str = "Article title",
    description: str = "Article description.",
    author: str = "Jane",
    sitename: str = "CNN",
    published_date: str = "2026-07-17",
) -> "FetchedArticle":
    from disaster_report.models import FetchedArticle

    return FetchedArticle(
        url=url,
        title=title,
        description=description,
        body="",
        published_date=published_date,
        author=author,
        sitename=sitename,
    )


class TestExtractUrl:
    def test_extracts_first_http_url(self) -> None:
        from scripts.ingest_submissions import _extract_url

        assert _extract_url("See https://a.com/x and https://b.com/y") == "https://a.com/x"

    def test_returns_none_when_no_url(self) -> None:
        from scripts.ingest_submissions import _extract_url

        assert _extract_url("Just text, no link.") is None

    def test_strips_trailing_punctuation(self) -> None:
        from scripts.ingest_submissions import _extract_url

        assert _extract_url("Read https://x.com/article.") == "https://x.com/article"


class TestSourceId:
    def test_is_16_hex_chars(self) -> None:
        from scripts.ingest_submissions import _source_id

        sid = _source_id("https://example.com/x")
        assert len(sid) == 16
        int(sid, 16)

    def test_is_deterministic(self) -> None:
        from scripts.ingest_submissions import _source_id

        assert _source_id("https://x.com") == _source_id("https://x.com")


class TestProcessIssue:
    def test_rejects_when_body_has_no_url(
        self,
        tmp_path: "Path",
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from scripts import ingest_submissions as mod

        calls: list[tuple] = []
        monkeypatch.setattr(mod, "_reject", lambda n, r: calls.append(("reject", n, r)))
        monkeypatch.setattr(mod, "_remove_label", lambda *a, **k: None)
        monkeypatch.setattr(mod, "_add_label", lambda *a, **k: None)
        monkeypatch.setattr(mod, "_comment", lambda *a, **k: None)
        store = MagicMock()
        digester = MagicMock()
        issue = _make_issue(body="no url here")
        outcome = mod._process_issue(issue, store, digester, set())
        assert outcome == "rejected:no-url"
        assert calls and calls[0][0] == "reject"

    def test_reimports_existing_manual_report_without_fetching(
        self,
        tmp_path: "Path",
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from scripts import ingest_submissions as mod


        sid_seen: list[str] = []
        monkeypatch.setattr(mod, "_reject", lambda *a, **k: pytest.fail("should not reject"))
        monkeypatch.setattr(mod, "_remove_label", lambda *a, **k: None)
        monkeypatch.setattr(mod, "_add_label", lambda n, l: sid_seen.append(l))
        monkeypatch.setattr(mod, "_comment", lambda *a, **k: None)
        fetch_calls: list[str] = []
        monkeypatch.setattr(mod, "fetch_article", lambda url: fetch_calls.append(url) or MagicMock())
        store = MagicMock()
        digester = MagicMock()
        url = "https://cnn.com/article"
        existing_sid = mod._source_id(url)
        outcome = mod._process_issue(
            _make_issue(body=url), store, digester, {existing_sid}
        )
        assert outcome == "imported:existing"
        assert fetch_calls == []
        assert mod.IMPORTED_LABEL in sid_seen

    def test_rejects_when_fetch_returns_none(
        self,
        tmp_path: "Path",
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from scripts import ingest_submissions as mod

        rejected: list[tuple] = []
        monkeypatch.setattr(mod, "_reject", lambda n, r: rejected.append((n, r)))
        monkeypatch.setattr(mod, "fetch_article", lambda url: None)
        store = MagicMock()
        digester = MagicMock()
        outcome = mod._process_issue(_make_issue(), store, digester, set())
        assert outcome == "rejected:fetch-failed"
        assert rejected and "could not fetch" in rejected[0][1]

    def test_rejects_when_classifier_says_not_disaster(
        self,
        tmp_path: "Path",
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from scripts import ingest_submissions as mod

        rejected: list[tuple] = []
        monkeypatch.setattr(mod, "_reject", lambda n, r: rejected.append((n, r)))
        monkeypatch.setattr(mod, "fetch_article", lambda url: _make_fetched())
        store = MagicMock()
        digester = MagicMock()
        digester.classify_submission.return_value = _make_classification(is_disaster=False)
        outcome = mod._process_issue(_make_issue(), store, digester, set())
        assert outcome == "rejected:not-disaster"
        assert rejected

    def test_full_ingest_path_births_incident_and_links_news(
        self,
        tmp_path: "Path",
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from scripts import ingest_submissions as mod

        monkeypatch.setattr(mod, "_reject", lambda *a, **k: pytest.fail("should not reject"))
        monkeypatch.setattr(mod, "_remove_label", lambda *a, **k: None)
        monkeypatch.setattr(mod, "_add_label", lambda *a, **k: None)
        monkeypatch.setattr(mod, "_comment", lambda *a, **k: None)
        monkeypatch.setattr(mod, "fetch_article", lambda url: _make_fetched())
        store = MagicMock()
        store.read_source_report_keys.return_value = []
        store.read_incident_ids_for_report.return_value = []
        store.ingest_source_report.return_value = "rid-1"
        digester = MagicMock()
        digester.classify_submission.return_value = _make_classification()
        outcome = mod._process_issue(_make_issue(), store, digester, set())
        assert outcome == "imported:new"
        store.ingest_source_report.assert_called_once()
        store.ingest_report_places.assert_called_once()
        store.add_report_incident.assert_called_once()
        args, _ = store.add_report_incident.call_args
        assert args[0] == "rid-1"
        assert isinstance(args[1], str) and len(args[1]) == 32  # uuid4 hex
        store.ingest_news_item.assert_called_once()
        store.assign_news_to_incident.assert_called_once()
