"""CLI entry point for the Disaster Surveillance Reporter pipeline."""

import argparse
import os

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
        "--output-dir",
        default="incidents",
        help="Output directory (default: incidents)",
    )
    parser.add_argument(
        "--ai-provider",
        default=os.environ.get("DSR_AI_PROVIDER", "none"),
        help="AI provider: ollama, gemini, openai, none (env: DSR_AI_PROVIDER)",
    )
    args = parser.parse_args()

    if args.command == "pipeline":
        os.environ.setdefault("DSR_AI_PROVIDER", args.ai_provider)
        provider = get_provider()
        extractor = ExtractorAgent(provider)
        classifier = ClassifierAgent(provider)
        pipeline = Pipeline(
            adapters=[
                GDACSAdapter(),
                WHOAdapter(),
                GDELTAdapter(),
            ],
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
