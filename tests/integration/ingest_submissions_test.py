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


class TestParseSubmissionHints:
    def test_parses_category_and_country_hints(self) -> None:
        from scripts.ingest_submissions import _parse_submission_hints

        body = (
            "### Article URL\n\nhttps://x.com/a\n\n"
            "### Category hint (optional)\n\n🔥 Wildfire\n\n"
            "### Country (optional)\n\n🇸🇬 SG - Singapore\n"
        )
        hints = _parse_submission_hints(body)
        assert hints.incident_type == "Wildfire"
        assert hints.country_code == "SG"

    def test_treats_none_and_default_category_as_empty(self) -> None:
        from scripts.ingest_submissions import _parse_submission_hints

        body = (
            "### Category hint (optional)\n\n"
            "🤖 Let the AI classify (default)\n\n"
            "### Country (optional)\n\n_No response_\n"
        )
        hints = _parse_submission_hints(body)
        assert hints.incident_type == ""
        assert hints.country_code == ""


class TestProcessIssue:
    def _patch_common(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from scripts import ingest_submissions as mod

        monkeypatch.setattr(mod, "_reject", lambda *a, **k: pytest.fail("should not reject"))
        monkeypatch.setattr(mod, "_review", lambda *a, **k: pytest.fail("should not review"))
        monkeypatch.setattr(mod, "_remove_label", lambda *a, **k: None)
        monkeypatch.setattr(mod, "_add_label", lambda *a, **k: None)
        monkeypatch.setattr(mod, "_comment", lambda *a, **k: None)

    def _make_store(self) -> MagicMock:
        store = MagicMock()
        store.read_source_report_keys.return_value = []
        store.read_incident_ids_for_report.return_value = []
        store.find_news_id_by_url.return_value = None
        store.ingest_source_report.return_value = "rid-1"
        return store

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

    def test_reviews_when_fetch_returns_none(
        self,
        tmp_path: "Path",
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from scripts import ingest_submissions as mod

        reviewed: list[tuple] = []
        monkeypatch.setattr(mod, "_reject", lambda *a, **k: pytest.fail("should not reject"))
        monkeypatch.setattr(mod, "_review", lambda n, r: reviewed.append((n, r)))
        monkeypatch.setattr(mod, "fetch_article", lambda url: None)
        store = MagicMock()
        store.find_news_id_by_url.return_value = None
        digester = MagicMock()
        outcome = mod._process_issue(_make_issue(), store, digester, set())
        assert outcome == "review:fetch-failed"
        assert reviewed and "could not fetch" in reviewed[0][1]

    def test_reviews_when_classifier_says_not_disaster(
        self,
        tmp_path: "Path",
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from scripts import ingest_submissions as mod

        reviewed: list[tuple] = []
        monkeypatch.setattr(mod, "_reject", lambda *a, **k: pytest.fail("should not reject"))
        monkeypatch.setattr(mod, "_review", lambda n, r: reviewed.append((n, r)))
        monkeypatch.setattr(mod, "fetch_article", lambda url: _make_fetched())
        store = MagicMock()
        store.find_news_id_by_url.return_value = None
        digester = MagicMock()
        digester.classify_submission.return_value = _make_classification(is_disaster=False)
        outcome = mod._process_issue(_make_issue(), store, digester, set())
        assert outcome == "review:not-disaster"
        assert reviewed

    def test_reviews_when_classifier_returns_no_country(
        self,
        tmp_path: "Path",
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from scripts import ingest_submissions as mod

        reviewed: list[tuple] = []
        monkeypatch.setattr(mod, "_reject", lambda *a, **k: pytest.fail("should not reject"))
        monkeypatch.setattr(mod, "_review", lambda n, r: reviewed.append((n, r)))
        monkeypatch.setattr(mod, "fetch_article", lambda url: _make_fetched())
        store = MagicMock()
        store.find_news_id_by_url.return_value = None
        digester = MagicMock()
        digester.classify_submission.return_value = _make_classification(country_code="")
        outcome = mod._process_issue(_make_issue(), store, digester, set())
        assert outcome == "review:no-country"
        assert reviewed and "country" in reviewed[0][1]

    def test_full_ingest_path_births_incident_and_links_news(
        self,
        tmp_path: "Path",
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from scripts import ingest_submissions as mod

        self._patch_common(monkeypatch)
        monkeypatch.setattr(mod, "fetch_article", lambda url: _make_fetched())
        store = self._make_store()
        store.read_incident_for_news.return_value = None
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

    def test_approved_submission_bypasses_not_disaster_classifier(
        self,
        tmp_path: "Path",
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from scripts import ingest_submissions as mod

        self._patch_common(monkeypatch)
        removed: list[str] = []
        monkeypatch.setattr(mod, "_remove_label", lambda n, label: removed.append(label))
        monkeypatch.setattr(mod, "fetch_article", lambda url: _make_fetched())
        store = self._make_store()
        store.read_incident_for_news.return_value = None
        digester = MagicMock()
        digester.classify_submission.return_value = _make_classification(is_disaster=False)
        outcome = mod._process_issue(
            _make_issue(), store, digester, set(), approved=True
        )
        assert outcome == "imported:new"
        report = store.ingest_source_report.call_args[0][0]
        assert report.raw_fields["approved_override"] is True
        assert mod.APPROVED_LABEL in removed

    def test_approved_submission_without_country_returns_to_review(
        self,
        tmp_path: "Path",
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from scripts import ingest_submissions as mod

        reviewed: list[tuple] = []
        monkeypatch.setattr(mod, "_reject", lambda *a, **k: pytest.fail("should not reject"))
        monkeypatch.setattr(mod, "_review", lambda n, r: reviewed.append((n, r)))
        monkeypatch.setattr(mod, "fetch_article", lambda url: _make_fetched())
        store = MagicMock()
        store.find_news_id_by_url.return_value = None
        digester = MagicMock()
        digester.classify_submission.return_value = _make_classification(country_code="")
        outcome = mod._process_issue(
            _make_issue(), store, digester, set(), approved=True
        )
        assert outcome == "review:no-country"
        assert reviewed and "country" in reviewed[0][1]

    def test_country_hint_fills_missing_classifier_country(
        self,
        tmp_path: "Path",
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from scripts import ingest_submissions as mod

        self._patch_common(monkeypatch)
        monkeypatch.setattr(mod, "fetch_article", lambda url: _make_fetched())
        store = self._make_store()
        store.read_incident_for_news.return_value = None
        digester = MagicMock()
        digester.classify_submission.return_value = _make_classification(country_code="")
        body = (
            "### Article URL\n\nhttps://cnn.com/article\n\n"
            "### Country (optional)\n\n🇸🇬 SG - Singapore\n"
        )
        outcome = mod._process_issue(_make_issue(body=body), store, digester, set())
        assert outcome == "imported:new"
        report = store.ingest_source_report.call_args[0][0]
        assert report.places[0].country_code == "SG"
        assert report.raw_fields["form_country_hint"] == "SG"

    def test_category_hint_fills_missing_classifier_type(
        self,
        tmp_path: "Path",
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from scripts import ingest_submissions as mod

        self._patch_common(monkeypatch)
        monkeypatch.setattr(mod, "fetch_article", lambda url: _make_fetched())
        store = self._make_store()
        store.read_incident_for_news.return_value = None
        digester = MagicMock()
        digester.classify_submission.return_value = _make_classification(
            incident_type=""
        )
        body = (
            "### Article URL\n\nhttps://cnn.com/article\n\n"
            "### Category hint (optional)\n\n🔥 Wildfire\n"
        )
        outcome = mod._process_issue(_make_issue(body=body), store, digester, set())
        assert outcome == "imported:new"
        report = store.ingest_source_report.call_args[0][0]
        assert report.incident_type == "Wildfire"

    def test_review_keeps_issue_open_and_explains_labels(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from scripts import ingest_submissions as mod

        labels: list[str] = []
        comments: list[str] = []
        monkeypatch.setattr(mod, "_remove_label", lambda n, label: None)
        monkeypatch.setattr(mod, "_add_label", lambda n, label: labels.append(label))
        monkeypatch.setattr(mod, "_comment", lambda n, body: comments.append(body))
        monkeypatch.setattr(mod, "_close", lambda *a, **k: pytest.fail("should not close"))
        mod._review(7, "DSPy classifier says this is not a disaster event.")
        assert mod.REVIEW_LABEL in labels
        assert comments and "submission-approved" in comments[0]

    def test_short_circuits_when_url_already_on_existing_incident(
        self,
        tmp_path: "Path",
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from scripts import ingest_submissions as mod

        comments: list[str] = []
        monkeypatch.setattr(mod, "_reject", lambda *a, **k: pytest.fail("should not reject"))
        monkeypatch.setattr(mod, "_remove_label", lambda *a, **k: None)
        monkeypatch.setattr(mod, "_add_label", lambda *a, **k: None)
        monkeypatch.setattr(mod, "_comment", lambda n, body: comments.append(body))
        fetch_calls: list[str] = []
        monkeypatch.setattr(mod, "fetch_article", lambda url: fetch_calls.append(url))
        store = MagicMock()
        store.find_news_id_by_url.return_value = "nuuid-existing"
        store.read_incident_for_news.return_value = "incident-abcdef1234"
        digester = MagicMock()
        outcome = mod._process_issue(_make_issue(), store, digester, set())
        assert outcome == "imported:existing-news"
        assert fetch_calls == []
        digester.classify_submission.assert_not_called()
        store.ingest_source_report.assert_not_called()
        assert any("incident `incident`" in c for c in comments)

    def test_short_circuits_when_url_in_staging(
        self,
        tmp_path: "Path",
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from scripts import ingest_submissions as mod

        comments: list[str] = []
        monkeypatch.setattr(mod, "_reject", lambda *a, **k: pytest.fail("should not reject"))
        monkeypatch.setattr(mod, "_remove_label", lambda *a, **k: None)
        monkeypatch.setattr(mod, "_add_label", lambda *a, **k: None)
        monkeypatch.setattr(mod, "_comment", lambda n, body: comments.append(body))
        monkeypatch.setattr(mod, "fetch_article", lambda url: pytest.fail("should not fetch"))
        store = MagicMock()
        store.find_news_id_by_url.return_value = "nuuid-staging"
        store.read_incident_for_news.return_value = None
        digester = MagicMock()
        outcome = mod._process_issue(_make_issue(), store, digester, set())
        assert outcome == "imported:existing-news"
        store.ingest_source_report.assert_not_called()
        assert any("pending news" in c for c in comments)

    def test_news_not_stolen_when_already_on_different_incident(
        self,
        tmp_path: "Path",
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from scripts import ingest_submissions as mod

        self._patch_common(monkeypatch)
        monkeypatch.setattr(mod, "fetch_article", lambda url: _make_fetched())
        store = self._make_store()
        store.read_incident_for_news.return_value = "incident-original"
        digester = MagicMock()
        digester.classify_submission.return_value = _make_classification()
        outcome = mod._process_issue(_make_issue(), store, digester, set())
        assert outcome == "imported:new"
        store.ingest_news_item.assert_called_once()
        store.assign_news_to_incident.assert_not_called()
