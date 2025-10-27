#!/usr/bin/env python3
"""Check how many header rows exist in page 20 tables."""

import psycopg2

from raglite.shared.config import settings

# Connect to database
conn = psycopg2.connect(
    host=settings.postgres_host,
    port=settings.postgres_port,
    database=settings.postgres_db,
    user=settings.postgres_user,
    password=settings.postgres_password,
)

cursor = conn.cursor()

# Query to find unique extraction methods on page 20
cursor.execute("""
    SELECT DISTINCT extraction_method, COUNT(*) as row_count
    FROM financial_tables
    WHERE page_number = 20
    GROUP BY extraction_method
    ORDER BY extraction_method
""")

print("=" * 80)
print("EXTRACTION METHODS ON PAGE 20")
print("=" * 80)

for method, count in cursor.fetchall():
    print(f"{method}: {count} rows")

# Check a sample row with NULL unit
cursor.execute("""
    SELECT entity, metric, value, unit, period, extraction_method, table_index
    FROM financial_tables
    WHERE page_number = 20
    AND entity = 'Portugal'
    AND metric = 'Variable Cost'
    LIMIT 5
""")

print("\n" + "=" * 80)
print("SAMPLE ROWS WITH NULL UNITS")
print("=" * 80)

for row in cursor.fetchall():
    entity, metric, value, unit, period, method, table_idx = row
    print(
        f"Table {table_idx}: entity={entity}, metric={metric}, value={value}, unit={unit}, method={method}"
    )

cursor.close()
conn.close()

print("\n" + "=" * 80)
print("HYPOTHESIS")
print("=" * 80)
print("If extraction_method = 'transposed_entity_cols_metric_row_labels':")
print("  → Code assumes 2 header rows (entities, periods)")
print("  → But actual tables may have 3 header rows (entities, periods, UNITS)")
print("  → Unit row is being IGNORED, leading to NULL units")
print("\nSOLUTION:")
print("  1. Check if len(row_levels) >= 3")
print("  2. If yes, row_levels[2] contains units")
print("  3. Build column_unit_map from row_levels[2]")
print("  4. Use unit from column_unit_map instead of parsing from data cells")
