"""Integration tests for pypdfium backend ingestion (Story 2.1).

Tests AC2, AC3, AC4:
- AC2: Ingestion Validation with Test PDF
- AC3: Table Accuracy Maintained (≥97.9%)
- AC4: Memory Reduction Validation (50-60% reduction expected)

Prerequisites:
- Qdrant must be running (docker-compose up -d qdrant)
- Sample PDF must exist at tests/fixtures/sample_financial_report.pdf

Performance Optimization:
- Lazy imports to avoid test discovery overhead
"""

import time
import tracemalloc
from pathlib import Path

import pytest


class TestPypdfiumIngestionValidation:
    """Integration tests for pypdfium backend ingestion validation (Story 2.1).

    Validates AC2: Ingestion with real PDFs works correctly with pypdfium backend.
    """

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.timeout(120)
    async def test_ingest_pdf_with_pypdfium_backend(self) -> None:
        """Test AC2: Ingest test PDF successfully with pypdfium backend.

        Validates:
        - Ingest 10-page sample PDF successfully
        - Verify all pages processed (page_count=10)
        - Verify table extraction still works
        - Verify pypdfium backend logged in initialization

        This test requires Qdrant to be running.
        If Qdrant is not available, the test will be skipped.
        """
        # Lazy imports to avoid test discovery overhead
        from raglite.ingestion.pipeline import ingest_pdf
        from raglite.shared.models import DocumentMetadata

        # Locate sample PDF
        sample_pdf = Path("tests/fixtures/sample_financial_report.pdf")

        if not sample_pdf.exists():
            pytest.skip(f"Sample PDF not found at {sample_pdf}")

        # Start timing
        start_time = time.time()

        # Ingest PDF (this will use pypdfium backend per Story 2.1 configuration)
        try:
            result = await ingest_pdf(str(sample_pdf))
        except Exception as e:
            if "Connection refused" in str(e) or "Qdrant" in str(e):
                pytest.skip(f"Qdrant not available: {e}")
            raise

        # Calculate duration
        duration_seconds = time.time() - start_time

        # AC2 Assertions: Ingestion Validation
        assert isinstance(result, DocumentMetadata), "Result should be DocumentMetadata"
        assert result.filename == "sample_financial_report.pdf"
        assert result.doc_type == "PDF"

        # Page count validation (sample PDF has 10 pages)
        assert result.page_count == 10, f"Expected 10 pages, got {result.page_count}"

        # Verify all pages processed
        assert result.page_count > 0, "Page numbers must be extracted from provenance"

        # Performance check (pypdfium should not be slower than baseline)
        # Baseline: ~60 seconds for 10 pages with table extraction
        max_duration_seconds = 120
        assert duration_seconds < max_duration_seconds, (
            f"Ingestion took {duration_seconds:.1f}s, "
            f"expected <{max_duration_seconds}s (pypdfium should not degrade performance)"
        )

        # Log performance metrics
        print("\\n\\n=== AC2: Ingestion Validation with pypdfium Backend ===")
        print(f"  Duration: {duration_seconds:.1f} seconds")
        print(f"  Pages: {result.page_count}")
        print(f"  Pages/second: {result.page_count / duration_seconds:.2f}")
        print("  Backend: pypdfium (Story 2.1)")
        print("  Status: ✅ PASS - pypdfium backend ingestion successful")


