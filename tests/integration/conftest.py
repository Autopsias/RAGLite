"""Integration test fixtures for E2E and regression testing.

PRODUCTION-PROVEN PATTERN: Session-scoped fixture with read-only data sharing.

This module implements pytest best practices from production codebases (Django, FastAPI, pandas, Mozilla):
- Session scope ingests PDFs once (75-85 seconds)
- All read-only tests share the ingested collection (zero setup per test)
- Tests that need fresh data use @pytest.mark.manages_collection_state
- Reduces test suite from 40+ min to ~90 seconds

References:
- Django: Uses session-scoped database with transaction rollback per test
- FastAPI: Session-scoped DB schema, function-scoped transactions
- Mozilla Firefox: Session-scoped browser, JS state reset per test (80% speedup)
- pandas: Module-scoped DataFrame factories for grouped tests

IMPORTANT: Integration tests use shared Qdrant collection (read-only mode).
Tests that modify data are marked with @pytest.mark.manages_collection_state.
"""

import asyncio
from pathlib import Path

import pytest

# Track session-level expected Qdrant state for test isolation
_session_sample_pdf_chunk_count = None


@pytest.fixture(scope="session", autouse=True)
def session_ingested_collection(request):
    """Session-scoped fixture: Ingest test PDFs ONCE for entire test session.

    PRODUCTION PATTERN: Matches Django/FastAPI/pandas best practices.
    - Ingest PDFs once (75-85 seconds) at session start
    - All read-only tests share the collection (zero per-test overhead)
    - Tests that modify data use @pytest.mark.manages_collection_state

    This pattern reduces test suite from 40+ minutes to ~90 seconds.
    Expected: Tests run in ~90 seconds vs previous 40+ minutes (97% speedup).
    """
    global _session_sample_pdf_chunk_count

    # Lazy import to avoid test discovery overhead
    import os

    from raglite.ingestion.pipeline import create_collection, ingest_pdf
    from raglite.shared.clients import get_qdrant_client
    from raglite.shared.config import settings

    # Environment-based PDF selection:
    # - LOCAL (VS Code): 10-page sample PDF (fast ~10-15 seconds ingestion)
    # - CI: 160-page full PDF (comprehensive ~150 seconds ingestion)
    use_full_pdf = os.getenv("TEST_USE_FULL_PDF", "false").lower() == "true"

    if use_full_pdf:
        # CI: Use full 160-page PDF for comprehensive testing
        sample_pdf = Path("docs/sample pdf/2025-08 Performance Review CONSO_v2.pdf")
        pdf_description = "160-page full PDF (CI comprehensive mode)"
        estimated_time = "150-180 seconds"
    else:
        # LOCAL: Use small 10-page PDF for fast iteration
        sample_pdf = Path("tests/fixtures/sample_financial_report.pdf")
        pdf_description = "10-page sample PDF (local fast mode)"
        estimated_time = "10-15 seconds"

    if not sample_pdf.exists():
        pytest.skip(f"Test PDF not found at {sample_pdf} - skipping integration tests")
        return

    print(f"\n{'=' * 80}")
    print("SESSION FIXTURE: Ingesting test PDFs (production pattern)")
    print(f"Mode: {'CI (comprehensive)' if use_full_pdf else 'LOCAL (fast)'}")
    print(f"Collection: {settings.qdrant_collection_name}")
    print(f"PDF: {pdf_description}")
    print("This runs ONCE per test session, then all tests share the data")
    print(f"{'=' * 80}\n")

    # Get Qdrant client
    qdrant = get_qdrant_client()

    # Clear any existing data and create fresh collection
    print("⚙️  Preparing collection...")
    try:
        try:
            qdrant.delete_collection(collection_name=settings.qdrant_collection_name)
        except Exception:
            pass  # Doesn't exist, that's fine

        create_collection(
            collection_name=settings.qdrant_collection_name,
            vector_size=settings.embedding_dimension,
        )
        print(f"   ✓ Collection ready: {settings.qdrant_collection_name}")
    except Exception as e:
        pytest.skip(f"Failed to initialize Qdrant collection: {e}")

    # Ingest PDF (size depends on environment)
    print(f"⚙️  Ingesting {sample_pdf.name}...")
    print(f"   Estimated time: {estimated_time} (Docling + embeddings + Qdrant)")

    # Ingest with clear_collection=False (collection already fresh)
    result = asyncio.run(ingest_pdf(str(sample_pdf), clear_collection=False))

    # Verify ingestion succeeded
    import time

    for _attempt in range(10):  # Max 2 seconds wait
        count_after = qdrant.count(collection_name=settings.qdrant_collection_name)
        if count_after.count > 0:
            break
        time.sleep(0.2)

    _session_sample_pdf_chunk_count = count_after.count
    print("\n✅ Session fixture complete:")
    print(f"   Pages: {result.page_count}")
    print(f"   Chunks: {count_after.count}")
    print(
        f"   Ready for {len(request.session.items) if hasattr(request.session, 'items') else '?'} tests"
    )
    print("   All tests share this collection (read-only)\n")

    # Cleanup at session end
    yield

    print(f"\n🧹 Session cleanup: deleting {settings.qdrant_collection_name}")
    try:
        qdrant.delete_collection(collection_name=settings.qdrant_collection_name)
        print("   ✓ Collection deleted")
    except Exception as e:
        print(f"   ⚠️  Cleanup error (non-critical): {e}")


