"""OpenCode client for AI-powered transformation and classification.

This module provides the client for calling OpenCode CLI with minimax-m2.5-free model
to transform raw incidents to schema format and classify them.
"""

import json
import subprocess
from typing import Any


class OpenCodeClient:
    """Client for OpenCode CLI with multiple model support and fallback."""

    # Available models in order of preference
    AVAILABLE_MODELS = [
        "opencode/nemotron-3-super-free",
        "opencode/minimax-m2.5-free",
    ]

    def __init__(self, mock_mode: bool = False):
        self._mock_mode = mock_mode
        self._model_index = 0  # Start with first model
        self._model = self.AVAILABLE_MODELS[self._model_index]

    def _get_next_available_model(self) -> str | None:
        """Get the next available model from AVAILABLE_MODELS.
        In a real implementation, this would check if the model is accessible.
        For now, we just move to the next model in the list.
        """
        # TODO: Implement actual model availability checking
        # For now, just move to next model in list (circular)
        self._model_index = (self._model_index + 1) % len(self.AVAILABLE_MODELS)
        return self.AVAILABLE_MODELS[self._model_index]

    def _switch_to_fallback_model(self) -> bool:
        """Switch to the next fallback model if current model fails.
        Returns True if switched, False if no more models available.
        """
        next_model = self._get_next_available_model()
        if next_model is not None:
            self._model = next_model
            return True
        return False

    @property
    def model(self) -> str:
        return self._model

    def transform(self, raw_incident: dict[str, Any]) -> dict[str, Any]:
        """Transform raw incident to schema-compliant format."""
        if self._mock_mode:
            return self._mock_transform(raw_incident)
        return self._real_transform(raw_incident)

    def classify(self, incident: dict[str, Any]) -> dict[str, Any]:
        """Classify incident using OpenCode CLI."""
        if self._mock_mode:
            return self._mock_classify(incident)
        return self._real_classify(incident)

    def _mock_transform(self, raw_incident: dict[str, Any]) -> dict[str, Any]:
        """Mock transformation returning sample schema."""
        country_code = raw_incident.get("country", "XX")[:2].upper()
        raw_fields = raw_incident.get("raw_fields", {})

        # Generate summary - never null
        summary = self._generate_summary(raw_incident, raw_fields)

        # Build sources list
        sources = self._build_sources_list(raw_incident)

        return {
            "incident_id": f"20260312-{country_code}-TC",
            "incident_name": raw_incident.get("incident_name", "Unknown"),
            "summary": summary,
            "estimated_affected": raw_fields.get("felt") or raw_fields.get("affected"),
            "estimated_deaths": raw_fields.get("deaths")
            or raw_fields.get("casualties"),
            "created_date": raw_incident.get("report_date", "2026-03-12T00:00:00Z"),
            "updated_date": raw_incident.get("report_date", "2026-03-12T00:00:00Z"),
            "status": "Active",
            "country": raw_incident.get("country", "Unknown"),
            "country_group": "B",
            "incident_type": raw_incident.get("disaster_type", "Unknown"),
            "incident_level": 2,
            "priority": "MEDIUM",
            "should_report": True,
            "sources": sources,
            "classification": {
                "country": raw_incident.get("country", "Unknown"),
                "country_group": "B",
                "region": "Southeast Asia",
                "incident_type": raw_incident.get("disaster_type", "Unknown"),
                "incident_level": 2,
                "priority": "MEDIUM",
                "should_report": True,
            },
            "classification_metadata": {
                "classified_by": "opencode-mock",
                "classified_date": raw_incident.get(
                    "report_date", "2026-03-12T00:00:00Z"
                ),
                "classification_confidence": 0.95,
                "rationale": "Mock classification",
                "special_flags": [],
            },
        }

    def _generate_summary(
        self, raw_incident: dict[str, Any], raw_fields: dict[str, Any]
    ) -> str:
        """Generate summary - from source data or code-based fallback."""
        # Priority 1: from raw_fields title
        if raw_fields.get("title"):
            return raw_fields["title"]

        # Priority 2: from explicit summary field
        if raw_incident.get("summary"):
            return raw_incident["summary"]

        # Priority 3: code-based fallback from incident fields
        return self._generate_fallback_summary(raw_incident)

    def _generate_fallback_summary(self, raw_incident: dict[str, Any]) -> str:
        """Generate summary from incident fields when no source data available."""
        parts = []

        disaster_type = raw_incident.get("disaster_type")
        incident_name = raw_incident.get("incident_name")
        country = raw_incident.get("country")

        if disaster_type:
            parts.append(disaster_type)

        if incident_name and incident_name != "Unknown":
            parts.append(f"in {incident_name}")

        if country and country != "Unknown":
            parts.append(f"in {country}")

        if not parts:
            return "Incident reported."

        return " ".join(parts) + "."

    def _build_sources_list(self, raw_incident: dict[str, Any]) -> list[dict[str, Any]]:
        """Build sources list from raw incident data."""
        source_name = raw_incident.get("source_name", "Unknown")
        source_url = raw_incident.get("source_url", "")
        report_date = raw_incident.get("report_date", "2026-03-12T00:00:00Z")

        source_type = self._infer_source_type(source_name)

        return [
            {
                "name": source_name,
                "type": source_type,
                "url": source_url,
                "accessed_date": report_date,
                "reliability_tier": self._get_reliability_tier(source_name),
                "data_freshness": "daily",
            }
        ]

    def _infer_source_type(self, source_name: str) -> str:
        """Infer source type from source name."""
        source_types = {
            "GDACS": "disaster-database",
            "USGS": "scientific-agency",
            "ProMED": "disease-database",
            "ReliefWeb": "humanitarian-database",
            "HealthMap": "disease-surveillance",
            "WHO": "health-authority",
        }
        return source_types.get(source_name, "other")

    def _get_reliability_tier(self, source_name: str) -> str:
        """Get reliability tier for source."""
        tier1_sources = ["GDACS", "USGS", "WHO", "ReliefWeb"]
        return "Tier1" if source_name in tier1_sources else "Tier2"

    def _mock_classify(self, incident: dict[str, Any]) -> dict[str, Any]:
        """Mock classification adding classification fields."""
        result = incident.copy()
        result["classification"] = {
            "country": incident.get("country", "Unknown"),
            "country_group": incident.get("country_group", "C"),
            "region": "Southeast Asia",
            "incident_type": incident.get("incident_type", "Unknown"),
            "incident_level": incident.get("incident_level", 2),
            "priority": incident.get("priority", "MEDIUM"),
            "should_report": incident.get("should_report", True),
        }
        result["classification_metadata"] = {
            "classified_by": "opencode-mock",
            "classified_date": "2026-03-12T00:00:00Z",
            "classification_confidence": 0.95,
            "rationale": "Mock classification",
            "special_flags": [],
        }
        return result

    def _real_transform(self, raw_incident: dict[str, Any]) -> dict[str, Any]:
        """Real implementation calling OpenCode CLI with automatic fallback."""
        last_error: Exception | None = None

        # Try each model in AVAILABLE_MODELS until one succeeds
        for _ in range(len(self.AVAILABLE_MODELS)):
            try:
                result = self._try_transform(raw_incident)
                if result is not None:
                    return result
            except Exception as e:
                last_error = e
                # Model failed, try the next one
                self._switch_to_fallback_model()

        # All models failed - raise exception with details
        raise RuntimeError(
            f"All {len(self.AVAILABLE_MODELS)} models failed. Last error: {last_error}"
        ) from last_error

    def _try_transform(self, raw_incident: dict[str, Any]) -> dict[str, Any] | None:
        """Try transformation with current model. Returns None on failure."""
        prompt = f"Transform to JSON: {json.dumps(raw_incident)}"
        result = subprocess.run(
            [
                "opencode",
                "run",
                prompt,
                "--model",
                self._model,
                "--format",
                "json",
                "--dangerously-skip-permissions",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )

        # Check for rate limit (429) or server errors (5xx)
        if result.returncode == 429 or (500 <= result.returncode < 600):
            raise RuntimeError(f"Model {self._model} returned {result.returncode}")

        if result.returncode == 0 and result.stdout:
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError:
                pass
        return None

    def _real_classify(self, incident: dict[str, Any]) -> dict[str, Any]:
        """Real implementation calling OpenCode CLI with automatic fallback."""
        last_error: Exception | None = None

        # Try each model in AVAILABLE_MODELS until one succeeds
        for _ in range(len(self.AVAILABLE_MODELS)):
            try:
                result = self._try_classify(incident)
                if result is not None:
                    return result
            except Exception as e:
                last_error = e
                # Model failed, try the next one
                self._switch_to_fallback_model()

        # All models failed - raise exception with details
        raise RuntimeError(
            f"All {len(self.AVAILABLE_MODELS)} models failed. Last error: {last_error}"
        ) from last_error

    def _try_classify(self, incident: dict[str, Any]) -> dict[str, Any] | None:
        """Try classification with current model. Returns None on failure."""
        prompt = f"Classify incident and add fields: {json.dumps(incident)}"
        result = subprocess.run(
            [
                "opencode",
                "run",
                prompt,
                "--model",
                self._model,
                "--format",
                "json",
                "--dangerously-skip-permissions",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )

        # Check for rate limit (429) or server errors (5xx)
        if result.returncode == 429 or (500 <= result.returncode < 600):
            raise RuntimeError(f"Model {self._model} returned {result.returncode}")

        if result.returncode == 0 and result.stdout:
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError:
                pass
        return None
