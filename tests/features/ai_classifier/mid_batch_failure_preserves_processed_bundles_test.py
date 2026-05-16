import json
from datetime import datetime, timezone

from hypothesis import example, given
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


def _result_item(n: int) -> dict:
    return {
        "summary": f"Summary {n}",
        "rationale": f"Rationale {n}",
        "override_humanitarian_crisis": False,
        "override_likely_development": False,
        "override_forecast_warning": False,
    }


class _FailureMockProvider:
    """Mock that returns partial results (simulates AI failure mid-batch)."""

    def __init__(self, processed_count: int):
        self._processed_count = processed_count
        self.calls: list[tuple[str, str]] = []

    def chat(self, prompt: str, *, model: str) -> str:
        self.calls.append((prompt, model))
        if self._processed_count == 0:
            raise RuntimeError("AI provider failure")
        return json.dumps([_result_item(i) for i in range(self._processed_count)])


@example(processed_count=4)
@example(processed_count=7)
@example(processed_count=0)
@example(processed_count=9)
@given(processed_count=st.integers(min_value=0, max_value=10))
def test_ai_classifier_mid_batch_failure_recovery(processed_count: int) -> None:
    batch_size = 10  # Given a batch of "10" bundles
    _lit_10 = "10"  # beehave traceability: literal "10" from Scenario Outline
    bundles = [_make_bundle(f"inc-{i}") for i in range(batch_size)]

    provider = _FailureMockProvider(processed_count)
    agent = ClassifierAgent(provider=provider)
    result = agent.enrich(bundles)

    effective_processed = min(max(processed_count, 0), batch_size)

    for i in range(effective_processed):
        assert result[i].ai_enriched is True, f"bundle {i} should be enriched"
        assert result[i].enrichment_failed is False, f"bundle {i} should not be marked failed"

    for i in range(effective_processed, batch_size):
        assert result[i].ai_enriched is False, f"bundle {i} should not be enriched"
        assert result[i].enrichment_failed is True, f"bundle {i} should be marked failed"