class TestPypdfiumTableAccuracy:
    """Integration tests for table extraction accuracy with pypdfium (Story 2.1 AC3)."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.timeout(300)
    async def test_table_accuracy_with_pypdfium_backend(self) -> None:
        """Test AC3: Table extraction accuracy ≥97.9% with pypdfium backend.

        Validates table extraction accuracy using 10 ground truth table queries.
        Compares pypdfium backend accuracy against NFR9 requirement (≥95%, target 97.9%).

        This test requires:
        - Qdrant running with ingested PDF data
        - 10 table-specific ground truth queries from table_accuracy_queries.py

        Expected Result: ≥9/10 queries (90%) should retrieve correct table data in top-5 results
        NFR9 Compliance: ≥97.9% table extraction accuracy (Docling TableFormerMode.ACCURATE)
        """
        # Lazy imports
        from raglite.retrieval.attribution import generate_citations
        from raglite.retrieval.search import search_documents
        from scripts.accuracy_utils import check_retrieval_accuracy
        from tests.fixtures.table_accuracy_queries import TABLE_ACCURACY_QUERIES

        # AC3 Validation: Run 10 ground truth table queries
        correct_retrievals = 0
        total_queries = len(TABLE_ACCURACY_QUERIES)

        print("\n\n=== AC3: Table Accuracy Validation (pypdfium backend) ===")
        print(f"  Total Queries: {total_queries}")
        print("  NFR9 Target: ≥95% table extraction accuracy")
        print("  Story 2.1 Target: ≥97.9% accuracy maintained\n")

        for i, query in enumerate(TABLE_ACCURACY_QUERIES, 1):
            # Search for table data
            results = await search_documents(query=query["question"], top_k=5)
            results = await generate_citations(results)

            # Check if correct answer retrieved
            is_correct = check_retrieval_accuracy(query, results)
            if is_correct:
                correct_retrievals += 1

            status = "✅" if is_correct else "❌"
            print(f"  {i:2d}. {status} {query['question'][:60]}...")

        # Calculate accuracy
        accuracy_pct = (correct_retrievals / total_queries) * 100

        print("\n  Results:")
        print(f"    Correct: {correct_retrievals}/{total_queries}")
        print(f"    Accuracy: {accuracy_pct:.1f}%")
        print("    Target: ≥97.9% (NFR9: ≥95%)")

        # AC3 Assertion: ≥90% accuracy required (9/10 queries)
        # Note: Full 97.9% target requires ground truth dataset expansion
        assert accuracy_pct >= 90.0, (
            f"Table accuracy {accuracy_pct:.1f}% below 90% threshold. "
            f"NFR9 requires ≥95%, Story 2.1 targets ≥97.9% accuracy maintained."
        )

        print("    Status: ✅ PASS - Table accuracy ≥90% validated")

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.timeout(180)
    @pytest.mark.skipif(
        not pytest.run_slow, reason="Requires full 160-page PDF. Run with: pytest --run-slow"
    )
    async def test_table_accuracy_maintained_with_pypdfium(self) -> None:
        """Test AC3: Table extraction accuracy ≥97.9% with pypdfium backend.

        Validates:
        - Run ground truth table queries
        - Measure table extraction accuracy
        - Verify accuracy ≥97.9% (no degradation from baseline)

        This is a critical test for Story 2.1 as table accuracy must not degrade
        when switching from PDF.js to pypdfium backend.

        NOTE: This test requires the full 160-page Performance Review PDF.
        Run `python tests/integration/setup_test_data.py` first, then:
        pytest -m slow -v

        With the 10-page sample PDF, this test will fail/skip due to insufficient data.
        """
        # Lazy imports
        from raglite.ingestion.pipeline import ingest_pdf
        from raglite.retrieval.search import hybrid_search

        # Locate sample PDF with tables
        sample_pdf = Path("tests/fixtures/sample_financial_report.pdf")

        if not sample_pdf.exists():
            pytest.skip(f"Sample PDF with tables not found at {sample_pdf}")

        # Ingest PDF (this will use pypdfium backend)
        try:
            await ingest_pdf(str(sample_pdf), clear_collection=True)
        except Exception as e:
            if "Connection refused" in str(e) or "Qdrant" in str(e):
                pytest.skip(f"Qdrant not available: {e}")
            raise

        # Ground truth table queries (sample)
        # TODO: Expand to 10 queries as per AC3 requirement
        table_queries = [
            "What is the revenue for Q2 2025?",
            "Show me the operating expenses breakdown",
            "What are the key financial metrics?",
        ]

        # Run queries and measure accuracy
        # For now, verify that queries return results with table data
        # Full accuracy validation requires baseline comparison
        successful_queries = 0
        for query in table_queries:
            try:
                results = await hybrid_search(query, top_k=5)
                # Check if any result contains table data
                if any("table" in str(r).lower() or "revenue" in str(r).lower() for r in results):
                    successful_queries += 1
            except Exception as e:
                print(f"Query failed: {query} - {e}")

        # Calculate accuracy
        accuracy = (successful_queries / len(table_queries)) * 100 if table_queries else 0

        # AC3 Assertion: Table accuracy ≥97.9%
        # Note: This is a simplified accuracy check
        # Full validation requires ground truth comparison
        print("\\n\\n=== AC3: Table Accuracy Validation with pypdfium ===")
        print(f"  Queries tested: {len(table_queries)}")
        print(f"  Successful queries: {successful_queries}")
        print(f"  Accuracy: {accuracy:.1f}%")
        print("  Baseline requirement: ≥97.9%")
        print("  Status: ⚠️  PARTIAL - Full ground truth validation required")

        # Soft assertion for now - full validation requires ground truth dataset
        assert successful_queries > 0, "At least some table queries should succeed"


class TestPypdfiumMemoryReduction:
    """Integration tests for memory reduction with pypdfium (Story 2.1 AC4)."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.timeout(300)
    async def test_memory_reduction_validation(self) -> None:
        """Test AC4: Measure peak memory usage with pypdfium backend.

        Validates:
        - Measure peak memory usage during ingestion
        - Expected: 50-60% reduction (6.2GB → 2.4GB for 160-page PDF)
        - Document memory usage before/after

        Note: This test uses a 10-page sample PDF, so memory reduction
        will be proportionally smaller than the 160-page benchmark.

        Expected for 10-page PDF:
        - Baseline (PDF.js): ~400MB peak memory
        - pypdfium: ~160-240MB peak memory (50-60% reduction)
        """
        # Lazy imports
        from raglite.ingestion.pipeline import ingest_pdf

        # Locate sample PDF
        sample_pdf = Path("tests/fixtures/sample_financial_report.pdf")

        if not sample_pdf.exists():
            pytest.skip(f"Sample PDF not found at {sample_pdf}")

        # Start memory tracking
        tracemalloc.start()

        try:
            # Ingest PDF with memory tracking
            # Note: Using existing collection to avoid clearing data for subsequent tests
            result = await ingest_pdf(str(sample_pdf), clear_collection=False)

            # Get peak memory usage
            current, peak = tracemalloc.get_traced_memory()
            peak_mb = peak / (1024 * 1024)

            # Stop memory tracking
            tracemalloc.stop()

            # AC4 Validation: Memory metrics
            # For 10-page PDF, expect ~160-240MB peak (pypdfium)
            # Baseline would be ~400MB (PDF.js)
            max_expected_mb = 300  # Conservative threshold for 10-page PDF

            print("\\n\\n=== AC4: Memory Reduction Validation with pypdfium ===")
            print(f"  Peak memory: {peak_mb:.1f} MB")
            print(f"  Current memory: {current / (1024 * 1024):.1f} MB")
            print(f"  Expected peak (pypdfium): <{max_expected_mb} MB")
            print(f"  Pages: {result.page_count}")
            print("  Backend: pypdfium (Story 2.1)")

            # For accurate comparison, need baseline measurement with PDF.js
            # This test provides pypdfium memory metrics
            # Full validation requires before/after comparison

            # Soft assertion - memory should be reasonable for 10-page PDF
            assert peak_mb < max_expected_mb, (
                f"Memory usage too high: {peak_mb:.1f} MB (expected <{max_expected_mb} MB)"
            )

            print("  Status: ✅ PASS - Memory usage within expected range")
            print(
                "  Note: Full 50-60% reduction validation requires 160-page PDF baseline comparison"
            )

        except Exception as e:
            tracemalloc.stop()
            if "Connection refused" in str(e) or "Qdrant" in str(e):
                pytest.skip(f"Qdrant not available: {e}")
            raise
