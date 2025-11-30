#!/usr/bin/env python
"""Batch ingest PDF files into production database.

Usage:
    python scripts/ingest-production-batch.py /path/to/folder

Ingests all PDF files in the specified folder one by one into the production
Qdrant (port 6333) and PostgreSQL (port 5432) databases.
"""

import asyncio

# Ensure production environment
import os
import sys
import time
import traceback
from pathlib import Path

os.environ["APP_ENV"] = "production"

from raglite.ingestion.document_ingestion import ingest_document
from raglite.shared.logging import get_logger
from raglite.shared.models import DocumentMetadata

logger = get_logger(__name__)


async def ingest_folder(folder_path: str) -> None:
    """Ingest all PDF files in a folder one by one."""
    folder = Path(folder_path)

    if not folder.exists():
        print(f"❌ Folder not found: {folder_path}")
        sys.exit(1)

    # Find all PDF files
    pdf_files = sorted(folder.glob("*.pdf"))

    if not pdf_files:
        print(f"❌ No PDF files found in: {folder_path}")
        sys.exit(1)

    print(f"\n📂 Found {len(pdf_files)} PDF files to ingest:")
    for i, pdf in enumerate(pdf_files, 1):
        print(f"   {i}. {pdf.name}")

    print("\n🎯 Target: Production database (Qdrant:6333, PostgreSQL:5432)")
    print("-" * 60)
    sys.stdout.flush()

    successful: list[tuple[str, DocumentMetadata]] = []
    failed: list[tuple[str, str]] = []

    for i, pdf_path in enumerate(pdf_files, 1):
        print(f"\n[{i}/{len(pdf_files)}] Ingesting: {pdf_path.name}")
        sys.stdout.flush()
        start_time = time.time()

        try:
            metadata = await ingest_document(str(pdf_path))
            elapsed = time.time() - start_time

            # Validate that we got the expected type
            if not isinstance(metadata, DocumentMetadata):
                raise TypeError(
                    f"Expected DocumentMetadata, got {type(metadata).__name__} "
                    f"from module {type(metadata).__module__}"
                )

            # Safely access attributes with explicit checks
            filename = getattr(metadata, "filename", "<unknown>")
            page_count = getattr(metadata, "page_count", 0)
            chunk_count = getattr(metadata, "chunk_count", 0)

            print(f"   ✅ Success in {elapsed:.1f}s")
            print(f"      Filename: {filename}")
            print(f"      Pages: {page_count}")
            print(f"      Chunks: {chunk_count}")
            sys.stdout.flush()

            successful.append((pdf_path.name, metadata))

        except Exception as e:
            elapsed = time.time() - start_time
            error_msg = str(e)

            # Print full traceback for debugging
            print(f"   ❌ Failed after {elapsed:.1f}s: {error_msg}")
            print("   📋 Full traceback:")
            traceback.print_exc()
            sys.stdout.flush()

            failed.append((pdf_path.name, error_msg))

    # Summary
    print("\n" + "=" * 60)
    print("📊 INGESTION SUMMARY")
    print("=" * 60)
    print(f"   Total files: {len(pdf_files)}")
    print(f"   Successful: {len(successful)}")
    print(f"   Failed: {len(failed)}")

    if successful:
        # Use safe attribute access for summary calculation
        total_pages = sum(getattr(m, "page_count", 0) for _, m in successful)
        total_chunks = sum(getattr(m, "chunk_count", 0) for _, m in successful)
        print(f"\n   📄 Total pages ingested: {total_pages}")
        print(f"   🧩 Total chunks created: {total_chunks}")

    if failed:
        print("\n   ⚠️  Failed files:")
        for name, error in failed:
            print(f"      - {name}: {error}")

    sys.stdout.flush()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/ingest-production-batch.py /path/to/folder")
        sys.exit(1)

    folder = sys.argv[1]
    asyncio.run(ingest_folder(folder))
