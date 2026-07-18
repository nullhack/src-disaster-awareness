from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from disaster_report.ai.base import FilterResult
    from disaster_report.models import IncidentLog, NewsItem

MODEL: str = "openrouter/deepseek/deepseek-v4-flash"
INVALID_MODEL: str = "this-model-does-not-exist-404"


class TestOpenRouterDigester:
    def test_filter_returns_result_from_canned_prediction(
        self, monkeypatch: Any
    ) -> None:
        from disaster_report.ai.base import FilterResult
        from disaster_report.ai.openrouter import OpenRouterDigester

        _stub_filter_cot(monkeypatch, kept_urls={"https://news.example/a"})
        digester = OpenRouterDigester(model=MODEL, api_key="test-key")
        result = digester.filter(
            build_candidate_news(),
            incident_type="Earthquake",
            incident_name="M 5.0 - Reykjanes Ridge",
            incident_places=[],
            incident_date="2026-07-04",
        )
        assert isinstance(result, FilterResult)

    def test_filter_takes_candidate_news_and_incident_context(self) -> None:
        import inspect

        from disaster_report.ai.openrouter import OpenRouterDigester

        signature = inspect.signature(OpenRouterDigester.filter)
        params = set(signature.parameters)
        assert "candidate_news" in params
        assert "incident_type" in params
        assert "incident_name" in params
        assert "incident_places" in params
        assert "incident_date" in params

    def test_filter_takes_no_prior_summaries(self) -> None:
        import inspect

        from disaster_report.ai.openrouter import OpenRouterDigester

        signature = inspect.signature(OpenRouterDigester.filter)
        assert "prior_summaries" not in signature.parameters
        assert "prior_timeline" not in signature.parameters

    def test_filter_result_carries_relevant_subset_of_news(
        self, monkeypatch: Any
    ) -> None:
        from disaster_report.ai.openrouter import OpenRouterDigester

        _stub_filter_cot(monkeypatch, kept_urls={"https://news.example/a"})
        digester = OpenRouterDigester(model=MODEL, api_key="test-key")
        result = digester.filter(
            build_candidate_news(),
            incident_type="Earthquake",
            incident_name="M 5.0 - Reykjanes Ridge",
            incident_places=[],
            incident_date="2026-07-04",
        )
        assert isinstance(result.selected_news, list)

    def test_filter_result_carries_per_item_relevance_score(
        self, monkeypatch: Any
    ) -> None:
        from disaster_report.ai.openrouter import OpenRouterDigester

        _stub_filter_cot(monkeypatch, kept_urls={"https://news.example/a"})
        digester = OpenRouterDigester(model=MODEL, api_key="test-key")
        result = digester.filter(
            build_candidate_news(),
            incident_type="Earthquake",
            incident_name="M 5.0 - Reykjanes Ridge",
            incident_places=[],
            incident_date="2026-07-04",
        )
        assert isinstance(result.relevance_scores, dict)

    def test_filter_result_has_no_summary(self, monkeypatch: Any) -> None:
        from disaster_report.ai.openrouter import OpenRouterDigester

        _stub_filter_cot(monkeypatch, kept_urls={"https://news.example/a"})
        digester = OpenRouterDigester(model=MODEL, api_key="test-key")
        result = digester.filter(
            build_candidate_news(),
            incident_type="Earthquake",
            incident_name="M 5.0 - Reykjanes Ridge",
            incident_places=[],
            incident_date="2026-07-04",
        )
        assert not hasattr(result, "summary")

    def test_filter_filters_non_relevant_news(self, monkeypatch: Any) -> None:
        from disaster_report.ai.openrouter import OpenRouterDigester

        _stub_filter_cot(monkeypatch, kept_urls=set())
        digester = OpenRouterDigester(model=MODEL, api_key="test-key")
        result = digester.filter(
            build_candidate_news(),
            incident_type="Earthquake",
            incident_name="M 5.0 - Reykjanes Ridge",
            incident_places=[],
            incident_date="2026-07-04",
        )
        assert len(result.selected_news) == 0
        for item in build_candidate_news():
            assert result.relevance_scores.get(item.url) == 0.0

    def test_filter_keeps_relevant_news_with_score_one(self, monkeypatch: Any) -> None:
        from disaster_report.ai.openrouter import OpenRouterDigester

        _stub_filter_cot(monkeypatch, kept_urls={"https://news.example/a"})
        digester = OpenRouterDigester(model=MODEL, api_key="test-key")
        result = digester.filter(
            build_candidate_news(),
            incident_type="Earthquake",
            incident_name="M 5.0 - Reykjanes Ridge",
            incident_places=[],
            incident_date="2026-07-04",
        )
        assert len(result.selected_news) == 1
        assert result.relevance_scores["https://news.example/a"] == 1.0

    def test_invalid_model_raises_bad_request_on_filter(self, monkeypatch: Any) -> None:
        from litellm.exceptions import BadRequestError

        from disaster_report.ai.openrouter import OpenRouterDigester

        err = BadRequestError(
            "invalid model", model=INVALID_MODEL, llm_provider="openrouter"
        )
        monkeypatch.setattr(
            "disaster_report.ai.openrouter.dspy.LM",
            lambda *args, **kwargs: _FakeLM(raise_error=err),
        )
        monkeypatch.setattr(
            "disaster_report.ai.openrouter.dspy.configure",
            lambda *args, **kwargs: None,
        )
        monkeypatch.setattr(
            "disaster_report.ai.openrouter.dspy.ChainOfThought",
            lambda *args, **kwargs: _FakeFilterCOT(raise_error=err),
        )
        digester = OpenRouterDigester(model=INVALID_MODEL, api_key="test-key")
        with pytest.raises(BadRequestError):
            digester.filter(
                build_candidate_news(),
                incident_type="Earthquake",
                incident_name="M 5.0 - Reykjanes Ridge",
                incident_places=[],
                incident_date="2026-07-04",
            )

    def test_summarize_returns_summary_from_canned_prediction(
        self, monkeypatch: Any
    ) -> None:
        from disaster_report.ai.openrouter import OpenRouterDigester

        _stub_summary_cot(monkeypatch, summary="delta summary")
        digester = OpenRouterDigester(model=MODEL, api_key="test-key")
        result = digester.summarize(
            build_selected_news(),
            build_prior_timeline(),
            incident_type="Earthquake",
            incident_name="M 5.0 - Reykjanes Ridge",
            incident_places=[],
            incident_date="2026-07-04",
        )
        assert result.summary == "delta summary"
        assert result.has_relevant_updates is True

    def test_summarize_takes_selected_news_and_prior_summaries(self) -> None:
        import inspect

        from disaster_report.ai.openrouter import OpenRouterDigester

        signature = inspect.signature(OpenRouterDigester.summarize)
        params = set(signature.parameters)
        assert "selected_news" in params
        assert "prior_summaries" in params

    def test_summarize_takes_incident_context(self) -> None:
        import inspect

        from disaster_report.ai.openrouter import OpenRouterDigester

        signature = inspect.signature(OpenRouterDigester.summarize)
        params = set(signature.parameters)
        assert "incident_type" in params
        assert "incident_name" in params
        assert "incident_places" in params
        assert "incident_date" in params

    def test_summarize_passes_prior_summaries_to_cot(self, monkeypatch: Any) -> None:
        from disaster_report.ai.openrouter import OpenRouterDigester

        captured: dict[str, object] = {}

        def capturing_cot(*args: Any, **kwargs: Any) -> Any:
            captured.update(kwargs)
            import dspy

            return dspy.Prediction(reasoning="stub", summary="delta summary", has_relevant_updates=True)

        monkeypatch.setattr(
            "disaster_report.ai.openrouter.dspy.LM",
            lambda *args, **kwargs: _FakeLM(),
        )
        monkeypatch.setattr(
            "disaster_report.ai.openrouter.dspy.configure",
            lambda *args, **kwargs: None,
        )
        monkeypatch.setattr(
            "disaster_report.ai.openrouter.dspy.ChainOfThought",
            lambda *args, **kwargs: capturing_cot,
        )
        digester = OpenRouterDigester(model=MODEL, api_key="test-key")
        digester.summarize(
            build_selected_news(),
            build_prior_timeline(),
            incident_type="Earthquake",
            incident_name="M 5.0 - Reykjanes Ridge",
            incident_places=[],
            incident_date="2026-07-04",
        )
        assert "prior_summaries" in captured
        assert isinstance(captured["prior_summaries"], list)
        assert len(captured["prior_summaries"]) == 1

    def test_summarize_returns_non_empty_summary(self, monkeypatch: Any) -> None:
        from disaster_report.ai.openrouter import OpenRouterDigester

        _stub_summary_cot(monkeypatch, summary="delta summary")
        digester = OpenRouterDigester(model=MODEL, api_key="test-key")
        result = digester.summarize(
            build_selected_news(),
            build_prior_timeline(),
            incident_type="Earthquake",
            incident_name="M 5.0 - Reykjanes Ridge",
            incident_places=[],
            incident_date="2026-07-04",
        )
        assert result.summary != ""

    def test_summarize_returns_summary_result(self, monkeypatch: Any) -> None:
        from disaster_report.ai.base import SummaryResult
        from disaster_report.ai.openrouter import OpenRouterDigester

        _stub_summary_cot(monkeypatch, summary="delta summary")
        digester = OpenRouterDigester(model=MODEL, api_key="test-key")
        result = digester.summarize(
            build_selected_news(),
            build_prior_timeline(),
            incident_type="Earthquake",
            incident_name="M 5.0 - Reykjanes Ridge",
            incident_places=[],
            incident_date="2026-07-04",
        )
        assert isinstance(result, SummaryResult)

    def test_summarize_has_relevant_updates_flag(self, monkeypatch: Any) -> None:
        from disaster_report.ai.openrouter import OpenRouterDigester

        _stub_summary_cot(monkeypatch, summary="no relevant news", has_relevant_updates=False)
        digester = OpenRouterDigester(model=MODEL, api_key="test-key")
        result = digester.summarize(
            build_selected_news(),
            build_prior_timeline(),
            incident_type="Earthquake",
            incident_name="M 5.0 - Reykjanes Ridge",
            incident_places=[],
            incident_date="2026-07-04",
        )
        assert result.has_relevant_updates is False

    def test_invalid_model_raises_bad_request_on_summarize(
        self, monkeypatch: Any
    ) -> None:
        from litellm.exceptions import BadRequestError

        from disaster_report.ai.openrouter import OpenRouterDigester

        err = BadRequestError(
            "invalid model", model=INVALID_MODEL, llm_provider="openrouter"
        )
        monkeypatch.setattr(
            "disaster_report.ai.openrouter.dspy.LM",
            lambda *args, **kwargs: _FakeLM(raise_error=err),
        )
        monkeypatch.setattr(
            "disaster_report.ai.openrouter.dspy.configure",
            lambda *args, **kwargs: None,
        )
        monkeypatch.setattr(
            "disaster_report.ai.openrouter.dspy.ChainOfThought",
            lambda *args, **kwargs: _FakeSummaryCOT(raise_error=err),
        )
        digester = OpenRouterDigester(model=INVALID_MODEL, api_key="test-key")
        with pytest.raises(BadRequestError):
            digester.summarize(
                build_selected_news(),
                build_prior_timeline(),
                incident_type="Earthquake",
                incident_name="M 5.0 - Reykjanes Ridge",
                incident_places=[],
                incident_date="2026-07-04",
            )


