#!/usr/bin/env python3
"""Simple script to ingest the Performance Review PDF into Qdrant."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from raglite.ingestion.pipeline import ingest_document  # noqa: E402


async def main():
    """Ingest the split PDF files."""
    pdf_dir = project_root / "docs" / "sample pdf" / "split"

    pdf_files = [
        pdf_dir / "2025-08 Performance Review CONSO_v2_part01_pages001-040.pdf",
        pdf_dir / "2025-08 Performance Review CONSO_v2_part02_pages041-080.pdf",
        pdf_dir / "2025-08 Performance Review CONSO_v2_part03_pages081-120.pdf",
        pdf_dir / "2025-08 Performance Review CONSO_v2_part04_pages121-160.pdf",
    ]

    print("=" * 80)
    print("PDF INGESTION - Story 1.14")
    print("=" * 80)
    print()

    for pdf_file in pdf_files:
        if not pdf_file.exists():
            print(f"❌ File not found: {pdf_file}")
            continue

        print(f"📄 Ingesting: {pdf_file.name}")
        try:
            metadata = await ingest_document(str(pdf_file))
            print(f"   ✓ Ingested {metadata.chunks_count} chunks from {metadata.pages} pages")
        except Exception as e:
            print(f"   ✗ Error: {e}")
            continue

    print()
    print("=" * 80)
    print("INGESTION COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
