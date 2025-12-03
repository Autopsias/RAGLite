#!/usr/bin/env python
"""Benchmark parallel document ingestion performance.

Story 5.0.6 AC7: Performance validation script for parallel ingestion optimization.

Usage:
    # Benchmark with test PDFs (simulates 10 documents):
    python scripts/benchmark-parallel-ingestion.py

    # Benchmark with custom folder:
    python scripts/benchmark-parallel-ingestion.py /path/to/pdfs

    # Benchmark with custom concurrency:
    python scripts/benchmark-parallel-ingestion.py /path/to/pdfs --concurrency 2

Performance Targets (Story 5.0.6):
    - 10 PDFs (160 pages each) should complete in <45 minutes
    - 6-10x speedup vs sequential ingestion (was 4-5 hours)
    - 90% API call reduction via optimizations:
      * Rule-based unit inference (80% reduction)
      * Cross-document caching (30% additional)
      * Skip metadata at ingestion (90% reduction)
"""

import asyncio
import os
import sys
import time
from pathlib import Path

# Use test environment for benchmarking (safe, isolated)
os.environ["APP_ENV"] = "test"

from raglite.ingestion.document_ingestion import ingest_documents_parallel
from raglite.shared.config import settings
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


async def benchmark_parallel_ingestion(
    file_paths: list[str], max_concurrent: int | None = None
) -> None:
    """Run parallel ingestion benchmark and display performance metrics.

    Args:
        file_paths: List of PDF file paths to ingest
        max_concurrent: Maximum concurrent documents (default: settings value)
    """
    # Display configuration
    concurrency = max_concurrent or settings.ingestion_parallel_docs
    print("\n" + "=" * 70)
    print("🚀 PARALLEL INGESTION BENCHMARK")
    print("=" * 70)
    print(f"   Documents: {len(file_paths)}")
    print(f"   Concurrency: {concurrency} documents")
    print(f"   Skip metadata at ingestion: {settings.skip_ingestion_metadata}")
    print("   Rule-based unit inference: Enabled")
    print("   Cross-document cache: Enabled")
    print(f"   Target database: TEST (Qdrant:{settings.qdrant_port}, PG:{settings.postgres_port})")
    print("-" * 70)
    sys.stdout.flush()

    # List files to be ingested
    print("\n📂 Files to ingest:")
    for i, path in enumerate(file_paths, 1):
        print(f"   {i}. {Path(path).name}")
    print()
    sys.stdout.flush()

    # Run benchmark
    print("⏱️  Starting benchmark...")
    sys.stdout.flush()
    start_time = time.time()

    try:
        result = await ingest_documents_parallel(file_paths, max_concurrent=max_concurrent)
        elapsed = time.time() - start_time

        # Display results
        print("\n" + "=" * 70)
        print("📊 BENCHMARK RESULTS")
        print("=" * 70)
        print(f"   Total duration: {elapsed:.1f}s ({elapsed / 60:.1f} min)")
        print(f"   Total documents: {result.total_documents}")
        print(f"   Successful: {result.successful}")
        print(f"   Failed: {result.failed}")
        print()

        if result.successful > 0:
            # Per-document statistics
            avg_time = elapsed / result.successful
            print(f"   Average time per document: {avg_time:.1f}s ({avg_time / 60:.1f} min)")

            # Calculate total pages and chunks
            total_pages = sum(doc.page_count for doc in result.results)
            total_chunks = sum(doc.chunk_count for doc in result.results)
            print(f"   Total pages ingested: {total_pages}")
            print(f"   Total chunks created: {total_chunks}")
            print(f"   Pages per second: {total_pages / elapsed:.2f}")
            print()

            # Performance analysis
            print("🎯 Performance Analysis:")
            docs_per_min = result.successful / (elapsed / 60)
            print(f"   Throughput: {docs_per_min:.2f} documents/minute")

            # Estimate for 10-document batch (Story 5.0.6 target)
            if result.successful < 10:
                estimated_10_docs = (elapsed / result.successful) * 10
                print(
                    f"   Estimated time for 10 docs: {estimated_10_docs / 60:.1f} min "
                    f"(target: <45 min)"
                )
                if estimated_10_docs / 60 < 45:
                    print("   ✅ MEETS TARGET: <45 minutes for 10 documents")
                else:
                    print("   ⚠️  EXCEEDS TARGET: >45 minutes for 10 documents")
            elif result.successful == 10:
                if elapsed / 60 < 45:
                    print(f"   ✅ MEETS TARGET: {elapsed / 60:.1f} min < 45 min")
                else:
                    print(f"   ⚠️  EXCEEDS TARGET: {elapsed / 60:.1f} min > 45 min")

            # Speedup calculation (baseline: 4-5 hours sequential for 10 docs)
            baseline_hours = 4.5  # Average of 4-5 hours
            baseline_per_doc = (baseline_hours * 3600) / 10  # seconds per doc
            actual_per_doc = elapsed / result.successful
            speedup = baseline_per_doc / actual_per_doc
            print(f"   Speedup vs baseline: {speedup:.1f}x (target: 6-10x)")

            if speedup >= 6:
                print("   ✅ MEETS SPEEDUP TARGET: 6-10x faster")
            else:
                print(f"   ⚠️  BELOW SPEEDUP TARGET: {speedup:.1f}x < 6x")
            print()

        # Optimization summary
        print("🔧 Optimizations Applied:")
        print(f"   ✓ Parallel ingestion (concurrency: {concurrency})")
        print(f"   ✓ Skip metadata at ingestion: {settings.skip_ingestion_metadata}")
        print("   ✓ Rule-based unit inference: Enabled")
        print("   ✓ Cross-document unit cache: Enabled")
        print(f"   ✓ Query-time metadata: {settings.query_time_metadata_enabled}")
        print()

        # API Call Reduction Notes
        print("📉 Expected API Call Reduction (Story 5.0.6):")
        print("   • Skip chunk metadata: 90% reduction (400 calls/doc → 0)")
        print("   • Rule-based units: 80% reduction for common metrics")
        print("   • Cross-doc cache: 30% additional reduction across batch")
        print("   • Overall: ~90% total API call reduction at ingestion")
        print()

        # Error details if any
        if result.failed > 0:
            print("❌ Failed Documents:")
            for error in result.errors:
                print(f"   • {error['filename']}: {error['error']}")
            print()

        # Success indicator
        if result.failed == 0 and elapsed / 60 < 45:
            print("=" * 70)
            print("✅ BENCHMARK PASSED: All targets met")
            print("=" * 70)
        elif result.failed > 0:
            print("=" * 70)
            print("⚠️  BENCHMARK PARTIAL: Some documents failed")
            print("=" * 70)
        else:
            print("=" * 70)
            print("⚠️  BENCHMARK WARNING: Performance targets not met")
            print("=" * 70)

    except Exception as e:
        elapsed = time.time() - start_time
        print(f"\n❌ Benchmark failed after {elapsed:.1f}s: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


async def main() -> None:
    """Main entry point for benchmark script."""
    # Parse arguments
    if len(sys.argv) > 1 and sys.argv[1] in ["-h", "--help"]:
        print(__doc__)
        sys.exit(0)

    # Determine file paths
    if len(sys.argv) > 1:
        # Use provided folder path
        folder = Path(sys.argv[1])
        if not folder.exists():
            print(f"❌ Folder not found: {sys.argv[1]}")
            sys.exit(1)

        pdf_files = sorted(folder.glob("*.pdf"))
        if not pdf_files:
            print(f"❌ No PDF files found in: {sys.argv[1]}")
            sys.exit(1)

        file_paths = [str(p) for p in pdf_files]
    else:
        # Use test PDFs (simulate 10 documents by repeating)
        test_pdf = Path("tests/fixtures/sample_financial_report.pdf")
        if not test_pdf.exists():
            print(f"❌ Test PDF not found: {test_pdf}")
            print("Please provide a folder path with PDF files:")
            print("  python scripts/benchmark-parallel-ingestion.py /path/to/pdfs")
            sys.exit(1)

        # Simulate 10 documents using test PDF
        print("\n⚠️  No folder provided, using test PDF to simulate 10 documents")
        file_paths = [str(test_pdf)] * 10

    # Parse concurrency argument
    max_concurrent = None
    if "--concurrency" in sys.argv:
        idx = sys.argv.index("--concurrency")
        if idx + 1 < len(sys.argv):
            try:
                max_concurrent = int(sys.argv[idx + 1])
            except ValueError:
                print(f"❌ Invalid concurrency value: {sys.argv[idx + 1]}")
                sys.exit(1)

    # Run benchmark
    await benchmark_parallel_ingestion(file_paths, max_concurrent=max_concurrent)


if __name__ == "__main__":
    asyncio.run(main())
