"""Helper functions for parallel ingestion integration tests.

These utilities support test_parallel_ingestion.py by providing reusable
functions for test document preparation, database setup, and verification.
"""

from pathlib import Path

from raglite.shared.clients import get_postgresql_connection, reset_postgresql_connection
from raglite.shared.config import settings
from raglite.shared.safety import SafetyGuard


def prepare_test_documents():
    """Prepare test document paths for parallel ingestion.

    Returns:
        List of test file paths
    """
    fixtures_dir = Path(__file__).parent.parent.parent / "fixtures"
    file_paths = [
        str(fixtures_dir / "sample_financial_report.pdf"),
        str(fixtures_dir / "sample-small-3-pages.pdf"),
        str(fixtures_dir / "sample_financial_data.xlsx"),
    ]

    # Verify all test files exist
    for file_path in file_paths:
        assert Path(file_path).exists(), f"Test file not found: {file_path}"

    return file_paths


def setup_postgresql_baseline():
    """Setup PostgreSQL connection and clear test data.

    Returns:
        Tuple of (connection, cursor, initial_chunk_count, initial_table_count)
    """
    reset_postgresql_connection()

    guard = SafetyGuard()
    guard.validate_test_environment("test_parallel_ingestion_cleanup")

    postgres_conn = get_postgresql_connection()
    cursor = postgres_conn.cursor()

    # Clear stale test data
    cursor.execute("DELETE FROM financial_chunks")
    cursor.execute("DELETE FROM financial_tables")
    postgres_conn.commit()
    cursor.close()

    # Reset connection and start fresh transaction AFTER cleanup
    reset_postgresql_connection()
    postgres_conn = get_postgresql_connection()
    cursor = postgres_conn.cursor()

    # Force new transaction BEFORE baseline counts
    if not postgres_conn.autocommit:
        postgres_conn.rollback()

    # Get baseline counts
    cursor.execute("SELECT COUNT(*) FROM financial_chunks")
    initial_chunk_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM financial_tables")
    initial_table_count = cursor.fetchone()[0]

    return postgres_conn, cursor, initial_chunk_count, initial_table_count


def get_baseline_counts(qdrant, cursor):
    """Get baseline counts from Qdrant and PostgreSQL.

    Args:
        qdrant: Qdrant client
        cursor: PostgreSQL cursor

    Returns:
        Tuple of (qdrant_count, chunk_count, table_count)
    """
    initial_qdrant_count = qdrant.count(collection_name=settings.qdrant_collection_name).count

    cursor.execute("SELECT COUNT(*) FROM financial_chunks")
    initial_chunk_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM financial_tables")
    initial_table_count = cursor.fetchone()[0]

    print("\nDEBUG: Baseline counts after cleanup:")
    print(f"  Qdrant: {initial_qdrant_count}")
    print(f"  PostgreSQL chunks: {initial_chunk_count}")
    print(f"  PostgreSQL tables: {initial_table_count}")

    return initial_qdrant_count, initial_chunk_count, initial_table_count


def verify_ingestion_result(result):
    """Verify ingestion result metadata.

    Args:
        result: IngestionResult from parallel ingestion

    Raises:
        AssertionError: If verification fails
    """
    assert result.total_documents == 3, "Should process all 3 documents"
    assert result.successful >= 2, "At least 2 documents should succeed"
    assert len(result.results) >= 2, "Should have results for successful documents"

    for metadata in result.results:
        assert metadata.filename is not None
        assert metadata.chunk_count > 0
        assert metadata.ingestion_timestamp is not None


def verify_qdrant_storage(qdrant, initial_count):
    """Verify new chunks were added to Qdrant.

    Args:
        qdrant: Qdrant client
        initial_count: Initial Qdrant point count

    Returns:
        Number of new chunks added
    """
    final_qdrant_count = qdrant.count(collection_name=settings.qdrant_collection_name).count
    new_qdrant_chunks = final_qdrant_count - initial_count

    print("\nDEBUG: Qdrant after ingestion:")
    print(f"  Initial: {initial_count}")
    print(f"  Final: {final_qdrant_count}")
    print(f"  New chunks: {new_qdrant_chunks}")

    assert new_qdrant_chunks > 0, "New chunks should be stored in Qdrant"

    return new_qdrant_chunks


def reset_postgresql_after_ingestion():
    """Reset PostgreSQL connection after ingestion.

    Returns:
        Tuple of (new connection, new cursor)
    """
    reset_postgresql_connection()
    postgres_conn = get_postgresql_connection()
    cursor = postgres_conn.cursor()

    # Force new transaction to see committed data from parallel workers
    if not postgres_conn.autocommit:
        postgres_conn.rollback()

    return postgres_conn, cursor


def verify_postgresql_storage(cursor, initial_chunk_count, initial_table_count):
    """Verify new chunks and tables were added to PostgreSQL.

    Args:
        cursor: PostgreSQL cursor
        initial_chunk_count: Initial chunk count
        initial_table_count: Initial table count

    Returns:
        Tuple of (new_chunks, new_tables)
    """
    cursor.execute("SELECT COUNT(*) FROM financial_chunks")
    final_chunk_count = cursor.fetchone()[0]
    new_postgres_chunks = final_chunk_count - initial_chunk_count

    print("\nDEBUG: PostgreSQL chunks after ingestion:")
    print(f"  Initial: {initial_chunk_count}")
    print(f"  Final: {final_chunk_count}")
    print(f"  New chunks: {new_postgres_chunks}")

    assert new_postgres_chunks > 0, "New chunks should be stored in PostgreSQL financial_chunks"

    cursor.execute("SELECT COUNT(*) FROM financial_tables")
    final_table_count = cursor.fetchone()[0]
    new_table_rows = final_table_count - initial_table_count

    assert new_table_rows >= 0, "Table count should not decrease"

    return new_postgres_chunks, new_table_rows


def verify_storage_systems(new_qdrant_chunks, new_postgres_chunks):
    """Verify both storage systems received data correctly.

    Args:
        new_qdrant_chunks: Number of new Qdrant chunks
        new_postgres_chunks: Number of new PostgreSQL chunks

    Raises:
        AssertionError: If verification fails
    """
    print("\n✅ Storage verification:")
    print(f"   Qdrant chunks: {new_qdrant_chunks}")
    print(f"   PostgreSQL chunks: {new_postgres_chunks}")

    assert new_qdrant_chunks > 0, "Qdrant should have received chunks"
    assert new_postgres_chunks > 0, "PostgreSQL should have received chunks"

    # PostgreSQL should have at least as many chunks as Qdrant
    assert new_postgres_chunks >= new_qdrant_chunks, (
        f"PostgreSQL should have at least as many chunks as Qdrant "
        f"(Qdrant: {new_qdrant_chunks}, PostgreSQL: {new_postgres_chunks})"
    )


def print_test_summary(result, new_qdrant_chunks, new_postgres_chunks, new_table_rows):
    """Print test completion summary.

    Args:
        result: IngestionResult
        new_qdrant_chunks: Number of new Qdrant chunks
        new_postgres_chunks: Number of new PostgreSQL chunks
        new_table_rows: Number of new PostgreSQL table rows
    """
    print("\n✅ Parallel ingestion test complete:")
    print(f"   Documents processed: {result.total_documents}")
    print(f"   Successful: {result.successful}")
    print(f"   Failed: {result.failed}")
    print(f"   New Qdrant chunks: {new_qdrant_chunks}")
    print(f"   New PostgreSQL chunks: {new_postgres_chunks}")
    print(f"   New PostgreSQL table rows: {new_table_rows}")
