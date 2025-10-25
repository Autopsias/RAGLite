"""Story 2.5: Ingest full 160-page PDF WITHOUT metadata extraction.

This script ingests the complete 160-page PDF into Qdrant, skipping the
Mistral metadata extraction step to avoid API 502 errors. This is a temporary
workaround to unblock the Story 2.5 Decision Gate validation.

The ingestion will include:
- Docling PDF processing with pypdfium backend (Story 2.1)
- Fixed 512-token chunking (Story 2.3)
- Fin-E5 embeddings generation
- Qdrant vector storage
- BM25 index building

Skips:
- Mistral LLM metadata extraction (Story 2.4) - to avoid API errors
- PostgreSQL metadata storage (Story 2.6) - requires metadata from Story 2.4
"""

import asyncio
import sys
from pathlib import Path

from raglite.ingestion.pipeline import ingest_pdf
from raglite.shared.clients import get_qdrant_client
from raglite.shared.config import settings


async def main():
    """Ingest full 160-page PDF WITHOUT metadata extraction."""
    print("=" * 80)
    print("Story 2.5 AC3: Ingesting Full 160-Page PDF (NO METADATA)")
    print("=" * 80)

    # Full PDF path
    pdf_path = Path("docs/sample pdf/2025-08 Performance Review CONSO_v2.pdf")

    if not pdf_path.exists():
        print(f"❌ Error: PDF not found: {pdf_path}")
        sys.exit(1)

    print(f"Source: {pdf_path}")
    print(f"Collection: {settings.qdrant_collection_name}")
    print("Expected: ~180-220 chunks (Story 2.3 fixed 512-token chunking)")
    print("Expected time: ~5-7 minutes (no metadata extraction)")
    print("SKIPPING: Mistral metadata extraction (API 502 errors)")
    print("=" * 80 + "\n")

    # Clear existing collection
    print("Clearing existing collection...")
    qdrant = get_qdrant_client()
    try:
        qdrant.delete_collection(collection_name=settings.qdrant_collection_name)
        print(f"✓ Collection deleted: {settings.qdrant_collection_name}\n")
    except Exception:
        print("ℹ No existing collection to delete\n")

    # Ingest full PDF WITHOUT metadata extraction
    print(f"Ingesting {pdf_path.name} (160 pages) WITHOUT metadata extraction...")
    print("This will take ~5-7 minutes...\n")

    try:
        # Use skip_metadata=True to bypass Mistral API calls
        result = await ingest_pdf(str(pdf_path), skip_metadata=True)

        print("\n" + "=" * 80)
        print("INGESTION COMPLETE")
        print("=" * 80)
        print(f"Pages processed: {result.pages_processed}")
        print(f"Chunks created: {result.chunks_created}")
        print(f"Collection: {settings.qdrant_collection_name}")
        print(f"BM25 index: {'Created' if result.bm25_index_created else 'Skipped'}")
        print("Metadata extraction: SKIPPED (skip_metadata=True)")
        print("=" * 80 + "\n")

        print("✅ Ready for AC3 ground truth validation!")
        print(
            "   Run: pytest tests/integration/test_ac3_ground_truth.py::test_ac2_decision_gate_validation -v -s"
        )
        print("   OR: python scripts/run-accuracy-tests.py")

    except Exception as e:
        print(f"\n❌ Error during ingestion: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
