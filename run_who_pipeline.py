#!/usr/bin/env python
"""Run WHO source through pipeline and email report."""

import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from disaster_surveillance_reporter.adapters.gdacs import GDACSAdapter
from disaster_surveillance_reporter.classification import RulesLoader
from disaster_surveillance_reporter.opencode import OpenCodeClient
from disaster_surveillance_reporter.pipeline import Pipeline
from disaster_surveillance_reporter.storage.email_reporter import EmailReporter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def main():
    env_path = Path(__file__).parent / ".env"
    load_dotenv(env_path)

    logger.info("=== GDACS Disaster Surveillance Pipeline ===")
    logger.info("Step 1: Fetching from GDACS...")

    sources = [GDACSAdapter()]
    ai_client = OpenCodeClient(mock_mode=True)
    rules_loader = RulesLoader()

    pipeline = Pipeline(sources, None, ai_client, rules_loader)

    raw = pipeline.fetch_all()
    logger.info(f"  Fetched {len(raw)} raw incidents from WHO")

    logger.info("Step 2: Transforming to schema...")
    transformed = pipeline.transform_all(raw)
    logger.info(f"  Transformed {len(transformed)} incidents")

    logger.info("Step 3: Classifying...")
    classified = pipeline.classify_all(transformed)
    logger.info(f"  Classified {len(classified)} incidents")

    logger.info("Step 4: Sending email report...")

    sender = os.environ.get("GMAIL_EMAIL")
    password = os.environ.get("GMAIL_PASSWORD")
    recipient = os.environ.get("GMAIL_RECIPIENT")

    email_reporter = EmailReporter(sender, password, recipient)
    email_reporter.write(classified)

    logger.info(f"  Email sent to {recipient}")
    logger.info("=== Pipeline Complete ===")

    return 0


if __name__ == "__main__":
    sys.exit(main())
