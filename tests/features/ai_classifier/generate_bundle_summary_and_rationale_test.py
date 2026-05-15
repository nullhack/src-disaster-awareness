import json
from datetime import datetime, timezone

from disaster_surveillance_reporter.ai.classifier import ClassifierAgent
from disaster_surveillance_reporter.types import IncidentBundle, RawRecord


class _MockProvider:
    def __init__(self, response: list):
        self._response = response
        self.calls: list[tuple[str, str]] = []

    def chat(self, prompt: str, *, model: str) -> str:
        self.calls.append((prompt, model))
        return json.dumps(self._response)


def test_ai_classifier_generates_summary_and_rationale() -> None:
    bundle = IncidentBundle(
        incident_id="20260101-JP-EQ",
        records=[
            RawRecord(
                source_name="reuters",
                fetched_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                raw_fields={"text": "Earthquake in Japan, magnitude 7.2"},
            )
        ],
        should_report=True,
    )

    response = [
        {
            "summary": "Major earthquake hits Japan",
            "rationale": "Detected earthquake event from text describing magnitude 7.2",
            "override_humanitarian_crisis": False,
            "override_likely_development": False,
            "override_forecast_warning": False,
        }
    ]
    provider = _MockProvider(response=response)
    agent = ClassifierAgent(provider=provider)
    result = agent.enrich([bundle])

    assert result[0].summary == "Major earthquake hits Japan"
    assert result[0].rationale == "Detected earthquake event from text describing magnitude 7.2"
    assert result[0].ai_enriched is True
