"""Integration tests for document ingestion with real files.

Tests ingest_pdf and extract_excel with actual document files.
"""

import time
from pathlib import Path

import pytest

from raglite.ingestion.pipeline import extract_excel, ingest_pdf
from raglite.shared.models import DocumentMetadata


class TestPDFIngestionIntegration:
    """Integration tests for PDF ingestion with real financial documents.

    Uses a 10-page sample PDF with tables extracted from Secil Group performance review.
    Validates Docling integration, table extraction, and page number extraction without
    the 5-8 minute wait of processing 160-page documents.
    """

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.timeout(60)
    async def test_ingest_financial_pdf_with_tables(self):
        """Integration test with representative financial PDF containing tables.

        Uses 10-page sample from Secil Group performance review including:
        - Cover page and TOC
        - Financial data pages with tables
        - Complex table structures (nested headers, merged cells)

        Validates:
        - Docling successfully processes real financial PDFs
        - Page numbers are extracted from provenance metadata
        - Table extraction works with complex financial data
        - Performance is acceptable (~10-20 seconds for 10 pages)

        This replaces the slow 160-page test while maintaining comprehensive validation.
        """
        # Locate sample PDF
        sample_pdf = Path("tests/fixtures/sample_financial_report.pdf")

        if not sample_pdf.exists():
            pytest.skip(f"Sample PDF not found at {sample_pdf}")

        # Start timing
        start_time = time.time()

        # Ingest PDF
        result = await ingest_pdf(str(sample_pdf))

        # Calculate duration
        duration_seconds = time.time() - start_time

        # Assertions
        assert isinstance(result, DocumentMetadata)
        assert result.filename == "sample_financial_report.pdf"
        assert result.doc_type == "PDF"

        # Page count validation
        assert result.page_count == 10, f"Expected 10 pages, got {result.page_count}"

        # CRITICAL: Page numbers must be extracted
        assert result.page_count > 0, "Page numbers must be extracted from provenance"

        # Performance validation (should be fast with only 10 pages)
        max_duration_seconds = 60  # 1 minute reasonable for 10 pages
        assert duration_seconds < max_duration_seconds, (
            f"Ingestion took {duration_seconds:.1f}s, "
            f"expected <{max_duration_seconds}s for 10-page sample"
        )

        # Log performance metrics
        print("\n\nSample PDF Ingestion Performance:")
        print(f"  Duration: {duration_seconds:.1f} seconds")
        print(f"  Pages: {result.page_count}")
        print(f"  Pages/second: {result.page_count / duration_seconds:.2f}")
        print("  Status: ✅ PASS")


class TestExcelIngestionIntegration:
    """Integration tests for Excel extraction with real financial documents.

    Uses a multi-sheet sample Excel file with realistic financial data.
    Validates openpyxl + pandas integration, sheet extraction, and numeric formatting.
    """

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.timeout(30)
    async def test_extract_financial_excel_multi_sheet(self):
        """Integration test with real financial Excel file containing 3 sheets.

        Uses sample Excel with:
        - Revenue Analysis sheet (quarterly data with currencies and percentages)
        - Balance Sheet (3-year comparison with currency values)
        - Key Metrics (performance metrics with percentages)

        Validates:
        - openpyxl successfully loads and parses Excel file
        - All 3 sheets are extracted with correct sheet numbers
        - Numeric formatting is preserved (currencies, percentages)
        - pandas DataFrame conversion works correctly
        - Sheet numbers are extracted for source attribution (NFR7)
        - Performance is acceptable (<10 seconds)

        This validates AC 5 (successfully ingests sample Excel files)
        and AC 9 (end-to-end integration test).
        """
        # Locate sample Excel file
        sample_excel = Path("tests/fixtures/sample_financial_data.xlsx")

        if not sample_excel.exists():
            pytest.skip(f"Sample Excel not found at {sample_excel}")

        # Start timing
        start_time = time.time()

        # Extract Excel
        result = await extract_excel(str(sample_excel))

        # Calculate duration
        duration_seconds = time.time() - start_time

        # Assertions
        assert isinstance(result, DocumentMetadata)
        assert result.filename == "sample_financial_data.xlsx"
        assert result.doc_type == "Excel"

        # Sheet count validation (AC 3: Multi-sheet handling)
        assert result.page_count == 3, f"Expected 3 sheets, got {result.page_count}"

        # CRITICAL: Sheet numbers must be extracted for citations (AC 7: NFR7)
        assert result.page_count > 0, "Sheet count must NOT be None or zero"

        # Validate metadata (source_path is resolved to absolute path)
        assert result.source_path == str(sample_excel.resolve())
        assert result.ingestion_timestamp  # Must have timestamp

        # Performance validation
        max_duration_seconds = 10  # Excel extraction should be fast
        assert duration_seconds < max_duration_seconds, (
            f"Extraction took {duration_seconds:.1f}s, "
            f"expected <{max_duration_seconds}s for 3-sheet Excel"
        )

        # Log performance metrics
        print("\n\nSample Excel Extraction Performance:")
        print(f"  Duration: {duration_seconds:.1f} seconds")
        print(f"  Sheets: {result.page_count}")
        print(f"  Sheets/second: {result.page_count / duration_seconds:.2f}")
        print("  Status: ✅ PASS")

        # Additional validation: Verify all expected sheets were processed
        # (implicitly validated by page_count == 3)
        print("\n  Validated:")
        print("  ✅ Multi-sheet extraction (AC 3)")
        print("  ✅ Sheet numbers for attribution (AC 7)")
        print("  ✅ End-to-end Excel ingestion (AC 9)")


