"""Validation and error handling tests for parallel ingestion.

Tests input validation, error handling, and metadata storage for the
parallel ingestion pipeline.
"""

from pathlib import Path

import pytest

from raglite.ingestion.document_ingestion import ingest_documents_parallel
from raglite.shared.clients import get_postgresql_connection, reset_postgresql_connection
from raglite.shared.safety import SafetyGuard

# Mark all tests in this module as integration tests
# CRITICAL: xdist_group required because tests use embedding model via ingest_documents_parallel
pytestmark = [
    pytest.mark.integration,
    pytest.mark.preserve_collection,
    pytest.mark.slow,
    pytest.mark.xdist_group(name="embedding_model_reads"),
]


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
    fixtures_dir = Path(__file__).parent.parent.parent / "fixtures"
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
    fixtures_dir = Path(__file__).parent.parent.parent / "fixtures"
    file_paths = [str(fixtures_dir / "sample-small-3-pages.pdf")]

    assert Path(file_paths[0]).exists(), "Test file not found"

    # Clear stale test data to ensure accurate differential counts
    # Tests with @pytest.mark.manages_collection_state don't use ingest_test_data fixture
    # which normally handles this cleanup (conftest.py lines 569-571)
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
