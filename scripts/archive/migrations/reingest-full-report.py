#!/usr/bin/env python3
"""
Re-ingest full financial report for Story 2.13 validation.

Ingests the complete 160-page financial report to populate:
- PostgreSQL financial_tables (for SQL table search)
- Qdrant vectors (for semantic search)
- BM25 index (for keyword search)
"""

import asyncio
from pathlib import Path

from raglite.ingestion.pipeline import ingest_document


async def main():
    """Re-ingest full financial report."""
    pdf_path = Path("docs/sample pdf/2025-08 Performance Review CONSO_v2.pdf")

    if not pdf_path.exists():
        print(f"Error: PDF not found at {pdf_path}")
        return

    print("=" * 80)
    print("RE-INGESTING FULL FINANCIAL REPORT")
    print("=" * 80)
    print(f"File: {pdf_path}")
    print("Expected: ~160 pages with Portugal/Spain/France entity data")
    print()

    print("Starting ingestion (this may take 5-10 minutes)...")
    result = await ingest_document(str(pdf_path))

    print("\n" + "=" * 80)
    print("INGESTION COMPLETE")
    print("=" * 80)
    print(f"Document: {result.filename}")
    print(f"Pages: {result.page_count}")
    print(f"Chunks: {result.chunk_count}")
    print(f"Timestamp: {result.ingestion_timestamp}")
    print()
    print("✅ Database ready for Story 2.13 validation")


if __name__ == "__main__":
    asyncio.run(main())