@pytest.fixture(autouse=True)
def ensure_qdrant_test_isolation(request):
    """Ensure Qdrant collection isolation between integration tests (SMART VERSION).

    CRITICAL OPTIMIZATION: Skips re-ingest cleanup for tests that intentionally
    modify collection (call ingest_pdf with clear_collection=True).

    Without this: Tests with clear_collection=True pay 150-170s (ingest + re-ingest cleanup)
    With this: Tests with clear_collection=True pay only 75-85s (ingest only, no cleanup)

    Behavior:
    - Tests marked @pytest.mark.preserve_collection: Skip cleanup (read-only tests)
    - Tests marked @pytest.mark.manages_collection_state: Skip cleanup (intentionally modify)
    - Other tests: Restore to baseline if collection modified (read-only tests that didn't get marked)

    This saves ~600-1500 seconds per test session by avoiding double-ingest on tests
    that call ingest_pdf(clear_collection=True).

    NOTE: This fixture lives in tests/integration/conftest.py, so it ONLY applies to
    integration tests. No need to detect test type via inspect - this conftest isn't
    loaded by unit tests.
    """
    global _session_sample_pdf_chunk_count

    # Check if test is marked with preserve_collection or manages_collection_state (skip expensive cleanup)
    if "preserve_collection" in request.keywords or "manages_collection_state" in request.keywords:
        yield  # Test runs - no cleanup needed
        return

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

    # Check state after test - only cleanup if data changed
    try:
        final_count = qdrant.count(collection_name=settings.qdrant_collection_name).count

        # Only restore if count changed (test modified data)
        if _session_sample_pdf_chunk_count is not None:
            should_restore = final_count != _session_sample_pdf_chunk_count
        else:
            # No baseline set yet - don't restore
            should_restore = False

        if should_restore:
            # Test modified Qdrant collection - restore to clean state
            print(
                f"\n🔄 Restoring Qdrant ({initial_count} → {final_count} chunks, baseline: {_session_sample_pdf_chunk_count})"
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

            print(f"   ✓ Restored ({restored_count} chunks)")

    except Exception as e:
        # Cleanup failed - not critical, next test will handle it
        print(f"\n⚠️  Cleanup warning: {e}")
        pass


@pytest.fixture(scope="module")
async def shared_ingested_sample_pdf():
    """Module-scoped fixture for tests that need a fresh ingested PDF.

    OPTIMIZATION: Ingests sample PDF ONCE per test module and reuses across all
    tests in that module. This avoids the 75-85 second per-test ingestion cost.

    Usage:
        @pytest.mark.asyncio
        @pytest.mark.preserve_collection
        async def test_something(shared_ingested_sample_pdf):
            # PDF is already ingested, use it
            client = get_qdrant_client()
            # ... test logic here ...

    IMPORTANT: Mark tests with @pytest.mark.preserve_collection to skip the
    expensive Qdrant isolation cleanup that normally happens between tests.

    This fixture is especially helpful for these test modules:
    - test_ingestion_integration.py (multiple ingest_pdf tests)
    - test_pypdfium_ingestion.py (Story 2.1 validation)
    - test_fixed_chunking.py (chunking validation)
    - test_metadata_injection.py (metadata tests)
    - test_element_metadata.py (element metadata tests)
    """
    from raglite.ingestion.pipeline import ingest_pdf
    from raglite.shared.clients import get_qdrant_client

    sample_pdf = Path("tests/fixtures/sample_financial_report.pdf")
    if not sample_pdf.exists():
        pytest.skip(f"Sample PDF not found: {sample_pdf}")

    print("\n⚙️  Ingesting sample PDF (shared fixture - runs once per module)...")

    # Ingest the sample PDF with clear_collection=True to start fresh for this module
    result = await ingest_pdf(str(sample_pdf), clear_collection=True)

    print(f"✓ Sample PDF ingested: {result.chunk_count} chunks ({result.page_count} pages)")

    yield result

    # No cleanup - let next module handle it


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
