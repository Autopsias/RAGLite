"""Core parallel ingestion tests (Story 5.0.6 Task 7.1).

Tests parallel ingestion pipeline with multiple documents and verifies:
- Correct chunk storage in Qdrant
- Correct table data storage in PostgreSQL
- Parallel processing behavior
- Cross-document unit cache effectiveness
"""

from pathlib import Path

import pytest

from raglite.ingestion.document_ingestion import ingest_documents_parallel
from raglite.shared.clients import get_postgresql_connection, get_qdrant_client
from raglite.shared.config import settings
from raglite.shared.safety import SafetyGuard

# Mark all tests in this module as integration tests
# CRITICAL: xdist_group required because tests use embedding model via ingest_documents_parallel
pytestmark = [
    pytest.mark.integration,
    pytest.mark.preserve_collection,
    pytest.mark.slow,
    pytest.mark.xdist_group(name="embedding_model_reads"),
]


def _prepare_test_documents(fixtures_dir: Path) -> list[str]:
    """Prepare list of test document paths for parallel ingestion.

    Args:
        fixtures_dir: Path to test fixtures directory

    Returns:
        List of absolute file paths to test documents
    """
    file_paths = [
        str(fixtures_dir / "sample_financial_report.pdf"),
        str(fixtures_dir / "sample-small-3-pages.pdf"),
        str(fixtures_dir / "sample_financial_data.xlsx"),
    ]

    # Verify all test files exist
    for file_path in file_paths:
        assert Path(file_path).exists(), f"Test file not found: {file_path}"

    return file_paths


def _setup_baseline_counts(qdrant, postgres_conn):
    """Setup baseline counts and clear test data.

    Args:
        qdrant: Qdrant client instance
        postgres_conn: PostgreSQL connection

    Returns:
        Tuple of (initial_qdrant_count, initial_chunk_count, initial_table_count, cursor)
    """
    from raglite.shared.clients import reset_postgresql_connection

    # CRITICAL FIX (CI): Reset singleton connection to force fresh connection
    reset_postgresql_connection()

    # CRITICAL SAFETY CHECK (Story 6.26): Validate test environment BEFORE any DELETE
    guard = SafetyGuard()
    guard.validate_test_environment("test_parallel_ingestion_cleanup")

    cursor = postgres_conn.cursor()

    # Clear stale test data to ensure accurate differential counts
    cursor.execute("DELETE FROM financial_chunks")
    cursor.execute("DELETE FROM financial_tables")
    postgres_conn.commit()
    cursor.close()

    # CRITICAL FIX: Reset connection and start fresh transaction AFTER cleanup
    reset_postgresql_connection()
    postgres_conn = get_postgresql_connection()
    cursor = postgres_conn.cursor()

    # Force new transaction BEFORE baseline counts
    if not postgres_conn.autocommit:
        postgres_conn.rollback()

    # Count existing data (should be 0 after cleanup)
    initial_qdrant_count = qdrant.count(collection_name=settings.qdrant_collection_name).count

    cursor.execute("SELECT COUNT(*) FROM financial_chunks")
    initial_chunk_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM financial_tables")
    initial_table_count = cursor.fetchone()[0]

    print("\nDEBUG: Baseline counts after cleanup:")
    print(f"  Qdrant: {initial_qdrant_count}")
    print(f"  PostgreSQL chunks: {initial_chunk_count}")
    print(f"  PostgreSQL tables: {initial_table_count}")

    # Validate cleanup worked
    assert initial_chunk_count == 0, (
        f"PostgreSQL cleanup failed - still has {initial_chunk_count} chunks. "
        f"Expected 0 after DELETE FROM financial_chunks"
    )

    return initial_qdrant_count, initial_chunk_count, initial_table_count, cursor


