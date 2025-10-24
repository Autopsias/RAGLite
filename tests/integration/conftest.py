"""Integration test fixtures for E2E and regression testing.

Provides session-scoped fixtures for real data ingestion and Qdrant setup.

IMPORTANT: Integration tests use shared Qdrant collection across parallel workers.
All integration tests are grouped to run in the same worker to avoid race conditions.
"""

import asyncio
from pathlib import Path

import pytest

# Track session-level expected Qdrant state for test isolation
_session_sample_pdf_chunk_count = None


@pytest.fixture(scope="session", autouse=True)
def ingest_test_data(request):
    """Ingest small sample PDF into Qdrant for fast integration tests.

    This session-scoped fixture uses the 10-page sample PDF for fast local testing.
    Tests that require the full 160-page PDF should use @pytest.mark.skipif.

    The fixture:
    1. CHECKS if data already exists in Qdrant (skip re-ingestion if present)
    2. CLEARS existing data if not from sample PDF (ensures clean state)
    3. Uses ONLY the 10-page sample PDF (fast: ~70-80 seconds with Docling + embeddings)
    4. Ingests PDF into Qdrant (creates collection if needed)
    5. Makes data available for all integration tests

    For accuracy tests with full 160-page PDF, use:
        @pytest.mark.skipif(
            not pytest.run_slow,
            reason="Requires full 160-page PDF. Run with: pytest --run-slow"
        )
    """
    # SKIP conftest for AC3 ground truth tests (Story 2.5)
    # These tests require the full 160-page PDF which must be pre-ingested
    # using: python tests/integration/setup_test_data.py
    #
    # Check if we're collecting AC3 ground truth tests by looking at the session items
    if hasattr(request.session, "items"):
        for item in request.session.items:
            if "test_ac3_ground_truth.py" in str(item.fspath):
                print(
                    "\n⚠️  AC3 ground truth test detected - skipping conftest sample PDF ingestion"
                )
                print("   Using pre-ingested full 160-page PDF from setup_test_data.py\n")
                return  # Skip conftest - use pre-ingested full PDF

    global _session_sample_pdf_chunk_count

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

    # DISABLED OPTIMIZATION: Always clear and re-ingest to prevent test contamination
    # Previous logic tried to reuse Qdrant data but caused race conditions when:
    # 1. TestPDFIngestionIntegration tests ingest different PDFs (contamination)
    # 2. Tests run in different orders produce different initial states
    # 3. _session_sample_pdf_chunk_count tracking gets out of sync
    #
    # Solution: Always start with clean state - only costs 8-10s per test session
    # To manually preserve Qdrant data between test runs: docker-compose restart qdrant
    #
    # Kept commented code for reference:
    # try:
    #     collection_info = qdrant.get_collection(settings.qdrant_collection_name)
    #     if collection_info.points_count and collection_info.points_count > 0:
    #         scroll_result = qdrant.scroll(collection_name=settings.qdrant_collection_name, limit=collection_info.points_count)
    #         if scroll_result[0]:
    #             all_from_sample = all(point.payload.get("source_document", "") == sample_pdf_name for point in scroll_result[0] if point.payload)
    #             if all_from_sample and _session_sample_pdf_chunk_count is None:
    #                 _session_sample_pdf_chunk_count = collection_info.points_count
    #                 return
    # except Exception:
    #     pass

    # CRITICAL FIX: Always delete and recreate collection to ensure clean state
    # This prevents test contamination from previous runs
    print("\n🧹 Clearing Qdrant collection for clean test state...")
    try:
        qdrant.delete_collection(collection_name=settings.qdrant_collection_name)

        # RACE CONDITION FIX: Wait for Qdrant to finish async deletion
        # Qdrant processes deletion asynchronously - verify it's truly gone before proceeding
        import time

        for _attempt in range(20):  # Max 4 seconds wait (20 × 0.2s)
            try:
                qdrant.get_collection(settings.qdrant_collection_name)
                time.sleep(0.2)  # Collection still exists, wait
            except Exception:
                # Collection is gone - safe to proceed
                break

        print("   ✓ Old collection deleted (verified)")
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

    # Verify ingestion succeeded and track expected state
    # CRITICAL: Wait for Qdrant to commit before proceeding to tests
    import time

    for _attempt in range(10):  # Max 2 seconds wait
        count_after = qdrant.count(collection_name=settings.qdrant_collection_name)
        if count_after.count > 0:
            break
        time.sleep(0.2)

    _session_sample_pdf_chunk_count = count_after.count
    print(f"✓ Ingested {result.page_count} pages, {count_after.count} chunks into Qdrant")
    print(f"   Session baseline set: {_session_sample_pdf_chunk_count} chunks")

    # Fixture doesn't need to yield anything - data is now in Qdrant
    # Tests can directly query Qdrant using search_documents()


