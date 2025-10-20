"""Integration test fixtures for E2E and regression testing.

Provides session-scoped fixtures for real data ingestion and Qdrant setup.

IMPORTANT: Integration tests use shared Qdrant collection across parallel workers.
All integration tests are grouped to run in the same worker to avoid race conditions.
"""

import asyncio
from pathlib import Path

import pytest


@pytest.fixture(scope="session", autouse=True)
def ingest_test_data():
    """Ingest small sample PDF into Qdrant for fast integration tests.

    This session-scoped fixture uses the 10-page sample PDF for fast local testing.
    Tests that require the full 160-page PDF should use @pytest.mark.skipif.

    The fixture:
    1. CLEARS any existing Qdrant data to ensure clean state
    2. Uses ONLY the 10-page sample PDF (fast: ~8 seconds)
    3. Ingests PDF into Qdrant (creates collection if needed)
    4. Makes data available for all integration tests

    For accuracy tests with full 160-page PDF, use:
        @pytest.mark.skipif(
            not pytest.run_slow,
            reason="Requires full 160-page PDF. Run with: pytest --run-slow"
        )
    """
    # Lazy import to avoid test discovery overhead
    from raglite.ingestion.pipeline import create_collection, ingest_pdf
    from raglite.shared.clients import get_qdrant_client
    from raglite.shared.config import settings

    # ALWAYS use 10-page sample PDF for fast local testing
    sample_pdf = Path("tests/fixtures/sample_financial_report.pdf")

    if not sample_pdf.exists():
        pytest.skip(f"Sample PDF not found at {sample_pdf} - skipping integration tests")
        return

    # Get Qdrant client
    qdrant = get_qdrant_client()

    # CRITICAL FIX: Always delete and recreate collection to ensure clean state
    # This prevents test contamination from previous runs
    print("\n🧹 Clearing Qdrant collection for clean test state...")
    try:
        qdrant.delete_collection(collection_name=settings.qdrant_collection_name)
        print("   ✓ Old collection deleted")
    except Exception:
        # Collection doesn't exist - that's fine
        pass

    # Create fresh collection with correct schema
    try:
        create_collection(
            collection_name=settings.qdrant_collection_name,
            vector_size=settings.embedding_dimension,
        )
        print(f"   ✓ Fresh collection created: {settings.qdrant_collection_name}")
    except Exception as e:
        pytest.skip(f"Failed to initialize Qdrant collection: {e}")

    # Ingest sample PDF (use asyncio.run for async function in sync fixture)
    print(f"\n⚙️  Ingesting {sample_pdf.name} (10-page sample) into Qdrant...")
    print("   This should take ~8-10 seconds for fast local testing...")

    result = asyncio.run(ingest_pdf(str(sample_pdf)))

    # Verify ingestion succeeded
    count_after = qdrant.count(collection_name=settings.qdrant_collection_name)
    print(f"✓ Ingested {result.page_count} pages, {count_after.count} chunks into Qdrant")

    # Fixture doesn't need to yield anything - data is now in Qdrant
    # Tests can directly query Qdrant using search_documents()
