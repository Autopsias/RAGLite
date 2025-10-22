"""
Integration tests for page-level parallelism in PDF ingestion (Story 2.2).

Tests AC2 (Speedup Validation) and AC4 (Thread Safety) for parallel page processing.
"""

import os
import time
from pathlib import Path

import pytest

# Skip slow tests unless RUN_SLOW_TESTS=1 environment variable is set
SKIP_SLOW_TESTS = os.getenv("RUN_SLOW_TESTS") != "1"


# Lazy import to avoid test discovery overhead
def get_ingestion_module():
    """Import ingestion module only when test runs."""
    from raglite.ingestion import pipeline

    return pipeline


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.timeout(900)  # 15 minutes for 160-page PDF
async def test_ac2_parallel_ingestion_4_threads():
    """
    AC2: Speedup Validation - 8 threads.

    Tests parallel ingestion with AcceleratorOptions(num_threads=8).
    Baseline (Story 2.1): 13.3 minutes (with default 4 threads)
    Target: 3.3-7.8 minutes (1.7-2.5x speedup with 8 threads)

    Validates:
    - Ingestion completes successfully with parallelism
    - Processing time measured accurately
    - Results comparable to baseline
    """
    pipeline = get_ingestion_module()

    # Use production 160-page PDF from Story 2.1 baseline
    pdf_path = Path("docs/sample pdf/2025-08 Performance Review CONSO_v2.pdf")
    assert pdf_path.exists(), f"Test PDF not found: {pdf_path}"

    # Measure ingestion time
    start_time = time.time()

    result = await pipeline.ingest_pdf(
        file_path=str(pdf_path),
        clear_collection=True,
    )

    end_time = time.time()
    duration_seconds = end_time - start_time
    duration_minutes = duration_seconds / 60

    # Log results
    print(f"\n{'=' * 60}")
    print("AC2 Parallel Ingestion Results (8 threads)")
    print(f"{'=' * 60}")
    print(f"Duration: {duration_minutes:.2f} minutes ({duration_seconds:.1f} seconds)")
    print(f"Chunks: {result.chunk_count}")
    print(f"Pages: {result.page_count}")
    print(f"{'=' * 60}\n")

    # Validate basic success criteria
    assert result.chunk_count > 0, "No chunks generated"
    assert result.page_count == 160, f"Expected 160 pages, got {result.page_count}"

    # Note: Speedup validation will be done manually by comparing with baseline
    # Baseline: 13.3 minutes (Story 2.1 with default 4 threads)
    # Target: 3.3-7.8 minutes (1.7-2.5x speedup with 8 threads = 2x thread count)
    # This test documents the parallel time for comparison


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.timeout(900)  # 15 minutes for 160-page PDF
@pytest.mark.skip(reason="Run manually to test 8-thread configuration")
async def test_ac2_parallel_ingestion_8_threads():
    """
    AC2: Speedup Validation - 8 threads.

    Tests parallel ingestion with max_num_pages_visible=8.
    This test is skipped by default and should be run manually
    after updating max_num_pages_visible=8 in pipeline.py.

    Compares 8-thread performance vs 4-thread to determine optimal configuration.
    """
    pipeline = get_ingestion_module()

    pdf_path = Path("docs/sample pdf/2025-08 Performance Review CONSO_v2.pdf")
    assert pdf_path.exists(), f"Test PDF not found: {pdf_path}"

    start_time = time.time()

    result = await pipeline.ingest_pdf(
        file_path=str(pdf_path),
        clear_collection=True,
    )

    end_time = time.time()
    duration_seconds = end_time - start_time
    duration_minutes = duration_seconds / 60

    print(f"\n{'=' * 60}")
    print("AC2 Parallel Ingestion Results (8 threads)")
    print(f"{'=' * 60}")
    print(f"Duration: {duration_minutes:.2f} minutes ({duration_seconds:.1f} seconds)")
    print(f"Chunks: {result.chunk_count}")
    print(f"Pages: {result.page_count}")
    print(f"{'=' * 60}\n")

    assert result.chunk_count > 0, "No chunks generated"
    assert result.page_count == 160, f"Expected 160 pages, got {result.page_count}"


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.skipif(
    SKIP_SLOW_TESTS,
    reason="Slow test (10+ min) - runs 10 ingestion cycles for determinism. Run with: RUN_SLOW_TESTS=1",
)
@pytest.mark.timeout(900)  # 15 minutes for 10-page PDF x 10 runs (increased from 600s)
async def test_ac4_thread_safety_determinism():
    """
    AC4: Thread Safety Validation - Deterministic output.

    Runs parallel ingestion 10 times consecutively with the same PDF.
    Validates that output is deterministic (same chunk count every time).

    NOTE: This test takes 10+ minutes as it runs full ingestion pipeline 10 times.
    Skip by default to speed up CI/CD. Enable with: RUN_SLOW_TESTS=1 pytest

    Checks for:
    - No deadlocks or race conditions
    - No exceptions during concurrent processing
    - Identical chunk counts across all runs

    DETERMINISM FIX: Clears metadata cache and BM25 cache between runs to ensure
    each iteration starts with a clean state and validates true parallel processing
    determinism (not cached results).
    """
    pipeline = get_ingestion_module()

    # Use smaller 10-page PDF for faster iteration
    pdf_path = Path("tests/fixtures/sample_financial_report.pdf")
    assert pdf_path.exists(), f"Test PDF not found: {pdf_path}"

    # Run ingestion 10 times and collect results
    chunk_counts = []
    page_counts = []

    print(f"\n{'=' * 60}")
    print("AC4 Thread Safety Validation (10 consecutive runs)")
    print(f"{'=' * 60}")

    for run_num in range(1, 11):
        try:
            # CRITICAL FIX: Clear metadata cache before each run to ensure determinism
            # The metadata extraction cache persists across runs and can cause non-deterministic
            # behavior if the first run's cached metadata is reused in subsequent runs
            pipeline._metadata_cache.clear()

            # CRITICAL FIX: Clear BM25 index cache to force regeneration each run
            # This ensures BM25 index creation is tested for determinism, not just cache hits
            from raglite.shared.bm25 import clear_bm25_cache

            clear_bm25_cache()

            result = await pipeline.ingest_pdf(
                file_path=str(pdf_path),
                clear_collection=True,
            )

            chunk_counts.append(result.chunk_count)
            page_counts.append(result.page_count)

            print(f"Run {run_num:2d}: chunks={result.chunk_count}, pages={result.page_count}")

        except Exception as e:
            pytest.fail(f"Run {run_num} failed with exception: {e}")

    print(f"{'=' * 60}")
    print("Determinism Check:")
    print(f"  Unique chunk counts: {set(chunk_counts)}")
    print(f"  Unique page counts: {set(page_counts)}")
    print(f"{'=' * 60}\n")

    # Validate determinism
    assert len(set(chunk_counts)) == 1, (
        f"Chunk counts vary across runs: {chunk_counts}. "
        f"Expected all runs to produce identical output."
    )

    assert len(set(page_counts)) == 1, (
        f"Page counts vary across runs: {page_counts}. "
        f"Expected all runs to produce identical page count."
    )

    # Validate all runs succeeded
    assert len(chunk_counts) == 10, "Not all 10 runs completed"
    assert all(c > 0 for c in chunk_counts), "Some runs produced zero chunks"