@pytest.fixture(autouse=True)
def ensure_qdrant_test_isolation():
    """Ensure Qdrant collection isolation between integration tests.

    Tracks collection state before/after each test and restores if modified.
    This prevents test contamination when tests ingest different PDFs or modify data.

    Only pays cleanup cost when tests actually modify Qdrant (most don't).

    NOTE: This fixture lives in tests/integration/conftest.py, so it ONLY applies to
    integration tests. No need to detect test type via inspect - this conftest isn't
    loaded by unit tests.
    """
    global _session_sample_pdf_chunk_count

    # Import Qdrant client and settings
    from raglite.shared.clients import get_qdrant_client
    from raglite.shared.config import settings

    qdrant = get_qdrant_client()

    # Record state before test
    try:
        initial_count = qdrant.count(collection_name=settings.qdrant_collection_name).count
    except Exception:
        initial_count = 0

    yield  # Test runs here

    # Check state after test
    try:
        final_count = qdrant.count(collection_name=settings.qdrant_collection_name).count

        # DEBUG: Always print state for troubleshooting
        print(
            f"\n[DEBUG] Test isolation check: initial={initial_count}, final={final_count}, baseline={_session_sample_pdf_chunk_count}"
        )

        # Restore if count changed AND doesn't match baseline (if baseline is set)
        # Simplified logic: if test changed data AND it's not the baseline, restore
        if _session_sample_pdf_chunk_count is not None:
            should_restore = final_count != _session_sample_pdf_chunk_count
        else:
            # No baseline set yet - don't restore
            should_restore = False

        print(f"[DEBUG] Should restore: {should_restore}")

        if should_restore:
            # Test modified Qdrant collection - restore to clean state
            print(
                f"\n🔄 Test modified Qdrant ({initial_count} → {final_count} chunks, baseline: {_session_sample_pdf_chunk_count}) - restoring clean state..."
            )

            from raglite.ingestion.pipeline import create_collection, ingest_pdf

            sample_pdf = Path("tests/fixtures/sample_financial_report.pdf")

            # Clear collection
            try:
                qdrant.delete_collection(collection_name=settings.qdrant_collection_name)
            except Exception:
                pass

            # Recreate with sample PDF data
            create_collection(
                collection_name=settings.qdrant_collection_name,
                vector_size=settings.embedding_dimension,
            )

            asyncio.run(ingest_pdf(str(sample_pdf)))

            # CRITICAL: Wait for Qdrant to commit the restoration
            # Qdrant processes async operations - verify data is actually there
            import time

            restored_count = 0
            for _attempt in range(10):  # Max 2 seconds wait (10 × 0.2s)
                restored_count = qdrant.count(collection_name=settings.qdrant_collection_name).count
                if restored_count == _session_sample_pdf_chunk_count:
                    break
                time.sleep(0.2)  # Wait for Qdrant to commit

            print(f"   ✓ Qdrant restored to clean state ({restored_count} chunks)")

    except Exception as e:
        # Cleanup failed - not critical, next test will handle it
        print(f"\n⚠️  Qdrant cleanup warning: {e} (next test will reinitialize if needed)")
        pass


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
    metadata = await ingest_pdf(str(pdf_path), clear_collection=True)
    client = get_qdrant_client()

    print(f"✓ 160-page PDF ingested: {metadata.chunk_count} chunks")

    yield metadata, client

    # No cleanup - let next test use the data or clean it up themselves
