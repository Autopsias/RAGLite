#!/usr/bin/env python3
"""Inject page 23 data from chunk PDF to fix GT-001 unit extraction.

Pages 20-21 were successfully injected with 96.77% unit population.
Page 23 from full PDF has only 37.07% unit population.
Solution: Extract page 23 from the same chunk PDF that worked for pages 20-21.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
from docling.document_converter import DocumentConverter, PdfFormatOption

from raglite.ingestion.adaptive_table_extraction import AdaptiveTableExtractor
from raglite.shared.clients import get_postgresql_connection

print("=" * 80)
print("INJECTING PAGE 23 DATA FROM CHUNK PDF")
print("=" * 80)
print()

# Step 1: Extract from chunk PDF
chunk_pdf = Path("docs/sample pdf/test-chunk-pages-18-23.pdf")
print(f"Step 1: Extracting page 6 (original page 23) from {chunk_pdf.name}...")
print("   (This will take ~27 seconds)")
print()

# Configure Docling with table extraction
pipeline_options = PdfPipelineOptions()
pipeline_options.do_table_structure = True
pipeline_options.table_structure_options.do_cell_matching = True
pipeline_options.table_structure_options.mode = TableFormerMode.ACCURATE

converter = DocumentConverter(
    format_options={
        InputFormat.PDF: PdfFormatOption(
            pipeline_options=pipeline_options, backend=PyPdfiumDocumentBackend
        )
    }
)

result = converter.convert(str(chunk_pdf))

# Extract tables using adaptive extractor
extractor = AdaptiveTableExtractor()
table_rows = extractor.extract_tables_from_docling_result(result, chunk_pdf.stem)

print(f"✅ Extracted {len(table_rows)} total rows from chunk")
print()

# Step 2: Filter for page 6 (original page 23) and remap page numbers
print("Step 2: Filtering and remapping page numbers...")
print("   Chunk page 6 → Original page 23")
print()

# Chunk pages 1-6 = original pages 18-23
# Chunk page 6 = original page 23
# Offset: +17

page_23_rows = []
for row in table_rows:
    chunk_page = row.get("page_number")
    if chunk_page == 6:
        # Remap page number
        row["page_number"] = 23  # 6 + 17 = 23

        # Update document_id to match full PDF
        row["document_id"] = "2025-08 Performance Review CONSO_v2"

        page_23_rows.append(row)

print(f"✅ Filtered {len(page_23_rows)} rows for page 23")
print()

# Count units
rows_with_units = sum(1 for r in page_23_rows if r.get("unit"))
unit_pct = 100.0 * rows_with_units / len(page_23_rows) if page_23_rows else 0
print(f"Unit population: {rows_with_units}/{len(page_23_rows)} = {unit_pct:.2f}%")
print()

# Step 3: Delete existing rows for page 23
print("Step 3: Clearing existing data for page 23...")
conn = get_postgresql_connection()
cursor = conn.cursor()

cursor.execute(
    """
    DELETE FROM financial_tables
    WHERE document_id = '2025-08 Performance Review CONSO_v2'
      AND page_number = 23
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
for row in page_23_rows:
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
    SELECT page_number, COUNT(*) as row_count,
           COUNT(unit) as rows_with_units,
           ROUND(100.0 * COUNT(unit) / COUNT(*), 2) as unit_pct
    FROM financial_tables
    WHERE document_id = '2025-08 Performance Review CONSO_v2'
      AND page_number IN (20, 21, 22, 23, 24)
    GROUP BY page_number
    ORDER BY page_number
"""
)

results = cursor.fetchall()
print("Page distribution with unit stats:")
for page_num, count, with_units, pct in results:
    marker = "✅" if page_num == 23 and count > 0 else ""
    print(f"  Page {page_num}: {count} rows, {with_units} with units ({float(pct)}%) {marker}")
print()

# Step 6: Validate GT-001
print("Step 6: Validating GT-001 (Group EBITDA)...")
cursor.execute(
    """
    SELECT
        metric,
        entity,
        period,
        value,
        unit
    FROM financial_tables
    WHERE page_number = 23
      AND (
          metric ILIKE '%EBITDA%'
          OR metric = 'EBITDA IFRS'
      )
      AND (
          entity ILIKE '%GROUP%'
          OR entity = 'GROUP'
      )
    ORDER BY period
    LIMIT 5
"""
)

gt001_results = cursor.fetchall()
if gt001_results:
    print(f"  Found {len(gt001_results)} EBITDA GROUP rows:")
    for metric, entity, period, value, unit in gt001_results:
        print(f"    {metric} | {entity} | {period}")
        print(f"      Value: {value}, Unit: {unit}")
        if unit:
            print(f"      ✅ Unit populated: '{unit}'")
        else:
            print("      ❌ Unit is NULL")
        print()
else:
    print("  ❌ No GT-001 rows found")

cursor.close()
conn.close()

print()
print("=" * 80)
print("INJECTION COMPLETE")
print("=" * 80)
print()
print("Next steps:")
print("  1. If GT-001 unit is populated → Phase 2.7.2 COMPLETE")
print("  2. If GT-001 unit is NULL → Investigate page 23 table structure")
