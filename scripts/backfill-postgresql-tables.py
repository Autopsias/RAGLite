#!/usr/bin/env python3
"""Backfill PostgreSQL financial_tables with table data from PDFs.

This script identifies documents that exist in Qdrant but are missing from PostgreSQL,
then extracts and stores their table data.

Story: Fix PostgreSQL Data Synchronization Gap
Root Cause: Documents restored from Qdrant snapshot without PostgreSQL sync.

Usage:
    python scripts/backfill-postgresql-tables.py --pdf-dir /path/to/pdfs
    python scripts/backfill-postgresql-tables.py --dry-run
    python scripts/backfill-postgresql-tables.py --single "2024-05 Performance Review.pdf"
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from qdrant_client import QdrantClient
from sqlalchemy import create_engine, text

from raglite.ingestion.storage import store_tables_in_postgresql
from raglite.ingestion.table_extraction import TableExtractor
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


def get_qdrant_documents() -> set[str]:
    """Get all unique source_document values from Qdrant."""
    client = QdrantClient(
        host=os.getenv("QDRANT_HOST", "localhost"),
        port=int(os.getenv("QDRANT_PORT", "6333")),
    )

    documents = set()
    offset = None
    batch_size = 100

    while True:
        result = client.scroll(
            collection_name="financial_docs",
            limit=batch_size,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )

        points, next_offset = result

        for point in points:
            source_doc = point.payload.get("source_document")
            if source_doc:
                documents.add(source_doc)

        if next_offset is None:
            break
        offset = next_offset

    return documents


def get_postgresql_documents() -> set[str]:
    """Get all unique document_id values from PostgreSQL financial_tables."""
    from raglite.shared.config import settings

    # Use settings-based URL to respect APP_ENV (test vs production)
    db_url = os.getenv(
        "DATABASE_URL",
        f"postgresql://{settings.postgres_user}:{settings.postgres_password}@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}",
    )
    engine = create_engine(db_url)

    with engine.connect() as conn:
        result = conn.execute(text("SELECT DISTINCT document_id FROM financial_tables"))
        documents = {row[0] for row in result}

    return documents


def find_pdf_file(document_name: str, search_dirs: list[Path]) -> Path | None:
    """Search for a PDF file matching the document name in multiple directories."""
    for search_dir in search_dirs:
        if not search_dir.exists():
            continue

        # Exact match
        exact_path = search_dir / document_name
        if exact_path.exists():
            return exact_path

        # Case-insensitive search
        for pdf_file in search_dir.glob("*.pdf"):
            if pdf_file.name.lower() == document_name.lower():
                return pdf_file

        # Recursive search
        for pdf_file in search_dir.rglob("*.pdf"):
            if pdf_file.name.lower() == document_name.lower():
                return pdf_file

    return None


async def backfill_document(pdf_path: Path, dry_run: bool = False) -> dict:
    """Extract tables from a single PDF and store in PostgreSQL.

    Returns:
        Dict with status, rows_extracted, rows_stored, error (if any)
    """
    document_name = pdf_path.name
    result = {
        "document": document_name,
        "pdf_path": str(pdf_path),
        "status": "pending",
        "rows_extracted": 0,
        "rows_stored": 0,
        "rows_skipped": 0,
        "error": None,
    }

    if dry_run:
        result["status"] = "dry_run"
        logger.info(f"[DRY RUN] Would process: {document_name}")
        return result

    try:
        logger.info(f"Processing: {document_name}")

        # Extract tables using TableExtractor
        extractor = TableExtractor()
        table_rows = await extractor.extract_tables(str(pdf_path))

        result["rows_extracted"] = len(table_rows)

        if not table_rows:
            result["status"] = "no_tables"
            logger.info(f"No tables found in: {document_name}")
            return result

        # Store in PostgreSQL
        rows_stored, rows_skipped = await store_tables_in_postgresql(table_rows)

        result["rows_stored"] = rows_stored
        result["rows_skipped"] = rows_skipped
        result["status"] = "success"

        logger.info(f"Stored {rows_stored} rows ({rows_skipped} skipped) for: {document_name}")

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        logger.error(f"Failed to process {document_name}: {e}")

    return result


async def main():
    parser = argparse.ArgumentParser(description="Backfill PostgreSQL with table data from PDFs")
    parser.add_argument(
        "--pdf-dir",
        type=Path,
        action="append",
        help="Directory to search for PDFs (can specify multiple)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    parser.add_argument(
        "--single",
        type=str,
        help="Process a single document by name",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-process documents even if already in PostgreSQL",
    )

    args = parser.parse_args()

    # Default search directories
    project_root = Path(__file__).parent.parent
    search_dirs = args.pdf_dir or [
        project_root / "docs" / "sample pdf",
        Path.home() / "Documents",
        Path.home() / "Downloads",
    ]

    print("=" * 60)
    print("PostgreSQL Table Backfill Script")
    print("=" * 60)

    # Step 1: Get documents from both databases
    print("\n[1/4] Querying Qdrant for documents...")
    qdrant_docs = get_qdrant_documents()
    print(f"      Found {len(qdrant_docs)} documents in Qdrant")

    print("\n[2/4] Querying PostgreSQL for documents...")
    postgresql_docs = get_postgresql_documents()
    print(f"      Found {len(postgresql_docs)} documents in PostgreSQL")

    # Step 2: Identify missing documents
    if args.single:
        missing_docs = {args.single}
        print(f"\n[3/4] Processing single document: {args.single}")
    else:
        if args.force:
            missing_docs = qdrant_docs
            print(f"\n[3/4] Force mode: will re-process all {len(missing_docs)} documents")
        else:
            missing_docs = qdrant_docs - postgresql_docs
            print(f"\n[3/4] Missing from PostgreSQL: {len(missing_docs)} documents")

    if not missing_docs:
        print("\n[SUCCESS] All documents are synchronized!")
        return

    # Step 3: Find PDFs
    print("\n[4/4] Searching for PDFs in:")
    for d in search_dirs:
        print(f"      - {d}")

    found_pdfs: dict[str, Path] = {}
    not_found: list[str] = []

    for doc_name in sorted(missing_docs):
        pdf_path = find_pdf_file(doc_name, search_dirs)
        if pdf_path:
            found_pdfs[doc_name] = pdf_path
        else:
            not_found.append(doc_name)

    print(f"\n      Found: {len(found_pdfs)} PDFs")
    print(f"      Not found: {len(not_found)} PDFs")

    # Report not found
    if not_found:
        print("\n[WARNING] The following PDFs could not be found:")
        for doc in sorted(not_found):
            print(f"      - {doc}")

    # Step 4: Process found PDFs
    if not found_pdfs:
        print("\n[ERROR] No PDFs available to process!")
        print("\nTo backfill, please:")
        print("  1. Copy your PDF files to: docs/sample pdf/")
        print("  2. Or specify a directory: --pdf-dir /path/to/pdfs")
        return

    print("\n" + "-" * 60)
    print("Processing PDFs:")
    print("-" * 60)

    results = []
    for _doc_name, pdf_path in sorted(found_pdfs.items()):
        result = await backfill_document(pdf_path, dry_run=args.dry_run)
        results.append(result)

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    success_count = sum(1 for r in results if r["status"] == "success")
    no_tables_count = sum(1 for r in results if r["status"] == "no_tables")
    error_count = sum(1 for r in results if r["status"] == "error")
    total_rows = sum(r["rows_stored"] for r in results)

    print(f"  Processed:    {len(results)}")
    print(f"  Success:      {success_count}")
    print(f"  No tables:    {no_tables_count}")
    print(f"  Errors:       {error_count}")
    print(f"  Total rows:   {total_rows}")
    print(f"  Not found:    {len(not_found)}")

    if error_count > 0:
        print("\nErrors:")
        for r in results:
            if r["status"] == "error":
                print(f"  - {r['document']}: {r['error']}")

    # Final status
    if not_found:
        print(f"\n[ACTION REQUIRED] {len(not_found)} PDFs need to be provided")
        print("Copy them to 'docs/sample pdf/' and re-run this script")


if __name__ == "__main__":
    asyncio.run(main())
