"""Test table-aware chunking on sample PDF.

Story 2.8 Task 1.4: Validate table detection on test PDF.

This script tests the table-aware chunking implementation by:
1. Ingesting a sample PDF
2. Counting table chunks vs total chunks
3. Verifying table metadata (section_type='Table')
4. Checking token counts for table chunks

Expected results:
- Table chunks should have section_type='Table'
- Table chunks should be <4096 tokens
- Total chunk count should be significantly reduced
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from raglite.ingestion.pipeline import ingest_pdf
from raglite.shared.clients import get_qdrant_client
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


async def test_table_aware_chunking():
    """Test table-aware chunking on sample PDF."""
    logger.info("=" * 80)
    logger.info("Testing Table-Aware Chunking (Story 2.8 Task 1.4)")
    logger.info("=" * 80)

    # Test PDF path
    pdf_path = "docs/sample pdf/test-10-pages.pdf"

    if not Path(pdf_path).exists():
        logger.error(f"Test PDF not found: {pdf_path}")
        logger.info("Trying alternative PDF...")
        pdf_path = "docs/sample pdf/2025-08 Performance Review CONSO_v2.pdf"

    if not Path(pdf_path).exists():
        logger.error(f"Alternative PDF not found: {pdf_path}")
        return

    logger.info(f"Test PDF: {pdf_path}")
    logger.info("")

    # Ingest PDF with table-aware chunking
    logger.info("Step 1: Ingesting PDF with table-aware chunking enabled...")
    metadata = await ingest_pdf(pdf_path, clear_collection=True, skip_metadata=True)

    logger.info(f"✅ Ingestion complete: {metadata.chunk_count} chunks created")
    logger.info("")

    # Query Qdrant to analyze chunks
    logger.info("Step 2: Analyzing chunk distribution...")
    client = get_qdrant_client()

    # Get all points from collection
    from qdrant_client.models import FieldCondition, Filter, MatchValue

    # Count table chunks
    table_filter = Filter(
        must=[
            FieldCondition(
                key="section_type",
                match=MatchValue(value="Table"),
            )
        ]
    )

    table_results = client.scroll(
        collection_name="financial_docs",
        scroll_filter=table_filter,
        limit=1000,
        with_payload=True,
    )

    table_chunks = table_results[0]
    total_points = client.count(collection_name="financial_docs").count

    logger.info(f"Total chunks in Qdrant: {total_points}")
    logger.info(f"Table chunks: {len(table_chunks)}")
    logger.info(f"Non-table chunks: {total_points - len(table_chunks)}")
    logger.info(f"Table chunk percentage: {len(table_chunks) / total_points * 100:.1f}%")
    logger.info("")

    # Analyze table chunk token counts
    if table_chunks:
        logger.info("Step 3: Analyzing table chunk sizes...")

        import tiktoken

        encoding = tiktoken.get_encoding("cl100k_base")

        token_counts = [len(encoding.encode(chunk.payload["text"])) for chunk in table_chunks]

        logger.info("Table chunk token count statistics:")
        logger.info(f"  Min tokens: {min(token_counts)}")
        logger.info(f"  Max tokens: {max(token_counts)}")
        logger.info(f"  Avg tokens: {sum(token_counts) / len(token_counts):.1f}")
        logger.info(f"  Chunks >4096 tokens: {sum(1 for tc in token_counts if tc > 4096)}")
        logger.info("")

        # Check if any table chunks exceed 4096 tokens
        if any(tc > 4096 for tc in token_counts):
            logger.warning("⚠️ Some table chunks exceed 4096 tokens!")
            for i, tc in enumerate(token_counts):
                if tc > 4096:
                    logger.warning(f"  Chunk {i}: {tc} tokens")
        else:
            logger.info("✅ All table chunks are <4096 tokens")

    logger.info("")
    logger.info("=" * 80)
    logger.info("Test complete!")
    logger.info("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_table_aware_chunking())
