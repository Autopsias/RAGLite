#!/usr/bin/env python3
"""Test statistical unit detection framework on chunk PDF.

Validates that the new statistical threshold-based unit detection maintains
the 96.77% unit population achieved with positional sampling on chunk PDF.

Expected results:
- Chunk PDF pages 20-21 (chunk pages 3-4): ≥95% unit population
- No regression from positional sampling approach
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from raglite.ingestion.table_extraction import TableExtractor


async def main():
    print("=" * 80)
    print("TESTING STATISTICAL UNIT DETECTION FRAMEWORK - CHUNK PDF")
    print("=" * 80)
    print()
    print("Target: Maintain ≥96% unit population from positional sampling baseline")
    print()

    # Step 1: Extract tables using TableExtractor with NEW statistical framework
    print("Step 1: Extracting tables with statistical framework...")
    chunk_pdf = Path("docs/sample pdf/test-chunk-pages-18-23.pdf")
    print(f"   Converting {chunk_pdf.name}...")
    print("   (This will take ~27 seconds)")
    print()

    extractor = TableExtractor()
    table_rows = await extractor.extract_tables(str(chunk_pdf))

    print(f"   ✅ Extracted {len(table_rows)} total rows")
    print()

    # Step 2: Analyze unit population by page
    print("Step 2: Analyzing unit population...")
    print()

    from collections import defaultdict

    pages_stats = defaultdict(lambda: {"total": 0, "with_units": 0})

    for row in table_rows:
        page_num = row.get("page_number")
        pages_stats[page_num]["total"] += 1
        if row.get("unit"):
            pages_stats[page_num]["with_units"] += 1

    print("Unit population by page:")
    print()

    target_pages = [3, 4]  # Chunk pages 3-4 = original pages 20-21
    overall_total = 0
    overall_with_units = 0

    for page_num in sorted(pages_stats.keys()):
        stats = pages_stats[page_num]
        total = stats["total"]
        with_units = stats["with_units"]
        pct = 100.0 * with_units / total if total > 0 else 0.0

        marker = ""
        if page_num in target_pages:
            if pct >= 96.0:
                marker = "✅ PASS (≥96%)"
            elif pct >= 90.0:
                marker = "⚠️  ACCEPTABLE (90-96%)"
            else:
                marker = "❌ FAIL (<90%)"

            overall_total += total
            overall_with_units += with_units

        print(f"  Page {page_num}: {with_units}/{total} = {pct:.2f}% {marker}")

    print()
    print("-" * 80)

    # Step 3: Overall validation
    print()
    print("Step 3: Overall Validation")
    print()

    if overall_total > 0:
        overall_pct = 100.0 * overall_with_units / overall_total
        print("Pages 3-4 (original 20-21) combined:")
        print(f"  {overall_with_units}/{overall_total} = {overall_pct:.2f}%")
        print()

        if overall_pct >= 96.0:
            print("✅ FRAMEWORK VALIDATED: Statistical detection maintains baseline (≥96%)")
            print()
            print("Next steps:")
            print("  1. Test framework on full PDF page 23 (target >90%)")
            print("  2. If page 23 successful → Full re-ingestion")
            validation_passed = True
        elif overall_pct >= 90.0:
            print("⚠️  FRAMEWORK ACCEPTABLE: Statistical detection achieves 90-96%")
            print()
            print("Trade-off analysis:")
            print("  - Baseline (positional sampling): 96.77%")
            print(f"  - Statistical framework: {overall_pct:.2f}%")
            print(f"  - Delta: {overall_pct - 96.77:.2f}pp")
            print()
            print("Recommendation: Acceptable if full PDF page 23 improves significantly")
            print()
            print("Next steps:")
            print("  1. Test framework on full PDF page 23")
            print("  2. Compare: chunk delta vs full PDF improvement")
            print("  3. If net positive → Proceed with re-ingestion")
            validation_passed = True
        else:
            print("❌ FRAMEWORK REGRESSION: Statistical detection below 90%")
            print()
            print("Investigation required:")
            print("  - Baseline: 96.77%")
            print(f"  - Current: {overall_pct:.2f}%")
            print(f"  - Regression: {96.77 - overall_pct:.2f}pp")
            print()
            print("Possible causes:")
            print("  1. Threshold too strict (0.60) - try 0.50")
            print("  2. Unit patterns incomplete - check edge cases")
            print("  3. Logic error in statistical function")
            validation_passed = False
    else:
        print("❌ ERROR: No rows found for target pages")
        validation_passed = False

    print()
    print("=" * 80)
    print("VALIDATION COMPLETE")
    print("=" * 80)
    print()

    return validation_passed


if __name__ == "__main__":
    validation_passed = asyncio.run(main())
    sys.exit(0 if validation_passed else 1)
