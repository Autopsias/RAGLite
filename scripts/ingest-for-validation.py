#!/usr/bin/env python3
"""Ingest PDF document for accuracy validation in CI.

This script ingests the standard validation PDF used for ground truth
accuracy testing. Used when cached data is not available.

Usage:
    python scripts/ingest-for-validation.py
"""

import asyncio
import logging
import os
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


async def validate_infrastructure() -> None:
    """Pre-flight validation of required infrastructure.

    Checks:
    - MISTRAL_API_KEY (warns if missing, doesn't fail)
    - Qdrant connectivity (fails if unavailable)
    - PostgreSQL connectivity (fails if unavailable)

    Retries database connections up to 3 times with 5s backoff.

    Raises:
        SystemExit: If critical infrastructure is unavailable after retries.
    """
    logger.info("=" * 60)
    logger.info("PRE-FLIGHT VALIDATION")
    logger.info("=" * 60)

    # Check MISTRAL_API_KEY (non-critical - metadata extraction will be skipped if missing)
    mistral_key = os.getenv("MISTRAL_API_KEY")
    if mistral_key:
        logger.info("✅ MISTRAL_API_KEY: configured (metadata extraction enabled)")
    else:
        logger.warning("⚠️  MISTRAL_API_KEY: not set (metadata extraction will be skipped)")

    # Check Qdrant connectivity with retries
    max_retries = 3
    retry_delay = 5

    for attempt in range(1, max_retries + 1):
        try:
            from qdrant_client import QdrantClient

            qdrant = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port, timeout=10)
            # Simple ping to verify connectivity
            qdrant.get_collections()
            logger.info(f"✅ Qdrant: connected at {settings.qdrant_host}:{settings.qdrant_port}")
            break
        except Exception as e:
            if attempt < max_retries:
                logger.warning(f"⚠️  Qdrant connection attempt {attempt}/{max_retries} failed: {e}")
                logger.info(f"   Retrying in {retry_delay}s...")
                await asyncio.sleep(retry_delay)
            else:
                logger.error(f"❌ Qdrant: connection failed after {max_retries} attempts")
                logger.error(f"   Host: {settings.qdrant_host}:{settings.qdrant_port}")
                logger.error(f"   Error: {e}")
                logger.error("")
                logger.error("RESOLUTION:")
                logger.error("  1. Ensure Qdrant container is running: docker ps | grep qdrant")
                logger.error("  2. Check correct port mapping in docker-compose.yml")
                logger.error("  3. Verify APP_ENV is set correctly (test vs production)")
                sys.exit(1)

    # Check PostgreSQL connectivity with retries
    for attempt in range(1, max_retries + 1):
        try:
            import psycopg2

            conn = psycopg2.connect(
                host=settings.postgres_host,
                port=settings.postgres_port,
                database=settings.postgres_db,
                user=settings.postgres_user,
                password=settings.postgres_password,
                connect_timeout=10,
            )
            conn.close()
            logger.info(
                f"✅ PostgreSQL: connected at {settings.postgres_host}:{settings.postgres_port}"
            )
            break
        except Exception as e:
            if attempt < max_retries:
                logger.warning(
                    f"⚠️  PostgreSQL connection attempt {attempt}/{max_retries} failed: {e}"
                )
                logger.info(f"   Retrying in {retry_delay}s...")
                await asyncio.sleep(retry_delay)
            else:
                logger.error(f"❌ PostgreSQL: connection failed after {max_retries} attempts")
                host = settings.postgres_host
                port = settings.postgres_port
                db = settings.postgres_db
                logger.error(f"   Host: {host}:{port}/{db}")
                logger.error(f"   Error: {e}")
                logger.error("")
                logger.error("RESOLUTION:")
                logger.error("  1. Ensure PostgreSQL is running: docker ps | grep postgres")
                logger.error("  2. Check correct port mapping in docker-compose.yml")
                logger.error("  3. Verify APP_ENV is set correctly (test vs production)")
                sys.exit(1)

    logger.info("=" * 60)
    logger.info("PRE-FLIGHT COMPLETE - All systems ready")
    logger.info("=" * 60)
    logger.info("")


async def ingest_validation_document() -> None:
    """Ingest the standard validation PDF document.

    This PDF is used for ground truth accuracy validation and contains
    160 pages of financial data.
    """
    if not VALIDATION_PDF.exists():
        logger.error(f"Validation PDF not found: {VALIDATION_PDF}")
        logger.error("Expected path: docs/sample pdf/2025-08 Performance Review CONSO_v2.pdf")
        sys.exit(1)

    # Run pre-flight validation before attempting expensive ingestion
    await validate_infrastructure()

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
