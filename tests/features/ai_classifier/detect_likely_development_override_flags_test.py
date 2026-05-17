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


def test_ai_classifier_detects_likely_development() -> None:
    bundle = IncidentBundle(
        incident_id="20260101-HT-LD",
        records=[
            RawRecord(
                source_name="ocha",
                fetched_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                raw_fields={"text": "situation expected to deteriorate rapidly"},
            )
        ],
        should_report=True,
    )

    response = [
        {
            "summary": "Deteriorating situation in Haiti",
            "rationale": "Situation expected to deteriorate rapidly detected",
            "override_humanitarian_crisis": False,
            "override_likely_development": True,
            "override_forecast_warning": False,
        }
    ]
    provider = _MockProvider(response=response)
    agent = ClassifierAgent(provider=provider)
    result = agent.enrich([bundle])

    assert "O3" in result[0].overrides
    assert result[0].ai_enriched is True
