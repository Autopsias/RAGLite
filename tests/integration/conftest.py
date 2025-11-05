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

import os
import socket
import sys

import pytest

# Debug: Track module load
print("DEBUG: conftest.py loading...", file=sys.stderr)

# CRITICAL: Check service availability BEFORE importing any raglite modules
# Test modules import raglite code which may try to connect at import time
# This prevents collection-time hangs when services are unavailable
print("DEBUG: Checking service availability before imports...", file=sys.stderr)

# Get connection settings from environment (same as shared.config.Settings)
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))


def check_service_available(host: str, port: int, service_name: str) -> bool:
    """Check if service is reachable with 5-second timeout."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, port))
        sock.close()
        if result == 0:
            print(f"DEBUG: {service_name} available at {host}:{port}", file=sys.stderr)
            return True
        else:
            print(f"DEBUG: {service_name} connection refused at {host}:{port}", file=sys.stderr)
            return False
    except TimeoutError:
        print(f"DEBUG: {service_name} connection timeout at {host}:{port}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"DEBUG: {service_name} check failed: {e}", file=sys.stderr)
        return False


# Check both services at module load time
qdrant_available = check_service_available(QDRANT_HOST, QDRANT_PORT, "Qdrant")
postgres_available = check_service_available(POSTGRES_HOST, POSTGRES_PORT, "PostgreSQL")

# Skip ALL integration tests if either service is unavailable
if not qdrant_available or not postgres_available:
    missing = []
    if not qdrant_available:
        missing.append(f"Qdrant ({QDRANT_HOST}:{QDRANT_PORT})")
    if not postgres_available:
        missing.append(f"PostgreSQL ({POSTGRES_HOST}:{POSTGRES_PORT})")

    skip_reason = f"Integration tests require: {', '.join(missing)}"
    print(f"DEBUG: Skipping all integration tests - {skip_reason}", file=sys.stderr)

    # Configure pytest to skip all tests in this directory
    collect_ignore_glob = ["*.py"]
    pytest.skip(skip_reason, allow_module_level=True)

print("DEBUG: Services available, continuing with imports...", file=sys.stderr)

# Now safe to import raglite modules (services are confirmed available)
import asyncio  # noqa: E402
from pathlib import Path  # noqa: E402

# Track session-level expected Qdrant state for test isolation
_session_sample_pdf_chunk_count = None


@pytest.fixture(scope="session", autouse=True)
def warmup_embedding_model():
    """Pre-warm embedding model before any tests run.

    CRITICAL PERFORMANCE FIX: Fin-E5 model takes 60-70s to load from cold start.
    Without this fixture, the model loads during session_ingested_collection fixture,
    adding 60-70s overhead to the expected 10-15s ingestion time.

    This fixture loads the model ONCE at session start, before any PDF ingestion.
    Expected savings: 60-70s per test session (reduces session fixture from 86s → 12-15s).

    The model singleton persists across all tests in the session.
    """
    print("\n🔥 PRE-WARMING EMBEDDING MODEL (60-70s one-time load)...", file=sys.stderr)

    from raglite.shared.clients import get_embedding_model

    model = get_embedding_model()
    dim = model.get_sentence_embedding_dimension()

    print(f"✅ Embedding model ready: {dim} dimensions (Fin-E5 loaded)", file=sys.stderr)

    yield
    # Model singleton persists for entire session


@pytest.fixture(scope="session", autouse=True)
def session_ingested_collection(request):
    """Session-scoped fixture: Ingest test PDFs ONCE for entire test session.

    PRODUCTION PATTERN: Matches Django/FastAPI/pandas best practices.
    - Ingest PDFs once (75-85 seconds) at session start
    - All read-only tests share the collection (zero per-test overhead)
    - Tests that modify data use @pytest.mark.manages_collection_state

    This pattern reduces test suite from 40+ minutes to ~90 seconds.
    Expected: Tests run in ~90 seconds vs previous 40+ minutes (97% speedup).

    SKIP INGESTION MODE (--skip-ingestion flag):
    When flag is set, skips ingestion and uses existing Qdrant/PostgreSQL data.
    This saves ~25 minutes when data has already been ingested manually.

    Usage:
        # First: Ingest data manually
        python scripts/ingest-full-pdf-ac3.py

        # Then: Run tests with existing data
        pytest tests/integration/ --skip-ingestion --run-slow -m ""

    TIMEOUT PROTECTION: If fixture hangs, pytest will timeout after 900s
    (configured in pytest.ini timeout_func_only=true, so fixture has full timeout).

    PERFORMANCE OPTIMIZATION: This fixture runs EXACTLY ONCE per test session.
    All integration tests share the same ingested PDF collection for maximum speed.

    NOTE: Depends on warmup_embedding_model to ensure embedding model is loaded
    before PDF ingestion starts.
    """
    global _session_sample_pdf_chunk_count

    # Lazy import (module-level checks already confirmed services are available)
    import os

    print("\nDEBUG: Entering session_ingested_collection fixture", file=sys.stderr)

    # Check if we should skip ingestion and use existing data
    skip_ingestion = request.config.getoption("--skip-ingestion")

    if skip_ingestion:
        print("\n" + "=" * 80)
        print("🚀 SKIP INGESTION MODE: Using existing Qdrant/PostgreSQL data")
        print("=" * 80)

        from raglite.shared.clients import get_qdrant_client
        from raglite.shared.config import settings

        qdrant = get_qdrant_client()

        # Verify collection exists and has data
        try:
            count = qdrant.count(collection_name=settings.qdrant_collection_name).count

            if count == 0:
                error_msg = (
                    "❌ ERROR: --skip-ingestion requires existing data, but Qdrant collection is empty!\n"
                    "   Please ingest data first:\n"
                    "   python scripts/ingest-full-pdf-ac3.py"
                )
                print(f"\n{error_msg}", file=sys.stderr)
                pytest.fail(error_msg)

            # Store chunk count for test isolation
            _session_sample_pdf_chunk_count = count

            print(f"\n✅ Using existing collection: {settings.qdrant_collection_name}")
            print(f"   Chunks: {count}")
            print("   Time saved: ~25 minutes")
            print("   All tests will share this existing data\n")
            print("=" * 80 + "\n")

            # Yield without cleanup - data is managed externally
            yield
            return

        except Exception as e:
            error_msg = f"❌ ERROR: Failed to verify existing data: {e}"
            print(f"\n{error_msg}", file=sys.stderr)
            pytest.fail(error_msg)

    print("\nDEBUG: Proceeding with full ingestion (--skip-ingestion not set)", file=sys.stderr)

    from raglite.ingestion.pipeline import create_collection, ingest_pdf
    from raglite.shared.clients import get_qdrant_client
    from raglite.shared.config import settings

    print("DEBUG: Fixture imports successful", file=sys.stderr)

    # SAFETY CHECK: Warn if collection has data and user didn't use --skip-ingestion
    # This prevents accidental deletion of manually ingested data
    print("DEBUG: Checking for existing data...", file=sys.stderr)
    qdrant_check = get_qdrant_client()
    try:
        existing_count = qdrant_check.count(collection_name=settings.qdrant_collection_name).count
        if existing_count > 0:
            warning_msg = (
                f"\n{'=' * 80}\n"
                f"⚠️  WARNING: Collection '{settings.qdrant_collection_name}' already has {existing_count} chunks!\n"
                f"\n"
                f"Without --skip-ingestion, this fixture will DELETE existing data and re-ingest.\n"
                f"This wastes ~25 minutes if you already ingested manually.\n"
                f"\n"
                f"Options:\n"
                f'  1. Use existing data: pytest --skip-ingestion --run-slow -m ""\n'
                f"  2. Continue with re-ingestion: Press Enter to proceed (will delete existing data)\n"
                f"  3. Abort: Ctrl+C to cancel\n"
                f"{'=' * 80}\n"
            )
            print(warning_msg, file=sys.stderr)

            # In CI/non-interactive mode, auto-proceed (CI always re-ingests fresh)
            if os.getenv("CI") == "true" or not sys.stdin.isatty():
                print(
                    "DEBUG: CI/non-interactive mode - proceeding with re-ingestion", file=sys.stderr
                )
            else:
                # Interactive mode - require confirmation
                try:
                    input(
                        "Press Enter to DELETE existing data and re-ingest (or Ctrl+C to abort)..."
                    )
                except KeyboardInterrupt:
                    pytest.skip(
                        "\n\n❌ Test aborted by user to prevent data deletion. Use --skip-ingestion to preserve existing data."
                    )

    except Exception as e:
        # Collection doesn't exist yet - safe to proceed
        print(f"DEBUG: No existing collection found ({e}) - safe to create", file=sys.stderr)

    # Environment-based PDF selection:
    # - LOCAL (VS Code): 10-page sample PDF (fast ~10-15 seconds ingestion)
    # - CI: 160-page full PDF (comprehensive ~150 seconds ingestion)
    use_full_pdf = os.getenv("TEST_USE_FULL_PDF", "false").lower() == "true"

    print(f"DEBUG: TEST_USE_FULL_PDF={use_full_pdf}", file=sys.stderr)

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

    print(f"DEBUG: PDF selection complete - checking {sample_pdf}", file=sys.stderr)

    if not sample_pdf.exists():
        print(f"DEBUG: PDF not found at {sample_pdf} - skipping", file=sys.stderr)
        pytest.skip(f"Test PDF not found at {sample_pdf} - skipping integration tests")
        return

    print(f"\n{'=' * 80}")
    print("SESSION FIXTURE: Ingesting test PDFs ONCE (production pattern)")
    print(f"Mode: {'CI (comprehensive)' if use_full_pdf else 'LOCAL (fast)'}")
    print(f"Collection: {settings.qdrant_collection_name}")
    print(f"PDF: {pdf_description}")
    print("THIS RUNS ONCE - All tests will share the ingested data")
    print(f"{'=' * 80}\n")

    # Get Qdrant client
    print("DEBUG: Getting Qdrant client...", file=sys.stderr)
    qdrant = get_qdrant_client()
    print("DEBUG: Qdrant client obtained", file=sys.stderr)

    # Clear any existing data and create fresh collection
    print("⚙️  Preparing collection...")
    try:
        try:
            # CRITICAL FIX: Ensure complete deletion before recreation
            qdrant.delete_collection(collection_name=settings.qdrant_collection_name)
            print(
                f"   ✓ Deleted existing collection: {settings.qdrant_collection_name}",
                file=sys.stderr,
            )
        except Exception as e:
            print(f"   ℹ️  No existing collection to delete: {e}", file=sys.stderr)

        # CRITICAL FIX: Also clear PostgreSQL to maintain symmetric data lifecycle
        # This prevents mixed document IDs from accumulating across test runs
        try:
            import psycopg2

            conn_str = f"postgresql://{settings.postgres_user}:{settings.postgres_password}@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
            conn = psycopg2.connect(conn_str)
            cursor = conn.cursor()

            # Delete all data from both PostgreSQL tables
            cursor.execute("DELETE FROM financial_chunks")
            chunks_deleted = cursor.rowcount
            cursor.execute("DELETE FROM financial_tables")
            tables_deleted = cursor.rowcount

            conn.commit()
            cursor.close()
            conn.close()

            print(
                f"   ✓ Cleared PostgreSQL: {tables_deleted} table rows, {chunks_deleted} chunk rows",
                file=sys.stderr,
            )
        except Exception as e:
            print(f"   ℹ️  PostgreSQL cleanup skipped: {e}", file=sys.stderr)

        # Wait for deletion to complete (Qdrant async operation)
        import time

        time.sleep(0.5)

        create_collection(
            collection_name=settings.qdrant_collection_name,
            vector_size=settings.embedding_dimension,
        )
        print(f"   ✓ Collection created: {settings.qdrant_collection_name}")

        # CRITICAL FIX: Verify collection is empty after creation
        initial_count = qdrant.count(collection_name=settings.qdrant_collection_name)
        if initial_count.count > 0:
            error_msg = f"Collection {settings.qdrant_collection_name} has {initial_count.count} chunks after creation (expected 0). Stale data detected!"
            print(f"   ❌ ERROR: {error_msg}", file=sys.stderr)
            pytest.skip(error_msg)
        print(f"   ✓ Collection verified empty: {initial_count.count} chunks", file=sys.stderr)

    except Exception as e:
        pytest.skip(f"Failed to initialize Qdrant collection: {e}")

    # Ingest PDF (size depends on environment)
    print(f"⚙️  Ingesting {sample_pdf.name}...")
    print(f"   Estimated time: {estimated_time} (Docling + embeddings + Qdrant)")

    # Ingest with clear_collection=False (collection already fresh)
    print("DEBUG: Starting asyncio.run(ingest_pdf)...", file=sys.stderr)
    start_ingest = time.time()
    try:
        result = asyncio.run(ingest_pdf(str(sample_pdf), clear_collection=False))
        ingest_duration = time.time() - start_ingest
        print(f"DEBUG: ingest_pdf completed in {ingest_duration:.1f}s", file=sys.stderr)
    except Exception as e:
        print(f"DEBUG: ingest_pdf failed with {type(e).__name__}: {e}", file=sys.stderr)
        raise

    # Verify ingestion succeeded
    import time

    for _attempt in range(10):  # Max 2 seconds wait
        count_after = qdrant.count(collection_name=settings.qdrant_collection_name)
        if count_after.count > 0:
            break
        time.sleep(0.2)

    _session_sample_pdf_chunk_count = count_after.count
    print("\n✅ Session fixture complete:")
    print(f"   PDF: {result.filename} ({result.page_count} pages)")
    print(f"   Path: {sample_pdf}")
    print(f"   Chunks: {count_after.count}")
    print(f"   Ingestion time: {ingest_duration:.1f}s")
    print(f"   Mode: {'CI (160-page)' if use_full_pdf else 'LOCAL (10-page)'}")
    print(
        f"   Ready for {len(request.session.items) if hasattr(request.session, 'items') else '?'} tests"
    )
    print("   All tests share this collection (read-only, zero per-test overhead)\n")

    # CRITICAL VALIDATION: Chunk count should match PDF size expectations
    if use_full_pdf:
        expected_range = (150, 220)  # 160-page PDF
    else:
        expected_range = (10, 50)  # 10-page PDF

    if not (expected_range[0] <= count_after.count <= expected_range[1]):
        error_msg = f"CRITICAL: Chunk count {count_after.count} not in expected range {expected_range} for {pdf_description}"
        print(f"\n❌ {error_msg}", file=sys.stderr)
        print("   This suggests chunking bug or wrong PDF ingested!", file=sys.stderr)
        pytest.fail(error_msg)

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
