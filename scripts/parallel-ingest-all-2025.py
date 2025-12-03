#!/usr/bin/env python3
"""Parallel ingestion of all 2025 Performance Review documents.

Uses Story 5.0.6 parallel ingestion with ALL performance optimizations:
- Parallel document processing (2 docs at once)
- Rule-based unit inference (80% API reduction)
- Cross-document caching (30% additional reduction)
- Skip metadata at ingestion (90% API reduction)
- Query-time metadata enrichment

Expected time: 30-45 minutes (vs 4-5 hours sequential)
"""

import asyncio
import os
import sys
from pathlib import Path

# Add raglite to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set production environment
os.environ["APP_ENV"] = "production"

from raglite.ingestion.document_ingestion import ingest_documents_parallel

# All 10 Performance Review documents (Jan-Oct 2025)
BASE_PATH = Path("/Users/ricardocarvalho/Downloads/OneDrive_1_11-25-2025 2")

DOCUMENTS = [
    "2025-01 Performance Review CONSO_v2.pdf",
    "2025-02 Performance Review CONSO_v1.pdf",
    "2025-03 Performance Review CONSO_V1.pdf",
    "2025-04 Performance Review CONSO.pdf",
    "2025-05 Performance Review CONSO_v1.pdf",
    "2025-06 Performance Review CONSO_v1.pdf",
    "2025-07 Performance Review CONSO.pdf",
    "2025-08 Performance Review CONSO_v1.pdf",
    "2025-09 Performance Review CONSO_rev3.pdf",
    "2025-10 Performance Review CONSO_v3.pdf",
]


async def main():
    """Run parallel ingestion with ALL Story 5.0.6 optimizations."""
    print("=" * 80)
    print("PARALLEL INGESTION - ALL 2025 PERFORMANCE REVIEW DOCUMENTS")
    print("=" * 80)
    print(f"Total documents: {len(DOCUMENTS)}")
    print(f"Environment: {os.environ.get('APP_ENV')}")
    print()
    print("Performance Optimizations (Story 5.0.6):")
    print("  ✓ Parallel document processing (2 concurrent)")
    print("  ✓ Rule-based unit inference (80% API reduction)")
    print("  ✓ Cross-document caching (30% additional reduction)")
    print("  ✓ Skip metadata at ingestion (90% API reduction)")
    print("  ✓ Query-time metadata enrichment")
    print()
    print("Expected time: 30-45 minutes (6-10x speedup vs sequential)")
    print("=" * 80)
    print()

    # Build full paths
    file_paths = [str(BASE_PATH / doc_name) for doc_name in DOCUMENTS]

    # Verify all files exist
    missing_files = [path for path in file_paths if not Path(path).exists()]
    if missing_files:
        print("❌ ERROR: Missing files:")
        for path in missing_files:
            print(f"   - {path}")
        return 1

    print("✅ All files verified. Starting parallel ingestion...")
    print()

    try:
        # AC1: Use parallel ingestion with default max_concurrent=2
        result = await ingest_documents_parallel(
            file_paths=file_paths,
            max_concurrent=2,  # Story 5.0.6 default for memory safety
        )

        # Display results
        print()
        print("=" * 80)
        print("PARALLEL INGESTION COMPLETE - SUMMARY")
        print("=" * 80)
        print(f"Total documents: {result.total_documents}")
        print(f"Successful: {result.successful}")
        print(f"Failed: {result.failed}")
        print(
            f"Duration: {result.duration_seconds:.1f}s ({result.duration_seconds / 60:.1f} minutes)"
        )
        print()

        if result.successful > 0:
            total_pages = sum(r.page_count for r in result.results)
            total_chunks = sum(r.chunk_count for r in result.results)
            total_tables = sum(getattr(r, "table_count", 0) for r in result.results)

            print(f"Total pages: {total_pages}")
            print(f"Total chunks: {total_chunks}")
            print(f"Total tables: {total_tables}")
            print()

        if result.errors:
            print(f"❌ Errors ({len(result.errors)}):")
            for error in result.errors:
                print(f"   - {error['file_path']}: {error['error']}")
        else:
            print("✅ All documents ingested successfully!")

        print("=" * 80)

        return 0 if result.failed == 0 else 1

    except Exception as e:
        print()
        print("=" * 80)
        print("❌ PARALLEL INGESTION FAILED!")
        print("=" * 80)
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
