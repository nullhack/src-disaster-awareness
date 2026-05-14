"""Deterministic classification engine for incident bundles.

Provides ClassifyEngine, the stateless service that classifies IncidentBundles
with country group assignment, source-level derivation (GDACS > WHO > GDELT),
priority matrix application, and two-phase override evaluation.
"""

from __future__ import annotations

from datetime import datetime, timezone

from disaster_surveillance_reporter.classification import RulesLoader
from disaster_surveillance_reporter.types import IncidentBundle, RawRecord


class ClassifyEngine:
    """Deterministic classification engine for incident bundles."""

    def classify(self, bundle: IncidentBundle) -> IncidentBundle:
        """Perform initial deterministic classification on a bundle."""
        rules = RulesLoader()

        # 1. Determine country group
        country_group = rules.get_country_group(bundle.country or "")

        # 2. Derive incident level from source records
        level = self._derive_level(bundle.records, country_group)

        # 3. Apply priority matrix
        priority = rules.get_priority(level, country_group)
        should_report = rules.should_report(level, country_group)

        # 4. Apply overrides (O2, O4, O6)
        overrides: list[str] = list(bundle.overrides or [])

        if self._check_o2(bundle.records):
            priority = "HIGH"
            should_report = True
            if "O2" not in overrides:
                overrides.append("O2")

        # O4: Environmental disaster in Group A
        if self._check_o4(bundle.disaster_type, country_group):
            priority = "HIGH"
            should_report = True
            if "O4" not in overrides:
                overrides.append("O4")

        # O6: Singapore/SRC/Red Cross
        if self._check_o6(bundle.records):
            priority = "HIGH"
            should_report = True
            if "O6" not in overrides:
                overrides.append("O6")

        # 5. Set timestamps (but NEVER regenerate incident_id)
        now = datetime.now(tz=timezone.utc)
        bundle.country_group = country_group
        bundle.incident_level = level
        bundle.priority = priority
        bundle.should_report = should_report
        bundle.overrides = overrides
        bundle.classified_at = now
        bundle.classification_date = now.date()

        return bundle

    def reevaluate_overrides(self, bundle: IncidentBundle) -> IncidentBundle:
        """Re-evaluate override flags after AI enrichment.

        Checks O1 (humanitarian_crisis), O3 (likely_development),
        and O5 (istemporary forecast).  O3 and O5 level bumps
        may compound (up to +2 total).
        """
        rules = RulesLoader()
        level = bundle.incident_level or 0
        country_group = bundle.country_group or "C"
        priority = bundle.priority or "LOW"
        should_report = bundle.should_report or False
        overrides: list[str] = list(bundle.overrides or [])

        # O1: Humanitarian Crisis
        for record in bundle.records:
            if record.raw_fields.get("humanitarian_crisis") is True:
                priority = "HIGH"
                should_report = True
                if "O1" not in overrides:
                    overrides.append("O1")
                break

        # O3: Likely Development (bump level, re-apply matrix)
        o3_applied = False
        for record in bundle.records:
            if record.raw_fields.get("likely_development") is True:
                level = min(level + 1, 4)
                o3_applied = True
                break

        if o3_applied:
            priority = rules.get_priority(level, country_group)
            should_report = True
            if "O3" not in overrides:
                overrides.append("O3")

        # O5: Forecast Early Warning (istemporary flag, bumps level)
        o5_applied = False
        for record in bundle.records:
            if record.source_name == "GDACS":
                istemp = record.raw_fields.get("istemporary")
                # Accept both boolean True and string "true"
                if istemp is True or istemp == "true":
                    level = min(level + 1, 4)
                    o5_applied = True
                    break

        if o5_applied:
            priority = rules.get_priority(level, country_group)
            should_report = True
            if "O5" not in overrides:
                overrides.append("O5")

        # Apply results (NEVER regenerate incident_id)
        bundle.incident_level = level
        bundle.priority = priority
        bundle.should_report = should_report
        bundle.overrides = overrides

        return bundle

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _derive_level(records: list[RawRecord], country_group: str) -> int:
        """Derive incident level from source records.

        Source reliability order: GDACS > WHO > GDELT.
        First source that provides level data wins.
        Defaults to level 2 if no source provides level data.
        """
        # GDACS
        for record in records:
            if record.source_name == "GDACS" and "alertlevel" in record.raw_fields:
                return ClassifyEngine._gdacs_level(
                    record.raw_fields["alertlevel"], country_group
                )

        # WHO
        for record in records:
            if record.source_name == "WHO":
                level = ClassifyEngine._who_level(record)
                if level is not None:
                    return level

        # GDELT
        for record in records:
            if record.source_name == "GDELT" and "title" in record.raw_fields:
                level = ClassifyEngine._gdelt_level(record)
                if level is not None:
                    return level

        return 2  # default

    @staticmethod
    def _gdacs_level(alert: str, country_group: str) -> int:
        base = {"Green": 1, "Orange": 3, "Red": 4}.get(alert, 2)
        # Group A severity bump: Green → 2, Orange → 4 (Red stays 4)
        if country_group == "A":
            if alert == "Green":
                return 2
            if alert == "Orange":
                return 4
        return base

    @staticmethod
    def _who_level(record: RawRecord) -> int | None:
        text = " ".join(
            str(v) for v in record.raw_fields.values() if isinstance(v, str)
        ).lower()
        if "pandemic" in text or "pheic" in text:
            return 4
        if "epidemic" in text or "widespread" in text:
            return 3
        if "cluster" in text or "cases reported" in text:
            return 2
        if "isolated case" in text:
            return 1
        return None  # signal "no level keyword" → default 2 later

    @staticmethod
    def _gdelt_level(record: RawRecord) -> int | None:
        title = record.raw_fields.get("title", "").lower()
        if (
            "devastating" in title
            or "hundreds dead" in title
            or "thousands displaced" in title
            or "pheic" in title
        ):
            return 4
        if (
            "major" in title
            or "catastrophic" in title
            or "deadly" in title
            or "massive" in title
        ):
            return 3
        if "minor" in title:
            return 1
        return None  # signal "no severity keyword" → default 2 later

    @staticmethod
    def _check_o2(records: list[RawRecord]) -> bool:
        for record in records:
            if record.source_name == "GDACS":
                affected = record.raw_fields.get("affectedcountries")
                if isinstance(affected, list) and len(affected) > 1:
                    return True
        return False

    @staticmethod
    def _check_o4(disaster_type: str | None, country_group: str) -> bool:
        return disaster_type in ("WF", "DR", "FL") and country_group == "A"

    @staticmethod
    def _check_o6(records: list[RawRecord]) -> bool:
        for record in records:
            text = " ".join(str(v) for v in record.raw_fields.values())
            if "Singapore" in text or "SRC" in text or "Red Cross" in text:
                return True
        return False
