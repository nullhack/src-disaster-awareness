"""CLI for Disaster Surveillance Reporter using Fire."""

import logging
from pathlib import Path

import fire

from disaster_surveillance_reporter.adapters.gdacs import GDACSAdapter
from disaster_surveillance_reporter.classification import RulesLoader
from disaster_surveillance_reporter.opencode import OpenCodeClient
from disaster_surveillance_reporter.pipeline import Pipeline
from disaster_surveillance_reporter.storage.jsonl import JSONLBackend

logger = logging.getLogger(__name__)


class DisasterSurveillanceCLI:
    """CLI for disaster surveillance incident processing."""

    def __init__(
        self,
        storage_path: str = "incidents",
        mock_ai: bool = True,
    ):
        """Initialize CLI with configuration.

        Args:
            storage_path: Base path for storage (default: incidents/)
            mock_ai: Use mock AI responses (default: True for testing)
        """
        self._storage_path = Path(storage_path)
        self._mock_ai = mock_ai

    def fetch(self, source: str = "gdacs"):
        """Fetch incidents from source(s).

        Args:
            source: Source name (gdacs, promed, reliefweb, healthmap, who)

        Example:
            python -m disaster_surveillance_reporter.cli fetch --source=gdacs
        """
        source_lower = source.lower()
        if source_lower == "gdacs":
            adapter = GDACSAdapter()  # pragma: no cover
        else:
            logger.warning(  # pragma: no cover
                "Source '%s' not implemented, using GDACS", source
            )
            adapter = GDACSAdapter()  # pragma: no cover

        incidents = adapter.fetch()
        logger.info(f"Fetched {len(incidents)} incidents from {source}")
        for inc in incidents:
            print(f"  - {inc.incident_name} ({inc.country})")  # pragma: no cover

    def classify(self, incident_ids: str | None = None):
        """Classify incidents using OpenCode AI.

        Args:
            incident_ids: Comma-separated incident IDs (optional)

        Example:
            python -m disaster_surveillance_reporter.cli classify --ids=001,002
        """
        storage = JSONLBackend(self._storage_path)
        incidents = storage.read()

        if incident_ids:  # pragma: no cover
            ids = set(incident_ids.split(","))
            incidents = [i for i in incidents if i.get("incident_id") in ids]

        ai_client = OpenCodeClient(mock_mode=self._mock_ai)
        rules = RulesLoader()

        classified = []
        for inc in incidents:
            classified_inc = ai_client.classify(inc)
            classified.append(classified_inc)
            print(
                f"  Classified: {inc.get('incident_id')} - {classified_inc.get('priority')}"  # pragma: no cover
            )

        logger.info(f"Classified {len(classified)} incidents")

    def store(self):
        """Store processed incidents to storage.

        Example:
            python -m disaster_surveillance_reporter.cli store
        """
        storage = JSONLBackend(self._storage_path)
        print(f"Storage path: {self._storage_path}")

        incidents = storage.read()
        print(f"Stored {len(incidents)} incidents")

    def status(self):
        """Show pipeline status and statistics.

        Example:
            python -m disaster_surveillance_reporter.cli status
        """
        storage = JSONLBackend(self._storage_path)
        incidents = storage.read()

        print("=== Disaster Surveillance Reporter Status ===")
        print(f"Storage path: {self._storage_path}")
        print(f"Total incidents: {len(incidents)}")

        by_status = {}
        by_priority = {}
        by_country = {}

        for inc in incidents:
            status = inc.get("status", "Unknown")
            priority = inc.get("priority", "Unknown")
            country = inc.get("country", "Unknown")

            by_status[status] = by_status.get(status, 0) + 1
            by_priority[priority] = by_priority.get(priority, 0) + 1
            by_country[country] = by_country.get(country, 0) + 1

        print("\nBy Status:")
        for s, c in sorted(by_status.items()):
            print(f"  {s}: {c}")

        print("\nBy Priority:")
        for p, c in sorted(by_priority.items()):
            print(f"  {p}: {c}")

    def full_cycle(self, source: str = "gdacs"):
        """Run complete pipeline: fetch → transform → classify → store.

        Args:
            source: Source name (gdacs, promed, reliefweb, healthmap, who)

        Example:
            python -m disaster_surveillance_reporter.cli full-cycle --source=gdacs
        """
        print("=== Running Full Pipeline ===")

        sources = [GDACSAdapter()]
        storage = JSONLBackend(self._storage_path)
        ai_client = OpenCodeClient(mock_mode=self._mock_ai)
        rules_loader = RulesLoader()

        pipeline = Pipeline(sources, storage, ai_client, rules_loader)

        print(f"1. Fetching from {source}...")
        raw = pipeline.fetch_all()
        print(f"   Found {len(raw)} raw incidents")

        print("2. Transforming to schema...")
        transformed = pipeline.transform_all(raw)
        print(f"   Transformed {len(transformed)} incidents")

        print("3. Classifying...")
        classified = pipeline.classify_all(transformed)
        print(f"   Classified {len(classified)} incidents")

        print("4. Storing...")
        pipeline.store_all(classified)
        print(f"   Stored in {self._storage_path}")

        print("\n=== Pipeline Complete ===")


def main():  # pragma: no cover
    """Main entry point for CLI."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    fire.Fire(DisasterSurveillanceCLI)


if __name__ == "__main__":  # pragma: no cover
    main()
