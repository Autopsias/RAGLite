"""Helper functions for post-ingestion verification in session_ingested_collection fixture."""

import asyncio
import logging
import sys
import time

import pytest
from psycopg2.extras import RealDictCursor

from raglite.ingestion.pipeline import ingest_pdf
from raglite.shared.clients import get_postgresql_connection, get_qdrant_client
from raglite.shared.config import settings

from .. import session_state


def execute_ingestion(sample_pdf, skip_metadata: bool) -> None:
    """Execute the PDF ingestion process.

    Args:
        sample_pdf: Path to the PDF file
        skip_metadata: Whether to skip LLM metadata extraction

    Raises:
        Exception: If ingestion fails
    """
    start_ingest = time.time()
    try:
        asyncio.run(ingest_pdf(str(sample_pdf), clear_existing=False, skip_metadata=skip_metadata))
        time.time() - start_ingest
    except Exception:
        raise


def verify_qdrant_data(expected_range: tuple[int, int]) -> int:
    """Verify that Qdrant has data in the expected range.

    Args:
        expected_range: Tuple of (min_chunks, max_chunks)

    Returns:
        int: Actual chunk count

    Raises:
        pytest.fail: If chunk count not in expected range
    """
    qdrant = get_qdrant_client()

    # Wait for data to be visible
    for _attempt in range(10):
        count_after = qdrant.count(collection_name=settings.qdrant_collection_name)
        if count_after.count > 0:
            break
        time.sleep(0.2)

    session_state.session_sample_pdf_chunk_count = count_after.count

    if not (expected_range[0] <= count_after.count <= expected_range[1]):
        pytest.fail(
            f"CRITICAL: Chunk count {count_after.count} not in expected range {expected_range}"
        )

    return count_after.count


def verify_postgresql_data(use_full_pdf: bool) -> None:
    """Verify that PostgreSQL has data.

    Args:
        use_full_pdf: Whether full PDF was used (affects expected row count)

    Raises:
        pytest.fail: If PostgreSQL data not visible or insufficient
    """
    logger = logging.getLogger(__name__)
    conn = get_postgresql_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    pg_count = 0
    expected_min_rows = 10 if not use_full_pdf else 100

    max_attempts = 20
    for attempt in range(max_attempts):
        if not conn.autocommit:
            conn.rollback()
        cursor.execute("SELECT COUNT(*) FROM financial_tables")
        pg_count = cursor.fetchone()["count"]

        if pg_count >= expected_min_rows:
            logger.info("PostgreSQL data visible", extra={"rows": pg_count, "attempt": attempt + 1})
            break

        sleep_time = min(0.2 * (2**attempt), 2.0)
        if attempt in [0, 2, 5, 8, 11, 14, 17]:
            print(
                f"   ⏳ PostgreSQL: {pg_count}/{expected_min_rows} rows (attempt {attempt + 1}/{max_attempts})",
                file=sys.stderr,
            )
        time.sleep(sleep_time)
    else:
        pytest.fail(
            f"PostgreSQL data not visible after {max_attempts} attempts: {pg_count}/{expected_min_rows} rows"
        )

    cursor.close()

    session_state.session_postgresql_row_count = pg_count

    if pg_count < expected_min_rows:
        pytest.fail(f"PostgreSQL has only {pg_count} rows, expected at least {expected_min_rows}")


def create_collection_snapshot(estimated_time: str) -> str | None:
    """Create a Qdrant snapshot for fast restoration.

    Args:
        estimated_time: Estimated time for full ingestion (for logging)

    Returns:
        str | None: Snapshot name if successful, None otherwise
    """
    import sys

    qdrant = get_qdrant_client()
    snapshot_start = time.time()
    try:
        snapshot_info = qdrant.create_snapshot(
            collection_name=settings.qdrant_collection_name, wait=True
        )
        time.time() - snapshot_start
        print(
            f"   ✓ Snapshot created for fast restoration (<1s vs {estimated_time})", file=sys.stderr
        )
        return snapshot_info.name
    except Exception:
        return None