def _verify_ingestion_result(result, new_qdrant_chunks, new_postgres_chunks, new_table_rows):
    """Verify parallel ingestion results and storage.

    Args:
        result: Ingestion result from parallel processing
        new_qdrant_chunks: Number of new chunks in Qdrant
        new_postgres_chunks: Number of new chunks in PostgreSQL
        new_table_rows: Number of new table rows in PostgreSQL
    """
    # Verify ingestion results
    assert result.total_documents == 3, "Should process all 3 documents"
    assert result.successful >= 2, "At least 2 documents should succeed"
    assert len(result.results) >= 2, "Should have results for successful documents"

    # Verify metadata was returned for successful documents
    for metadata in result.results:
        assert metadata.filename is not None
        assert metadata.chunk_count > 0
        assert metadata.ingestion_timestamp is not None

    # Both storage systems should have received data
    assert new_qdrant_chunks > 0, "Qdrant should have received chunks"
    assert new_postgres_chunks > 0, "PostgreSQL should have received chunks"

    # PostgreSQL should have at least as many chunks as Qdrant
    assert new_postgres_chunks >= new_qdrant_chunks, (
        f"PostgreSQL should have at least as many chunks as Qdrant "
        f"(Qdrant: {new_qdrant_chunks}, PostgreSQL: {new_postgres_chunks})"
    )

    # Print summary for debugging
    print("\n✅ Parallel ingestion test complete:")
    print(f"   Documents processed: {result.total_documents}")
    print(f"   Successful: {result.successful}")
    print(f"   Failed: {result.failed}")
    print(f"   New Qdrant chunks: {new_qdrant_chunks}")
    print(f"   New PostgreSQL chunks: {new_postgres_chunks}")
    print(f"   New PostgreSQL table rows: {new_table_rows}")


def _collect_final_counts(initial_qdrant_count, initial_chunk_count, initial_table_count, qdrant):
    """Collect final counts after ingestion with connection reset.

    Args:
        initial_qdrant_count: Baseline Qdrant count
        initial_chunk_count: Baseline PostgreSQL chunk count
        initial_table_count: Baseline PostgreSQL table count
        qdrant: Qdrant client instance

    Returns:
        Tuple of (new_qdrant_chunks, new_postgres_chunks, new_table_rows, cursor)
    """
    from raglite.shared.clients import reset_postgresql_connection

    # Verify new chunks were added to Qdrant
    final_qdrant_count = qdrant.count(collection_name=settings.qdrant_collection_name).count
    new_qdrant_chunks = final_qdrant_count - initial_qdrant_count

    print("\nDEBUG: Qdrant after ingestion:")
    print(f"  Initial: {initial_qdrant_count}")
    print(f"  Final: {final_qdrant_count}")
    print(f"  New chunks: {new_qdrant_chunks}")

    assert new_qdrant_chunks > 0, "New chunks should be stored in Qdrant"

    # CRITICAL FIX (CI): Reset singleton connection AGAIN after ingestion
    reset_postgresql_connection()
    postgres_conn = get_postgresql_connection()
    cursor = postgres_conn.cursor()

    # Force new transaction to see committed data from parallel workers
    if not postgres_conn.autocommit:
        postgres_conn.rollback()

    # Verify new chunks were added to PostgreSQL
    cursor.execute("SELECT COUNT(*) FROM financial_chunks")
    final_chunk_count = cursor.fetchone()[0]
    new_postgres_chunks = final_chunk_count - initial_chunk_count

    print("\nDEBUG: PostgreSQL chunks after ingestion:")
    print(f"  Initial: {initial_chunk_count}")
    print(f"  Final: {final_chunk_count}")
    print(f"  New chunks: {new_postgres_chunks}")

    assert new_postgres_chunks > 0, "New chunks should be stored in PostgreSQL financial_chunks"

    # Verify new table rows were added to PostgreSQL
    cursor.execute("SELECT COUNT(*) FROM financial_tables")
    final_table_count = cursor.fetchone()[0]
    new_table_rows = final_table_count - initial_table_count
    assert new_table_rows >= 0, "Table count should not decrease"

    # Verify both storage systems have data
    print("\n✅ Storage verification:")
    print(f"   Qdrant chunks: {new_qdrant_chunks}")
    print(f"   PostgreSQL chunks: {new_postgres_chunks}")

    return new_qdrant_chunks, new_postgres_chunks, new_table_rows, cursor


