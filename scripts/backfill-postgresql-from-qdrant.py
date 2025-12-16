#!/usr/bin/env python3
"""Backfill PostgreSQL from Qdrant table chunks (no PDF re-processing needed).

This script extracts structured table data directly from Qdrant's markdown chunks
using Mistral LLM to parse the table structure. Much faster than full re-ingestion
since it skips PDF parsing, OCR, and embedding generation.

Story: PostgreSQL Data Recovery from Qdrant
Root Cause: PostgreSQL container recreated on Nov 23, 2025

Performance Estimate:
    - Full re-ingestion: ~10 hours (PDF parsing + embedding + all storage)
    - This script: ~65-130 minutes (LLM extraction only)
    - Speedup: 4.5x to 9x faster

Usage:
    python scripts/backfill-postgresql-from-qdrant.py --dry-run
    python scripts/backfill-postgresql-from-qdrant.py
    python scripts/backfill-postgresql-from-qdrant.py --single "2024-05 Performance Review"
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue

from raglite.ingestion.storage_operations import store_tables_in_postgresql
from raglite.shared.clients import get_mistral_client
from raglite.shared.config import settings
from raglite.shared.logging import get_logger

logger = get_logger(__name__)

# Rate limiting for Mistral API
# With batching, we need fewer concurrent requests
MISTRAL_SEMAPHORE = asyncio.Semaphore(10)  # Max 10 concurrent requests

# Batch size for chunks per API call (key optimization!)
CHUNKS_PER_API_CALL = 10  # Process 10 chunks in one API call = 10x fewer calls


def get_qdrant_documents() -> set[str]:
    """Get all unique source_document values from Qdrant."""
    client = QdrantClient(
        host=os.getenv("QDRANT_HOST", "localhost"),
        port=int(os.getenv("QDRANT_PORT", "6333")),
    )

    documents = set()
    offset = None

    while True:
        result = client.scroll(
            collection_name="financial_docs",
            limit=100,
            offset=offset,
            with_payload=["source_document"],
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
    """Get all unique document_id values from PostgreSQL."""
    try:
        from raglite.shared.clients import get_postgresql_connection

        conn = get_postgresql_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT document_id FROM financial_tables")
        documents = {row[0] for row in cursor.fetchall()}
        cursor.close()
        return documents
    except Exception as e:
        logger.warning(f"Could not query PostgreSQL: {e}")
        return set()


def get_table_chunks_for_document(doc_name: str) -> list[dict]:
    """Get all table chunks from Qdrant for a specific document."""
    client = QdrantClient(
        host=os.getenv("QDRANT_HOST", "localhost"),
        port=int(os.getenv("QDRANT_PORT", "6333")),
    )

    chunks = []
    offset = None

    while True:
        result = client.scroll(
            collection_name="financial_docs",
            limit=100,
            offset=offset,
            scroll_filter=Filter(
                must=[
                    FieldCondition(key="source_document", match=MatchValue(value=doc_name)),
                    FieldCondition(key="section_type", match=MatchValue(value="Table")),
                ]
            ),
            with_payload=True,
            with_vectors=False,
        )
        points, next_offset = result

        for point in points:
            chunks.append(
                {
                    "text": point.payload.get("text", ""),
                    "page_number": point.payload.get("page_number", 0),
                    "document_type": point.payload.get("document_type", ""),
                    "chunk_index": point.payload.get("chunk_index", 0),
                }
            )

        if next_offset is None:
            break
        offset = next_offset

    return chunks


async def extract_structured_rows_from_markdown(
    markdown_text: str,
    document_id: str,
    page_number: int,
    table_index: int,
    document_type: str = "",
) -> list[dict]:
    """Use Mistral LLM to extract structured table rows from markdown.

    Args:
        markdown_text: Raw markdown table text from Qdrant
        document_id: Document filename
        page_number: Source page number
        table_index: Table index on page
        document_type: Type of financial statement (Income Statement, etc.)

    Returns:
        List of structured rows ready for PostgreSQL insertion
    """
    if not markdown_text or len(markdown_text.strip()) < 20:
        return []

    # Skip non-table content
    if "|" not in markdown_text:
        return []

    prompt = f"""Extract structured financial data from this markdown table.
The table is from a {document_type or "financial document"}.

For each data cell with a numeric value, extract:
- entity: Company/division name (e.g., "Portugal Cement", "SECIL Group", "Tunisia")
- metric: Financial metric name (e.g., "EBITDA", "Revenue", "Variable Costs")
- period: Time period (e.g., "May-24", "YTD Oct-25", "2024")
- value: Numeric value as a float (convert thousands: 62.075 = 62075 if in K units)
- unit: Unit of measurement (e.g., "EUR", "EUR/ton", "%", "K EUR")

