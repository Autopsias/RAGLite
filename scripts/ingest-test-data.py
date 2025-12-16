#!/usr/bin/env python3
"""Ingest test PDF documents for test suite.

This script ingests the standard test PDFs used for integration testing.
Run this before using pytest --skip-ingestion.

Usage:
    # For test environment (default)
    python scripts/ingest-test-data.py

    # For production environment
    python scripts/ingest-test-data.py --env=production
"""

import argparse
import asyncio
import logging
import os
import sys
import time
from pathlib import Path

# Set environment from command line BEFORE any imports
if "--env=production" in sys.argv:
    os.environ["APP_ENV"] = "production"
else:
    os.environ["APP_ENV"] = "test"

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from raglite.ingestion.pipeline import ingest_pdf  # noqa: E402
from raglite.shared.config import settings  # noqa: E402
from raglite.shared.logging import get_logger  # noqa: E402

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = get_logger(__name__)

# Test PDF paths
TEST_PDF_10_PAGE = Path("tests/fixtures/sample_financial_report.pdf")
TEST_PDF_3_PAGE = Path("tests/fixtures/sample-small-3-pages.pdf")


async def ingest_test_document(pdf_path: Path, clear_existing: bool = True) -> None:
    """Ingest a test PDF document."""
    if not pdf_path.exists():
        logger.error(f"Test PDF not found: {pdf_path}")
        sys.exit(1)

    logger.info(f"Ingesting: {pdf_path.name}")
    logger.info(f"Path: {pdf_path}")
    logger.info(f"Size: {pdf_path.stat().st_size / 1024 / 1024:.2f} MB")

    start_time = time.time()
    try:
        result = await ingest_pdf(
            str(pdf_path),
            clear_existing=clear_existing,
            skip_metadata=True,  # Skip metadata for faster ingestion
        )
        duration = time.time() - start_time

        logger.info(f"✅ Ingestion complete in {duration:.1f}s")
        logger.info(f"   Pages: {result.page_count}")
        logger.info(f"   Chunks: {result.chunk_count}")

    except Exception as e:
        logger.error(f"❌ Ingestion failed: {e}")
        sys.exit(1)


async def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Ingest test PDF documents")
    parser.add_argument(
        "--env",
        choices=["test", "production"],
        default=os.environ.get("APP_ENV", "test"),
        help="Target environment (test: port 6335, production: port 6333)",
    )
    parser.add_argument(
        "--pdf",
        choices=["10-page", "3-page", "both"],
        default="10-page",
        help="Which PDF to ingest",
    )
    args = parser.parse_args()

    if args.env == "production":
        logger.info("🚨 PRODUCTION MODE: Will ingest to port 6333")
    else:
        logger.info("🧪 TEST MODE: Will ingest to port 6335")

    # Verify environment settings
    logger.info(f"Qdrant port: {settings.qdrant_port}")
    logger.info(f"PostgreSQL port: {settings.postgres_port}")
    logger.info(f"Collection: {settings.qdrant_collection_name}")

    # Ingest requested PDF(s)
    if args.pdf == "both":
        await ingest_test_document(TEST_PDF_10_PAGE, clear_existing=True)
        await ingest_test_document(TEST_PDF_3_PAGE, clear_existing=False)
    elif args.pdf == "3-page":
        await ingest_test_document(TEST_PDF_3_PAGE, clear_existing=True)
    else:  # default: 10-page
        await ingest_test_document(TEST_PDF_10_PAGE, clear_existing=True)

    logger.info("\n✅ Test data ingestion complete!")
    logger.info(f"Environment: {args.env}")
    logger.info(
        f"Qdrant collection: {settings.qdrant_collection_name} (port {settings.qdrant_port})"
    )
    logger.info("\nYou can now run tests with:")
    if args.env == "test":
        logger.info("  pytest --skip-ingestion")
    else:
        logger.info("  APP_ENV=production pytest --skip-ingestion")


if __name__ == "__main__":
    asyncio.run(main())
