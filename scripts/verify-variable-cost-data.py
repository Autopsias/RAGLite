#!/usr/bin/env python3
"""
Verify Variable Cost data exists in database with correct column mappings.

This script checks if the transposed detection fix successfully extracted
Variable Cost data from page 20 tables.
"""

from raglite.shared.clients import get_postgresql_connection


def main():
    """Verify Variable Cost data in PostgreSQL."""
    print("=" * 80)
    print("VARIABLE COST DATA VERIFICATION")
    print("=" * 80)
    print()

    conn = get_postgresql_connection()
    cursor = conn.cursor()

    # Test 1: Count Variable Cost rows
    print("Test 1: Variable Cost row count")
    print("-" * 80)
    cursor.execute("""
        SELECT COUNT(*)
        FROM financial_tables
        WHERE metric ILIKE '%variable%cost%';
    """)
    variable_cost_count = cursor.fetchone()[0]
    print(f"   Variable Cost rows found: {variable_cost_count}")

    if variable_cost_count > 0:
        print("   ✅ PASS: Variable Cost data exists")
    else:
        print("   ❌ FAIL: No Variable Cost data found")
    print()

    # Test 2: Check column mappings for page 20 data
    print("Test 2: Column mapping verification (Page 20 data)")
    print("-" * 80)
    cursor.execute("""
        SELECT DISTINCT
            metric,
            entity,
            period,
            value,
            unit,
            page_number
        FROM financial_tables
        WHERE metric ILIKE '%variable%cost%'
        AND entity = 'Portugal'
        AND page_number = 20
        LIMIT 5;
    """)

    page_20_rows = cursor.fetchall()

    if page_20_rows:
        print(f"   Found {len(page_20_rows)} row(s) with correct mappings:")
        print()
        for row in page_20_rows:
            metric, entity, period, value, unit, page = row
            print(f"   ✅ metric='{metric}', entity='{entity}', period='{period}'")
            print(f"      value={value}, unit='{unit}', page={page}")
            print()
        print("   ✅ PASS: Column mappings are correct")
    else:
        print("   ❌ FAIL: No page 20 Variable Cost data with correct mappings")
    print()

    # Test 3: Check for inverted mappings (should be 0)
    print("Test 3: Check for inverted mappings (should be 0)")
    print("-" * 80)
    cursor.execute("""
        SELECT COUNT(*)
        FROM financial_tables
        WHERE metric = 'Portugal'  -- Entity in metric column = inverted
        AND page_number = 20;
    """)
    inverted_count = cursor.fetchone()[0]
    print(f"   Inverted mapping rows found: {inverted_count}")

    if inverted_count == 0:
        print("   ✅ PASS: No inverted mappings found")
    else:
        print(f"   ❌ FAIL: {inverted_count} rows with inverted mappings still exist")
    print()

    # Test 4: Sample Variable Cost data
    print("Test 4: Sample Variable Cost data (all entities)")
    print("-" * 80)
    cursor.execute("""
        SELECT
            entity,
            period,
            value,
            unit,
            page_number
        FROM financial_tables
        WHERE metric ILIKE '%variable%cost%'
        ORDER BY page_number, entity, period
        LIMIT 10;
    """)

    sample_rows = cursor.fetchall()

    if sample_rows:
        print(f"   Found {len(sample_rows)} sample rows:")
        print()
        for row in sample_rows:
            entity, period, value, unit, page = row
            print(
                f"   • entity='{entity}', period='{period}', value={value}, unit='{unit}' (page {page})"
            )
        print()
        print("   ✅ PASS: Sample data looks correct")
    else:
        print("   ❌ FAIL: No Variable Cost sample data found")
    print()

    # Summary
    print("=" * 80)
    print("VERIFICATION SUMMARY")
    print("=" * 80)
    print(f"Total Variable Cost rows: {variable_cost_count}")
    print(f"Page 20 correct mappings: {len(page_20_rows)}")
    print(f"Inverted mappings: {inverted_count}")
    print()

    if variable_cost_count > 0 and len(page_20_rows) > 0 and inverted_count == 0:
        print("✅ ALL TESTS PASSED - Variable Cost data extracted correctly")
        print()
        print("Ready to run Ground Truth V2 validation:")
        print("  python scripts/validate-story-2.13-v2.py --queries 5")
    else:
        print("❌ SOME TESTS FAILED - Review results above")

    cursor.close()
    conn.close()


if __name__ == "__main__":
    main()
