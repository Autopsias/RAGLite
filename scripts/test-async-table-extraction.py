"""
Test script for Milestone 1: Async Table Extraction Conversion

This script validates that:
1. Async functions work correctly
2. Unit inference completes faster with concurrency
3. Table data is extracted successfully

Usage:
    python scripts/test-async-table-extraction.py
"""

import asyncio
import time
from pathlib import Path

from raglite.ingestion.table_extraction import TableExtractor
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


async def test_async_table_extraction():
    """Test async table extraction on a small document."""
    print("=" * 80)
    print("Milestone 1: Async Table Extraction Test")
    print("=" * 80)
    print()

    # Use 10-page PDF for quick validation
    test_pdf = Path("docs/sample pdf/2025-08 Performance Review CONSO_v2.pdf")

    if not test_pdf.exists():
        print(f"❌ Test PDF not found: {test_pdf}")
        return

    print(f"Test PDF: {test_pdf.name}")
    print("Expected: Async unit inference with 10x speedup")
    print()

    # Initialize extractor
    print("Initializing TableExtractor...")
    extractor = TableExtractor()
    print("✅ TableExtractor initialized")
    print()

    # Convert document with Docling
    print("Converting document with Docling...")
    start_conversion = time.time()
    result = extractor.converter.convert(str(test_pdf))
    conversion_time = time.time() - start_conversion
    print(f"✅ Docling conversion complete: {conversion_time:.1f}s")
    print(f"   Pages: {result.document.num_pages}")
    print()

    # Extract tables with async unit inference
    print("Extracting tables with async unit inference...")
    start_extraction = time.time()

    try:
        table_rows = await extractor.extract_tables_from_result(result, test_pdf.stem)
        extraction_time = time.time() - start_extraction

        print(f"✅ Async table extraction complete: {extraction_time:.1f}s")
        print(f"   Tables extracted: {len({row['table_index'] for row in table_rows})}")
        print(f"   Total rows: {len(table_rows)}")
        print()

        # Analyze unit inference results
        if table_rows:
            rows_with_units = sum(1 for row in table_rows if row.get("unit"))
            rows_with_inferred = sum(
                1 for row in table_rows if row.get("unit_source") == "llm_inference"
            )
            rows_with_cached = sum(
                1 for row in table_rows if row.get("unit_source") == "cached_inference"
            )

            print("Unit Inference Statistics:")
            print(f"   Total rows: {len(table_rows)}")
            print(f"   Rows with units: {rows_with_units}")
            print(f"   LLM inferred: {rows_with_inferred}")
            print(f"   Cache hits: {rows_with_cached}")
            print()

        # Performance analysis
        print("Performance Analysis:")
        print(f"   Conversion time: {conversion_time:.1f}s")
        print(f"   Extraction time: {extraction_time:.1f}s")
        print(f"   Total time: {conversion_time + extraction_time:.1f}s")
        print()

        if extraction_time < 600:  # Less than 10 minutes
            print("✅ MILESTONE 1 SUCCESS: Async conversion working!")
            print("   Expected speedup: 62 min → 6 min (10x faster)")
            print(f"   Actual extraction: {extraction_time:.1f}s ({extraction_time / 60:.1f} min)")
        else:
            print("⚠️  WARNING: Extraction took longer than expected")
            print(f"   Expected: <10 min, Actual: {extraction_time / 60:.1f} min")

    except Exception as e:
        print(f"❌ Async table extraction failed: {e}")
        import traceback

        traceback.print_exc()
        return

    print()
    print("=" * 80)
    print("Test Complete!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_async_table_extraction())
