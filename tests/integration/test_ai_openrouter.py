from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from disaster_report.ai.openrouter import OpenRouterDigester


FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "ai" / "openrouter_summary.json"


def _load_fixture() -> dict:
    return json.loads(FIXTURE.read_bytes())


def _response(status: int, body: dict, url: str) -> httpx.Response:
    return httpx.Response(status, json=body, request=httpx.Request("POST", url))


def test_given_source_reports_when_digest_then_returns_name_summary_and_severity(
    monkeypatch,
):
    fixture = _load_fixture()
    expected = json.loads(fixture["choices"][0]["message"]["content"])
    captured: dict = {}

    def fake_post(url, *, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["payload"] = json
        return _response(200, fixture, url)

    monkeypatch.setattr("disaster_report.ai.openrouter.httpx.post", fake_post)

    result = OpenRouterDigester(api_key="test-key").digest(
        sources=[{"source": "USGS", "text": "M5.2 quake, Sarangani, Philippines."}]
    )

    assert result == expected
    assert result["summary"]
    assert result["severity"] in {"LOW", "MEDIUM", "HIGH"}
    assert captured["url"].endswith("/chat/completions")
    assert captured["payload"]["response_format"] == {"type": "json_object"}
    assert captured["payload"]["model"] == "nvidia/nemotron-3-super-120b-a12b:free"
    roles = [m["role"] for m in captured["payload"]["messages"]]
    assert roles == ["system", "user"], "prompt must use system+user roles"


def test_given_first_model_rate_limited_when_digest_then_falls_back_to_next_model(
    monkeypatch,
):
    fixture = _load_fixture()
    tried: list[str] = []

    def fake_post(url, *, headers=None, json=None, timeout=None):
        tried.append(json["model"])
        if len(tried) == 1:
            return _response(429, {"error": {"message": "rate limited"}}, url)
        return _response(200, fixture, url)

    monkeypatch.setattr("disaster_report.ai.openrouter.httpx.post", fake_post)

    result = OpenRouterDigester(api_key="k").digest("a single text source")

    assert len(tried) == 2
    assert tried[0] != tried[1]
    assert result["summary"]


def test_given_all_models_fail_when_digest_then_raises_runtime_error(monkeypatch):
    def fake_post(url, *, headers=None, json=None, timeout=None):
        return _response(429, {"error": {"message": "rate limited"}}, url)

    monkeypatch.setattr("disaster_report.ai.openrouter.httpx.post", fake_post)

    digester = OpenRouterDigester(api_key="k", models=("a:free", "b:free"))
    with pytest.raises(RuntimeError):
        digester.digest("text")


def test_given_source_reports_when_digest_then_prompt_asks_for_and_returns_search_keys(
    monkeypatch,
):
    payload_with_keys = {
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": json.dumps(
                        {
                            "canonical_name": "Sarangani Earthquake",
                            "summary": "A magnitude 5.2 earthquake struck near Sarangani.",
                            "severity": "LOW",
                            "search_keys": ["Sarangani earthquake", "Mindanao quake 2026"],
                        }
                    ),
                },
            }
        ]
    }
    captured: dict = {}

    def fake_post(url, *, headers=None, json=None, timeout=None):
        captured["messages"] = json["messages"]
        return _response(200, payload_with_keys, url)

    monkeypatch.setattr("disaster_report.ai.openrouter.httpx.post", fake_post)

    result = OpenRouterDigester(api_key="k").digest(sources=[{"source": "USGS"}])

    all_content = " ".join(m["content"] for m in captured["messages"])
    assert "search_keys" in all_content, "prompt must instruct the model to return search_keys"
    assert result["search_keys"] == ["Sarangani earthquake", "Mindanao quake 2026"]


def test_prompt_includes_schema_rubric_example_and_delimited_input(monkeypatch):
    captured: dict = {}
    body = {
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": json.dumps(
                        {"canonical_name": "X", "summary": "ok", "severity": "LOW", "search_keys": ["k"]}
                    ),
                },
            }
        ]
    }

    def fake_post(url, *, headers=None, json=None, timeout=None):
        captured["messages"] = json["messages"]
        return _response(200, body, url)

    monkeypatch.setattr("disaster_report.ai.openrouter.httpx.post", fake_post)

    OpenRouterDigester(api_key="k").digest(
        sources={
            "source_reports": [{"source_name": "USGS", "incident_name": "M5.2 quake"}],
            "news_articles": [{"url": "https://example/n1", "headline": "Quake"}],
        }
    )

    system, user = captured["messages"][0]["content"], captured["messages"][1]["content"]

    for required in ("canonical_name", "summary", "severity", "search_keys", "LOW", "MEDIUM", "HIGH", "CRITICAL"):
        assert required in user, f"schema must mention {required!r}"
    assert "EXAMPLE OUTPUT" in user, "prompt must include a few-shot example"
    assert '"severity": "LOW"' in user, "example must show allowed enum values"
    assert "<source_reports>" in user and "</source_reports>" in user
    assert "<news_articles>" in user and "</news_articles>" in user
    assert "M5.2 quake" in user, "source reports must be embedded in delimited input"
    assert "https://example/n1" in user, "news articles must be embedded in delimited input"
    assert "SEVERITY RUBRIC" in user
    for rule in ("No casualties", "Catastrophic"):
        assert rule in user
    assert "English only" in system
    assert "NEVER FABRICATE" in system, "system prompt must forbid fabrication"
    assert "SEVERITY MUST MATCH EVIDENCE" in system, "system prompt must tie severity to evidence"


