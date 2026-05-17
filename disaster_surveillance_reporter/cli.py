"""CLI entry point for the Disaster Surveillance Reporter pipeline."""

from __future__ import annotations

import argparse
import os
from collections.abc import Callable

from disaster_surveillance_reporter.adapters import SourceAdapter
from disaster_surveillance_reporter.adapters.eonet import EONETAdapter
from disaster_surveillance_reporter.adapters.gdacs import GDACSAdapter
from disaster_surveillance_reporter.adapters.gdelt import GDELTAdapter
from disaster_surveillance_reporter.adapters.news import NewsSearcher
from disaster_surveillance_reporter.adapters.who import WHOAdapter
from disaster_surveillance_reporter.ai.classifier import ClassifierAgent
from disaster_surveillance_reporter.ai.extractor import ExtractorAgent
from disaster_surveillance_reporter.ai.provider import get_provider
from disaster_surveillance_reporter.classification.classify import ClassifyEngine
from disaster_surveillance_reporter.correlation.correlate import Correlator
from disaster_surveillance_reporter.pipeline import Pipeline
from disaster_surveillance_reporter.storage import get_storage_backend

_ADAPTER_REGISTRY: dict[str, Callable[[], SourceAdapter]] = {
    "gdacs": GDACSAdapter,
    "who": WHOAdapter,
    "eonet": EONETAdapter,
    "gdelt": GDELTAdapter,
}


def _build_adapters(sources: str) -> list[SourceAdapter]:
    names = [s.strip().lower() for s in sources.split(",") if s.strip()]
    adapters: list[SourceAdapter] = []
    for name in names:
        factory = _ADAPTER_REGISTRY.get(name)
        if factory is None:
            print(f"Warning: unknown source '{name}' — skipping")
            continue
        adapters.append(factory())
    return adapters


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Disaster Surveillance Reporter"
    )
    parser.add_argument(
        "command",
        choices=["pipeline"],
        help="Command: pipeline",
    )
    parser.add_argument(
        "--sources",
        default=os.environ.get("DSR_SOURCES", "gdacs,who,eonet"),
        help=(
            "Comma-separated source list: gdacs,who,eonet,gdelt "
            "(env: DSR_SOURCES, default: gdacs,who,eonet)"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default=os.environ.get("DSR_OUTPUT_DIR", "incidents"),
        help="Output directory (env: DSR_OUTPUT_DIR, default: incidents)",
    )
    parser.add_argument(
        "--ai-provider",
        default=os.environ.get("DSR_AI_PROVIDER", "none"),
        help=(
            "AI provider: ollama, opencode, gemini, openai, none "
            "(env: DSR_AI_PROVIDER, default: none)"
        ),
    )
    args = parser.parse_args()

    if args.command == "pipeline":
        os.environ.setdefault("DSR_AI_PROVIDER", args.ai_provider)
        provider = get_provider()
        extractor = ExtractorAgent(provider)
        classifier = ClassifierAgent(provider)
        pipeline = Pipeline(
            adapters=_build_adapters(args.sources),
            correlator=Correlator(),
            classify_engine=ClassifyEngine(),
            news_searcher=NewsSearcher(),
            extractor=extractor,
            classifier=classifier,
            storage_backend=get_storage_backend(args.output_dir),
        )
        result = pipeline.run()
        print(f"\n{result} bundles stored.")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
