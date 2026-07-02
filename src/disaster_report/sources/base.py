from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    import httpx


@dataclass(frozen=True)
class RawIncident:
    source_name: str
    incident_name: str
    country: str
    incident_type: str
    report_date: str
    source_url: str
    raw_fields: dict[str, Any] = field(default_factory=dict)


class SourceAdapter(Protocol):
    source_name: str

    def fetch(self) -> list[RawIncident]: ...


@dataclass(frozen=True)
class RawArticle:
    source_name: str
    headline: str
    body: str
    url: str
    outlet: str
    published_date: str
    image: str = ""
    raw_fields: dict[str, Any] = field(default_factory=dict)


class NewsAdapter(Protocol):
    source_name: str

    def fetch(self) -> list[RawArticle]: ...

    def search(self, query: str, timelimit: str | None = None) -> list[RawArticle]: ...


# Sentinel ``source_name`` used when re-feeding a prior AI summary back into the
# digester (re-digest / retry paths) so the model sees the existing summary as a
# pseudo source report. Shared by the pipeline and the store.
PRIOR_DIGEST_SOURCE = "PRIOR_DIGEST"


def json_list(response: "httpx.Response", key: str) -> list:
    """Decode ``response`` and return ``json[key]`` as a list (default ``[]``).

    Collapses the repeated ``response.json().get(key, [])`` chain (Law of
    Demeter) across the JSON-backed source adapters (USGS / WHO / HealthMap).
    """
    value = response.json().get(key, [])
    return value if isinstance(value, list) else []