Return a JSON array of objects. Each object must have these exact keys:
["entity", "metric", "period", "value", "unit"]

If you cannot determine a value, use null. Skip percentage variance columns (% B, % LY).
Focus on actual financial values, not comparative percentages.

MARKDOWN TABLE:
{markdown_text[:3000]}

Return ONLY valid JSON array, no explanation:"""

    async with MISTRAL_SEMAPHORE:
        try:
            from mistralai.models import UserMessage

            client = get_mistral_client()
            response = client.chat.complete(
                model=settings.metadata_extraction_model,
                messages=[UserMessage(content=prompt)],
                response_format={"type": "json_object"},
                temperature=0.1,
            )

            if not response.choices or not response.choices[0].message.content:
                return []

            content = response.choices[0].message.content.strip()

            # Parse JSON response
            try:
                data = json.loads(content)
                # Handle both array and object with array
                if isinstance(data, dict):
                    data = data.get("rows", data.get("data", []))
                if not isinstance(data, list):
                    return []
            except json.JSONDecodeError:
                # Try to extract JSON array from response
                match = re.search(r"\[.*\]", content, re.DOTALL)
                if match:
                    try:
                        data = json.loads(match.group())
                    except json.JSONDecodeError:
                        return []
                else:
                    return []

            # Convert to PostgreSQL row format
            rows = []
            for i, item in enumerate(data):
                if not isinstance(item, dict):
                    continue

                value = item.get("value")
                if value is None:
                    continue

                # Convert value to float
                try:
                    if isinstance(value, str):
                        value = float(value.replace(",", "").replace(" ", ""))
                    else:
                        value = float(value)
                except (ValueError, TypeError):
                    continue

                # Extract fiscal year from period
                period = item.get("period", "")
                fiscal_year = None
                if period:
                    year_match = re.search(r"20\d{2}", str(period))
                    if year_match:
                        fiscal_year = int(year_match.group())
                    elif re.search(r"-2[0-9]$", str(period)):
                        year_suffix = int(period[-2:])
                        fiscal_year = 2000 + year_suffix if year_suffix < 50 else 1900 + year_suffix

                rows.append(
                    {
                        "document_id": document_id,
                        "page_number": page_number,
                        "table_index": table_index,
                        "table_caption": document_type,
                        "entity": item.get("entity", ""),
                        "metric": item.get("metric", ""),
                        "period": period,
                        "fiscal_year": fiscal_year,
                        "value": value,
                        "unit": item.get("unit", ""),
                        "row_index": i,
                        "column_name": period,
                        "section_type": "Table",
                        "chunk_text": markdown_text[:500],
                    }
                )

            return rows

        except Exception as e:
            logger.warning(f"Mistral extraction failed: {e}")
            return []


async def extract_structured_rows_from_chunks_batch(
    chunks: list[dict],
    document_id: str,
) -> list[dict]:
    """Extract structured data from MULTIPLE chunks in a SINGLE API call.

    This is the key optimization: instead of 1 API call per chunk,
    we batch 10 chunks together, reducing API calls by 10x.

    Args:
        chunks: List of chunk dicts with text, page_number, document_type
        document_id: Document filename

    Returns:
        List of structured rows ready for PostgreSQL
    """
    if not chunks:
        return []

    # Filter valid table chunks
    valid_chunks = [c for c in chunks if c.get("text") and "|" in c.get("text", "")]
    if not valid_chunks:
        return []

    # Build batched prompt with all chunks
    chunks_text = ""
    for i, chunk in enumerate(valid_chunks):
        text = chunk["text"][:1500]  # Limit each chunk to 1500 chars
        page = chunk.get("page_number", 0)
        doc_type = chunk.get("document_type", "")
        chunks_text += f"\n--- TABLE {i + 1} (page {page}, {doc_type}) ---\n{text}\n"

    prompt = f"""Extract structured financial data from these {len(valid_chunks)} markdown tables.

For EACH table, extract rows with:
- table_id: The table number (1, 2, 3, etc.)
- entity: Company/division name (e.g., "Portugal Cement", "SECIL Group")
- metric: Financial metric name (e.g., "EBITDA", "Revenue", "Variable Costs")
- period: Time period (e.g., "May-24", "YTD Oct-25")
- value: Numeric value as float
- unit: Unit (e.g., "EUR", "K EUR", "%")

Return a JSON object with key "rows" containing an array.
Skip percentage variance columns (% B, % LY). Focus on actual values.

TABLES:
{chunks_text}

