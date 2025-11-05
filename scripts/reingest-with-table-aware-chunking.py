"""Re-ingest financial PDF with table-aware chunking.

Story 2.8 AC3: Re-ingestion and validation script.

This script:
1. Clears existing PostgreSQL data
2. Recreates Qdrant collection
3. Re-ingests PDF with table-aware chunking enabled
4. Validates chunk metrics
5. Spot-checks chunk quality
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from raglite.ingestion.pipeline import ingest_pdf
from raglite.shared.clients import get_postgresql_connection, get_qdrant_client
from raglite.shared.config import settings
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


async def reingest_with_table_aware_chunking():
    """Re-ingest PDF with table-aware chunking and validate results."""
    logger.info("=" * 80)
    logger.info("Story 2.8 AC3: Re-Ingestion and Validation")
    logger.info("=" * 80)
    logger.info("")

    # Step 1: Clear existing data
    logger.info("Step 1: Clearing existing data...")
    logger.info("")

    # Clear PostgreSQL
    try:
        conn = get_postgresql_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM financial_chunks")
        conn.commit()
        logger.info("✅ PostgreSQL cleared (all rows deleted from financial_chunks)")
        cursor.close()
    except Exception as e:
        logger.warning(f"PostgreSQL clearing failed (may not be initialized): {e}")

    # Clear Qdrant collection (will be recreated automatically during ingestion)
    try:
        qdrant_client = get_qdrant_client()
        qdrant_client.delete_collection(settings.qdrant_collection_name)
        logger.info(f"✅ Qdrant collection deleted: {settings.qdrant_collection_name}")
    except Exception as e:
        logger.warning(f"Qdrant collection deletion failed (may not exist): {e}")

    logger.info("")

    # Step 2: Re-ingest with table-aware chunking
    logger.info("Step 2: Re-ingesting PDF with table-aware chunking...")
    logger.info("")

    # Use full 160-page PDF for comprehensive validation
    pdf_path = "docs/sample pdf/2025-08 Performance Review CONSO_v2.pdf"

    if not Path(pdf_path).exists():
        logger.error(f"PDF not found: {pdf_path}")
        logger.info("Trying 10-page test PDF...")
        pdf_path = "docs/sample pdf/test-10-pages.pdf"

    if not Path(pdf_path).exists():
        logger.error(f"Test PDF not found: {pdf_path}")
        return

    logger.info(f"Ingesting: {pdf_path}")
    logger.info("Expected time: 10-15 minutes for 160-page PDF")
    logger.info("")

    # Ingest with table-aware chunking
    # skip_metadata=True to avoid Mistral API dependency for this validation
    metadata = await ingest_pdf(pdf_path, clear_collection=True, skip_metadata=True)

    logger.info("")
    logger.info("✅ Re-ingestion complete!")
    logger.info(f"   Total chunks created: {metadata.chunk_count}")
    logger.info(f"   Pages processed: {metadata.page_count}")
    logger.info("")

    # Step 3: Validate chunk metrics
    logger.info("Step 3: Validating chunk metrics...")
    logger.info("")

    # Query Qdrant for statistics
    qdrant_client = get_qdrant_client()
    collection_info = qdrant_client.get_collection(settings.qdrant_collection_name)
    total_points = collection_info.points_count

    # Count table chunks
    from qdrant_client.models import FieldCondition, Filter, MatchValue

    table_filter = Filter(
        must=[
            FieldCondition(
                key="section_type",
                match=MatchValue(value="Table"),
            )
        ]
    )

    table_results = qdrant_client.scroll(
        collection_name=settings.qdrant_collection_name,
        scroll_filter=table_filter,
        limit=10000,  # High limit to get all table chunks
        with_payload=True,
    )

    table_chunks = table_results[0]
    table_count = len(table_chunks)
    text_count = total_points - table_count

    logger.info("Chunk Distribution:")
    logger.info(f"  Total chunks: {total_points}")
    logger.info(f"  Table chunks: {table_count}")
    logger.info(f"  Text chunks: {text_count}")
    logger.info(f"  Table percentage: {table_count / total_points * 100:.1f}%")
    logger.info("")

    # Calculate chunks per table (estimate unique tables by page numbers)
    if table_chunks:
        unique_pages_with_tables = len({chunk.payload["page_number"] for chunk in table_chunks})
        estimated_tables = unique_pages_with_tables  # Rough estimate: 1 table per page
        chunks_per_table = table_count / estimated_tables if estimated_tables > 0 else table_count

        logger.info("Table Metrics:")
        logger.info(f"  Estimated unique tables: ~{estimated_tables}")
        logger.info(f"  Chunks per table (avg): {chunks_per_table:.2f}")
        logger.info("")

        # AC3 Target: chunks per table ≤1.5 (goal: 1.2)
        if chunks_per_table <= 1.5:
            logger.info(f"✅ AC3 Target MET: Chunks per table = {chunks_per_table:.2f} (≤1.5)")
        else:
            logger.warning(f"⚠️ AC3 Target MISSED: Chunks per table = {chunks_per_table:.2f} (>1.5)")

    # Analyze chunk sizes
    import tiktoken

    encoding = tiktoken.get_encoding("cl100k_base")

    if table_chunks:
        logger.info("")
        logger.info("Table Chunk Size Analysis:")

        table_token_counts = [len(encoding.encode(chunk.payload["text"])) for chunk in table_chunks]

        logger.info(f"  Min tokens: {min(table_token_counts)}")
        logger.info(f"  Max tokens: {max(table_token_counts)}")
        logger.info(f"  Avg tokens: {sum(table_token_counts) / len(table_token_counts):.1f}")
        logger.info(f"  Median tokens: {sorted(table_token_counts)[len(table_token_counts) // 2]}")

        # Check if any chunks exceed 4096 tokens
        oversized = sum(1 for tc in table_token_counts if tc > 4096)
        if oversized > 0:
            logger.warning(f"⚠️ {oversized} table chunks exceed 4096 tokens!")
        else:
            logger.info("✅ All table chunks are <4096 tokens")

        # Distribution by size buckets
        small_tables = sum(1 for tc in table_token_counts if tc < 1000)
        medium_tables = sum(1 for tc in table_token_counts if 1000 <= tc < 2500)
        large_tables = sum(1 for tc in table_token_counts if 2500 <= tc < 4096)

        logger.info("")
        logger.info("Size Distribution:")
        logger.info(
            f"  Small (<1000 tokens):   {small_tables} ({small_tables / table_count * 100:.1f}%)"
        )
        logger.info(
            f"  Medium (1000-2500):     {medium_tables} ({medium_tables / table_count * 100:.1f}%)"
        )
        logger.info(
            f"  Large (2500-4096):      {large_tables} ({large_tables / table_count * 100:.1f}%)"
        )

    logger.info("")
    logger.info("=" * 80)
    logger.info("Step 4: Spot-Check Chunk Quality")
    logger.info("=" * 80)

    # Spot-check 10 random table chunks
    import random

    if table_chunks and len(table_chunks) >= 10:
        sample_size = min(10, len(table_chunks))
        sample_chunks = random.sample(table_chunks, sample_size)

        logger.info(f"Sampling {sample_size} random table chunks for quality check...")
        logger.info("")

        for i, chunk in enumerate(sample_chunks[:3], start=1):  # Show first 3
            logger.info(f"Sample {i}:")
            logger.info(f"  Page: {chunk.payload.get('page_number')}")
            logger.info(f"  Tokens: {len(encoding.encode(chunk.payload['text']))}")
            logger.info(f"  Preview: {chunk.payload['text'][:200]}...")
            logger.info("")

    logger.info("=" * 80)
    logger.info("Re-Ingestion and Validation Complete!")
    logger.info("=" * 80)

    # Summary
    logger.info("")
    logger.info("SUMMARY:")
    logger.info(f"  ✅ Total chunks: {total_points}")
    logger.info(f"  ✅ Table chunks: {table_count}")
    logger.info(f"  ✅ Chunks per table: {chunks_per_table:.2f}" if table_chunks else "  N/A")
    logger.info(
        f"  ✅ Max table chunk size: {max(table_token_counts)} tokens" if table_chunks else "  N/A"
    )
    logger.info("")


if __name__ == "__main__":
    asyncio.run(reingest_with_table_aware_chunking())
