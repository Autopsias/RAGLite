#!/usr/bin/env python3
"""
Verify PostgreSQL data quality after table_cells re-ingestion.

Checks for:
1. Total row count
2. Unique entities (should be valid names, not corrupted)
3. Unique metrics (should be valid financial metrics, not corrupted)
4. Sample rows to verify structure
"""

from raglite.shared.clients import get_postgresql_connection


def verify_data_quality():
    """Verify PostgreSQL data quality after re-ingestion."""
    print("=" * 80)
    print("POSTGRESQL DATA QUALITY VERIFICATION")
    print("=" * 80)
    print()

    conn = get_postgresql_connection()
    cursor = conn.cursor()

    # 1. Total row count
    print("1. TOTAL ROW COUNT")
    cursor.execute("SELECT COUNT(*) FROM financial_tables;")
    total_rows = cursor.fetchone()[0]
    print(f"   Total rows: {total_rows:,}")
    print()

    # 2. Unique counts
    print("2. UNIQUE VALUES")
    cursor.execute("""
        SELECT
            COUNT(DISTINCT entity) as unique_entities,
            COUNT(DISTINCT metric) as unique_metrics,
            COUNT(DISTINCT period) as unique_periods
        FROM financial_tables;
    """)
    row = cursor.fetchone()
    print(f"   Unique entities: {row[0]}")
    print(f"   Unique metrics: {row[1]}")
    print(f"   Unique periods: {row[2]}")
    print()

    # 3. Check for corrupted entities (before these were "-", "0", "Jan-25")
    print("3. CORRUPTED ENTITY CHECK")
    cursor.execute("""
        SELECT entity, COUNT(*)
        FROM financial_tables
        WHERE entity IN ('-', '0', 'Jan-25', 'Feb-25', 'Mar-25')
        GROUP BY entity
        ORDER BY COUNT(*) DESC;
    """)
    corrupted_entities = cursor.fetchall()
    if corrupted_entities:
        print("   ⚠️  WARNING: Found corrupted entities:")
        for entity, count in corrupted_entities:
            print(f"      - '{entity}': {count:,} rows")
    else:
        print("   ✅ No corrupted entities found")
    print()

    # 4. Check for corrupted metrics (before these were "Group", "3,68")
    print("4. CORRUPTED METRIC CHECK")
    cursor.execute("""
        SELECT metric, COUNT(*)
        FROM financial_tables
        WHERE metric IN ('Group', '3,68', '7,45', 'Portugal', 'Angola')
        GROUP BY metric
        ORDER BY COUNT(*) DESC;
    """)
    corrupted_metrics = cursor.fetchall()
    if corrupted_metrics:
        print("   ⚠️  WARNING: Found corrupted metrics:")
        for metric, count in corrupted_metrics:
            print(f"      - '{metric}': {count:,} rows")
    else:
        print("   ✅ No corrupted metrics found")
    print()

    # 5. Sample entities (should be valid names)
    print("5. SAMPLE ENTITIES (Top 10)")
    cursor.execute("""
        SELECT entity, COUNT(*)
        FROM financial_tables
        WHERE entity IS NOT NULL
        GROUP BY entity
        ORDER BY COUNT(*) DESC
        LIMIT 10;
    """)
    entities = cursor.fetchall()
    for entity, count in entities:
        print(f"   - {entity}: {count:,} rows")
    print()

    # 6. Sample metrics (should be valid financial metrics)
    print("6. SAMPLE METRICS (Top 10)")
    cursor.execute("""
        SELECT metric, COUNT(*)
        FROM financial_tables
        WHERE metric IS NOT NULL
        GROUP BY metric
        ORDER BY COUNT(*) DESC
        LIMIT 10;
    """)
    metrics = cursor.fetchall()
    for metric, count in metrics:
        print(f"   - {metric}: {count:,} rows")
    print()

    # 7. Sample data rows
    print("7. SAMPLE DATA ROWS (First 5)")
    cursor.execute("""
        SELECT entity, metric, period, value, unit, fiscal_year, page_number
        FROM financial_tables
        WHERE entity IS NOT NULL AND metric IS NOT NULL
        ORDER BY page_number, id
        LIMIT 5;
    """)
    rows = cursor.fetchall()
    for i, row in enumerate(rows, 1):
        entity, metric, period, value, unit, fiscal_year, page_number = row
        print(f"\n   Row {i}:")
        print(f"      Entity: {entity}")
        print(f"      Metric: {metric}")
        print(f"      Period: {period}")
        print(f"      Value: {value}")
        print(f"      Unit: {unit}")
        print(f"      Fiscal Year: {fiscal_year}")
        print(f"      Page: {page_number}")

    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)

    # Determine if data is clean
    is_clean = len(corrupted_entities) == 0 and len(corrupted_metrics) == 0

    if is_clean:
        print("✅ SUCCESS - Data is clean!")
        print(f"   - Total rows: {total_rows:,}")
        print("   - No corrupted entities")
        print("   - No corrupted metrics")
        print("   - Ready for AC4 validation")
    else:
        print("⚠️  WARNING - Data quality issues detected")
        print("   Review corrupted entity/metric checks above")

    cursor.close()
    conn.close()


if __name__ == "__main__":
    verify_data_quality()