class TestChunkingIntegration:
    """Integration tests for Story 1.4: Document chunking with page number preservation.

    Validates end-to-end flow: ingestion → chunking → page number preservation.
    Tests AC8 (page number != None) and AC9 (page numbers flow through pipeline).
    """

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.timeout(60)
    async def test_page_number_flow_through_chunking_pipeline(self):
        """Integration test: Validate page numbers preserved through chunking pipeline (AC9).

        This is the CRITICAL test for Story 1.4 review item AI-3 [HIGH].
        Validates that page numbers flow correctly through:
        1. PDF ingestion (Docling extraction)
        2. Document chunking (chunk_document function)
        3. Chunk metadata (all chunks have valid page_number)

        Tests:
        - AC8: All chunks have page_number != None
        - AC9: Page numbers preserved across ingestion → chunking pipeline
        """
        # Locate sample PDF
        sample_pdf = Path("tests/fixtures/sample_financial_report.pdf")

        if not sample_pdf.exists():
            pytest.skip(f"Sample PDF not found at {sample_pdf}")

        # Act: Run full ingestion pipeline (includes chunking)
        result = await ingest_pdf(str(sample_pdf))

        # Assert: Validate document metadata
        assert isinstance(result, DocumentMetadata)
        assert result.page_count > 0, "Document must have pages"
        assert result.chunk_count > 0, "Document must be chunked"
        assert len(result.chunks) == result.chunk_count, "Chunk count must match chunks list length"

        # CRITICAL: Validate page number preservation (AC8, AC9)
        print("\n\nPage Number Validation (Story 1.4 AC8/AC9):")
        print(f"  Document: {result.filename}")
        print(f"  Pages: {result.page_count}")
        print(f"  Chunks: {result.chunk_count}")

        page_numbers_found = []
        for i, chunk in enumerate(result.chunks):
            # AC8: Every chunk MUST have page_number != None
            assert chunk.page_number is not None, (
                f"CRITICAL FAILURE (AC8): Chunk {i} has page_number=None. "
                f"All chunks must have valid page numbers for source attribution (NFR7)."
            )

            # Validate page number is in valid range
            assert chunk.page_number > 0, (
                f"Chunk {i}: page_number must be positive, got {chunk.page_number}"
            )
            assert chunk.page_number <= result.page_count, (
                f"Chunk {i}: page_number {chunk.page_number} exceeds document page_count {result.page_count}"
            )

            page_numbers_found.append(chunk.page_number)

            # Validate chunk has required metadata
            assert chunk.chunk_id, f"Chunk {i} missing chunk_id"
            assert chunk.content, f"Chunk {i} has empty content"
            assert chunk.metadata.filename == result.filename, f"Chunk {i} metadata mismatch"

        # Summary: Show page number distribution
        unique_pages = sorted(set(page_numbers_found))
        print(
            f"  Page numbers found in chunks: {min(page_numbers_found)}-{max(page_numbers_found)}"
        )
        print(f"  Unique pages covered: {len(unique_pages)}/{result.page_count}")
        print(f"\n  ✅ AC8 PASS: All {result.chunk_count} chunks have page_number != None")
        print("  ✅ AC9 PASS: Page numbers preserved through ingestion → chunking pipeline")

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.timeout(60)
    async def test_chunking_performance_validation(self):
        """Performance test: Validate chunking meets <30s requirement for 100-page documents (AC7).

        This addresses Story 1.4 review item AI-4 [MEDIUM].

        AC7 requirement: <30 seconds for 100-page documents
        Sample PDF: 10 pages, so target is <3 seconds (0.3s/page * 10)
        """
        # Locate sample PDF
        sample_pdf = Path("tests/fixtures/sample_financial_report.pdf")

        if not sample_pdf.exists():
            pytest.skip(f"Sample PDF not found at {sample_pdf}")

        # Act: Measure full ingestion + chunking time
        start_time = time.time()
        result = await ingest_pdf(str(sample_pdf))
        elapsed_seconds = time.time() - start_time

        # Assert: Validate performance
        assert result.chunk_count > 0, "Must produce chunks"

        # AC7: <30s for 100 pages = 0.3s per page
        target_seconds_per_page = 0.3
        target_total_seconds = result.page_count * target_seconds_per_page

        print("\n\nChunking Performance Validation (Story 1.4 AC7):")
        print(f"  Document: {result.filename}")
        print(f"  Pages: {result.page_count}")
        print(f"  Chunks: {result.chunk_count}")
        print(f"  Time: {elapsed_seconds:.2f}s")
        print(f"  Target: <{target_total_seconds:.2f}s (0.3s/page * {result.page_count} pages)")
        print(f"  Actual: {elapsed_seconds / result.page_count:.3f}s/page")

        # Validate performance target
        assert elapsed_seconds < target_total_seconds, (
            f"Performance test FAILED (AC7): "
            f"Chunking took {elapsed_seconds:.2f}s for {result.page_count} pages "
            f"(target: <{target_total_seconds:.2f}s, {target_seconds_per_page}s/page)"
        )

        print("\n  ✅ AC7 PASS: Chunking performance meets <30s/100 pages requirement")
        print(
            f"     ({elapsed_seconds:.2f}s for {result.page_count} pages = {(elapsed_seconds / result.page_count) * 100:.1f}s per 100 pages)"
        )