def _stub_filter_cot(monkeypatch: Any, *, kept_urls: set[str]) -> None:
    monkeypatch.setattr(
        "disaster_report.ai.openrouter.dspy.LM",
        lambda *args, **kwargs: _FakeLM(),
    )
    monkeypatch.setattr(
        "disaster_report.ai.openrouter.dspy.configure",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "disaster_report.ai.openrouter.dspy.ChainOfThought",
        lambda *args, **kwargs: _FakeFilterCOT(kept_urls=kept_urls),
    )


def _stub_summary_cot(monkeypatch: Any, *, summary: str, has_relevant_updates: bool = True) -> None:
    monkeypatch.setattr(
        "disaster_report.ai.openrouter.dspy.LM",
        lambda *args, **kwargs: _FakeLM(),
    )
    monkeypatch.setattr(
        "disaster_report.ai.openrouter.dspy.configure",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "disaster_report.ai.openrouter.dspy.ChainOfThought",
        lambda *args, **kwargs: _FakeSummaryCOT(summary=summary, has_relevant_updates=has_relevant_updates),
    )


def _fake_filter_cot_call(candidates: Any, *, kept_urls: set[str]) -> Any:
    import dspy

    judgements = [
        {
            "url": c.get("url", ""),
            "relevant": c.get("url", "") in kept_urls,
            "reason": "kept" if c.get("url", "") in kept_urls else "not relevant",
        }
        for c in candidates
    ]
    return dspy.Prediction(reasoning="stub", judgements=judgements)


