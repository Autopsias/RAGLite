"""Module-scoped fixtures for integration tests.

This module provides expensive module-scoped fixtures that run once per test module:
- ingested_160_page_pdf: Full PDF ingestion for comprehensive tests
- ingested_excerpt_pdf: Story 2.14 excerpt (pages 18-50) for validation tests

Fixtures:
    ingested_160_page_pdf: 160-page PDF ingestion (shared across slow tests)
    ingested_excerpt_pdf: 33-page excerpt PDF for Story 2.14 validation
"""

from pathlib import Path

import pytest

# Import session state globals
from . import session_state


@pytest.fixture(scope="module")
async def ingested_160_page_pdf():
    """Module-scoped fixture for 160-page PDF ingestion - shared across slow tests.

    This fixture ingests the 160-page PDF ONCE per test module and reuses the result
    across multiple tests, avoiding the 16-18 minute re-ingestion cost per test.

    Usage:
        @pytest.mark.slow
        @pytest.mark.asyncio
        async def test_something(ingested_160_page_pdf):
            # PDF is already ingested, just use the Qdrant collection
            client = get_qdrant_client()
            # ... test logic here ...

    Returns:
        tuple: (metadata, qdrant_client) - Ingestion metadata and Qdrant client
    """
    from raglite.ingestion.pipeline import ingest_pdf
    from raglite.shared.clients import get_qdrant_client

    pdf_path = Path("docs/sample pdf/2025-08 Performance Review CONSO_v2.pdf")
    if not pdf_path.exists():
        pytest.skip(f"160-page PDF not found: {pdf_path}")

    print("\n⚙️  Ingesting 160-page PDF (shared fixture - runs once per module)...")
    metadata = await ingest_pdf(str(pdf_path), clear_existing=True)
    client = get_qdrant_client()

    print(f"✓ 160-page PDF ingested: {metadata.chunk_count} chunks")

    yield metadata, client

    # No cleanup - let next test use the data or clean it up themselves


@pytest.fixture(scope="module")
async def ingested_excerpt_pdf():
    """Module-scoped fixture for Story 2.14 excerpt PDF (pages 18-50).

    This fixture ingests the 33-page excerpt PDF ONCE per test module for Story 2.14
    validation tests. The excerpt contains specific test data:
    - Pages: 18-50 (33 pages)
    - Entities: Portugal, Tunisia, Angola, Brazil, Lebanon
    - Metrics: Variable Cost, EBITDA, Sales Volumes, Thermal Energy, etc.
    - Periods: Aug-25, Aug-25 YTD, 2025

    Usage:
        @pytest.mark.asyncio
        @pytest.mark.preserve_collection
        async def test_excerpt_query(ingested_excerpt_pdf):
            # Excerpt PDF is already ingested with PostgreSQL tables populated
            # ... test logic here ...

    Returns:
        tuple: (metadata, qdrant_client) - Ingestion metadata and Qdrant client
    """
    from raglite.ingestion.pipeline import ingest_pdf
    from raglite.shared.clients import get_postgresql_connection, get_qdrant_client

    # Use absolute path from project root
    project_root = Path(__file__).parent.parent.parent.parent
    pdf_path = project_root / "docs" / "sample pdf" / "test-pages-18-50.pdf"
    if not pdf_path.exists():
        pytest.skip(f"Story 2.14 excerpt PDF not found: {pdf_path}")

    print("\n⚙️  Ingesting Story 2.14 excerpt PDF (pages 18-50, 33 pages)...")
    metadata = await ingest_pdf(str(pdf_path), clear_existing=True)
    client = get_qdrant_client()

    print(f"✓ Excerpt PDF ingested: {metadata.chunk_count} chunks ({metadata.page_count} pages)")

    # Verify PostgreSQL has data
    try:
        # PERFORMANCE: Use cached connection to reduce overhead
        conn = get_postgresql_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM financial_tables")
        table_count = cursor.fetchone()[0]

        cursor.execute("SELECT MIN(page_number), MAX(page_number) FROM financial_tables")
        page_range = cursor.fetchone()

        cursor.close()  # Only close cursor, keep connection cached
        # Note: Connection kept open for session to reduce overhead

        print(
            f"✓ PostgreSQL financial_tables: {table_count} rows, pages {page_range[0]}-{page_range[1]}"
        )

        if table_count == 0:
            pytest.skip("Excerpt PDF ingestion did not populate PostgreSQL tables")

    except Exception as e:
        print(f"⚠️  PostgreSQL verification failed: {e}")

    yield metadata, client

    # CRITICAL: Restore session fixture state after module ends
    # This prevents excerpt data from polluting subsequent tests
    print("\n🔄 Restoring session fixture state (excerpt module cleanup)...")

    if session_state.session_snapshot_name:
        # FAST PATH: Restore from snapshot (<1s)
        try:
            from raglite.shared.config import settings

            # Delete excerpt collection
            try:
                client.delete_collection(collection_name=settings.qdrant_collection_name)
            except Exception:
                pass

            # Recover from snapshot
            qdrant_host = settings.qdrant_url.rstrip("/")
            snapshot_url = f"{qdrant_host}/collections/{settings.qdrant_collection_name}/snapshots/{session_state.session_snapshot_name}"

            client.recover_snapshot(
                collection_name=settings.qdrant_collection_name,
                location=snapshot_url,
                priority="snapshot",
                wait=True,
            )

            # Verify restoration
            count_after = client.count(collection_name=settings.qdrant_collection_name)
            print(f"   ✓ Session state restored: {count_after.count} chunks (snapshot recovery)")
        except Exception as e:
            print(f"   ⚠️  Snapshot recovery failed: {e}, falling back to re-ingestion")
            # Fallback: trigger session fixture re-ingestion by clearing and relying on autouse fixture
            try:
                client.delete_collection(collection_name=settings.qdrant_collection_name)
            except Exception:
                pass
    else:
        print("   ⚠️  No snapshot available, session state NOT restored (tests may fail!)")
