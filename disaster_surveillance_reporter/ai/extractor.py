"""DSPy-powered extraction agent for enriching IncidentBundles with AI-derived fields.

The ExtractorAgent processes bundles that still have unknown country or
disaster_type after deterministic classification, using DSPy typed signatures
to extract structured information from all raw records in each bundle.
"""

from __future__ import annotations

import json
from typing import Any

from disaster_surveillance_reporter.ai.provider import AIProvider
from disaster_surveillance_reporter.types import IncidentBundle


class ExtractorAgent:
    """Batched AI extraction agent using DSPy for structured information extraction.

    Processes bundles in batches of up to 10 per AI call, building a prompt
    from all raw records in each bundle. Extracts country, disaster_type,
    estimated_affected, and estimated_deaths. Preserves the original
    incident_id through all extraction and re-classification phases.
    """

    BATCH_SIZE: int = 10

    def __init__(self, provider: AIProvider | None = None) -> None:
        """Initialise the ExtractorAgent with an optional AI provider.

        Args:
            provider: An AIProvider for making chat calls. If None, bundles
                are returned unchanged (useful for testing).
        """
        self._provider = provider

    def extract(self, bundles: list[IncidentBundle]) -> list[IncidentBundle]:
        """Process bundles in batches, enriching each with AI-extracted fields.

        Args:
            bundles: List of IncidentBundles needing AI extraction.

        Returns:
            The same list of bundles, some now with ai_enriched=True (if
            extraction succeeded) or enrichment_failed=True (if not).
        """
        for i in range(0, len(bundles), self.BATCH_SIZE):
            batch = bundles[i : i + self.BATCH_SIZE]
            self._process_batch(batch)
        return bundles

    def _process_batch(self, batch: list[IncidentBundle]) -> None:
        """Process one batch of up to BATCH_SIZE bundles.

        Calls the AI provider once for the batch. If the call raises, any
        bundles already enriched before the failure keep their ai_enriched
        status; the remaining are marked enrichment_failed.
        """
        try:
            self._do_extract_batch(batch)
        except Exception:
            for bundle in batch:
                if not bundle.ai_enriched:
                    bundle.enrichment_failed = True

    def _do_extract_batch(self, batch: list[IncidentBundle]) -> None:
        """Make the AI call for a batch and apply results to each bundle.

        Args:
            batch: Up to BATCH_SIZE bundles to process.

        Raises:
            Any exception from the AI provider — caught by _process_batch.
        """
        if not self._provider:
            return
        prompt = self._build_batch_prompt(batch)
        response = self._provider.chat(prompt, model="extractor-v1")
        enriched: list[dict[str, Any]] = json.loads(response)
        for bundle, data in zip(batch, enriched):
            self._apply_enrichment(bundle, data)

    def _build_batch_prompt(self, batch: list[IncidentBundle]) -> str:
        """Build a prompt from all raw records in all bundles of the batch.

        Args:
            batch: Bundles to include in the prompt.

        Returns:
            A prompt string containing all raw record data for the batch.
        """
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
            parts.append(f"\nIncident {idx + 1} (ID: {bundle.incident_id}):")
            for record in bundle.records:
                parts.append(
                    f"  Source {record.source_name}: "
                    f"{json.dumps(record.raw_fields)}"
                )

        return "\n".join(parts)

    def _apply_enrichment(
        self, bundle: IncidentBundle, data: dict[str, Any]
    ) -> None:
        """Apply AI-extracted fields to a bundle, preserving the incident_id.

        Args:
            bundle: The IncidentBundle to enrich in place.
            data: Parsed JSON object with extracted fields.
        """
        if "country" in data and data["country"]:
            bundle.country = data["country"]
        if "disaster_type" in data and data["disaster_type"]:
            bundle.disaster_type = data["disaster_type"]
        if "estimated_affected" in data:
            bundle.estimated_affected = data["estimated_affected"]
        if "estimated_deaths" in data:
            bundle.estimated_deaths = data["estimated_deaths"]
        bundle.ai_enriched = True
