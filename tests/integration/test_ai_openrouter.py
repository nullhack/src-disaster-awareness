"""Contract tests for the dspy-backed OpenRouter digester (3-signature split).

The HTTP/parsing layer is dspy's responsibility (it enforces the typed
Signature). These tests target OUR code: two-track routing, output-shape
contract (AI-only fields; no canonical_name/search_keys - those are derived
downstream), model failover, partial-success on the disease track, retry, and
total-failure. The dspy predictors are stubbed so no network call is made.
"""
from __future__ import annotations

import pytest

import dspy
from disaster_report.ai.openrouter import OpenRouterDigester


class _FakePredict:
    """Stand-in for dspy.Predict: pops queued outcomes (Prediction or Exception)."""

    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls: list[tuple] = []

    def __call__(self, *, lm, **kw):
        self.calls.append((lm, kw))
        if not self.outcomes:
            raise AssertionError("no queued outcome left")
        out = self.outcomes.pop(0)
        if isinstance(out, BaseException):
            raise out
        return out


def _dig(models=("m1", "m2")) -> OpenRouterDigester:
    # max_attempts=1: each model tried once (no real time.sleep in failover tests)
    return OpenRouterDigester(api_key="test-key", models=models, timeout=1.0, max_attempts=1)


def _classify_pred(**kw):
    base = {
        "severity": "HIGH",
        "disease_name": "Ebola",
        "pandemic_potential": "CRITICAL",
        "event_status": "new_outbreak",
    }
    base.update(kw)
    return dspy.Prediction(**base)


def _summary_pred(summary="a summary"):
    return dspy.Prediction(summary=summary)


def _disease_sources(dtype="Disease"):
    return {
        "source_reports": [{"source_name": "WHO", "incident_type": dtype, "text": "x"}],
        "news_articles": [],
    }


def _physical_sources():
    return {
        "source_reports": [{"source_name": "USGS", "incident_type": "Earthquake", "text": "x"}],
        "news_articles": [],
    }


def test_disease_track_runs_classify_then_summary():
    dig = _dig()
    classify = _FakePredict([_classify_pred()])
    summary = _FakePredict([_summary_pred()])
    dig._classify, dig._disease_summary = classify, summary
    r = dig.digest(_disease_sources())
    assert set(r) == {
        "severity", "disease_name", "pandemic_potential", "event_status", "summary",
    }
    assert r["disease_name"] == "Ebola"
    assert r["pandemic_potential"] == "CRITICAL"
    assert r["event_status"] == "new_outbreak"
    assert r["summary"] == "a summary"
    assert len(classify.calls) == 1 and len(summary.calls) == 1


def test_physical_track_runs_summary_only():
    dig = _dig()
    phys = _FakePredict([_summary_pred()])
    dig._physical_summary = phys
    r = dig.digest(_physical_sources())
    assert set(r) == {"summary"}
    assert "disease_name" not in r and "severity" not in r
    assert len(phys.calls) == 1


def test_routing_disease_synonyms_to_disease_track():
    for dtype in ("Disease", "epidemic", "Outbreak", "EPIDEMICS"):
        dig = _dig()
        classify = _FakePredict([_classify_pred()])
        summary = _FakePredict([_summary_pred()])
        phys = _FakePredict([_summary_pred()])  # would fire if misrouted
        dig._classify, dig._disease_summary, dig._physical_summary = (
            classify, summary, phys,
        )
        dig.digest(_disease_sources(dtype=dtype))
        assert len(classify.calls) == 1, dtype
        assert len(phys.calls) == 0, f"{dtype} must not hit physical track"


def test_routing_physical_to_physical_track():
    dig = _dig()
    classify = _FakePredict([_classify_pred()])  # would fire if misrouted
    summary = _FakePredict([_summary_pred()])
    phys = _FakePredict([_summary_pred()])
    dig._classify, dig._disease_summary, dig._physical_summary = (
        classify, summary, phys,
    )
    dig.digest(_physical_sources())
    assert len(phys.calls) == 1
    assert len(classify.calls) == 0


def test_failover_advances_to_next_model_on_error():
    dig = _dig(("m1", "m2"))
    stub = _FakePredict([RuntimeError("m1 down"), _summary_pred()])
    dig._physical_summary = stub
    r = dig.digest(_physical_sources())
    assert r["summary"] == "a summary"
    assert len(stub.calls) == 2
    assert stub.calls[0][0] is not stub.calls[1][0]


def test_empty_summary_retries_next_model():
    dig = _dig(("m1", "m2"))
    stub = _FakePredict([_summary_pred(""), _summary_pred("real summary")])
    dig._physical_summary = stub
    r = dig.digest(_physical_sources())
    assert r["summary"] == "real summary"
    assert len(stub.calls) == 2


def test_all_models_fail_raises_runtime_error():
    dig = _dig(("m1", "m2"))
    dig._physical_summary = _FakePredict([RuntimeError("down1"), RuntimeError("down2")])
    with pytest.raises(RuntimeError, match="physical digest failed"):
        dig.digest(_physical_sources())


def test_partial_success_classify_succeeds_summary_fails():
    """Disease track: classify succeeds but summary fails every model -> the
    classification fields are still returned (partial success); no raise."""
    dig = _dig(("m1", "m2"))
    classify = _FakePredict([_classify_pred()])
    summary = _FakePredict([RuntimeError("summary 1 down"), RuntimeError("summary 2 down")])
    dig._classify, dig._disease_summary = classify, summary
    r = dig.digest(_disease_sources())
    assert "disease_name" in r and r["disease_name"] == "Ebola"
    assert "summary" not in r


def test_predictor_receives_shaped_inputs():
    dig = _dig()
    stub = _FakePredict([_summary_pred()])
    dig._physical_summary = stub
    dig.digest(_physical_sources())
    _, kw = stub.calls[0]
    assert "source_reports" in kw and "news_articles" in kw
    import json
    assert json.loads(kw["source_reports"])[0]["incident_type"] == "Earthquake"
    assert kw["news_articles"] == "[]"


def test_retries_transient_error_on_same_model(monkeypatch):
    """A transient provider error is retried on the SAME model (not just failover)."""
    import disaster_report.ai.openrouter as mod
    monkeypatch.setattr(mod.time, "sleep", lambda *_: None)
    dig = OpenRouterDigester(api_key="k", models=("m1",), max_attempts=3, backoff=1.0)
    stub = _FakePredict([RuntimeError("transient"), RuntimeError("transient"), _summary_pred()])
    dig._physical_summary = stub
    r = dig.digest(_physical_sources())
    assert r["summary"] == "a summary"
    assert len(stub.calls) == 3  # retried twice on the same model, then succeeded