def test_system_prompt_includes_update_mode_rules_for_re_digest(monkeypatch):
    captured: dict = {}
    body = {
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": json.dumps(
                        {"canonical_name": "X", "summary": "ok", "severity": "LOW", "search_keys": ["k"]}
                    ),
                },
            }
        ]
    }

    def fake_post(url, *, headers=None, json=None, timeout=None):
        captured["messages"] = json["messages"]
        return _response(200, body, url)

    monkeypatch.setattr("disaster_report.ai.openrouter.httpx.post", fake_post)

    OpenRouterDigester(api_key="k").digest(
        sources={
            "source_reports": [{"source_name": "PRIOR_DIGEST", "incident_name": "Afghanistan Earthquake"}],
            "news_articles": [{"url": "https://example/n1", "headline": "Venezuela quake"}],
        }
    )

    system = captured["messages"][0]["content"]
    user = captured["messages"][1]["content"]
    assert "UPDATE MODE" in system, "system prompt must define UPDATE MODE for PRIOR_DIGEST"
    assert "PRIOR_DIGEST" in system
    assert "IRRELEVANT" in system.upper() or "irrelevant" in system, (
        "system prompt must warn that news_articles may contain irrelevant articles"
    )
    assert "identity" in system.lower(), (
        "system prompt must instruct model to preserve incident identity"
    )
    assert "PRIOR_DIGEST" in user, "prior digest identity must be embedded in source_reports"
    assert "Afghanistan Earthquake" in user


@pytest.mark.parametrize(
    "content",
    [
        "```json\n" + json.dumps({"canonical_name": "X", "summary": "ok", "severity": "LOW"}) + "\n```",
        "```\n" + json.dumps({"canonical_name": "X", "summary": "ok", "severity": "LOW"}) + "\n```",
        "Sure, here is the JSON:\n" + json.dumps({"canonical_name": "X", "summary": "ok", "severity": "LOW"}),
        json.dumps({"canonical_name": "X", "summary": "ok", "severity": "LOW"}),
        "  \n" + json.dumps({"canonical_name": "X", "summary": "ok", "severity": "LOW"}) + "  ",
    ],
)
def test_given_model_wraps_or_decorates_json_when_digest_then_extracts_object(
    monkeypatch, content
):
    body = {"choices": [{"index": 0, "message": {"role": "assistant", "content": content}}]}

    def fake_post(url, *, headers=None, json=None, timeout=None):
        return _response(200, body, url)

    monkeypatch.setattr("disaster_report.ai.openrouter.httpx.post", fake_post)

    result = OpenRouterDigester(api_key="k").digest("text")

    assert result["summary"] == "ok"
    assert result["canonical_name"] == "X"


def test_given_unparseable_content_from_first_model_when_digest_then_falls_back(
    monkeypatch,
):
    good = json.dumps({"canonical_name": "X", "summary": "ok", "severity": "LOW"})
    calls: list[str] = []

    def fake_post(url, *, headers=None, json=None, timeout=None):
        calls.append(json["model"])
        content = "nonsense no json here" if len(calls) == 1 else good
        body = {"choices": [{"index": 0, "message": {"role": "assistant", "content": content}}]}
        return _response(200, body, url)

    monkeypatch.setattr("disaster_report.ai.openrouter.httpx.post", fake_post)

    result = OpenRouterDigester(api_key="k").digest("text")

    assert len(calls) == 2
    assert result["summary"] == "ok"


def test_given_200_response_without_choices_when_digest_then_falls_back(monkeypatch):
    good = json.dumps({"canonical_name": "X", "summary": "ok", "severity": "LOW"})
    calls: list[str] = []

    def fake_post(url, *, headers=None, json=None, timeout=None):
        calls.append(json["model"])
        body = (
            {"error": {"message": "rate limited"}, "user": "limited"}
            if len(calls) == 1
            else {"choices": [{"index": 0, "message": {"role": "assistant", "content": good}}]}
        )
        return _response(200, body, url)

    monkeypatch.setattr("disaster_report.ai.openrouter.httpx.post", fake_post)

    result = OpenRouterDigester(api_key="k").digest("text")

    assert len(calls) == 2, "must fall through to next model when 200 body lacks choices"
    assert result["summary"] == "ok"


def test_given_all_200_responses_missing_choices_when_digest_then_raises(monkeypatch):
    def fake_post(url, *, headers=None, json=None, timeout=None):
        return _response(200, {"error": "all models unavailable"}, url)

    monkeypatch.setattr("disaster_report.ai.openrouter.httpx.post", fake_post)

    with pytest.raises(RuntimeError, match="models failed"):
        OpenRouterDigester(api_key="k", models=("a:free", "b:free")).digest("text")
