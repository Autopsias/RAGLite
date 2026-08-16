#!/usr/bin/env python3
"""Classify a sample of existing database rows for validation testing.

This script updates classification columns (period_type, value_type, entity_level)
on existing rows without full re-ingestion. Much faster than re-processing PDFs.

Usage:
    python scripts/classify-sample-data.py --limit 10000  # Classify 10,000 rows
    python scripts/classify-sample-data.py --all           # Classify all rows
"""

import argparse
import logging
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import psycopg2
from psycopg2.extras import execute_batch

from raglite.ingestion.classification.integration import classify_rows_batch

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def get_db_connection():
    """Get PostgreSQL connection."""
    return psycopg2.connect(
        host="localhost", port=5432, database="raglite", user="raglite", password="raglite"
    )


def classify_sample(limit: int | None = None, batch_size: int = 1000) -> dict:
    """Classify a sample of existing rows.

    Args:
        limit: Maximum rows to classify (None = all)
        batch_size: Rows per batch

    Returns:
        dict with statistics
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Count total rows needing classification
    cursor.execute("SELECT COUNT(*) FROM financial_tables WHERE period_type IS NULL")
    total_null = cursor.fetchone()[0]
    logger.info(f"Total rows with NULL classification: {total_null:,}")

    if total_null == 0:
        logger.info("All rows already classified!")
        return {"classified": 0, "total": 0}

    limit_clause = f"LIMIT {limit}" if limit else ""

    # Fetch rows needing classification
    logger.info(f"Fetching rows to classify{f' (limit: {limit:,})' if limit else ''}...")
    cursor.execute(f"""
        SELECT id, entity, period, metric
        FROM financial_tables
        WHERE period_type IS NULL
        {limit_clause}
    """)

    rows = cursor.fetchall()
    total_to_process = len(rows)
    logger.info(f"Fetched {total_to_process:,} rows to classify")

    # Process in batches using classify_rows_batch for efficiency
    start_time = time.perf_counter()
    classified_count = 0

    # Process rows in chunks for batch classification
    for chunk_start in range(0, total_to_process, batch_size):
        chunk_end = min(chunk_start + batch_size, total_to_process)
        chunk = rows[chunk_start:chunk_end]

        # Convert tuples to dicts for batch classification
        row_dicts = [
            {"id": row_id, "entity": entity, "period": period, "metric": metric}
            for row_id, entity, period, metric in chunk
        ]

        # Batch classify for efficiency
        classified_rows = classify_rows_batch(row_dicts)

        # Prepare updates
        updates = [
            (
                classified["period_type"],
                classified["value_type"],
                classified["entity_level"],
                classified["id"],
            )
            for classified in classified_rows
        ]

        # Execute batch database update
        execute_batch(
            cursor,
            """
            UPDATE financial_tables
            SET period_type = %s, value_type = %s, entity_level = %s
            WHERE id = %s
        """,
            updates,
        )
        conn.commit()
        classified_count += len(updates)

        elapsed = time.perf_counter() - start_time
        rate = classified_count / elapsed if elapsed > 0 else 0
        logger.info(
            f"Progress: {classified_count:,}/{total_to_process:,} "
            f"({100 * classified_count / total_to_process:.1f}%) - "
            f"{rate:.0f} rows/sec"
        )

    elapsed = time.perf_counter() - start_time

    # Verify results
    cursor.execute("SELECT COUNT(*) FROM financial_tables WHERE period_type IS NOT NULL")
    classified_total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM financial_tables")
    grand_total = cursor.fetchone()[0]

    cursor.close()
    conn.close()

    stats = {
        "classified_this_run": classified_count,
        "total_classified": classified_total,
        "total_rows": grand_total,
        "coverage_percent": 100 * classified_total / grand_total if grand_total > 0 else 0,
        "elapsed_seconds": elapsed,
        "rate_per_second": classified_count / elapsed if elapsed > 0 else 0,
    }

    logger.info(f"Classification complete in {elapsed:.1f}s")
    logger.info(
        f"Total classified: {classified_total:,}/{grand_total:,} ({stats['coverage_percent']:.1f}%)"
    )

    return stats


def main():
    parser = argparse.ArgumentParser(description="Classify existing database rows")
    parser.add_argument("--limit", type=int, help="Maximum rows to classify")
    parser.add_argument("--all", action="store_true", help="Classify all rows")
    parser.add_argument("--batch-size", type=int, default=1000, help="Batch size (default: 1000)")

    args = parser.parse_args()

    if not args.all and not args.limit:
        # Default: classify 10,000 rows for validation sample
        args.limit = 10000
        logger.info(
            f"Using default limit of {args.limit:,} rows. Use --all for full classification."
        )

    limit = None if args.all else args.limit
    stats = classify_sample(limit=limit, batch_size=args.batch_size)

    print("\n" + "=" * 60)
    print("CLASSIFICATION RESULTS")
    print("=" * 60)
    print(f"Rows classified this run: {stats['classified_this_run']:,}")
    print(f"Total classified: {stats['total_classified']:,}")
    print(f"Total rows: {stats['total_rows']:,}")
    print(f"Coverage: {stats['coverage_percent']:.1f}%")
    print(f"Time: {stats['elapsed_seconds']:.1f}s ({stats['rate_per_second']:.0f} rows/sec)")
    print("=" * 60)


if __name__ == "__main__":
    main()
