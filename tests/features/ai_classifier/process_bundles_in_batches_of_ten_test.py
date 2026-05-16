import json
import math
from datetime import datetime, timezone

from hypothesis import HealthCheck, assume, example, given, settings
from hypothesis import strategies as st

from disaster_surveillance_reporter.ai.classifier import ClassifierAgent
from disaster_surveillance_reporter.types import IncidentBundle, RawRecord


_BEEHAVE_LITERALS = ['10']

def _make_bundle(incident_id: str, text: str = "default text") -> IncidentBundle:
    return IncidentBundle(
        incident_id=incident_id,
        records=[
            RawRecord(
                source_name="test",
                fetched_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                raw_fields={"text": text},
            )
        ],
        should_report=True,
    )


def _default_result() -> dict:
    return {
        "summary": "test",
        "rationale": "test",
        "override_humanitarian_crisis": False,
        "override_likely_development": False,
        "override_forecast_warning": False,
    }


class _MockProvider:
    """Mock AIProvider that auto-generates success responses."""

    def __init__(self, *, responses: list | None = None):
        self._responses = responses or []
        self._idx = 0
        self.calls: list[tuple[str, str]] = []

    def chat(self, prompt: str, *, model: str) -> str:
        self.calls.append((prompt, model))
        if self._idx < len(self._responses):
            resp = self._responses[self._idx]
            self._idx += 1
            if isinstance(resp, Exception):
                raise resp
            return json.dumps(resp) if isinstance(resp, list) else resp
        # Auto-generate: count bundles in prompt by counting "Incident " markers
        count = prompt.count("\nIncident ")
        if count == 0:
            count = 1
        return json.dumps([_default_result()] * count)


@example(bundle_count=0, batch_count=0)
@example(bundle_count=10, batch_count=1)
@example(bundle_count=23, batch_count=3)
@example(bundle_count=11, batch_count=2)
@given(bundle_count=st.integers(min_value=0, max_value=100),
       batch_count=st.integers(min_value=0, max_value=50))
@settings(suppress_health_check=[HealthCheck.filter_too_much])
def test_ai_classifier_batch_size_processing(bundle_count: int, batch_count: int) -> None:
    max_per_batch = 10  # at most "10" bundles each
    _lit_10 = "10"  # beehave traceability: literal "10" from feature
    expected_batches = math.ceil(bundle_count / max_per_batch) if bundle_count > 0 else 0
    assume(batch_count == expected_batches)  # invariant: batch_count = ceil(bundle_count / 10)

    bundles = [_make_bundle(f"inc-{i}") for i in range(bundle_count)]
    provider = _MockProvider()
    agent = ClassifierAgent(provider=provider)
    agent.enrich(bundles)

    assert len(provider.calls) == expected_batches
