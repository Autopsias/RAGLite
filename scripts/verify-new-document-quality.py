#!/usr/bin/env python3
"""Verify data quality for ONLY the new document (2025-08 Performance Review CONSO_v2)."""

from raglite.shared.clients import get_postgresql_connection

conn = get_postgresql_connection()
cursor = conn.cursor()

doc_id = "2025-08 Performance Review CONSO_v2"

print("=" * 80)
print(f"DATA QUALITY VERIFICATION: {doc_id}")
print("=" * 80)
print()

# 1. Total row count
print("1. TOTAL ROW COUNT")
cursor.execute("SELECT COUNT(*) FROM financial_tables WHERE document_id = %s;", (doc_id,))
total_rows = cursor.fetchone()[0]
print(f"   Total rows: {total_rows:,}")
print()

# 2. Unique counts
print("2. UNIQUE VALUES")
cursor.execute(
    """
    SELECT
        COUNT(DISTINCT entity) as unique_entities,
        COUNT(DISTINCT metric) as unique_metrics,
        COUNT(DISTINCT period) as unique_periods
    FROM financial_tables
    WHERE document_id = %s;
""",
    (doc_id,),
)
row = cursor.fetchone()
print(f"   Unique entities: {row[0]}")
print(f"   Unique metrics: {row[1]}")
print(f"   Unique periods: {row[2]}")
print()

# 3. Check for corrupted entities
print("3. CORRUPTED ENTITY CHECK")
cursor.execute(
    """
    SELECT entity, COUNT(*)
    FROM financial_tables
    WHERE document_id = %s AND entity IN ('-', '0', 'Jan-25', 'Feb-25', 'Mar-25')
    GROUP BY entity
    ORDER BY COUNT(*) DESC;
""",
    (doc_id,),
)
corrupted_entities = cursor.fetchall()
if corrupted_entities:
    print("   ⚠️  WARNING: Found corrupted entities:")
    for entity, count in corrupted_entities:
        print(f"      - '{entity}': {count:,} rows")
else:
    print("   ✅ No corrupted entities found")
print()

# 4. Check for corrupted metrics
print("4. CORRUPTED METRIC CHECK")
cursor.execute(
    """
    SELECT metric, COUNT(*)
    FROM financial_tables
    WHERE document_id = %s AND metric IN ('Group', '3,68', '7,45', 'Portugal', 'Angola')
    GROUP BY metric
    ORDER BY COUNT(*) DESC;
""",
    (doc_id,),
)
corrupted_metrics = cursor.fetchall()
if corrupted_metrics:
    print("   ⚠️  WARNING: Found corrupted metrics:")
    for metric, count in corrupted_metrics:
        print(f"      - '{metric}': {count:,} rows")
else:
    print("   ✅ No corrupted metrics found")
print()

# 5. Sample entities
print("5. SAMPLE ENTITIES (Top 10)")
cursor.execute(
    """
    SELECT entity, COUNT(*)
    FROM financial_tables
    WHERE document_id = %s AND entity IS NOT NULL
    GROUP BY entity
    ORDER BY COUNT(*) DESC
    LIMIT 10;
""",
    (doc_id,),
)
entities = cursor.fetchall()
for entity, count in entities:
    print(f"   - {entity}: {count:,} rows")
print()

# 6. Sample metrics
print("6. SAMPLE METRICS (Top 10)")
cursor.execute(
    """
    SELECT metric, COUNT(*)
    FROM financial_tables
    WHERE document_id = %s AND metric IS NOT NULL
    GROUP BY metric
    ORDER BY COUNT(*) DESC
    LIMIT 10;
""",
    (doc_id,),
)
metrics = cursor.fetchall()
for metric, count in metrics:
    print(f"   - {metric}: {count:,} rows")
print()

# 7. Sample data rows
print("7. SAMPLE DATA ROWS (First 5)")
cursor.execute(
    """
    SELECT entity, metric, period, value, unit, fiscal_year, page_number
    FROM financial_tables
    WHERE document_id = %s AND entity IS NOT NULL AND metric IS NOT NULL
    ORDER BY page_number, id
    LIMIT 5;
""",
    (doc_id,),
)
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

is_clean = len(corrupted_entities) == 0 and len(corrupted_metrics) == 0

if is_clean:
    print("✅ SUCCESS - New document data is CLEAN!")
    print(f"   - Total rows: {total_rows:,}")
    print("   - No corrupted entities")
    print("   - No corrupted metrics")
    print("   - table_cells extraction working correctly!")
else:
    print("⚠️  WARNING - Data quality issues detected in new document")

cursor.close()
conn.close()
