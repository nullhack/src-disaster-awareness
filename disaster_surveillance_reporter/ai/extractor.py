"""DSPy-powered extraction agent for enriching IncidentBundles with AI fields.

The ExtractorAgent processes bundles that still have unknown country or
disaster_type after deterministic classification, using DSPy typed
signatures to document extraction contracts.
"""

from __future__ import annotations

import json
from typing import Any

import dspy

from disaster_surveillance_reporter.ai.provider import AIProvider
from disaster_surveillance_reporter.types import IncidentBundle


class ExtractFields(dspy.Signature):
    """Extract structured information from disaster incident records.

    Given raw records from multiple sources, identify the country where
    the incident occurred, the type of disaster, and estimated impact.
    """

    incident_id: str = dspy.InputField()
    raw_records: str = dspy.InputField()
    country: str | None = dspy.OutputField()
    disaster_type: str | None = dspy.OutputField()
    estimated_affected: int | None = dspy.OutputField()
    estimated_deaths: int | None = dspy.OutputField()


class ExtractorAgent:
    """Batched AI extraction agent using DSPy typed signatures.

    Processes bundles in batches of up to 10 per AI call, building a prompt
    from all raw records in each bundle. Extracts country, disaster_type,
    estimated_affected, and estimated_deaths. Preserves the original
    incident_id through all extraction and re-classification phases.
    """

    BATCH_SIZE: int = 10

    def __init__(self, provider: AIProvider | None = None) -> None:
        """Initialise the ExtractorAgent.

        Args:
            provider: An AIProvider for making chat calls. If None, bundles
                are returned unchanged.
        """
        self._provider = provider

    def extract(self, bundles: list[IncidentBundle]) -> list[IncidentBundle]:
        """Process bundles in batches, enriching each with AI-extracted fields."""
        for i in range(0, len(bundles), self.BATCH_SIZE):
            batch = bundles[i : i + self.BATCH_SIZE]
            self._process_batch(batch)
        return bundles

    def _process_batch(self, batch: list[IncidentBundle]) -> None:
        try:
            self._do_extract_batch(batch)
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

    def _do_extract_batch(self, batch: list[IncidentBundle]) -> None:
        if not self._provider:
            return
        prompt = self._build_batch_prompt(batch)
        response = self._provider.chat(prompt, model="extractor-v1")
        response = self._strip_json_fences(response)
        enriched: list[dict[str, Any]] = json.loads(response)
        for bundle, data in zip(batch, enriched):
            pred = dspy.Prediction(ExtractFields, **{
                k: data.get(k) for k in (
                    "country", "disaster_type",
                    "estimated_affected", "estimated_deaths",
                )
            })
            self._apply_enrichment(bundle, pred)

    def _build_batch_prompt(self, batch: list[IncidentBundle]) -> str:
        parts: list[str] = []
        parts.append(
            "Extract structured information from these disaster incidents.\n"
        )
        parts.append(
            "For each incident, extract: country, disaster_type, "
            "estimated_affected, estimated_deaths.\n"
        )
        parts.append(
            "Return a JSON array with one object per incident. "
            'Each object: {"country": null, "disaster_type": null, '
            '"estimated_affected": null, "estimated_deaths": null}\n'
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
        if result.country:
            bundle.country = str(result.country)
        if result.disaster_type:
            bundle.disaster_type = str(result.disaster_type)
        if result.estimated_affected is not None:
            bundle.estimated_affected = int(result.estimated_affected)
        if result.estimated_deaths is not None:
            bundle.estimated_deaths = int(result.estimated_deaths)
        bundle.ai_enriched = True

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