Return JSON object with "rows" array:"""

    async with MISTRAL_SEMAPHORE:
        try:
            from mistralai.models import UserMessage

            client = get_mistral_client()
            response = client.chat.complete(
                model=settings.metadata_extraction_model,
                messages=[UserMessage(content=prompt)],
                response_format={"type": "json_object"},
                temperature=0.1,
            )

            if not response.choices or not response.choices[0].message.content:
                return []

            content = response.choices[0].message.content.strip()

            # Parse JSON response
            try:
                data = json.loads(content)
                if isinstance(data, dict):
                    data = data.get("rows", [])
                if not isinstance(data, list):
                    return []
            except json.JSONDecodeError:
                return []

            # Convert to PostgreSQL row format
            rows = []
            for item in data:
                if not isinstance(item, dict):
                    continue

                value = item.get("value")
                if value is None:
                    continue

                try:
                    if isinstance(value, str):
                        value = float(value.replace(",", "").replace(" ", ""))
                    else:
                        value = float(value)
                except (ValueError, TypeError):
                    continue

                # Get table_id to map back to chunk metadata
                table_id = item.get("table_id", 1)
                if isinstance(table_id, str):
                    table_id = int(table_id) if table_id.isdigit() else 1
                chunk_idx = min(table_id - 1, len(valid_chunks) - 1)
                chunk_idx = max(0, chunk_idx)

                chunk = valid_chunks[chunk_idx]
                period = item.get("period", "")

                # Extract fiscal year
                fiscal_year = None
                if period:
                    year_match = re.search(r"20\d{2}", str(period))
                    if year_match:
                        fiscal_year = int(year_match.group())
                    elif re.search(r"-2[0-9]$", str(period)):
                        year_suffix = int(period[-2:])
                        fiscal_year = 2000 + year_suffix if year_suffix < 50 else 1900 + year_suffix

                rows.append(
                    {
                        "document_id": document_id,
                        "page_number": chunk.get("page_number", 0),
                        "table_index": chunk_idx,
                        "table_caption": chunk.get("document_type", ""),
                        "entity": item.get("entity", ""),
                        "metric": item.get("metric", ""),
                        "period": period,
                        "fiscal_year": fiscal_year,
                        "value": value,
                        "unit": item.get("unit", ""),
                        "row_index": len(rows),
                        "column_name": period,
                        "section_type": "Table",
                        "chunk_text": chunk.get("text", "")[:500],
                    }
                )

            return rows

        except Exception as e:
            logger.warning(f"Batched Mistral extraction failed: {e}")
            return []


async def backfill_document(doc_name: str, dry_run: bool = False) -> dict:
    """Extract tables from Qdrant chunks and store in PostgreSQL.

    Returns:
        Dict with extraction statistics
    """
    result = {
        "document": doc_name,
        "status": "pending",
        "chunks_processed": 0,
        "rows_extracted": 0,
        "rows_stored": 0,
        "errors": [],
    }

    # Get table chunks from Qdrant
    chunks = get_table_chunks_for_document(doc_name)
    result["chunks_processed"] = len(chunks)

    if not chunks:
        result["status"] = "no_tables"
        logger.info(f"No table chunks found for: {doc_name}")
        return result

    if dry_run:
        result["status"] = "dry_run"
        logger.info(f"[DRY RUN] Would process {len(chunks)} chunks from: {doc_name}")
        return result

    # Extract document_id (filename without extension)
    document_id = doc_name.replace(".pdf", "").replace(".PDF", "")

    # Process chunks in BATCHES (key optimization: 10x fewer API calls)
    all_rows = []
    total_chunks = len(chunks)
    num_batches = (total_chunks + CHUNKS_PER_API_CALL - 1) // CHUNKS_PER_API_CALL

    print(
        f"    Processing {total_chunks} chunks in {num_batches} batches ({CHUNKS_PER_API_CALL} chunks/batch)...",
        flush=True,
    )

    for batch_idx in range(num_batches):
        start_idx = batch_idx * CHUNKS_PER_API_CALL
        end_idx = min(start_idx + CHUNKS_PER_API_CALL, total_chunks)
        batch_chunks = chunks[start_idx:end_idx]

        print(
            f"    Batch {batch_idx + 1}/{num_batches} (chunks {start_idx + 1}-{end_idx})...",
            flush=True,
        )

        try:
            rows = await extract_structured_rows_from_chunks_batch(
                chunks=batch_chunks,
                document_id=document_id,
            )
            all_rows.extend(rows)

            if rows:
                logger.debug(f"Extracted {len(rows)} rows from batch {batch_idx + 1}")

        except Exception as e:
            result["errors"].append(f"Batch {batch_idx}: {str(e)}")
            logger.warning(f"Failed to process batch {batch_idx}: {e}")

    result["rows_extracted"] = len(all_rows)

    if not all_rows:
        result["status"] = "no_data"
        return result

    # Store in PostgreSQL
    try:
        rows_stored, rows_skipped = await store_tables_in_postgresql(all_rows)
        result["rows_stored"] = rows_stored
        result["rows_skipped"] = rows_skipped
        result["status"] = "success"
        logger.info(f"Stored {rows_stored} rows ({rows_skipped} skipped) for: {doc_name}")
    except Exception as e:
        result["status"] = "error"
        result["errors"].append(f"Storage failed: {str(e)}")
        logger.error(f"Failed to store rows for {doc_name}: {e}")

    return result


async def main():
    parser = argparse.ArgumentParser(
        description="Backfill PostgreSQL from Qdrant table chunks (no PDF needed)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    parser.add_argument(
        "--single",
        type=str,
        help="Process a single document by name (partial match)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-process documents even if already in PostgreSQL",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of documents to process",
    )
    parser.add_argument(
        "--parallel",
        type=int,
        default=1,
        help="Number of documents to process in parallel (default: 1, recommended: 3-4)",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("PostgreSQL Backfill from Qdrant (No PDF Re-processing)")
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
        # Find matching documents
        matching = [d for d in qdrant_docs if args.single.lower() in d.lower()]
        if not matching:
            print(f"\n[ERROR] No documents matching '{args.single}'")
            return
        missing_docs = set(matching)
        print(f"\n[3/4] Processing {len(missing_docs)} documents matching '{args.single}'")
    elif args.force:
        missing_docs = qdrant_docs
        print(f"\n[3/4] Force mode: will process all {len(missing_docs)} documents")
    else:
        missing_docs = qdrant_docs - postgresql_docs
        print(f"\n[3/4] Missing from PostgreSQL: {len(missing_docs)} documents")

    if not missing_docs:
        print("\n[SUCCESS] All documents are synchronized!")
        return

    # Apply limit
    if args.limit:
        missing_docs = set(sorted(missing_docs)[: args.limit])
        print(f"      Limited to {len(missing_docs)} documents")

    # Show documents to process
    print("\n      Documents to process:")
    for doc in sorted(missing_docs)[:10]:
        print(f"        - {doc}")
    if len(missing_docs) > 10:
        print(f"        ... and {len(missing_docs) - 10} more")

    # Count table chunks
    print("\n[4/4] Counting table chunks in Qdrant...")
    total_chunks = 0
    for doc in missing_docs:
        chunks = get_table_chunks_for_document(doc)
        total_chunks += len(chunks)
    print(f"      Total table chunks to process: {total_chunks}")

    est_minutes_low = total_chunks / 60  # ~1 sec per chunk
    est_minutes_high = total_chunks / 30  # ~2 sec per chunk
    parallel_factor = args.parallel
    print(
        f"      Estimated time: {est_minutes_low / parallel_factor:.0f}-{est_minutes_high / parallel_factor:.0f} minutes (with {parallel_factor}x parallelism)"
    )

    # Process documents
    print("\n" + "-" * 60)
    print(f"Processing documents ({parallel_factor} in parallel):")
    print("-" * 60)

    results = []
    sorted_docs = sorted(missing_docs)

    # Process in parallel batches
    for batch_start in range(0, len(sorted_docs), parallel_factor):
        batch_end = min(batch_start + parallel_factor, len(sorted_docs))
        batch_docs = sorted_docs[batch_start:batch_end]

        print(
            f"\n--- Batch {batch_start // parallel_factor + 1}: Documents {batch_start + 1}-{batch_end} of {len(sorted_docs)} ---"
        )
        for doc in batch_docs:
            print(f"  Starting: {doc}")

        # Process batch in parallel
        batch_tasks = [backfill_document(doc_name, dry_run=args.dry_run) for doc_name in batch_docs]
        batch_results = await asyncio.gather(*batch_tasks)

        # Report results
        for doc_name, result in zip(batch_docs, batch_results, strict=False):
            results.append(result)
            print(
                f"  Completed: {doc_name} - Status: {result['status']}, Rows: {result['rows_extracted']}",
                flush=True,
            )

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    success_count = sum(1 for r in results if r["status"] == "success")
    no_data_count = sum(1 for r in results if r["status"] in ("no_tables", "no_data"))
    error_count = sum(1 for r in results if r["status"] == "error")
    dry_run_count = sum(1 for r in results if r["status"] == "dry_run")
    total_rows = sum(r["rows_stored"] for r in results)
    total_extracted = sum(r["rows_extracted"] for r in results)

    print(f"  Documents:      {len(results)}")
    print(f"  Success:        {success_count}")
    print(f"  No data:        {no_data_count}")
    print(f"  Errors:         {error_count}")
    if dry_run_count:
        print(f"  Dry run:        {dry_run_count}")
    print(f"  Rows extracted: {total_extracted}")
    print(f"  Rows stored:    {total_rows}")

    if error_count > 0:
        print("\nErrors:")
        for r in results:
            if r["status"] == "error":
                print(f"  - {r['document']}: {r.get('errors', ['Unknown error'])}")


if __name__ == "__main__":
    asyncio.run(main())
