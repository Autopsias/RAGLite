#!/usr/bin/env python3
"""Re-ingest all 10 documents with FIXED entity validation code.

This script re-ingests all financial documents sequentially with the validated fixes.
Estimated time: ~3-4 hours for all 10 documents.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add raglite to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set production environment
os.environ["APP_ENV"] = "production"

from raglite.ingestion.document_ingestion import ingest_document

# All 10 financial documents to re-ingest
DOCUMENTS = [
    "2024-09 Performance Review CONSO_v1.pdf",
    "2024-12 Performance Review CONSO_v1.pdf",
    "2025-03 Performance Review CONSO_v1.pdf",
    "2025-06 Performance Review CONSO_v1.pdf",
    "2025-07 Performance Review CONSO_v1.pdf",
    "BdC-Quarterly-Report-1Q25.pdf",
    "BdC-Quarterly-Report-2Q25.pdf",
    "Indicadores_Trimestrais_jun_2025.pdf",
    "Novobanco_1Q2025_Quarterly-Report.pdf",
    "Novobanco_2Q2025_Quarterly-Report.pdf",
]

BASE_PATH = Path("/Users/ricardocarvalho/Downloads/OneDrive_1_11-25-2025 2")


async def main():
    """Re-ingest all documents sequentially."""
    print("=" * 80)
    print("FULL DATABASE RE-INGESTION WITH VALIDATED FIXES")
    print("=" * 80)
    print(f"Total documents: {len(DOCUMENTS)}")
    print("Estimated time: 3-4 hours")
    print(f"Environment: {os.environ.get('APP_ENV')}")
    print("=" * 80)
    print()

    total_pages = 0
    total_chunks = 0
    total_tables = 0
    completed = 0
    failed = []

    for i, doc_name in enumerate(DOCUMENTS, 1):
        doc_path = BASE_PATH / doc_name

        if not doc_path.exists():
            print(f"\n❌ [{i}/{len(DOCUMENTS)}] SKIPPED: {doc_name} (file not found)")
            failed.append((doc_name, "File not found"))
            continue

        print(f"\n{'=' * 80}")
        print(f"[{i}/{len(DOCUMENTS)}] Ingesting: {doc_name}")
        print(f"{'=' * 80}")

        try:
            result = await ingest_document(str(doc_path))

            total_pages += result.page_count
            total_chunks += result.chunk_count
            total_tables += getattr(result, "table_count", 0)
            completed += 1

            print("\n✅ SUCCESS!")
            print(f"   Pages: {result.page_count}")
            print(f"   Chunks: {result.chunk_count}")
            print(f"   Tables: {getattr(result, 'table_count', 0)}")
            print(f"   Progress: {completed}/{len(DOCUMENTS)} documents complete")

        except Exception as e:
            print(f"\n❌ FAILED: {doc_name}")
            print(f"   Error: {e}")
            failed.append((doc_name, str(e)))

    # Final summary
    print()
    print("=" * 80)
    print("INGESTION COMPLETE - SUMMARY")
    print("=" * 80)
    print(f"Documents completed: {completed}/{len(DOCUMENTS)}")
    print(f"Total pages: {total_pages}")
    print(f"Total chunks: {total_chunks}")
    print(f"Total tables: {total_tables}")

    if failed:
        print(f"\n❌ Failed documents ({len(failed)}):")
        for doc_name, error in failed:
            print(f"   - {doc_name}: {error}")
    else:
        print("\n✅ All documents ingested successfully!")

    print("=" * 80)

    return 0 if not failed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
