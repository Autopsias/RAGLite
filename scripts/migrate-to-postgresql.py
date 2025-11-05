"""Migrate existing Qdrant chunks to PostgreSQL with metadata extraction.

This script performs a one-time migration of existing chunks from Qdrant to PostgreSQL,
extracting LLM metadata for each chunk and creating proper linkages.

Story 2.6 AC2 & AC3:
- AC2: LLM-extracted metadata stored in PostgreSQL (15 fields)
- AC3: 100% of chunks have PostgreSQL metadata records linked to Qdrant vectors

Usage:
    python scripts/migrate-to-postgresql.py [--dry-run] [--batch-size N]
"""

import asyncio
import logging
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

import psycopg2
import psycopg2.extras
from psycopg2.extras import execute_values

# Register UUID adapter for psycopg2
psycopg2.extras.register_uuid()

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from raglite.ingestion.pipeline import extract_chunk_metadata  # noqa: E402
from raglite.shared.clients import get_qdrant_client  # noqa: E402
from raglite.shared.config import Settings  # noqa: E402

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def migrate_chunks_to_postgresql(
    dry_run: bool = False, batch_size: int = 50
) -> tuple[int, int, int]:
    """Migrate chunks from Qdrant to PostgreSQL with metadata extraction.

    Args:
        dry_run: If True, simulate migration without writing to database
        batch_size: Number of chunks to process in each batch

    Returns:
        Tuple of (total_chunks, migrated_chunks, failed_chunks)
    """
    settings = Settings()

    # Validate Mistral API key
    if not settings.mistral_api_key:
        logger.error("MISTRAL_API_KEY not configured - metadata extraction requires API key")
        return (0, 0, 0)

    # Connect to Qdrant
    logger.info("Connecting to Qdrant")
    qdrant = get_qdrant_client()

    # Check if collection exists
    try:
        collection_info = qdrant.get_collection(settings.qdrant_collection_name)
        total_chunks = collection_info.points_count
        logger.info(
            f"Found {total_chunks} chunks in Qdrant collection '{settings.qdrant_collection_name}'"
        )
    except Exception as e:
        logger.error(f"Failed to access Qdrant collection: {e}")
        return (0, 0, 0)

    if total_chunks == 0:
        logger.warning("No chunks found in Qdrant - nothing to migrate")
        return (0, 0, 0)

    # Connect to PostgreSQL
    logger.info("Connecting to PostgreSQL")
    try:
        conn = psycopg2.connect(
            host=settings.postgres_host,
            port=settings.postgres_port,
            dbname=settings.postgres_db,
            user=settings.postgres_user,
            password=settings.postgres_password,
        )
        cursor = conn.cursor()
        logger.info("PostgreSQL connection established")
    except Exception as e:
        logger.error(f"Failed to connect to PostgreSQL: {e}")
        return (total_chunks, 0, 0)

    # Create Mistral client for metadata extraction (reuse across all chunks)
    from mistralai import Mistral

    mistral_client = Mistral(api_key=settings.mistral_api_key)
    logger.info("Mistral client initialized for metadata extraction")

    # Scroll through all chunks in Qdrant
    migrated_count = 0
    failed_count = 0
    offset = None

    logger.info(f"Starting migration (batch_size={batch_size}, dry_run={dry_run})")

    while True:
        # Fetch batch of chunks from Qdrant
        try:
            result = qdrant.scroll(
                collection_name=settings.qdrant_collection_name,
                limit=batch_size,
                offset=offset,
                with_payload=True,
                with_vectors=False,  # Don't need vectors for metadata extraction
            )
            points, next_offset = result

            if not points:
                break  # No more chunks

        except Exception as e:
            logger.error(f"Failed to fetch chunks from Qdrant: {e}")
            break

        # Process batch
        batch_records = []

        for point in points:
            chunk_id = str(point.id)
            payload = point.payload

            # Extract required fields from payload
            content = payload.get("text", "")
            document_id = payload.get("document_id", "")
            page_number = payload.get("page_number", 0)
            chunk_index = payload.get("chunk_index", 0)

            if not content:
                logger.warning(f"Chunk {chunk_id} has no content - skipping")
                failed_count += 1
                continue

            # Extract metadata using Mistral (with client pooling)
            try:
                logger.debug(f"Extracting metadata for chunk {chunk_id}")
                metadata = await extract_chunk_metadata(
                    text=content,
                    chunk_id=chunk_id,
                    client=mistral_client,  # Reuse shared client
                )

                # Prepare PostgreSQL record (matching ExtractedMetadata model fields)
                record = (
                    uuid.UUID(chunk_id) if chunk_id else uuid.uuid4(),
                    uuid.UUID(document_id) if document_id else uuid.uuid4(),
                    page_number,
                    chunk_index,
                    content,
                    # Document-Level Metadata (7 fields)
                    metadata.document_type,
                    metadata.reporting_period,
                    metadata.time_granularity,
                    metadata.company_name,
                    metadata.geographic_jurisdiction,
                    metadata.data_source_type,
                    metadata.version_date,
                    # Chunk/Section-Level Metadata (5 fields)
                    metadata.section_type,
                    metadata.metric_category,
                    metadata.units,
                    metadata.department_scope,
                    # Table-Specific Metadata (3 fields)
                    metadata.table_context,
                    metadata.table_name,
                    metadata.statistical_summary,
                    # Search optimization
                    None,  # content_tsv (will be generated by trigger)
                    chunk_id,  # embedding_id (link to Qdrant)
                    datetime.now(UTC),  # created_at (timezone-aware)
                    datetime.now(UTC),  # updated_at (timezone-aware)
                )
                batch_records.append(record)

            except Exception as e:
                logger.warning(f"Failed to extract metadata for chunk {chunk_id}: {e}")
                failed_count += 1
                continue

        # Insert batch into PostgreSQL
        if batch_records and not dry_run:
            try:
                execute_values(
                    cursor,
                    """
                    INSERT INTO financial_chunks (
                        chunk_id, document_id, page_number, chunk_index, content,
                        document_type, reporting_period, time_granularity, company_name,
                        geographic_jurisdiction, data_source_type, version_date,
                        section_type, metric_category, units, department_scope,
                        table_context, table_name, statistical_summary,
                        content_tsv, embedding_id, created_at, updated_at
                    ) VALUES %s
                    ON CONFLICT (chunk_id) DO UPDATE SET
                        document_type = EXCLUDED.document_type,
                        reporting_period = EXCLUDED.reporting_period,
                        time_granularity = EXCLUDED.time_granularity,
                        company_name = EXCLUDED.company_name,
                        geographic_jurisdiction = EXCLUDED.geographic_jurisdiction,
                        data_source_type = EXCLUDED.data_source_type,
                        version_date = EXCLUDED.version_date,
                        section_type = EXCLUDED.section_type,
                        metric_category = EXCLUDED.metric_category,
                        units = EXCLUDED.units,
                        department_scope = EXCLUDED.department_scope,
                        table_context = EXCLUDED.table_context,
                        table_name = EXCLUDED.table_name,
                        statistical_summary = EXCLUDED.statistical_summary,
                        embedding_id = EXCLUDED.embedding_id,
                        updated_at = NOW()
                    """,
                    batch_records,
                )
                conn.commit()
                migrated_count += len(batch_records)
                logger.info(
                    f"Migrated batch: {len(batch_records)} chunks ({migrated_count}/{total_chunks})"
                )

            except Exception as e:
                logger.error(f"Failed to insert batch into PostgreSQL: {e}")
                conn.rollback()
                failed_count += len(batch_records)

        elif batch_records and dry_run:
            migrated_count += len(batch_records)
            logger.info(
                f"[DRY RUN] Would migrate batch: {len(batch_records)} chunks ({migrated_count}/{total_chunks})"
            )

        # Move to next batch
        offset = next_offset
        if offset is None:
            break  # No more chunks

    # Close connections
    cursor.close()
    conn.close()
    logger.info("PostgreSQL connection closed")

    # Summary
    logger.info("=" * 60)
    logger.info("MIGRATION COMPLETE")
    logger.info("=" * 60)
    logger.info(f"Total chunks in Qdrant: {total_chunks}")
    logger.info(f"Successfully migrated: {migrated_count}")
    logger.info(f"Failed: {failed_count}")
    logger.info(f"Success rate: {migrated_count / total_chunks * 100:.1f}%")

    return (total_chunks, migrated_count, failed_count)


async def main():
    """Main entry point for migration script."""
    import argparse

    parser = argparse.ArgumentParser(description="Migrate Qdrant chunks to PostgreSQL")
    parser.add_argument(
        "--dry-run", action="store_true", help="Simulate migration without writing to database"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Number of chunks to process in each batch (default: 50)",
    )
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("QDRANT → POSTGRESQL MIGRATION")
    logger.info("=" * 60)
    logger.info(f"Dry run: {args.dry_run}")
    logger.info(f"Batch size: {args.batch_size}")
    logger.info("")

    total, migrated, failed = await migrate_chunks_to_postgresql(
        dry_run=args.dry_run, batch_size=args.batch_size
    )

    # Exit with error code if migration failed
    if failed > 0 and migrated == 0:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
