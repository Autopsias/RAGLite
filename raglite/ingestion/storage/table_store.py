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


def _filter_valid_table_rows(table_rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    """Filter table rows to include only those with at least one data field populated.

    Args:
        table_rows: List of raw table row dicts

    Returns:
        Tuple of (valid_rows, skipped_count)
    """
    valid_rows = [
        row
        for row in table_rows
        if row.get("entity") or row.get("metric") or row.get("value") is not None
    ]
    skipped_count = len(table_rows) - len(valid_rows)
    return valid_rows, skipped_count


def _prepare_table_records(valid_rows: list[dict[str, Any]]) -> tuple[list[tuple], int]:
    """Prepare table rows for batch insert into PostgreSQL.

    Args:
        valid_rows: List of validated table row dicts

    Returns:
        Tuple of (records, skipped_no_document_id)
        where records is a list of tuples ready for execute_values
    """
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

    return records, skipped_no_document_id


def _insert_records_in_batches(cursor: Any, records: list[tuple], batch_size: int) -> None:
    """Insert table records into PostgreSQL in batches.

    Args:
        cursor: PostgreSQL cursor
        records: List of record tuples
        batch_size: Number of records per batch
    """
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


def _cleanup_database_resources(cursor: Any, conn: Any, operation: str) -> None:
    """Clean up database resources after an error.

    Args:
        cursor: PostgreSQL cursor (may be None)
        conn: PostgreSQL connection
        operation: Name of operation that failed (for logging)
    """
    # Close cursor if it exists
    try:
        if cursor:
            cursor.close()
    except Exception:  # nosec B110 - Cleanup handler: cursor close errors are non-critical
        pass  # Cleanup handler: ignore cursor close errors

    # Rollback transaction
    try:
        conn.rollback()
    except Exception:  # nosec B110 - Cleanup handler: rollback errors are non-critical
        pass  # Cleanup handler: ignore rollback errors


def _log_storage_success(
    records_count: int,
    skipped_count: int,
    skipped_no_document_id: int,
    valid_rows_count: int,
    start_time: float,
) -> None:
    """Log successful PostgreSQL storage operation.

    Args:
        records_count: Number of records stored
        skipped_count: Number of rows skipped (empty fields)
        skipped_no_document_id: Number of rows skipped (missing document_id)
        valid_rows_count: Total valid rows processed
        start_time: Operation start time
    """
    duration_ms = int((time.time() - start_time) * 1000)

    logger.info(
        "PostgreSQL table storage complete",
        extra={
            "records_stored": records_count,
            "records_skipped": skipped_count,
            "records_skipped_no_document_id": skipped_no_document_id,
            "duration_ms": duration_ms,
            "records_per_second": (
                round(valid_rows_count / (duration_ms / 1000), 2) if duration_ms > 0 else 0
            ),
        },
    )


def _validate_and_filter_rows(
    table_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], int] | tuple[None, tuple[int, int]]:
    """Validate and filter table rows, returning early if no valid rows.

    Args:
        table_rows: List of table row dicts from TableExtractor

    Returns:
        Either:
        - Tuple of (valid_rows, skipped_count) if valid rows exist
        - Tuple of (None, (records_stored, records_skipped)) to return early
    """
    if not table_rows:
        logger.info("No table rows to store in PostgreSQL")
        return (None, (0, 0))

    # Filter rows with at least one data field populated
    valid_rows, skipped_count = _filter_valid_table_rows(table_rows)

    if not valid_rows:
        logger.info(
            "No valid table rows to store in PostgreSQL - all rows empty",
            extra={"total_rows": len(table_rows)},
        )
        return (None, (0, len(table_rows)))

    logger.info(
        "Filtered table rows for PostgreSQL storage",
        extra={
            "total_rows": len(table_rows),
            "valid_rows": len(valid_rows),
            "skipped": skipped_count,
        },
    )

    return (valid_rows, skipped_count)


def _execute_database_storage(valid_rows: list[dict[str, Any]], batch_size: int) -> tuple[int, int]:
    """Execute the database storage operation.

    Args:
        valid_rows: List of validated table row dicts
        batch_size: Records per batch

    Returns:
        Tuple of (records_count, skipped_no_document_id)

    Raises:
        Exception: If database operation fails
    """
    conn = get_postgresql_connection()
    cursor = conn.cursor()

    try:
        # Prepare records for batch insert
        records, skipped_no_document_id = _prepare_table_records(valid_rows)

        # Insert in batches
        _insert_records_in_batches(cursor, records, batch_size)

        conn.commit()
        cursor.close()

        return (len(records), skipped_no_document_id)

    except Exception:
        _cleanup_database_resources(cursor, conn, "store_tables")
        raise


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

    # Validate and filter rows (returns early if no valid rows)
    result = _validate_and_filter_rows(table_rows)
    if result[0] is None:
        return result[1]  # type: ignore
    valid_rows, skipped_count = result

    try:
        # Execute database storage
        records_count, skipped_no_document_id = _execute_database_storage(valid_rows, batch_size)

        # Log success metrics
        _log_storage_success(
            records_count, skipped_count, skipped_no_document_id, len(valid_rows), start_time
        )

        # Return actual records stored (may be less than valid_rows if some had no document_id)
        total_skipped = skipped_count + skipped_no_document_id
        return (records_count, total_skipped)

    except Exception as e:
        logger.error(
            "PostgreSQL table storage failed",
            extra={"error": str(e)},
            exc_info=True,
        )
        raise RuntimeError(f"Failed to store tables in PostgreSQL: {e}") from e
