from __future__ import annotations

from dataclasses import dataclass

from disaster_report.sources.ddg_news import DdgNewsAdapter
from disaster_report.sources.gdacs import GDACSAdapter
from disaster_report.sources.healthmap import HealthMapAdapter
from disaster_report.sources.usgs import UsgsAdapter
from disaster_report.sources.who import WHODiseaseOutbreakAdapter


@dataclass(frozen=True)
class SourceSpec:
    """Single-source-of-truth descriptor for a configured adapter.

    The CLI derives its adapter registries from :data:`SOURCE_REGISTRY`
    (filtered by ``source_type``); the store derives its ``DimSource`` seed
    rows and its tier-lookup tokens from it. Adding a source is one entry
    here instead of edits across three lookup tables.
    """

    token: str
    display_name: str
    source_type: str  # "feed" produces RawIncident; "news" produces RawArticle via search()
    reliability_tier: str  # "A" authoritative, "B" secondary, "C" on-demand
    data_freshness: str
    adapter_cls: type


SOURCE_REGISTRY: dict[str, SourceSpec] = {
    "usgs": SourceSpec(
        token="usgs",
        display_name="USGS Earthquakes",
        source_type="feed",
        reliability_tier="A",
        data_freshness="near-real-time",
        adapter_cls=UsgsAdapter,
    ),
    "gdacs": SourceSpec(
        token="gdacs",
        display_name="GDACS",
        source_type="feed",
        reliability_tier="A",
        data_freshness="daily",
        adapter_cls=GDACSAdapter,
    ),
    "who": SourceSpec(
        token="who",
        display_name="WHO Disease Outbreak News",
        source_type="feed",
        reliability_tier="A",
        data_freshness="daily",
        adapter_cls=WHODiseaseOutbreakAdapter,
    ),
    "healthmap": SourceSpec(
        token="healthmap",
        display_name="HealthMap",
        source_type="feed",
        reliability_tier="B",
        data_freshness="near-real-time",
        adapter_cls=HealthMapAdapter,
    ),
    # display_name "DDG" matches the seeded DimSource.name; the adapter's own
    # source_name ("DuckDuckGo News") is what flows through RawArticle at
    # runtime. They intentionally differ (news adapter, not a feed).
    "ddg": SourceSpec(
        token="ddg",
        display_name="DDG",
        source_type="news",
        reliability_tier="C",
        data_freshness="on-demand",
        adapter_cls=DdgNewsAdapter,
    ),
}
