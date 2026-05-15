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


def test_ai_classifier_detects_forecast_warning() -> None:
    bundle = IncidentBundle(
        incident_id="20260101-PH-TC",
        records=[
            RawRecord(
                source_name="pagasa",
                fetched_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                raw_fields={"text": "early warning of approaching tropical cyclone"},
            )
        ],
        should_report=True,
    )

    response = [
        {
            "summary": "Tropical cyclone approaching Philippines",
            "rationale": "Early warning of approaching tropical cyclone detected",
            "override_humanitarian_crisis": False,
            "override_likely_development": False,
            "override_forecast_warning": True,
        }
    ]
    provider = _MockProvider(response=response)
    agent = ClassifierAgent(provider=provider)
    result = agent.enrich([bundle])

    assert "O5" in result[0].overrides
    assert result[0].ai_enriched is True
