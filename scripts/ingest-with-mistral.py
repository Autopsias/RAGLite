"""Ingest full 160-page PDF with Mistral Small metadata extraction.

This script validates Story 2.4 with the corrected Mistral implementation,
replacing the failed o1-mini approach (47.9% success) with Mistral Small (91% expected).
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from raglite.ingestion.pipeline import ingest_pdf  # noqa: E402
from raglite.shared.config import settings  # noqa: E402


async def main():
    """Ingest full PDF with Mistral metadata extraction."""

    pdf_path = "docs/sample pdf/2025-08 Performance Review CONSO_v2.pdf"

    print("=" * 80)
    print("📄 FULL PDF INGESTION WITH MISTRAL SMALL")
    print("=" * 80)
    print(f"\nPDF: {pdf_path}")
    print(f"Metadata Model: {settings.metadata_extraction_model}")
    print(f"API Key configured: {'✅ Yes' if settings.mistral_api_key else '❌ No'}")
    print("\n" + "=" * 80)
    print("Starting ingestion... This will take 10-15 minutes for 160 pages.")
    print("Mistral will extract metadata for ~400 chunks.")
    print("=" * 80 + "\n")

    try:
        result = await ingest_pdf(file_path=pdf_path, clear_collection=True)

        print("\n" + "=" * 80)
        print("✅ INGESTION COMPLETE")
        print("=" * 80)
        print(f"Filename: {result.filename}")
        print(f"Document Type: {result.doc_type}")
        print(f"Total Chunks: {result.chunk_count}")
        print(f"Pages Processed: {result.page_count}")
        print(f"Source Path: {result.source_path}")
        print(f"Ingestion Time: {result.ingestion_timestamp}")
        print("=" * 80)

        return True

    except Exception as e:
        print("\n" + "=" * 80)
        print("❌ INGESTION FAILED")
        print("=" * 80)
        print(f"Error: {e}")
        print(f"Error type: {type(e).__name__}")
        print("=" * 80)
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
