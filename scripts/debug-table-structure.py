#!/usr/bin/env python
"""Debug script to inspect table structure in test document."""

import asyncio

from raglite.ingestion.table_extraction import TableExtractor


async def inspect_tables():
    """Inspect table structure to understand parsing issues."""
    test_doc = "docs/sample pdf/test-10-pages.pdf"

    extractor = TableExtractor()
    table_rows = await extractor.extract_tables(test_doc)

    # Group rows by table_index
    tables = {}
    for row in table_rows:
        table_idx = row.get("table_index", 0)
        if table_idx not in tables:
            tables[table_idx] = []
        tables[table_idx].append(row)

    # Print first table's first 10 rows to understand structure
    print(f"\nTotal tables found: {len(tables)}")
    print("\nTable 0 (first 10 rows):")
    print("=" * 120)

    for i, row in enumerate(tables.get(0, [])[:10]):
        print(f"\nRow {i}:")
        print(f"  Entity:      {row.get('entity')}")
        print(f"  Metric:      {row.get('metric')}")
        print(f"  Period:      {row.get('period')}")
        print(f"  Fiscal Year: {row.get('fiscal_year')}")
        print(f"  Value:       {row.get('value')}")
        print(f"  Unit:        {row.get('unit')}")
        print(f"  Chunk preview: {row.get('chunk_text', '')[:100]}")

    # Show stats for each table
    print("\n\n" + "=" * 120)
    print("Table Statistics:")
    for table_idx, rows in tables.items():
        valid_rows = sum(
            1 for r in rows if r.get("entity") and r.get("metric") and r.get("value") is not None
        )
        print(
            f"  Table {table_idx}: {len(rows)} rows, {valid_rows} valid ({valid_rows / len(rows) * 100:.1f}%)"
        )


if __name__ == "__main__":
    asyncio.run(inspect_tables())
