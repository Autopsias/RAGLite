#!/usr/bin/env python3
"""Ingest PDF document for accuracy validation in CI.

This script ingests the standard validation PDF used for ground truth
accuracy testing. Used when cached data is not available.

Usage:
    python scripts/ingest-for-validation.py
"""

import asyncio
import logging
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from raglite.ingestion.document_ingestion import ingest_document  # noqa: E402
from raglite.shared.config import settings  # noqa: E402
from raglite.shared.logging import get_logger  # noqa: E402

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = get_logger(__name__)

# Standard validation PDF path
VALIDATION_PDF = Path("docs/sample pdf/2025-08 Performance Review CONSO_v2.pdf")


async def ingest_validation_document() -> None:
    """Ingest the standard validation PDF document.

    This PDF is used for ground truth accuracy validation and contains
    160 pages of financial data.
    """
    if not VALIDATION_PDF.exists():
        logger.error(f"Validation PDF not found: {VALIDATION_PDF}")
        logger.error("Expected path: docs/sample pdf/2025-08 Performance Review CONSO_v2.pdf")
        sys.exit(1)

    logger.info("=" * 60)
    logger.info("VALIDATION DOCUMENT INGESTION")
    logger.info("=" * 60)
    logger.info(f"Document: {VALIDATION_PDF.name}")
    logger.info(f"Path: {VALIDATION_PDF}")
    logger.info(f"Size: {VALIDATION_PDF.stat().st_size / 1024 / 1024:.2f} MB")
    logger.info("")
    logger.info("Configuration:")
    logger.info(f"  Qdrant: {settings.qdrant_host}:{settings.qdrant_port}")
    logger.info(
        f"  PostgreSQL: {settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
    )
    logger.info(f"  Collection: {settings.qdrant_collection_name}")
    logger.info("")
    logger.info("Starting ingestion (this may take 13-15 minutes)...")
    logger.info("")

    start_time = time.time()

    try:
        metadata = await ingest_document(str(VALIDATION_PDF))
        elapsed = time.time() - start_time

        logger.info("")
        logger.info("=" * 60)
        logger.info("INGESTION COMPLETE")
        logger.info("=" * 60)
        logger.info(f"✅ Successfully ingested: {metadata.filename}")
        logger.info(f"   Document ID: {metadata.document_id}")
        logger.info(f"   Pages: {metadata.page_count}")
        logger.info(f"   Chunks: {metadata.chunk_count}")
        logger.info(f"   Tables: {getattr(metadata, 'table_count', 'N/A')}")
        logger.info(f"   Duration: {elapsed:.1f}s ({elapsed / 60:.1f} minutes)")
        logger.info("")
        logger.info("Document is now ready for accuracy validation.")

    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"❌ Ingestion failed after {elapsed:.1f}s: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


def main() -> int:
    """Main entry point."""
    try:
        asyncio.run(ingest_validation_document())
        return 0
    except KeyboardInterrupt:
        logger.warning("Ingestion interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
