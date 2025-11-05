#!/usr/bin/env python3
"""Inject pages 20-21 data from chunk PDF into database.

ROOT CAUSE: Docling fails to detect tables on pages 20-21 in full 160-page PDF
but successfully detects them in a 6-page chunk.

SOLUTION: Extract from chunk, remap page numbers, inject into database.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from docling.document_converter import DocumentConverter

from raglite.ingestion.table_extraction import TableExtractor
from raglite.shared.clients import get_postgresql_connection

print("=" * 80)
print("INJECTING PAGES 20-21 DATA FROM CHUNK PDF")
print("=" * 80)
print()

# Step 1: Extract from chunk PDF
chunk_pdf = Path("docs/sample pdf/test-chunk-pages-18-23.pdf")
print(f"Step 1: Extracting tables from {chunk_pdf.name}...")
print("   (This will take ~27 seconds)")
print()

converter = DocumentConverter()
result = converter.convert(str(chunk_pdf))

extractor = TableExtractor()
table_rows = extractor.extract_tables_from_result(result, chunk_pdf.stem)

print(f"✅ Extracted {len(table_rows)} total rows from chunk")
print()

# Step 2: Filter for pages 3-4 (original 20-21) and remap page numbers
print("Step 2: Filtering and remapping page numbers...")
print("   Chunk page 3 → Original page 20")
print("   Chunk page 4 → Original page 21")
print()

# Chunk was extracted from pages 18-23, so chunk pages 3-4 = original pages 20-21
# Chunk page numbering: 1,2,3,4,5,6
# Original page numbering: 18,19,20,21,22,23
# Offset: +17

pages_20_21_rows = []
for row in table_rows:
    chunk_page = row.get("page_number")
    if chunk_page in [3, 4]:
        # Remap page number
        original_page = chunk_page + 17  # 3+17=20, 4+17=21
        row["page_number"] = original_page

        # Update document_id to match full PDF
        row["document_id"] = "2025-08 Performance Review CONSO_v2"

        pages_20_21_rows.append(row)

print(f"✅ Filtered {len(pages_20_21_rows)} rows for pages 20-21")
print(f"   Page 20: {sum(1 for r in pages_20_21_rows if r['page_number'] == 20)} rows")
print(f"   Page 21: {sum(1 for r in pages_20_21_rows if r['page_number'] == 21)} rows")
print()

# Step 3: Delete existing rows for pages 20-21 (if any)
print("Step 3: Clearing existing data for pages 20-21...")
conn = get_postgresql_connection()
cursor = conn.cursor()

cursor.execute(
    """
    DELETE FROM financial_tables
    WHERE document_id = '2025-08 Performance Review CONSO_v2'
      AND page_number IN (20, 21)
"""
)

deleted_count = cursor.rowcount
conn.commit()
print(f"✅ Deleted {deleted_count} existing rows")
print()

# Step 4: Insert new rows
print("Step 4: Inserting new rows into database...")

insert_query = """
    INSERT INTO financial_tables (
        document_id, page_number, table_index, table_caption,
        entity, metric, period, fiscal_year,
        value, unit, row_index, column_name, chunk_text
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""

records = []
for row in pages_20_21_rows:
    record = (
        row.get("document_id"),
        row.get("page_number"),
        row.get("table_index"),
        row.get("table_caption"),
        row.get("entity"),
        row.get("metric"),
        row.get("period"),
        row.get("fiscal_year"),
        row.get("value"),
        row.get("unit"),
        row.get("row_index"),
        row.get("column_name"),
        row.get("chunk_text"),
    )
    records.append(record)

# Insert in batches of 100
batch_size = 100
inserted_count = 0

for i in range(0, len(records), batch_size):
    batch = records[i : i + batch_size]
    cursor.executemany(insert_query, batch)
    inserted_count += len(batch)
    print(f"   Inserted batch {i // batch_size + 1}: {len(batch)} rows")

conn.commit()
print()
print(f"✅ Inserted {inserted_count} rows total")
print()

# Step 5: Verify insertion
print("Step 5: Verifying insertion...")
cursor.execute(
    """
    SELECT page_number, COUNT(*) as row_count
    FROM financial_tables
    WHERE document_id = '2025-08 Performance Review CONSO_v2'
      AND page_number IN (19, 20, 21, 22)
    GROUP BY page_number
    ORDER BY page_number
"""
)

results = cursor.fetchall()
print("Page distribution (19-22):")
for page_num, count in results:
    marker = "✅" if page_num in [20, 21] and count > 0 else ""
    print(f"  Page {page_num}: {count} rows {marker}")

cursor.close()
conn.close()

print()
print("=" * 80)
print("INJECTION COMPLETE")
print("=" * 80)
print()
print("Next steps:")
print("  1. Validate unit extraction fix on GT-001 and GT-002")
print("  2. Check unit population improvement (expected: 51.76% → 90-95%)")
print("  3. Measure validation accuracy improvement (expected: 0% → 50-60%)")
