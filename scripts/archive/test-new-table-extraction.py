#!/usr/bin/env python3
"""
Quick integration test for new table_cells-based extraction.

Tests the updated TableExtractor on a small PDF to verify:
1. Multi-header detection works
2. Entity/metric extraction is correct
3. Data is structured properly for PostgreSQL
"""

import asyncio
from pathlib import Path

from raglite.ingestion.table_extraction import TableExtractor
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


async def test_new_extraction():
    """Test new table_cells-based extraction."""
    print("=" * 80)
    print("NEW TABLE EXTRACTION TEST (table_cells API)")
    print("=" * 80)
    print()

    pdf_path = "docs/sample pdf/2025-08 Performance Review CONSO_v2.pdf"

    if not Path(pdf_path).exists():
        print(f"❌ PDF not found: {pdf_path}")
        return

    print(f"Testing PDF: {pdf_path}")
    print("Extracting tables with new table_cells approach...")
    print()

    # Create extractor
    extractor = TableExtractor()

    # Extract tables
    try:
        rows = await extractor.extract_tables(pdf_path)

        print("=" * 80)
        print("EXTRACTION RESULTS")
        print("=" * 80)
        print(f"Total rows extracted: {len(rows)}")
        print()

        # Analyze data quality
        entities = {r["entity"] for r in rows if r["entity"]}
        metrics = {r["metric"] for r in rows if r["metric"]}
        periods = {r["period"] for r in rows if r["period"]}

        print(f"Unique entities: {len(entities)}")
        print(f"Unique metrics: {len(metrics)}")
        print(f"Unique periods: {len(periods)}")
        print()

        # Show sample data
        print("=" * 80)
        print("SAMPLE ROWS (First 5):")
        print("=" * 80)
        for i, row in enumerate(rows[:5], 1):
            print(f"\nRow {i}:")
            print(f"  Entity: {row['entity']}")
            print(f"  Metric: {row['metric']}")
            print(f"  Period: {row['period']}")
            print(f"  Value: {row['value']}")
            print(f"  Unit: {row['unit']}")
            print(f"  Fiscal Year: {row['fiscal_year']}")
            print(f"  Page: {row['page_number']}")

        print()
        print("=" * 80)
        print("DATA QUALITY CHECK")
        print("=" * 80)

        # Check for corrupted data (the 25.8% failure indicators)
        corrupted_entities = [e for e in entities if e in ("-", "0", "Jan-25", "Feb-25")]
        corrupted_metrics = [m for m in metrics if m in ("Group", "3,68", "7,45")]

        if corrupted_entities:
            print(f"⚠️  WARNING: Found corrupted entities: {corrupted_entities}")
        else:
            print("✅ No corrupted entities (like '-', '0', 'Jan-25')")

        if corrupted_metrics:
            print(f"⚠️  WARNING: Found corrupted metrics: {corrupted_metrics}")
        else:
            print("✅ No corrupted metrics (like 'Group', '3,68')")

        # Check for proper entity examples
        good_entities = [e for e in entities if "Portugal" in e or "Cement" in e or "Angola" in e]
        if good_entities:
            print(f"✅ Found expected entities: {good_entities[:3]}")
        else:
            print("⚠️  WARNING: No expected entities found (Portugal, Cement, etc.)")

        # Check for proper metric examples
        good_metrics = [
            m for m in metrics if any(word in m for word in ["Variable", "Cost", "EBITDA", "Ratio"])
        ]
        if good_metrics:
            print(f"✅ Found expected metrics: {good_metrics[:3]}")
        else:
            print("⚠️  WARNING: No expected metrics found (Variable Cost, EBITDA, etc.)")

        print()
        print("=" * 80)
        print("SUMMARY")
        print("=" * 80)

        if not corrupted_entities and not corrupted_metrics and good_entities and good_metrics:
            print("✅ SUCCESS - Table extraction looks correct!")
            print("   - No corrupted data detected")
            print("   - Entity/metric structure preserved")
            print(f"   - Ready to re-ingest ({len(rows)} rows)")
        else:
            print("⚠️  ISSUES DETECTED - Review extraction logic")

    except Exception as e:
        print(f"❌ Extraction failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_new_extraction())
