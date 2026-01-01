"""Table storage operations for PostgreSQL database.

Handles structured table data storage in the financial_tables table.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

from psycopg2.extras import execute_values

from raglite.shared.clients import get_postgresql_connection
from raglite.shared.logging import get_logger
from raglite.shared.safety import SafetyGuard

logger = get_logger(__name__)

# Story 4.0.6: SafetyGuard instance for environment audit logging
_guard = SafetyGuard()


async def store_tables_in_postgresql(
    table_rows: list[dict[str, Any]], batch_size: int = 100
) -> tuple[int, int]:
    """Store extracted table rows in PostgreSQL financial_tables table.

    Story 2.13 AC1: Table Extraction to SQL Database

    Args:
        table_rows: List of table row dicts from TableExtractor
        batch_size: Records per batch (default: 100 for memory efficiency)

    Returns:
        Tuple of (records_stored, records_skipped)

    Raises:
        RuntimeError: If PostgreSQL storage fails

    Example:
        >>> stored, skipped = await store_tables_in_postgresql(table_rows)
        >>> logger.info(f"Stored {stored} rows, skipped {skipped}")
    """
    start_time = time.time()

    # Story 4.0.6: Log environment for audit trail
    _guard.log_operation("store_tables_postgresql")
    logger.info(
        "Storing table data in PostgreSQL",
        extra={
            "row_count": len(table_rows),
            "batch_size": batch_size,
            "environment": "PRODUCTION" if _guard.is_production else "TEST",
        },
    )

    if not table_rows:
        logger.info("No table rows to store in PostgreSQL")
        return (0, 0)

    # Filter rows with at least one data field populated
    valid_rows = [
        row
        for row in table_rows
        if row.get("entity") or row.get("metric") or row.get("value") is not None
    ]

    skipped_count = len(table_rows) - len(valid_rows)

    if not valid_rows:
        logger.info(
            "No valid table rows to store in PostgreSQL - all rows empty",
            extra={"total_rows": len(table_rows)},
        )
        return (0, len(table_rows))

    logger.info(
        "Filtered table rows for PostgreSQL storage",
        extra={
            "total_rows": len(table_rows),
            "valid_rows": len(valid_rows),
            "skipped": skipped_count,
        },
    )

    try:
        conn = get_postgresql_connection()
        cursor = conn.cursor()

        # Prepare records for batch insert
        records = []
        skipped_no_document_id = 0
        for row in valid_rows:
            # CRITICAL FIX (EXC-006): Validate document_id is present
            # Some table extraction paths may not set document_id, causing
            # source attribution to fail with source_document='unknown'
            document_id = row.get("document_id")
            if not document_id:
                skipped_no_document_id += 1
                logger.warning(
                    "Skipping table row with missing document_id",
                    extra={
                        "row_index": row.get("row_index"),
                        "table_index": row.get("table_index"),
                        "entity": row.get("entity"),
                        "metric": row.get("metric"),
                    },
                )
                continue

            record = (
                document_id,
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

        # Insert in batches
        total_batches = (len(records) + batch_size - 1) // batch_size

        for i in range(0, len(records), batch_size):
            batch_num = (i // batch_size) + 1
            batch_records = records[i : i + batch_size]

            logger.info(
                f"Uploading PostgreSQL batch {batch_num}/{total_batches}",
                extra={
                    "batch_num": batch_num,
                    "batch_size": len(batch_records),
                    "total_batches": total_batches,
                },
            )

            execute_values(
                cursor,
                """
                INSERT INTO financial_tables (
                    document_id, page_number, table_index, table_caption,
                    entity, metric, period, fiscal_year, value, unit,
                    row_index, column_name, chunk_text
                ) VALUES %s
                """,
                batch_records,
            )

        conn.commit()
        cursor.close()

        duration_ms = int((time.time() - start_time) * 1000)

        logger.info(
            "PostgreSQL table storage complete",
            extra={
                "records_stored": len(records),
                "records_skipped": skipped_count,
                "records_skipped_no_document_id": skipped_no_document_id,
                "duration_ms": duration_ms,
                "records_per_second": (
                    round(len(valid_rows) / (duration_ms / 1000), 2) if duration_ms > 0 else 0
                ),
            },
        )

        # Return actual records stored (may be less than valid_rows if some had no document_id)
        total_skipped = skipped_count + skipped_no_document_id
        return (len(records), total_skipped)

    except Exception as e:
        # Rollback the transaction to clean up the connection
        try:
            if "cursor" in locals() and cursor:
                cursor.close()
        except Exception:  # nosec B110 - Cleanup handler: errors are non-critical  # nosec B110 - Cleanup handler: cursor close errors are non-critical
            pass  # Cleanup handler: ignore cursor close errors

        try:
            conn.rollback()
        except Exception:  # nosec B110 - Cleanup handler: errors are non-critical  # nosec B110 - Cleanup handler: rollback errors are non-critical
            pass  # Cleanup handler: ignore rollback errors

        logger.error(
            "PostgreSQL table storage failed",
            extra={"error": str(e)},
            exc_info=True,
        )
        raise RuntimeError(f"Failed to store tables in PostgreSQL: {e}") from e
