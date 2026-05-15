from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from disaster_surveillance_reporter.ai.provider import AIProvider
    from disaster_surveillance_reporter.types import IncidentBundle

import json
from typing import Any


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
        raise NotImplementedError
