"""Batched AI classifier agent using DSPy typed signatures to generate
summaries, rationales, and detect override flags O1, O3, O5."""

from __future__ import annotations

import json
from typing import Any

import dspy

from disaster_surveillance_reporter.ai.provider import AIProvider
from disaster_surveillance_reporter.types import IncidentBundle


class ClassifyIncident(dspy.Signature):
    """Classify a disaster incident and detect override conditions.

    Given all raw records for an incident, generate a concise summary,
    a rationale for the priority classification, and detect whether any
    of the AI-assisted override conditions (O1 Humanitarian Crisis,
    O3 Likely Development, O5 Forecast/Early Warning) apply.
    """

    incident_id: str = dspy.InputField()
    incident_level: int = dspy.InputField()
    priority: str = dspy.InputField()
    country: str | None = dspy.InputField()
    disaster_type: str | None = dspy.InputField()
    raw_records: str = dspy.InputField()
    summary: str = dspy.OutputField()
    rationale: str = dspy.OutputField()
    override_humanitarian_crisis: bool = dspy.OutputField()
    override_likely_development: bool = dspy.OutputField()
    override_forecast_warning: bool = dspy.OutputField()


class ClassifierAgent:
    """Batched AI enrichment agent using DSPy typed signatures.

    Generates summaries, rationales, and detects AI-assisted override
    conditions O1, O3, and O5 from should_report=True IncidentBundles.
    """

    BATCH_SIZE: int = 10

    def __init__(self, provider: AIProvider | None = None) -> None:
        """Initialise the ClassifierAgent.

        Args:
            provider: An AIProvider for making chat calls. If None, bundles
                are returned unchanged.
        """
        self._provider = provider

    def enrich(self, bundles: list[IncidentBundle]) -> list[IncidentBundle]:
        """Process reportable bundles in batches, generating summaries and
        detecting O1/O3/O5 override flags via AI."""
        for i in range(0, len(bundles), self.BATCH_SIZE):
            batch = bundles[i : i + self.BATCH_SIZE]
            self._process_batch(batch)
        return bundles

    def _process_batch(self, batch: list[IncidentBundle]) -> None:
        if not self._provider:
            return
        try:
            self._do_classify_batch(batch)
        except Exception:
            self._mark_unenriched_failed(batch)

    @staticmethod
    def _mark_unenriched_failed(
        bundles: list[IncidentBundle],
    ) -> None:
        for bundle in bundles:
            bundle.enrichment_failed = (
                bundle.enrichment_failed or not bundle.ai_enriched
            )

    def _do_classify_batch(self, batch: list[IncidentBundle]) -> None:
        if not self._provider:
            return
        prompt = self._build_batch_prompt(batch)
        response = self._provider.chat(prompt, model="classifier-v1")
        response = self._strip_json_fences(response)
        results: list[dict[str, Any]] = json.loads(response)
        for bundle, data in zip(batch, results):
            pred = dspy.Prediction(ClassifyIncident, **{
                k: data.get(k) for k in (
                    "summary", "rationale",
                    "override_humanitarian_crisis",
                    "override_likely_development",
                    "override_forecast_warning",
                )
            })
            self._apply_enrichment(bundle, pred)
        for bundle in batch[len(results):]:
            bundle.enrichment_failed = True

    def _build_batch_prompt(self, batch: list[IncidentBundle]) -> str:
        parts: list[str] = []
        parts.append(
            "Classify and generate summaries for these disaster incidents.\n"
        )
        parts.append(
            "For each incident, generate: summary, rationale, "
            "and detect override flags (override_humanitarian_crisis for O1, "
            "override_likely_development for O3, "
            "override_forecast_warning for O5).\n"
        )
        parts.append(
            "Return a JSON array with one object per incident. "
            'Each object: {"summary": "...", "rationale": "...", '
            '"override_humanitarian_crisis": false, '
            '"override_likely_development": false, '
            '"override_forecast_warning": false}\n'
        )
        for idx, bundle in enumerate(batch):
            parts.append(
                f"\nIncident {idx + 1} (ID: {bundle.incident_id}):"
            )
            parts.extend(self._format_records(bundle.records))
        return "\n".join(parts)

    @staticmethod
    def _format_records(records: list) -> list[str]:
        return [
            f"  Source {r.source_name}: {json.dumps(r.raw_fields)}"
            for r in records
        ]

    @staticmethod
    def _apply_enrichment(
        bundle: IncidentBundle, result: dspy.Prediction,
    ) -> None:
        bundle.summary = result.summary
        bundle.rationale = result.rationale
        bundle.ai_enriched = True

        if result.override_humanitarian_crisis:
            bundle.overrides.append("O1")
        if result.override_likely_development:
            bundle.overrides.append("O3")
        if result.override_forecast_warning:
            bundle.overrides.append("O5")

    @staticmethod
    def _strip_json_fences(text: str) -> str:
        """Strip markdown code fences and extract JSON from LLM response."""
        text = text.strip()
        if text.startswith("```"):
            first_newline = text.find("\n")
            if first_newline != -1:
                text = text[first_newline + 1:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
        return text
