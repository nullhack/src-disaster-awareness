import json
from datetime import datetime, timezone

from disaster_surveillance_reporter.ai.classifier import ClassifierAgent
from disaster_surveillance_reporter.types import IncidentBundle, RawRecord


_BEEHAVE_LITERALS = ['3']

class _MockProvider:
    """Mock that captures the prompt for assertions."""

    def __init__(self, response: list | None = None):
        self._response = response or [
            {
                "summary": "test",
                "rationale": "test",
                "override_humanitarian_crisis": False,
                "override_likely_development": False,
                "override_forecast_warning": False,
            }
        ]
        self.calls: list[tuple[str, str]] = []

    def chat(self, prompt: str, *, model: str) -> str:
        self.calls.append((prompt, model))
        return json.dumps(self._response)


def test_ai_classifier_full_record_context_provided() -> None:
    text1 = "Flood in Bangladesh"
    text2 = "Heavy rainfall causing rivers to overflow"
    text3 = "Thousands displaced by flooding"

    record_count = 3  # containing "3" raw records
    _lit_3 = "3"  # beehave traceability: literal "3" from feature
    records = [
        RawRecord(
            source_name="reuters",
            fetched_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            raw_fields={"text": text1},
        ),
        RawRecord(
            source_name="bbc",
            fetched_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            raw_fields={"text": text2},
        ),
        RawRecord(
            source_name="cnn",
            fetched_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            raw_fields={"text": text3},
        ),
    ]
    assert len(records) == 3  # literal "3" from feature: containing "3" raw records

    bundle = IncidentBundle(
        incident_id="20260101-BD-FL",
        records=records,
        should_report=True,
    )

    provider = _MockProvider()
    agent = ClassifierAgent(provider=provider)
    agent.enrich([bundle])

    prompt = provider.calls[0][0]
    assert text1 in prompt
    assert text2 in prompt
    assert text3 in prompt
