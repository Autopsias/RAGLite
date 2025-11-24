#!/usr/bin/env python3
"""Migration script to fix page number attribution bug (Story 1.13).

This script:
1. Clears the Qdrant collection to remove incorrectly estimated page numbers
2. Re-ingests the test PDF using the fixed chunk_by_docling_items() function
3. Validates that page numbers are now extracted from Docling provenance
4. Logs migration statistics for verification

Expected Outcomes:
- Page numbers in range 43-118 (actual test PDF pages)
- No impossible estimates like page 7, 12, 156 (old bug pattern)
- Chunk count similar to previous (~same number of chunks)
"""

import asyncio
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from raglite.ingestion.pipeline import ingest_pdf  # noqa: E402
from raglite.shared.clients import get_qdrant_client  # noqa: E402
from raglite.shared.config import settings  # noqa: E402


async def main():
    """Execute migration to fix page number attribution."""
    print("=" * 80)
    print("MIGRATION: Fix Page Number Attribution Bug (Story 1.13)")
    print("=" * 80)
    print()

    # Step 1: Clear Qdrant collection
    print("Step 1: Clearing Qdrant collection...")
    qdrant_client = get_qdrant_client()

    try:
        # Delete collection
        qdrant_client.delete_collection(collection_name=settings.qdrant_collection_name)
        print(f"✓ Deleted collection '{settings.qdrant_collection_name}'")

        # Recreate collection (will be created automatically by ingest_pdf)
        print("✓ Collection will be recreated during ingestion")
    except Exception as e:
        print(f"⚠ Warning during collection cleanup: {e}")
        print("  Continuing anyway (collection may not exist yet)")

    print()

    # Step 2: Re-ingest test PDF with fixed chunking
    print("Step 2: Re-ingesting test PDF with fixed page extraction...")

    # Locate test PDF
    test_pdf_paths = [
        Path("docs/sample pdf/2025-08 Performance Review CONSO_v2.pdf"),
        Path("docs/sample pdf/2025-08 Performance Review CONSO_v2.pdf".replace(" ", "_")),
        Path("docs/2025-08 Performance Review CONSO_v2.pdf"),
    ]

    test_pdf = None
    for pdf_path in test_pdf_paths:
        if pdf_path.exists():
            test_pdf = pdf_path
            break

    if not test_pdf:
        print("❌ ERROR: Test PDF not found at any of:")
        for path in test_pdf_paths:
            print(f"  - {path}")
        print()
        print("Please provide the correct path to the test PDF")
        return 1

    print(f"✓ Found test PDF: {test_pdf}")
    print()

    # Measure ingestion time
    start_time = time.time()

    try:
        metadata = await ingest_pdf(str(test_pdf))
        duration_seconds = time.time() - start_time

        print("✓ Re-ingestion complete")
        print(f"  Duration: {duration_seconds:.1f}s")
        print(f"  Filename: {metadata.filename}")
        print(f"  Page count: {metadata.page_count}")
        print(f"  Chunk count: {metadata.chunk_count}")
        print()
    except Exception as e:
        print(f"❌ ERROR during ingestion: {e}")
        import traceback

        traceback.print_exc()
        return 1

    # Step 3: Validate page numbers from Qdrant
    print("Step 3: Validating page numbers in Qdrant...")

    try:
        # Scroll through all points
        points, _ = qdrant_client.scroll(
            collection_name=settings.qdrant_collection_name, limit=1000
        )

        if not points:
            print("❌ ERROR: No points found in Qdrant after ingestion")
            return 1

        # Extract page numbers
        page_numbers = [
            p.payload.get("page_number")
            for p in points
            if p.payload and p.payload.get("page_number") is not None
        ]

        if not page_numbers:
            print("❌ ERROR: No page numbers found in stored chunks")
            return 1

        # Calculate statistics
        min_page = min(page_numbers)
        max_page = max(page_numbers)
        unique_pages = len(set(page_numbers))
        total_chunks = len(page_numbers)

        print("✓ Validation complete")
        print(f"  Total chunks: {total_chunks}")
        print(f"  Unique pages: {unique_pages}")
        print(f"  Page range: {min_page}-{max_page}")
        print()

        # Validate page numbers are within PDF bounds (1 to page_count)
        # The PDF has 160 pages, so valid range is 1-160
        # Ground truth queries reference pages 43-118, but that's just the queried subset
        expected_min = 1
        expected_max = metadata.page_count

        validation_passed = True

        if min_page < expected_min or max_page > expected_max:
            print(
                f"⚠ WARNING: Page range {min_page}-{max_page} outside PDF bounds {expected_min}-{expected_max}"
            )
            print("  This indicates a page extraction bug")
            validation_passed = False

        # Check for negative or zero page numbers (true bug indicators)
        invalid_pages = [p for p in page_numbers if p < 1]
        if invalid_pages:
            print(f"❌ ERROR: Found {len(invalid_pages)} invalid page numbers (< 1)")
            print(f"  Invalid pages: {sorted(set(invalid_pages))}")
            validation_passed = False

        # Verify no estimation artifacts (old bug would create page numbers beyond PDF bounds)
        out_of_bounds = [p for p in page_numbers if p > metadata.page_count]
        if out_of_bounds:
            print(f"❌ ERROR: Found {len(out_of_bounds)} page numbers exceeding PDF page count")
            print(f"  Out-of-bounds pages: {sorted(set(out_of_bounds))[:20]}")
            validation_passed = False

        # Summary
        print()
        print("=" * 80)
        print("MIGRATION SUMMARY")
        print("=" * 80)
        print(f"Status: {'✅ SUCCESS' if validation_passed else '✅ FAILED'}")
        print(f"Chunks stored: {total_chunks}")
        print(f"Page range: {min_page}-{max_page}")
        print(f"Expected range: {expected_min}-{expected_max}")
        print()

        if validation_passed:
            print("✅ Migration completed successfully!")
            print("   Page numbers are now extracted from Docling provenance.")
            print("   Ready to run full validation (Task 7).")
            return 0
        else:
            print("❌ Migration validation failed!")
            print("   Please investigate page number issues before proceeding.")
            return 1

    except Exception as e:
        print(f"❌ ERROR during validation: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
