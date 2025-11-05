#!/usr/bin/env python3
"""
Clear PostgreSQL and re-ingest with updated table_cells extraction.

This ensures we're using the latest TableExtractor code with table_cells API.
"""

import asyncio
from pathlib import Path

from raglite.ingestion.pipeline import ingest_document
from raglite.shared.clients import get_postgresql_connection


async def main():
    """Clear PostgreSQL and re-ingest."""
    print("=" * 80)
    print("CLEAR POSTGRESQL & RE-INGEST WITH table_cells")
    print("=" * 80)
    print()

    # Step 1: Clear PostgreSQL
    print("Step 1: Clearing PostgreSQL financial_tables...")
    conn = get_postgresql_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM financial_tables;")
    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM financial_tables;")
    count = cursor.fetchone()[0]
    print(f"   PostgreSQL cleared: {count} rows remaining")
    cursor.close()
    conn.close()
    print()

    # Step 2: Re-ingest PDF
    pdf_path = Path("docs/sample pdf/2025-08 Performance Review CONSO_v2.pdf")

    if not pdf_path.exists():
        print(f"ERROR: PDF not found at {pdf_path}")
        return

    print("Step 2: Re-ingesting with NEW table_cells extraction...")
    print(f"   File: {pdf_path}")
    print("   This will take ~13 minutes...")
    print()

    result = await ingest_document(str(pdf_path))

    print()
    print("=" * 80)
    print("RE-INGESTION COMPLETE")
    print("=" * 80)
    print(f"Document: {result.filename}")
    print(f"Pages: {result.page_count}")
    print(f"Chunks: {result.chunk_count}")
    print()
    print("✅ Ready to verify data quality and run AC4 validation")


if __name__ == "__main__":
    asyncio.run(main())
