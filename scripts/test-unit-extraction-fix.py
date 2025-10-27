#!/usr/bin/env python3
"""Quick test of unit extraction fix on pages 20-21.

This script:
1. Clears page 20-21 data from PostgreSQL
2. Re-ingests just pages 20-21 with the NEW unit extraction code
3. Verifies units are now populated for GT-001 and GT-002
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg2

from raglite.ingestion.pipeline import ingest_document
from raglite.shared.config import settings


async def test_unit_extraction_fix():
    """Test unit extraction fix on pages 20-21."""

    print("=" * 80)
    print("TESTING UNIT EXTRACTION FIX - PAGES 20-21 ONLY")
    print("=" * 80)
    print()

    # Step 1: Clear existing page 20-21 data
    print("Step 1: Clearing page 20-21 data from PostgreSQL...")
    conn = psycopg2.connect(
        host=settings.postgres_host,
        port=settings.postgres_port,
        database=settings.postgres_db,
        user=settings.postgres_user,
        password=settings.postgres_password,
    )

    cursor = conn.cursor()
    cursor.execute("DELETE FROM financial_tables WHERE page_number IN (20, 21)")
    deleted_count = cursor.rowcount
    conn.commit()
    print(f"   Deleted {deleted_count} rows from pages 20-21")
    print()

    # Check remaining data
    cursor.execute("SELECT COUNT(*) FROM financial_tables")
    remaining = cursor.fetchone()[0]
    print(f"   Remaining rows in database: {remaining:,}")
    print()

    cursor.close()
    conn.close()

    # Step 2: Re-ingest pages 20-21 with NEW code
    print("Step 2: Re-ingesting pages 20-21 with NEW unit extraction code...")
    print("   Using: docs/sample pdf/test-pages-4-10-20.pdf (contains page 20)")
    print("   This will take ~10 seconds...")
    print()

    # Use the test PDF that contains page 20
    pdf_path = Path("docs/sample pdf/test-pages-4-10-20.pdf")

    if not pdf_path.exists():
        print(f"❌ ERROR: Test PDF not found: {pdf_path}")
        print("   Using full PDF instead (will take longer)...")
        pdf_path = Path(
            "docs/sample pdf/split/2025-08 Performance Review CONSO_v2_part01_pages001-040.pdf"
        )

    # Ingest with table extraction
    try:
        await ingest_document(
            pdf_path,
            extract_tables=True,
            update_collections=False,  # Don't update Qdrant, just PostgreSQL
        )
        print("   ✅ Re-ingestion complete")
    except Exception as e:
        print(f"   ❌ Re-ingestion failed: {e}")
        return

    print()

    # Step 3: Verify units are populated
    print("Step 3: Verifying unit population...")
    print()

    conn = psycopg2.connect(
        host=settings.postgres_host,
        port=settings.postgres_port,
        database=settings.postgres_db,
        user=settings.postgres_user,
        password=settings.postgres_password,
    )

    cursor = conn.cursor()

    # Check overall unit population on page 20
    cursor.execute("""
        SELECT
            COUNT(*) as total_rows,
            COUNT(unit) as rows_with_unit,
            ROUND(COUNT(unit) * 100.0 / COUNT(*), 2) as percentage
        FROM financial_tables
        WHERE page_number = 20
    """)

    total, with_unit, pct = cursor.fetchone()
    print("Page 20 Unit Population:")
    print(f"   Total rows: {total}")
    print(f"   Rows with unit: {with_unit}")
    print(f"   Percentage: {pct}%")
    print()

    # Check GT-001: Group EBITDA
    print("GT-001 (Group EBITDA YTD August 2025):")
    cursor.execute("""
        SELECT entity, metric, value, unit, period
        FROM financial_tables
        WHERE page_number = 20
        AND entity = 'GROUP'
        AND metric ILIKE '%EBITDA%'
        AND period ILIKE '%YTD%Aug-25%'
        LIMIT 1
    """)

    row = cursor.fetchone()
    if row:
        entity, metric, value, unit, period = row
        status = "✅ HAS UNIT" if unit else "❌ NULL UNIT"
        print(f"   entity={entity}")
        print(f"   metric={metric}")
        print(f"   value={value}")
        print(f"   unit={unit} {status}")
        print(f"   period={period}")

        if unit:
            print(f"   🎉 SUCCESS! Unit extracted from header row: '{unit}'")
        else:
            print("   ⚠️  FAILED! Unit still NULL - fix may not be working")
    else:
        print("   ❌ No rows found")

    print()

    # Check GT-002: Portugal Variable Cost
    print("GT-002 (Portugal Variable Cost August 2025):")
    cursor.execute("""
        SELECT entity, metric, value, unit, period
        FROM financial_tables
        WHERE page_number = 20
        AND entity = 'Portugal'
        AND metric = 'Variable Cost'
        AND period = 'Aug-25'
        LIMIT 1
    """)

    row = cursor.fetchone()
    if row:
        entity, metric, value, unit, period = row
        status = "✅ HAS UNIT" if unit else "❌ NULL UNIT"
        print(f"   entity={entity}")
        print(f"   metric={metric}")
        print(f"   value={value}")
        print(f"   unit={unit} {status}")
        print(f"   period={period}")

        if unit:
            print(f"   🎉 SUCCESS! Unit extracted from header row: '{unit}'")
        else:
            print("   ⚠️  FAILED! Unit still NULL - fix may not be working")
    else:
        print("   ❌ No rows found")

    print()

    cursor.close()
    conn.close()

    # Summary
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    if with_unit > 0 and pct > 50:
        print("✅ PASS - Units are being extracted from header rows!")
        print()
        print("Next step: Run full re-ingestion to populate all pages:")
        print("   python scripts/clear-postgres-and-reingest.py")
    else:
        print("❌ FAIL - Units still NULL, fix may not be working correctly")
        print()
        print("Debug steps:")
        print("   1. Check adaptive_table_extraction.py lines 784-847")
        print("   2. Verify column_unit_map is being populated")
        print("   3. Check if table has 3+ header rows")


if __name__ == "__main__":
    asyncio.run(test_unit_extraction_fix())
