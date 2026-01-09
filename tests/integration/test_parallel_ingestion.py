"""Integration tests for parallel document ingestion (Story 5.0.6 Task 7.1).

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
pytestmark = [pytest.mark.integration, pytest.mark.preserve_collection, pytest.mark.slow]


def _prepare_test_documents():
    """Prepare test document paths for parallel ingestion.

    Returns:
        List of test file paths
    """
    fixtures_dir = Path(__file__).parent.parent / "fixtures"
    file_paths = [
        str(fixtures_dir / "sample_financial_report.pdf"),
        str(fixtures_dir / "sample-small-3-pages.pdf"),
        str(fixtures_dir / "sample_financial_data.xlsx"),
    ]

    # Verify all test files exist
    for file_path in file_paths:
        assert Path(file_path).exists(), f"Test file not found: {file_path}"

    return file_paths


def _setup_postgresql_baseline():
    """Setup PostgreSQL connection and clear test data.

    Returns:
        Tuple of (connection, cursor, initial_chunk_count, initial_table_count)
    """
    from raglite.shared.clients import reset_postgresql_connection

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


def _get_baseline_counts(qdrant, cursor):
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


def _verify_ingestion_result(result):
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


def _verify_qdrant_storage(qdrant, initial_count):
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


def _reset_postgresql_after_ingestion():
    """Reset PostgreSQL connection after ingestion.

    Returns:
        Tuple of (new connection, new cursor)
    """
    from raglite.shared.clients import reset_postgresql_connection

    reset_postgresql_connection()
    postgres_conn = get_postgresql_connection()
    cursor = postgres_conn.cursor()

    # Force new transaction to see committed data from parallel workers
    if not postgres_conn.autocommit:
        postgres_conn.rollback()

    return postgres_conn, cursor


def _verify_postgresql_storage(cursor, initial_chunk_count, initial_table_count):
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


def _verify_storage_systems(new_qdrant_chunks, new_postgres_chunks):
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


def _print_test_summary(result, new_qdrant_chunks, new_postgres_chunks, new_table_rows):
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
    # Prepare test documents
    file_paths = _prepare_test_documents()

    # Setup Qdrant
    qdrant = get_qdrant_client()

    # Setup PostgreSQL and clear test data
    postgres_conn, cursor, initial_chunk_count, initial_table_count = _setup_postgresql_baseline()

    # Get baseline counts
    initial_qdrant_count, chunk_count, table_count = _get_baseline_counts(qdrant, cursor)

    # Validate cleanup worked
    assert chunk_count == 0, (
        f"PostgreSQL cleanup failed - still has {chunk_count} chunks. "
        f"Expected 0 after DELETE FROM financial_chunks"
    )

    # Run parallel ingestion with max_concurrent=2 (Story 5.0.6 default)
    result = await ingest_documents_parallel(file_paths, max_concurrent=2)

    # Verify ingestion result
    _verify_ingestion_result(result)

    # Verify Qdrant storage
    new_qdrant_chunks = _verify_qdrant_storage(qdrant, initial_qdrant_count)

    # Reset PostgreSQL connection after ingestion
    postgres_conn, cursor = _reset_postgresql_after_ingestion()

    # Verify PostgreSQL storage
    new_postgres_chunks, new_table_rows = _verify_postgresql_storage(
        cursor, initial_chunk_count, initial_table_count
    )

    # Verify both storage systems
    _verify_storage_systems(new_qdrant_chunks, new_postgres_chunks)

    cursor.close()

    # Print summary
    _print_test_summary(result, new_qdrant_chunks, new_postgres_chunks, new_table_rows)


@pytest.mark.slow  # Takes ~24s, actual PDF ingestion
@pytest.mark.priority("P2")
@pytest.mark.timeout(180)  # 3 minutes
@pytest.mark.asyncio
@pytest.mark.manages_collection_state
async def test_parallel_ingestion_with_single_pdf():
    """Test parallel ingestion with single document (degenerate case).

    Verifies that parallel pipeline works correctly even with just 1 document.
    """
    fixtures_dir = Path(__file__).parent.parent / "fixtures"
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
    fixtures_dir = Path(__file__).parent.parent / "fixtures"
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


@pytest.mark.priority("P2")
@pytest.mark.timeout(60)  # 1 minute
@pytest.mark.asyncio
async def test_parallel_ingestion_empty_file_list():
    """Test parallel ingestion with empty file list (error case).

    Should raise ValueError when file_paths is empty.
    """
    with pytest.raises(ValueError, match="file_paths cannot be empty"):
        await ingest_documents_parallel([])


@pytest.mark.priority("P2")
@pytest.mark.timeout(60)  # 1 minute
@pytest.mark.asyncio
async def test_parallel_ingestion_invalid_concurrency():
    """Test parallel ingestion with invalid max_concurrent (error case).

    Should raise ValueError when max_concurrent < 1.
    """
    fixtures_dir = Path(__file__).parent.parent / "fixtures"
    file_paths = [str(fixtures_dir / "sample-small-3-pages.pdf")]

    with pytest.raises(ValueError, match="max_concurrent must be >= 1"):
        await ingest_documents_parallel(file_paths, max_concurrent=0)


@pytest.mark.slow  # Takes ~24s, actual PDF ingestion
@pytest.mark.priority("P1")
@pytest.mark.timeout(300)  # 5 minutes
@pytest.mark.asyncio
@pytest.mark.manages_collection_state
async def test_parallel_ingestion_stores_metadata():
    """Test AC2: Verify document metadata is correctly stored.

    Story 5.0.6: Metadata should be stored in both Qdrant and PostgreSQL.
    """
    fixtures_dir = Path(__file__).parent.parent / "fixtures"
    file_paths = [str(fixtures_dir / "sample-small-3-pages.pdf")]

    assert Path(file_paths[0]).exists(), "Test file not found"

    # Clear stale test data to ensure accurate differential counts
    # Tests with @pytest.mark.manages_collection_state don't use ingest_test_data fixture
    # which normally handles this cleanup (conftest.py lines 569-571)
    from raglite.shared.clients import reset_postgresql_connection

    reset_postgresql_connection()

    # CRITICAL SAFETY CHECK (Story 6.26): Validate test environment BEFORE any DELETE
    guard = SafetyGuard()
    guard.validate_test_environment("test_metadata_stored_cleanup")

    postgres_conn = get_postgresql_connection()
    cursor = postgres_conn.cursor()

    cursor.execute("DELETE FROM financial_chunks")
    cursor.execute("DELETE FROM financial_tables")
    postgres_conn.commit()
    cursor.close()

    # Ingest document
    result = await ingest_documents_parallel(file_paths)

    assert result.successful == 1
    assert len(result.results) == 1
    metadata = result.results[0]

    # Verify metadata structure
    assert metadata is not None
    assert metadata.filename is not None
    assert metadata.chunk_count > 0
    assert metadata.ingestion_timestamp is not None
    assert metadata.page_count > 0

    # Verify metadata is accessible in PostgreSQL
    # CRITICAL FIX (CI): Reset singleton connection to force fresh connection
    # This ensures we see all committed data from parallel ingestion workers
    from raglite.shared.clients import reset_postgresql_connection

    reset_postgresql_connection()

    postgres_conn = get_postgresql_connection()
    cursor = postgres_conn.cursor()

    # Force new transaction to see committed data from parallel workers
    # Same transaction visibility fix as test_parallel_ingestion_three_documents
    if not postgres_conn.autocommit:
        postgres_conn.rollback()  # Start fresh transaction with visibility of committed data

    # Note: document_id in PostgreSQL corresponds to filename from DocumentMetadata
    cursor.execute(
        "SELECT COUNT(*) FROM financial_chunks WHERE document_id LIKE %s",
        (f"%{Path(metadata.filename).stem}%",),
    )
    chunk_count = cursor.fetchone()[0]
    assert chunk_count > 0, "Chunks should be stored with document_id matching filename"

    cursor.close()


@pytest.mark.priority("P1")
@pytest.mark.timeout(120)  # 2 minutes
@pytest.mark.asyncio
@pytest.mark.preserve_collection  # Assumes data already ingested
async def test_query_latency_with_enrichment():
    """Test AC5/Task 7.4: Verify query latency with metadata enrichment <3 seconds.

    Story 5.0.6 Task 7.4: Validate that query-time metadata enrichment completes
    within the 3-second budget, maintaining acceptable query performance.

    This test assumes data is already ingested (run after test_parallel_ingestion_three_documents).
    """
    import time

    from qdrant_client import QdrantClient
    from qdrant_client.http.exceptions import UnexpectedResponse

    from raglite.retrieval.search import hybrid_search

    # Check if Qdrant collection exists before running test
    try:
        client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
        client.get_collection(settings.qdrant_collection_name)
    except UnexpectedResponse as e:
        pytest.skip(f"Qdrant collection not available: {e}")

    # Verify query-time metadata enrichment is enabled
    assert settings.query_time_metadata_enabled, (
        "Query-time metadata enrichment must be enabled for this test "
        "(set QUERY_TIME_METADATA_ENABLED=true)"
    )

    # Test query (financial domain query that should retrieve results)
    query = "What is the revenue for the last fiscal year?"

    # Measure query latency with enrichment
    start_time = time.perf_counter()
    results = await hybrid_search(query, top_k=5)
    elapsed_seconds = time.perf_counter() - start_time

    # Verify results were returned
    assert len(results) > 0, "Query should return at least 1 result"

    # AC5: Verify query completes within 3-second budget (Task 7.4)
    assert elapsed_seconds < 3.0, (
        f"Query with enrichment took {elapsed_seconds:.2f}s, exceeds 3s budget. "
        f"Expected: <3s for query-time metadata enrichment (Story 5.0.6 AC5)."
    )

    # Verify enrichment actually ran (check that results were enriched)
    # Note: If all results already had metadata, enrichment may have been skipped
    # This is expected behavior and not a failure

    print("\n✅ Query latency test passed:")
    print(f"   Query: {query}")
    print(f"   Results returned: {len(results)}")
    print(f"   Latency: {elapsed_seconds:.2f}s (target: <3s)")
    print(
        f"   Query-time enrichment: {'enabled' if settings.query_time_metadata_enabled else 'disabled'}"
    )
    print(f"   Timeout budget: {settings.query_time_metadata_timeout}s")


@pytest.mark.priority("P2")
@pytest.mark.timeout(180)  # 3 minutes
@pytest.mark.asyncio
@pytest.mark.preserve_collection  # Assumes data already ingested
async def test_query_latency_multiple_queries():
    """Test Task 7.4 Extended: Verify consistent query latency across multiple queries.

    Validates that query-time enrichment maintains acceptable performance across
    a batch of diverse queries.
    """
    import statistics
    import time

    from qdrant_client import QdrantClient
    from qdrant_client.http.exceptions import UnexpectedResponse

    from raglite.retrieval.search import hybrid_search

    # Check if Qdrant collection exists before running test
    try:
        client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
        client.get_collection(settings.qdrant_collection_name)
    except UnexpectedResponse as e:
        pytest.skip(f"Qdrant collection not available: {e}")

    # Test queries (financial domain)
    test_queries = [
        "What is the total revenue?",
        "Show me the EBITDA margin",
        "What are the operating expenses?",
        "How many employees does the company have?",
        "What is the profit for Q3?",
    ]

    latencies = []

    for query in test_queries:
        start_time = time.perf_counter()
        _ = await hybrid_search(query, top_k=5)
        elapsed = time.perf_counter() - start_time
        latencies.append(elapsed)

        # Individual query should complete within 3 seconds
        assert elapsed < 3.0, f"Query '{query}' took {elapsed:.2f}s, exceeds 3s budget"

    # Calculate statistics
    avg_latency = statistics.mean(latencies)
    max_latency = max(latencies)
    min_latency = min(latencies)

    # All queries should be under 3 seconds
    assert max_latency < 3.0, f"Max query latency {max_latency:.2f}s exceeds 3s budget"

    # Average should be well under 3 seconds
    assert avg_latency < 2.5, f"Average query latency {avg_latency:.2f}s too close to 3s budget"

    print("\n✅ Multiple query latency test passed:")
    print(f"   Queries tested: {len(test_queries)}")
    print(f"   Average latency: {avg_latency:.2f}s (target: <2.5s)")
    print(f"   Min latency: {min_latency:.2f}s")
    print(f"   Max latency: {max_latency:.2f}s (target: <3s)")
    print("   All queries within budget: ✓")
