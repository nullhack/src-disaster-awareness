"""JSONL storage backend implementation."""

import json
from datetime import datetime, timezone
from pathlib import Path

from disaster_surveillance_reporter.storage import StorageBackend


class JSONLBackend(StorageBackend):
    """JSONL (JSON Lines) storage backend with date-based subfolder organization."""

    def __init__(
        self,
        base_path: Path,
        date: datetime | None = None,
    ):
        self._base_path = base_path
        self._date = date or datetime.now(timezone.utc)
        self._filename = "incidents.jsonl"

    @property
    def _current_path(self) -> Path:
        date_str = self._date.strftime("%Y-%m-%d")
        return self._base_path / date_str / self._filename

    def write(self, incidents: list[dict]) -> None:
        """Write incidents to JSONL file, replacing existing content."""
        self._current_path.parent.mkdir(parents=True, exist_ok=True)
        with self._current_path.open("w") as f:
            f.writelines(json.dumps(incident) + "\n" for incident in incidents)

    def read(self) -> list[dict]:
        """Read all incidents from JSONL file."""
        if not self._current_path.exists():
            return []
        with self._current_path.open("r") as f:
            return [json.loads(line) for line in f if line.strip()]

    def append(self, incidents: list[dict]) -> None:
        """Append incidents to JSONL file."""
        self._current_path.parent.mkdir(parents=True, exist_ok=True)
        with self._current_path.open("a") as f:
            f.writelines(json.dumps(incident) + "\n" for incident in incidents)
