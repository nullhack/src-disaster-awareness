"""
Disaster Awareness Monitoring CLI.

Automates fetching, processing, and storing disaster incident data.
Uses subprocess to call opencode CLI directly.
"""

import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

import fire


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


STAGING_DIR = Path("incidents/staging")
STAGING_INCIDENTS = STAGING_DIR / "incidents.jsonl"
STAGING_MEDIA = STAGING_DIR / "media.jsonl"
DEFAULT_MODEL = "opencode/minimax-m2.5-free"


class DisasterMonitor:
    """CLI for Disaster Awareness Monitoring."""

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        verbose: bool = False,
        timeout: int = 1800,
    ):
        self.model = model
        self.verbose = verbose
        self.timeout = timeout
        if verbose:
            logging.getLogger().setLevel(logging.DEBUG)

    def _ensure_staging_dir(self) -> None:
        """Ensure staging directory exists."""
        STAGING_DIR.mkdir(parents=True, exist_ok=True)

    def _run_opencode(self, prompt: str, timeout: Optional[int] = None) -> str:
        """Execute opencode with given prompt using subprocess.

        Args:
            prompt: The prompt to send to opencode
            timeout: Maximum execution time in seconds (uses instance default if None)
        """
        if timeout is None:
            timeout = self.timeout
        logger.debug(f"Running opencode with model: {self.model}, timeout: {timeout}s")

        cmd = ["opencode", "run", "--model", self.model, prompt]
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            logger.error(f"opencode timed out after {timeout} seconds")
            raise RuntimeError(f"opencode execution timed out after {timeout} seconds")

        if result.returncode != 0:
            logger.error(f"opencode failed: {result.stderr}")
            raise RuntimeError(f"opencode failed: {result.stderr}")

        logger.debug(f"Opencode output: {result.stdout}")
        return result.stdout

    def _check_staging(self) -> dict[str, Any]:
        """Check what's currently in staging."""
        incidents_count = 0
        media_count = 0

        if STAGING_INCIDENTS.exists():
            with open(STAGING_INCIDENTS) as f:
                incidents_count = sum(1 for line in f if line.strip())

        if STAGING_MEDIA.exists():
            with open(STAGING_MEDIA) as f:
                media_count = sum(1 for line in f if line.strip())

        return {
            "incidents_count": incidents_count,
            "media_count": media_count,
            "has_data": incidents_count > 0 or media_count > 0,
        }

    def fetch_disaster(self) -> dict[str, Any]:
        """Fetch disaster incidents from all 5 data sources."""
        logger.info(
            "Fetching disaster incidents from GDACS, ProMED, ReliefWeb, HealthMap, WHO"
        )

        self._ensure_staging_dir()

        prompt = f"""Use @disaster-incident-reporter to check these 5 data sources:
- GDACS (https://www.gdacs.org/)
- ProMED (https://www.promedmail.org/)
- ReliefWeb (https://reliefweb.int/)
- HealthMap (https://www.healthmap.org/)
- WHO (https://www.who.int/emergencies/)

After finding incidents, use @skill incident-classifier to classify them by country group (A/B/C), severity level (1-4), and priority (HIGH/MEDIUM/LOW). Then write all incidents to {STAGING_INCIDENTS} in JSONL format. Report the number of incidents written."""

        try:
            self._run_opencode(prompt)
        except Exception as e:
            logger.error(f"Failed to fetch disasters: {e}")
            if "timed out" in str(e):
                logger.warning(
                    f"Consider increasing timeout (current: {self.timeout}s) for disaster monitoring"
                )
            return {"success": False, "error": str(e)}

        staging = self._check_staging()
        return {
            "success": True,
            "incidents_count": staging["incidents_count"],
        }

    def fetch_media(self) -> dict[str, Any]:
        """Fetch media coverage from news sources."""
        logger.info("Fetching media coverage from news sources")

        self._ensure_staging_dir()

        prompt = f"""Use @media-incident-reporter to scan news sources for disaster coverage:
- Tier 1: Reuters, AP, BBC, AFP, Al Jazeera
- Tier 2: Channel NewsAsia, Straits Times, The Star
- Tier 3: ReliefWeb, Devex

Focus on Singapore/SRC mentions, donation concerns, and misinformation. Write all media coverage to {STAGING_MEDIA} in JSONL format. Report the number of articles written."""

        try:
            self._run_opencode(prompt)
        except Exception as e:
            logger.error(f"Failed to fetch media: {e}")
            if "timed out" in str(e):
                logger.warning(
                    f"Consider increasing timeout (current: {self.timeout}s) for media monitoring"
                )
            return {"success": False, "error": str(e)}

        staging = self._check_staging()
        return {
            "success": True,
            "media_count": staging["media_count"],
        }

    def store(self) -> dict[str, Any]:
        """Process staging data and store to final locations."""
        logger.info("Processing staging data and storing to final locations")

        staging = self._check_staging()
        if not staging["has_data"]:
            logger.info("No data in staging to process")
            return {"success": True, "message": "No data to process"}

        prompt = f"""Use @data-engineer to process data from staging:
- Read from {STAGING_INCIDENTS}
- Read from {STAGING_MEDIA}
- Validate against @skill data-schema
- Deduplicate against existing incidents
- Transform and store to final locations:
  - incidents/by-date/[YYYY-MM-DD]/
  - incidents/by-country-group/[A|B|C]/[YYYY-MM]/
  - incidents/by-incident-type/[type]/[status]/
  - incidents/by-country/[country]/
- Update indices and metadata
- Clear staging files after successful processing

Report: number of incidents stored, duplicates skipped, any errors."""

        try:
            self._run_opencode(prompt)
        except Exception as e:
            logger.error(f"Failed to store data: {e}")
            if "timed out" in str(e):
                logger.warning(
                    f"Consider increasing timeout (current: {self.timeout}s) for data storage"
                )
            return {"success": False, "error": str(e)}

        staging_after = self._check_staging()
        return {
            "success": True,
            "incidents_processed": staging["incidents_count"]
            - staging_after["incidents_count"],
            "media_processed": staging["media_count"] - staging_after["media_count"],
        }

    def full_cycle(self) -> dict[str, Any]:
        """Run complete monitoring cycle."""
        logger.info("Starting full monitoring cycle")

        result = self.fetch_disaster()
        if not result.get("success"):
            return result

        result_media = self.fetch_media()
        if not result_media.get("success"):
            logger.warning("Media fetch failed, continuing with disasters")

        result_store = self.store()
        return {
            "success": result_store.get("success", False),
            "disasters_fetched": result.get("incidents_count", 0),
            "media_fetched": result_media.get("media_count", 0),
            "stored": result_store.get("incidents_processed", 0),
        }

    def status(self) -> dict[str, Any]:
        """Check current status."""
        logger.info("Checking status")
        staging = self._check_staging()
        logger.info(
            f"Staging - Incidents: {staging['incidents_count']}, "
            f"Media: {staging['media_count']}"
        )
        return staging


def main():
    """CLI entry point."""
    fire.Fire(DisasterMonitor)


if __name__ == "__main__":
    main()
