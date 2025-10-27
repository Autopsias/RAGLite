#!/usr/bin/env python3
"""Test statistical unit detection framework on full PDF page 23.

Validates that the new statistical threshold-based unit detection improves
unit population on page 23 from 37.07% baseline toward target of >90%.

Expected results:
- Full PDF page 23: Target ≥90% unit population
- Improvement from Phase 2.7.2 baseline (37.07%)
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from raglite.ingestion.table_extraction import TableExtractor


async def main():
    print("=" * 80)
    print("TESTING STATISTICAL UNIT DETECTION FRAMEWORK - FULL PDF PAGE 23")
    print("=" * 80)
    print()
    print("Target: Achieve ≥90% unit population on page 23")
    print("Baseline: 37.07% (Phase 2.7.2 with positional sampling)")
    print()

    # Step 1: Extract tables using TableExtractor with statistical framework
    print("Step 1: Extracting tables with statistical framework...")
    full_pdf = Path("docs/sample pdf/2025-08 Performance Review CONSO_v2.pdf")
    print(f"   Converting {full_pdf.name}...")
    print("   (This will take ~14 minutes for full 160-page PDF)")
    print()

    extractor = TableExtractor()
    table_rows = await extractor.extract_tables(str(full_pdf))

    print(f"   ✅ Extracted {len(table_rows)} total rows")
    print()

    # Step 2: Analyze unit population for page 23 specifically
    print("Step 2: Analyzing unit population for page 23...")
    print()

    page_23_rows = [row for row in table_rows if row.get("page_number") == 23]

    if not page_23_rows:
        print("❌ ERROR: No rows found for page 23")
        print()
        print("This suggests:")
        print("  1. Page 23 has no tables detected")
        print("  2. Table extraction failed for page 23")
        print("  3. Page numbering mismatch")
        print()
        return False

    total_rows = len(page_23_rows)
    rows_with_units = sum(1 for r in page_23_rows if r.get("unit"))
    unit_pct = 100.0 * rows_with_units / total_rows if total_rows > 0 else 0.0

    print("Page 23 Results:")
    print(f"  Total rows: {total_rows}")
    print(f"  Rows with units: {rows_with_units}")
    print(f"  Unit population: {unit_pct:.2f}%")
    print()

    # Sample some rows to inspect unit extraction
    print("Sample rows (first 10):")
    for i, row in enumerate(page_23_rows[:10], 1):
        entity = row.get("entity", "N/A")
        metric = row.get("metric", "N/A")
        value = row.get("value", "N/A")
        unit = row.get("unit", "NULL")
        marker = "✅" if unit != "NULL" else "❌"
        print(f"  {i}. {marker} {entity} | {metric} | {value} | Unit: {unit}")
    print()

    # Step 3: Compare with baseline and validate
    print("-" * 80)
    print()
    print("Step 3: Comparison with Baseline")
    print()

    baseline_pct = 37.07
    improvement = unit_pct - baseline_pct

    print(f"Phase 2.7.2 Baseline (positional sampling): {baseline_pct:.2f}%")
    print(f"Phase 2.7.3 Statistical Framework: {unit_pct:.2f}%")
    print(f"Improvement: {improvement:+.2f}pp")
    print()

    # Validation logic
    validation_passed = False

    if unit_pct >= 90.0:
        print("✅ TARGET ACHIEVED: Statistical framework achieves ≥90% on page 23")
        print()
        print("Next steps:")
        print("  1. Full re-ingestion with statistical framework")
        print("  2. Validate AC4 accuracy metrics")
        print("  3. Phase 2.7.3 COMPLETE")
        validation_passed = True
    elif unit_pct >= 70.0:
        print("⚠️  PARTIAL SUCCESS: Statistical framework achieves 70-90%")
        print()
        print("Analysis:")
        print(f"  - Baseline: {baseline_pct:.2f}%")
        print(f"  - Current: {unit_pct:.2f}%")
        print(f"  - Improvement: {improvement:+.2f}pp")
        print()
        print("Recommendation: Acceptable for full re-ingestion")
        print()
        print("Next steps:")
        print("  1. Proceed with full re-ingestion")
        print("  2. Monitor AC4 accuracy metrics")
        print("  3. If needed, tune threshold or add page-specific strategies")
        validation_passed = True
    elif improvement > 10.0:
        print("⚠️  SIGNIFICANT IMPROVEMENT: +10pp but below 70% target")
        print()
        print("Analysis:")
        print(f"  - Baseline: {baseline_pct:.2f}%")
        print(f"  - Current: {unit_pct:.2f}%")
        print(f"  - Improvement: {improvement:+.2f}pp")
        print()
        print("Recommendation: Investigate page 23 table structure")
        print()
        print("Possible causes:")
        print("  1. Page 23 has different table layout (not transposed)")
        print("  2. Units in different columns (not column 1)")
        print("  3. Different unit notation patterns")
        print()
        print("Next steps:")
        print("  1. Inspect page 23 table structure manually")
        print("  2. Run diagnostic script to analyze cell layout")
        print("  3. Consider page-specific detection strategy")
        validation_passed = False
    else:
        print("❌ NO IMPROVEMENT: Statistical framework does not improve page 23")
        print()
        print("Analysis:")
        print(f"  - Baseline: {baseline_pct:.2f}%")
        print(f"  - Current: {unit_pct:.2f}%")
        print(f"  - Change: {improvement:+.2f}pp")
        print()
        print("Root cause investigation required:")
        print("  1. Page 23 may have fundamentally different structure")
        print("  2. Units may not be in column 1")
        print("  3. Table may not be transposed format")
        print()
        print("Recommended actions:")
        print("  1. Run diagnostic script on page 23:")
        print("     python scripts/diagnose-header-cells-page23.py")
        print("  2. Manually inspect page 23 in PDF")
        print("  3. Compare page 23 structure with pages 20-21")
        print()
        print("Decision:")
        print("  - If page 23 is fundamentally different → Accept lower coverage")
        print("  - If page 23 is similar → Requires additional investigation")
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
