#!/usr/bin/env python3
"""Ingest the WHOLE Performance Review PDF (160 pages) into Qdrant."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from raglite.ingestion.pipeline import ingest_document  # noqa: E402


async def main():
    """Ingest the WHOLE PDF file."""
    pdf_file = project_root / "docs" / "sample pdf" / "2025-08 Performance Review CONSO_v2.pdf"

    print("=" * 80)
    print("WHOLE PDF INGESTION - Story 1.15 Prerequisite")
    print("=" * 80)
    print()

    if not pdf_file.exists():
        print(f"❌ File not found: {pdf_file}")
        return

    print(f"📄 Ingesting: {pdf_file.name}")
    print("📄 Expected: 160 pages, ~300+ chunks")
    print()

    try:
        metadata = await ingest_document(str(pdf_file))
        print("   ✓ SUCCESS!")
        print(f"   ✓ Document ID: {metadata.document_id}")
        print(f"   ✓ Pages: {metadata.pages}")
        print(f"   ✓ Source: {metadata.source_document}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        import traceback

        traceback.print_exc()

    print()
    print("=" * 80)
    print("INGESTION COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
