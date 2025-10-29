"""Rebuild BM25 index from existing Qdrant collection.

This script rebuilds the BM25 index from chunks already stored in Qdrant.
Use this when the BM25 index is out of sync with Qdrant data.

Usage:
    python scripts/rebuild_bm25_index.py
"""

import asyncio

from raglite.shared.bm25 import create_bm25_index, save_bm25_index
from raglite.shared.clients import get_qdrant_client
from raglite.shared.config import settings
from raglite.shared.logging import get_logger
from raglite.shared.models import Chunk

logger = get_logger(__name__)


async def main():
    """Rebuild BM25 index from Qdrant collection."""
    print("=" * 80)
    print("REBUILD BM25 INDEX FROM QDRANT")
    print("=" * 80)

    # Connect to Qdrant
    client = get_qdrant_client()
    collection_name = settings.qdrant_collection_name

    # Get collection info
    collection_info = client.get_collection(collection_name)
    points_count = collection_info.points_count

    print(f"\nCollection: {collection_name}")
    print(f"Points count: {points_count}")

    if points_count == 0:
        print("\n❌ ERROR: No points in collection. Run ingestion first.")
        return

    # Fetch all points
    print(f"\nFetching {points_count} points from Qdrant...")

    chunks = []
    offset = None
    batch_size = 100

    while True:
        # Scroll through all points
        scroll_result = client.scroll(
            collection_name=collection_name,
            limit=batch_size,
            offset=offset,
            with_payload=True,
            with_vectors=False,  # Don't need vectors for BM25
        )

        points, next_offset = scroll_result

        if not points:
            break

        # Convert points to Chunk objects
        for point in points:
            payload = point.payload

            # Create minimal DocumentMetadata for BM25 (doesn't need full metadata)
            from raglite.shared.models import DocumentMetadata

            doc_metadata = DocumentMetadata(
                filename=payload.get("source_document", "unknown.pdf"),
                doc_type="PDF",
                ingestion_timestamp="2025-10-18T00:00:00Z",
                page_count=0,
                source_path="",
                chunk_count=0,
            )

            # Create Chunk object with required fields for BM25
            chunk = Chunk(
                chunk_id=f"chunk_{payload.get('chunk_index', 0)}",
                content=payload.get("text", ""),
                metadata=doc_metadata,
                page_number=payload.get("page_number", 0),
                chunk_index=payload.get("chunk_index", 0),
                embedding=[],  # Empty list (not needed for BM25)
            )
            chunks.append(chunk)

        print(f"  Fetched {len(chunks)} chunks so far...")

        offset = next_offset
        if offset is None:
            break

    print(f"\n✓ Fetched {len(chunks)} chunks from Qdrant")

    # Create BM25 index from chunks (no sorting needed - use natural order)
    print(f"\nCreating BM25 index from {len(chunks)} chunks...")
    bm25, tokenized_docs = create_bm25_index(chunks, k1=1.7, b=0.6)

    print("✓ BM25 index created:")
    print(f"  - Corpus size: {bm25.corpus_size}")
    print(f"  - Vocabulary size: {len({word for doc in tokenized_docs for word in doc})}")
    print(
        f"  - Avg tokens/chunk: {sum(len(doc) for doc in tokenized_docs) / len(tokenized_docs):.1f}"
    )

    # Create chunk metadata for BM25-to-Qdrant mapping
    print("\nCreating chunk metadata for hybrid search mapping...")
    chunk_metadata = [
        {
            "source_document": chunk.metadata.filename,
            "chunk_index": chunk.chunk_index,
            "page_number": chunk.page_number,
        }
        for chunk in chunks
    ]
    print(f"  ✓ Metadata created for {len(chunk_metadata)} chunks")

    # Save BM25 index with metadata
    print("\nSaving BM25 index to disk...")
    save_bm25_index(bm25, tokenized_docs, chunk_metadata=chunk_metadata)

    print("\n" + "=" * 80)
    print("✓ BM25 INDEX REBUILD COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
