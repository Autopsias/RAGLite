"""Measure ingestion performance for MCP timeout investigation.

Story 4.0.3 - Task 1: Investigate current MCP ingestion timeout
This script measures baseline ingestion performance with current optimizations.
"""

import asyncio
import sys
import time
from pathlib import Path

# Add raglite to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from raglite.ingestion.pipeline import ingest_document
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


async def measure_ingestion(doc_path: str) -> dict:
    """Measure ingestion time for a single document.

    Args:
        doc_path: Path to document file

    Returns:
        dict with timing results
    """
    start_time = time.perf_counter()

    try:
        metadata = await ingest_document(doc_path)
        duration_s = time.perf_counter() - start_time

        return {
            "filename": metadata.filename,
            "pages": metadata.page_count,
            "chunks": metadata.chunk_count,
            "duration_s": round(duration_s, 2),
            "seconds_per_page": round(duration_s / metadata.page_count, 2)
            if metadata.page_count > 0
            else 0,
            "status": "success",
        }

    except Exception as e:
        duration_s = time.perf_counter() - start_time
        return {
            "filename": Path(doc_path).name,
            "duration_s": round(duration_s, 2),
            "status": "failed",
            "error": str(e),
        }


async def main():
    """Measure ingestion performance for sample PDFs."""
    print("=" * 80)
    print("Story 4.0.3 - MCP Ingestion Performance Investigation")
    print("=" * 80)
    print()

    # Test files
    test_files = [
        "tests/fixtures/sample-small-3-pages.pdf",  # 4 pages, 228 KB
        "tests/fixtures/sample_financial_report.pdf",  # ~10-15 pages
    ]

    results = []

    for test_file in test_files:
        if not Path(test_file).exists():
            print(f"⚠️  File not found: {test_file}")
            continue

        print(f"📄 Testing: {test_file}")
        print(f"   Size: {Path(test_file).stat().st_size / 1024:.1f} KB")
        print("   Measuring ingestion time...")

        result = await measure_ingestion(test_file)
        results.append(result)

        if result["status"] == "success":
            print(f"   ✅ Success: {result['duration_s']}s total")
            print(f"      Pages: {result['pages']}")
            print(f"      Chunks: {result['chunks']}")
            print(f"      Speed: {result['seconds_per_page']}s/page")
        else:
            print(f"   ❌ Failed: {result.get('error', 'Unknown error')}")
            print(f"      Duration: {result['duration_s']}s")

        print()

    # Summary
    print("=" * 80)
    print("SUMMARY: Ingestion Performance")
    print("=" * 80)
    print()

    successful_results = [r for r in results if r["status"] == "success"]

    if successful_results:
        print("✅ Successful Ingestions:")
        print()
        for r in successful_results:
            print(f"   {r['filename']}:")
            print(f"      Total Time: {r['duration_s']}s")
            print(f"      Pages: {r['pages']}")
            print(f"      Chunks: {r['chunks']}")
            print(f"      Speed: {r['seconds_per_page']}s/page")
            print()

        # Calculate MCP timeout risk
        avg_s_per_page = sum(r["seconds_per_page"] for r in successful_results) / len(
            successful_results
        )
        print(f"📊 Average Speed: {avg_s_per_page:.2f}s/page")
        print()

        print("🔍 MCP Timeout Risk Analysis:")
        print("   MCP Default Timeout: 60-120s")
        print()

        for pages in [10, 30, 50, 100, 150, 200]:
            estimated_time = avg_s_per_page * pages
            status = "✅" if estimated_time < 60 else "⚠️" if estimated_time < 120 else "❌"
            print(f"   {pages:3d} pages → {estimated_time:6.1f}s {status}")

        print()

    failed_results = [r for r in results if r["status"] == "failed"]
    if failed_results:
        print("❌ Failed Ingestions:")
        for r in failed_results:
            print(f"   {r['filename']}: {r.get('error', 'Unknown error')}")
        print()

    print("=" * 80)
    print("NEXT STEPS:")
    print("=" * 80)
    print()
    print("Based on results above:")
    print("  1. If ≥50 page timeout risk → Implement async ingestion (AC5)")
    print("  2. Verify pypdfium backend enabled (AC2)")
    print("  3. Verify page-level parallelism enabled (AC2)")
    print("  4. Consider embedding batch optimization (AC2)")
    print()


if __name__ == "__main__":
    asyncio.run(main())
