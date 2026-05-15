"""Batched AI classifier agent that generates summaries, rationales, and
detects override flags O1, O3, and O5 from should_report=True IncidentBundles.
"""

from __future__ import annotations

import json
from typing import Any

from disaster_surveillance_reporter.ai.provider import AIProvider
from disaster_surveillance_reporter.types import IncidentBundle


class ClassifierAgent:
    """Batched AI enrichment agent that generates summaries, rationales, and
    detects AI-assisted override conditions O1, O3, and O5 from
    should_report=True IncidentBundles using DSPy typed signatures.
    """

    BATCH_SIZE: int = 10

    def __init__(self, provider: AIProvider | None = None) -> None:
        """Initialise the ClassifierAgent with an optional AI provider.

        Args:
            provider: An AIProvider for making chat calls. If None, bundles
                are returned unchanged (useful for testing).
        """
        self._provider = provider

    def enrich(self, bundles: list[IncidentBundle]) -> list[IncidentBundle]:
        """Process reportable bundles in batches, generating summaries and
        detecting O1/O3/O5 override flags via AI.

        Args:
            bundles: List of IncidentBundles with should_report=True.

        Returns:
            The same list of bundles, some now with ai_enriched=True (if
            enrichment succeeded) or enrichment_failed=True (if not).
        """
        for i in range(0, len(bundles), self.BATCH_SIZE):
            batch = bundles[i : i + self.BATCH_SIZE]
            self._process_batch(batch)
        return bundles

    def _process_batch(self, batch: list[IncidentBundle]) -> None:
        """Process one batch of up to BATCH_SIZE bundles.

        Calls the AI provider once for the batch. If the AI response provides
        fewer results than bundles, the remaining bundles are marked
        enrichment_failed. If the call raises, any bundles not yet enriched
        are marked enrichment_failed.
        """
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
        """Make the AI call for a batch and apply results to each bundle.

        Args:
            batch: Up to BATCH_SIZE bundles to process.

        Raises:
            Any exception from the AI provider — caught by _process_batch.
        """
        if not self._provider:
            return
        prompt = self._build_batch_prompt(batch)
        response = self._provider.chat(prompt, model="classifier-v1")
        results: list[dict[str, Any]] = json.loads(response)
        for bundle, data in zip(batch, results):
            self._apply_enrichment(bundle, data)
        # Mark remaining bundles as failed if partial result
        for bundle in batch[len(results):]:
            bundle.enrichment_failed = True

    def _build_batch_prompt(self, batch: list[IncidentBundle]) -> str:
        """Build a prompt from all raw records in all bundles of the batch.

        Args:
            batch: Bundles to include in the prompt.

        Returns:
            A prompt string containing all raw record data for the batch.
        """
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
            parts.append(f"\nIncident {idx + 1} (ID: {bundle.incident_id}):")
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
        bundle: IncidentBundle, data: dict[str, Any]
    ) -> None:
        """Apply AI-classified fields and override flags to a bundle.

        Args:
            bundle: The IncidentBundle to enrich in place.
            data: Parsed JSON object with summary, rationale, and
                override flags.
        """
        bundle.summary = data.get("summary")
        bundle.rationale = data.get("rationale")
        bundle.ai_enriched = True

        if data.get("override_humanitarian_crisis"):
            bundle.overrides.append("O1")
        if data.get("override_likely_development"):
            bundle.overrides.append("O3")
        if data.get("override_forecast_warning"):
            bundle.overrides.append("O5")