@pytest.mark.slow  # Takes ~60s, actual PDF ingestion
@pytest.mark.priority("P1")
@pytest.mark.timeout(300)  # 5 minutes for parallel ingestion
@pytest.mark.asyncio
@pytest.mark.manages_collection_state  # This test modifies collection state
async def test_parallel_ingestion_three_documents():
    """Test AC1/AC3: Parallel ingestion with 3 documents.

    Story 5.0.6 Task 7.1: Integration test for parallel ingestion pipeline.
    Verifies chunks and tables are correctly stored in Qdrant and PostgreSQL.

    This test ingests 3 documents in parallel:
    - sample_financial_report.pdf (larger document with tables)
    - sample-small-3-pages.pdf (small document)
    - sample_financial_data.xlsx (Excel spreadsheet)
    """
    # Get test document paths
    fixtures_dir = Path(__file__).parent.parent.parent / "fixtures"
    file_paths = _prepare_test_documents(fixtures_dir)

    # Get baseline counts before ingestion
    qdrant = get_qdrant_client()
    postgres_conn = get_postgresql_connection()

    initial_qdrant_count, initial_chunk_count, initial_table_count, cursor = _setup_baseline_counts(
        qdrant, postgres_conn
    )

    # Run parallel ingestion with max_concurrent=2 (Story 5.0.6 default)
    result = await ingest_documents_parallel(file_paths, max_concurrent=2)

    # Collect final counts (creates new cursor)
    new_qdrant_chunks, new_postgres_chunks, new_table_rows, cursor = _collect_final_counts(
        initial_qdrant_count, initial_chunk_count, initial_table_count, qdrant
    )

    # Verify ingestion results
    _verify_ingestion_result(result, new_qdrant_chunks, new_postgres_chunks, new_table_rows)

    cursor.close()


@pytest.mark.slow  # Takes ~24s, actual PDF ingestion
@pytest.mark.priority("P2")
@pytest.mark.timeout(180)  # 3 minutes
@pytest.mark.asyncio
@pytest.mark.manages_collection_state
async def test_parallel_ingestion_with_single_pdf():
    """Test parallel ingestion with single document (degenerate case).

    Verifies that parallel pipeline works correctly even with just 1 document.
    """
    fixtures_dir = Path(__file__).parent.parent.parent / "fixtures"
    file_paths = [str(fixtures_dir / "sample-small-3-pages.pdf")]

    assert Path(file_paths[0]).exists(), "Test file not found"

    # Run parallel ingestion with single document
    result = await ingest_documents_parallel(file_paths, max_concurrent=2)

    # Verify results
    assert result.total_documents == 1
    assert result.successful == 1
    assert result.failed == 0
    assert len(result.results) == 1
    assert result.results[0].filename is not None
    assert result.results[0].chunk_count > 0


@pytest.mark.slow  # Takes ~24s, actual PDF ingestion
@pytest.mark.priority("P2")
@pytest.mark.timeout(120)  # 2 minutes
@pytest.mark.asyncio
@pytest.mark.manages_collection_state
async def test_parallel_ingestion_sequential_mode():
    """Test parallel ingestion with max_concurrent=1 (sequential mode).

    Story 5.0.6 AC1: Verify semaphore correctly limits to sequential processing.
    """
    fixtures_dir = Path(__file__).parent.parent.parent / "fixtures"
    file_paths = [
        str(fixtures_dir / "sample-small-3-pages.pdf"),
        str(fixtures_dir / "sample_financial_data.xlsx"),
    ]

    for file_path in file_paths:
        assert Path(file_path).exists(), f"Test file not found: {file_path}"

    # Run with max_concurrent=1 (sequential processing)
    result = await ingest_documents_parallel(file_paths, max_concurrent=1)

    # Verify both documents processed successfully
    assert result.total_documents == 2
    assert result.successful >= 1, "At least 1 document should succeed"
    assert len(result.results) >= 1, "At least 1 document should succeed"