def _fake_summary_cot_call(
    selected_news: Any, prior_summaries: Any, *, summary: str, has_relevant_updates: bool = True
) -> Any:
    import dspy

    return dspy.Prediction(reasoning="stub", summary=summary, has_relevant_updates=has_relevant_updates)


class _FakeLM:
    def __init__(self, *, raise_error: Exception | None = None) -> None:
        self._raise_error = raise_error

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        if self._raise_error is not None:
            raise self._raise_error
        return ["stub"]


class _FakeFilterCOT:
    def __init__(
        self,
        *,
        kept_urls: set[str] | None = None,
        raise_error: Exception | None = None,
    ) -> None:
        self._kept_urls = kept_urls if kept_urls is not None else set()
        self._raise_error = raise_error

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        if self._raise_error is not None:
            raise self._raise_error
        candidates = kwargs.get("candidate_news", [])
        return _fake_filter_cot_call(candidates, kept_urls=self._kept_urls)


class _FakeSummaryCOT:
    def __init__(
        self,
        *,
        summary: str = "delta summary",
        has_relevant_updates: bool = True,
        raise_error: Exception | None = None,
    ) -> None:
        self._summary = summary
        self._has_relevant_updates = has_relevant_updates
        self._raise_error = raise_error

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        if self._raise_error is not None:
            raise self._raise_error
        return _fake_summary_cot_call(
            kwargs.get("selected_news", []),
            kwargs.get("prior_summaries", []),
            summary=self._summary,
            has_relevant_updates=self._has_relevant_updates,
        )


def build_candidate_news() -> list[NewsItem]:
    from disaster_report.models import NewsItem

    return [
        NewsItem(
            url="https://news.example/a",
            title="headline a",
            body="body a",
            published_date="2026-07-02",
            source="example",
            domain="news.example",
            image="",
        )
    ]


def build_selected_news() -> list[NewsItem]:
    from disaster_report.models import NewsItem

    return [
        NewsItem(
            url="https://news.example/a",
            title="headline a",
            body="body a",
            published_date="2026-07-02",
            source="example",
            domain="news.example",
            image="",
        )
    ]


def build_prior_timeline() -> list[IncidentLog]:
    from disaster_report.models import IncidentLog

    return [
        IncidentLog(
            incident_id="100",
            log_date="2026-07-01",
            summary="prior summary",
        )
    ]


def load_filter_result(result: FilterResult) -> FilterResult:
    return result
