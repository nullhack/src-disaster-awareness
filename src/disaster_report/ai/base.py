from __future__ import annotations

from typing import Any, Protocol


class AIDigester(Protocol):
    def digest(self, sources: str | list[dict[str, Any]]) -> dict[str, Any]: ...
