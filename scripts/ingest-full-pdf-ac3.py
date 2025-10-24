"""Story 2.5: Ingest full 160-page PDF for AC3 ground truth validation.

This script ingests the complete 160-page PDF into Qdrant for accuracy testing.
"""

import asyncio
import sys
from pathlib import Path

from raglite.ingestion.pipeline import ingest_pdf
from raglite.shared.clients import get_qdrant_client
from raglite.shared.config import settings


async def main():
    """Ingest full 160-page PDF for Story 2.5 AC3 validation."""
    print("=" * 80)
    print("Story 2.5 AC3: Ingesting Full 160-Page PDF")
    print("=" * 80)

    # Full PDF path
    pdf_path = Path("docs/sample pdf/2025-08 Performance Review CONSO_v2.pdf")

    if not pdf_path.exists():
        print(f"❌ Error: PDF not found: {pdf_path}")
        sys.exit(1)

    print(f"Source: {pdf_path}")
    print(f"Collection: {settings.qdrant_collection_name}")
    print("Expected: ~180-220 chunks (Story 2.3 fixed 512-token chunking)")
    print("Expected time: ~13-15 minutes (Story 2.1 + 2.2 optimization)")
    print("=" * 80 + "\n")

    # Clear existing collection
    print("Clearing existing collection...")
    qdrant = get_qdrant_client()
    try:
        qdrant.delete_collection(collection_name=settings.qdrant_collection_name)
        print(f"✓ Collection deleted: {settings.qdrant_collection_name}\n")
    except Exception:
        print("ℹ No existing collection to delete\n")

    # Ingest full PDF
    print(f"Ingesting {pdf_path.name} (160 pages)...")
    print("This will take ~13-15 minutes...\n")

    try:
        result = await ingest_pdf(str(pdf_path))

        print("\n" + "=" * 80)
        print("INGESTION COMPLETE")
        print("=" * 80)
        print(f"Pages processed: {result.pages_processed}")
        print(f"Chunks created: {result.chunks_created}")
        print(f"Collection: {settings.qdrant_collection_name}")
        print(f"BM25 index: {'Created' if result.bm25_index_created else 'Skipped'}")
        print("=" * 80 + "\n")

        print("✅ Ready for AC3 ground truth validation!")
        print(
            "   Run: pytest tests/integration/test_ac3_ground_truth.py::test_ac2_decision_gate_validation -v -s"
        )

    except Exception as e:
        print(f"\n❌ Error during ingestion: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
