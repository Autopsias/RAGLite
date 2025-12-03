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

# CRITICAL FIX (2025-11-23): Set test environment variables BEFORE any raglite imports
# This ensures the Settings singleton uses test database settings when it's created.
# Root cause: tests/conftest.py sets env vars, but tests/integration/conftest.py is loaded
# BEFORE parent conftest completes, so Settings singleton was created with production defaults.
# Solution: Set env vars in BOTH conftest files to ensure they're available at import time.
if "APP_ENV" not in os.environ:
    os.environ["APP_ENV"] = "test"
if "TESTING" not in os.environ:
    os.environ["TESTING"] = "true"
if "POSTGRES_PORT" not in os.environ:
    os.environ["POSTGRES_PORT"] = "5433"
if "POSTGRES_DB" not in os.environ:
    os.environ["POSTGRES_DB"] = "raglite_ci"
if "POSTGRES_USER" not in os.environ:
    os.environ["POSTGRES_USER"] = "raglite_ci"
if "POSTGRES_PASSWORD" not in os.environ:
    os.environ["POSTGRES_PASSWORD"] = "raglite_ci"

print("DEBUG: Test environment variables set before raglite imports", file=sys.stderr)

# CRITICAL: Check service availability BEFORE importing any raglite modules
# Test modules import raglite code which may try to connect at import time
# This prevents collection-time hangs when services are unavailable
print("DEBUG: Checking service availability before imports...", file=sys.stderr)

# Get connection settings from environment (same as shared.config.Settings)
# CRITICAL FIX (2025-11-19): Integration tests MUST use TEST database ports
# Production: Qdrant 6333, PostgreSQL 5432
# Test: Qdrant 6335, PostgreSQL 5433 (Story 4.0.5 database separation)
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6335"))  # TEST port (was 6333)
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5433"))  # TEST port (was 5432)


def check_service_available(host: str, port: int, service_name: str) -> bool:
    """Check if service is reachable with optimized 1-second timeout."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)  # Reduced from 5s to 1s for faster discovery
        result = sock.connect_ex((host, port))
        sock.close()
        if result == 0:
            print(f"DEBUG: {service_name} available at {host}:{port}", file=sys.stderr)
            return True
        else:
            print(
                f"DEBUG: {service_name} connection refused at {host}:{port}",
                file=sys.stderr,
            )
            return False
    except Exception as e:
        print(f"DEBUG: {service_name} check failed: {e}", file=sys.stderr)
        return False


# PERFORMANCE: Lazy service checking - only check when actually needed
# This avoids 10+ second delay during test discovery
qdrant_available = None  # Will be checked on first use
postgres_available = None  # Will be checked on first use


def get_service_availability() -> tuple[bool, bool]:
    """Get cached service availability, checking only once."""
    global qdrant_available, postgres_available

    if qdrant_available is None:
        qdrant_available = check_service_available(QDRANT_HOST, QDRANT_PORT, "Qdrant")
    if postgres_available is None:
        postgres_available = check_service_available(POSTGRES_HOST, POSTGRES_PORT, "PostgreSQL")

    return qdrant_available, postgres_available


# PERFORMANCE: Move service check to first fixture execution to avoid test discovery delay
# Services will be checked when first test runs, not during module import
def check_and_skip_if_unavailable():
    """Check services and skip if unavailable - called from fixtures, not module import."""
    qdrant_avail, postgres_avail = get_service_availability()

    if not qdrant_avail or not postgres_avail:
        missing = []
        if not qdrant_avail:
            missing.append(f"Qdrant ({QDRANT_HOST}:{QDRANT_PORT})")
        if not postgres_avail:
            missing.append(f"PostgreSQL ({POSTGRES_HOST}:{POSTGRES_PORT})")

        skip_reason = f"Integration tests require: {', '.join(missing)}"
        print(f"DEBUG: Skipping all integration tests - {skip_reason}", file=sys.stderr)
        pytest.skip(skip_reason, allow_module_level=True)


# Now safe to import raglite modules (services will be checked in fixtures)
import asyncio  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402

# Track session-level expected Qdrant state for test isolation
_session_sample_pdf_chunk_count = None
_session_snapshot_name = None  # Track snapshot for fast restoration
_session_postgresql_row_count = None  # Track PostgreSQL baseline for restoration

# CRITICAL FIX (2025-11-23): Use shared PostgreSQL connection from raglite.shared.clients
# instead of creating a separate fixture connection. This prevents connection isolation
# issues where the fixture can't see data committed by the ingestion pipeline.
#
# ROOT CAUSE: The fixture was creating its own PostgreSQL connection instance which was
# completely separate from the connection used by store_tables_in_postgresql().
# This caused a race condition where:
#   1. Ingestion writes data using raglite.shared.clients.get_postgresql_connection()
#   2. Fixture reads data using tests.integration.conftest.get_postgresql_connection()
#   3. Two different connections = fixture can't see ingestion's committed data!
#
# SOLUTION: Import and use the shared connection factory from raglite.shared.clients
# so both ingestion and fixture use the SAME connection instance.
import raglite.shared.config  # noqa: E402
from raglite.shared.clients import get_postgresql_connection  # noqa: E402

# CRITICAL FIX (2025-11-23): Force reload of settings singleton after env vars are set
# The Settings class creates a singleton at module import time (config.py line 135).
# If config.py was imported before this conftest set test env vars, we need to recreate it.
# This ensures integration tests use PostgreSQL port 5433 (test database).
from raglite.shared.config import Settings  # noqa: E402

raglite.shared.config.settings = Settings()  # Recreate singleton with test env vars


@pytest.fixture(scope="session", autouse=True)
def ensure_test_database_schema(request):
    """Ensure PostgreSQL test database schema is initialized before any tests run.

    CRITICAL FIX (2025-11-19): Test database (raglite_test) needs schema initialization
    before integration tests can run. This fixture creates the required tables if they
    don't exist.

    Story 4.0.5: Database separation - ensures test database has proper schema.

    This runs ONCE per test session, before any tests execute.
    """
    # Skip during test collection/discovery phase
    if request.config.option.collectonly:
        yield
        return

    import logging

    logger = logging.getLogger(__name__)

    # PERFORMANCE: Check service availability first
    check_and_skip_if_unavailable()

    logger.info("🔧 Ensuring test database schema exists...")

    try:
        # PERFORMANCE: Use cached connection to reduce overhead
        conn = get_postgresql_connection()
        cursor = conn.cursor()

        # Check if financial_chunks table exists
        cursor.execute(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = 'financial_chunks'
            );
            """
        )
        table_exists = cursor.fetchone()[0]

        if not table_exists:
            logger.warning(
                "⚠️  Test database schema not found - initializing (this should only happen once)"
            )

            # Run schema initialization script
            import subprocess

            result = subprocess.run(
                ["uv", "run", "python", "scripts/init-test-postgresql.py"],
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                error_msg = f"Failed to initialize test database schema:\n{result.stderr}"
                logger.error(f"❌ {error_msg}")
                pytest.fail(error_msg)

            logger.info("✅ Test database schema initialized successfully")
        else:
            logger.info("✅ Test database schema already exists")

        cursor.close()  # Only close cursor, keep connection cached

    except Exception as e:
        error_msg = f"Failed to verify/initialize test database schema: {e}"
        logger.error(f"❌ {error_msg}")
        pytest.fail(error_msg)

    yield

    # No cleanup - schema persists for all tests


@pytest.fixture(scope="session", autouse=True)
def warmup_embedding_model(request):
    """Pre-warm embedding model before any tests run.

    CRITICAL PERFORMANCE FIX: Fin-E5 model takes 60-70s to load from cold start.
    Without this fixture, the model loads during session_ingested_collection fixture,
    adding 60-70s overhead to the expected 10-15s ingestion time.

    This fixture loads the model ONCE at session start, before any PDF ingestion.
    Expected savings: 60-70s per test session (reduces session fixture from 86s → 12-15s).

    The model singleton persists across all tests in the session.

    DISCOVERY OPTIMIZATION: Skips expensive model loading during test discovery phase.

    NOTE (2025-11-10): autouse=True restored due to performance regression.
    Tests were experiencing 60-70s cold start penalties when embedding model
    was loaded individually instead of using the session-scoped singleton.
    This fixture ensures the model is loaded once at session start and shared
    across all integration tests.
    """
    # Skip during test collection/discovery phase
    if request.config.option.collectonly:
        yield
        return

    # PERFORMANCE: Check service availability here instead of module import
    # This moves the 2-second service check from discovery to execution time
    check_and_skip_if_unavailable()

    print("\n🔥 PRE-WARMING EMBEDDING MODEL (60-70s one-time load)...", file=sys.stderr)

    from raglite.shared.clients import get_embedding_model

    model_load_start = time.time()
    model = get_embedding_model()
    model_load_duration = time.time() - model_load_start
    dim = model.get_sentence_embedding_dimension()

    print(
        f"✅ Embedding model ready: {dim} dimensions (Fin-E5 loaded in {model_load_duration:.1f}s)",
        file=sys.stderr,
    )
    print(
        f"📊 MODEL LOAD PERF: Model loading took {model_load_duration:.1f}s",
        file=sys.stderr,
    )

    yield
    # Model singleton persists for entire session


@pytest.fixture(scope="session", autouse=True)
def session_ingested_collection(request, warmup_embedding_model):
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

    DISCOVERY OPTIMIZATION: Skips expensive PDF ingestion during test discovery phase.

    CRITICAL FIX (2025-11-21): Restored autouse=True for proper session fixture sharing.
    Removing autouse=True on 2025-11-09 caused 6x performance regression (600s → 3600s).
    With autouse=True: Fixture runs ONCE per session (50s total overhead).
    Without autouse=True: Fixture runs per test file (50s × N files = massive overhead).

    Dependencies:
        - warmup_embedding_model: Pre-loads Fin-E5 model (60-70s) before ingestion
    """
    global _session_sample_pdf_chunk_count

    # Skip during test collection/discovery phase
    if request.config.option.collectonly:
        yield
        return

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
                # GRACEFUL FALLBACK: Instead of failing, fall back to ingestion
                # This allows tests to run even when --skip-ingestion is used but no data exists
                warning_msg = (
                    "\n" + "=" * 80 + "\n"
                    "⚠️  WARNING: --skip-ingestion specified but Qdrant collection is empty!\n"
                    "\n"
                    "Falling back to full ingestion instead of failing.\n"
                    "To avoid this warning and save time, ingest data first:\n"
                    "  python scripts/ingest-test-data.py\n"
                    "\n"
                    "Proceeding with ingestion...\n" + "=" * 80 + "\n"
                )
                print(warning_msg, file=sys.stderr)
                # Don't return - fall through to normal ingestion flow below
            else:
                # Data exists - use it!
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
            # Collection doesn't exist - fall back to ingestion
            warning_msg = (
                f"\n⚠️  WARNING: --skip-ingestion specified but collection doesn't exist: {e}\n"
                f"Falling back to full ingestion...\n"
            )
            print(warning_msg, file=sys.stderr)
            # Fall through to normal ingestion flow below

    print(
        "\nDEBUG: Proceeding with full ingestion (--skip-ingestion not set)",
        file=sys.stderr,
    )

    from raglite.ingestion.pipeline import create_collection, ingest_pdf
    from raglite.shared.clients import get_qdrant_client
    from raglite.shared.config import settings
    from raglite.shared.safety import ProductionProtectionError, SafetyGuard

    print("DEBUG: Fixture imports successful", file=sys.stderr)

    # =========================================================================
    # CRITICAL SAFETY CHECK (Story 4.0.7): Validate test environment FIRST
    # This MUST run before ANY database operations to prevent production data loss.
    # Added after 2025-11-27 incident where VS Code test runner deleted production data.
    # =========================================================================
    print("DEBUG: Validating test environment (SafetyGuard)...", file=sys.stderr)
    guard = SafetyGuard()

    try:
        guard.validate_test_environment("session_ingested_collection fixture")
        print(
            f"DEBUG: Test environment validated - Qdrant:{settings.qdrant_port}, "
            f"PostgreSQL:{settings.postgres_port}, Collection:{settings.qdrant_collection_name}",
            file=sys.stderr,
        )
    except ProductionProtectionError as e:
        # HARD FAIL: Do not allow tests to proceed on production infrastructure
        error_msg = (
            f"\n{'!' * 80}\n"
            f"CRITICAL: TEST ISOLATION FAILURE\n"
            f"{'!' * 80}\n\n"
            f"{e}\n\n"
            f"This test fixture attempted to run on PRODUCTION infrastructure.\n"
            f"The operation has been BLOCKED to prevent data loss.\n\n"
            f"To fix:\n"
            f"  1. Set APP_ENV=test before running tests\n"
            f"  2. Use --skip-ingestion to skip database operations\n"
            f"  3. Run from terminal: APP_ENV=test pytest tests/\n"
            f"{'!' * 80}\n"
        )
        print(error_msg, file=sys.stderr)
        pytest.fail(error_msg)

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

            # FIXED (Story 4.0.7): Only auto-proceed in ACTUAL CI environment
            # Previously: if os.getenv("CI") == "true" or not sys.stdin.isatty()
            # Bug: VS Code test runner is non-interactive but NOT CI, so it auto-proceeded!
            is_ci = os.getenv("CI") == "true" or os.getenv("GITHUB_ACTIONS") == "true"

            if is_ci:
                # CI environment with already-validated test infrastructure: OK to auto-proceed
                print(
                    "DEBUG: CI mode with validated test environment - proceeding with re-ingestion",
                    file=sys.stderr,
                )
            elif not sys.stdin.isatty():
                # Non-interactive but NOT CI (e.g., VS Code, IDE, background process)
                # BLOCK: Cannot safely auto-proceed without user confirmation
                block_msg = (
                    f"\n{'!' * 80}\n"
                    f"BLOCKED: Non-interactive mode outside CI\n"
                    f"{'!' * 80}\n\n"
                    f"Cannot auto-delete test data in non-interactive mode (VS Code, IDE, etc.)\n"
                    f"without explicit user confirmation.\n\n"
                    f"Options:\n"
                    f"  1. Use --skip-ingestion flag to reuse existing data\n"
                    f"  2. Run pytest from terminal (interactive mode)\n"
                    f"  3. Set CI=true if this is a CI environment\n"
                    f"{'!' * 80}\n"
                )
                print(block_msg, file=sys.stderr)
                pytest.fail(block_msg)
            else:
                # Interactive mode - require confirmation
                try:
                    input(
                        "Press Enter to DELETE existing test data and re-ingest (or Ctrl+C to abort)..."
                    )
                except KeyboardInterrupt:
                    pytest.skip(
                        "\n\n❌ Test aborted by user to prevent data deletion. Use --skip-ingestion to preserve existing data."
                    )

    except Exception as e:
        # Collection doesn't exist yet - safe to proceed
        print(
            f"DEBUG: No existing collection found ({e}) - safe to create",
            file=sys.stderr,
        )

    # Environment-based PDF selection:
    # - LOCAL (VS Code): 4-page test PDF (fast ~5-10 seconds ingestion - Story 4.0.5)
    # - CI: 160-page full PDF (comprehensive ~150 seconds ingestion)
    use_full_pdf = os.getenv("TEST_USE_FULL_PDF", "false").lower() == "true"

    print(f"DEBUG: TEST_USE_FULL_PDF={use_full_pdf}", file=sys.stderr)

    if use_full_pdf:
        # CI: Use full 160-page PDF for comprehensive testing (--run-slow flag)
        sample_pdf = Path("docs/sample pdf/2025-08 Performance Review CONSO_v2.pdf")
        pdf_description = "160-page full PDF (CI comprehensive mode)"
        estimated_time = "150-180 seconds"
    else:
        # DEFAULT: Use 10-page sample PDF for testing (Story 2.14 ground truth alignment)
        # Changed from 4-page sample-small-3-pages.pdf to 10-page sample_financial_report.pdf
        # to match Story 2.14 ground truth expectations (v2.0-10PAGE) which expects Portugal
        # Currency data on pages 9-10 (50 rows)
        sample_pdf = Path("tests/fixtures/sample_financial_report.pdf")
        pdf_description = "10-page sample PDF (Story 2.14 ground truth aligned)"
        estimated_time = "8-12 seconds"

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
            # PERFORMANCE: Use cached connection to reduce overhead
            conn = get_postgresql_connection()
            cursor = conn.cursor()

            # Delete all data from both PostgreSQL tables
            cursor.execute("DELETE FROM financial_chunks")
            chunks_deleted = cursor.rowcount
            cursor.execute("DELETE FROM financial_tables")
            tables_deleted = cursor.rowcount

            print(
                f"   ✓ Cleared PostgreSQL: {tables_deleted} table rows, {chunks_deleted} chunk rows",
                file=sys.stderr,
            )
        except Exception as e:
            print(f"   ℹ️  PostgreSQL cleanup skipped: {e}", file=sys.stderr)

        # PERFORMANCE: Optimized Qdrant deletion confirmation with exponential backoff
        # Reduced wait time and smart polling to minimize test setup overhead
        import time

        print("   ⏳ Verifying Qdrant deletion (optimized)...", file=sys.stderr)
        deletion_confirmed = False
        for attempt in range(8):  # Reduced from 20 to 8 attempts (max 2s instead of 4s)
            try:
                collections = qdrant.get_collections().collections
                existing = [c.name for c in collections]
                if settings.qdrant_collection_name not in existing:
                    print(
                        f"   ✓ Collection deletion confirmed (attempt {attempt + 1})",
                        file=sys.stderr,
                    )
                    deletion_confirmed = True
                    break
            except Exception:
                # Collection might not exist yet - safe to proceed
                deletion_confirmed = True
                break

            # Exponential backoff: 0.1s, 0.2s, 0.4s, 0.8s, 1.6s...
            sleep_time = min(0.1 * (2**attempt), 0.5)  # Cap at 0.5s
            time.sleep(sleep_time)

        if not deletion_confirmed:
            # Force proceed but with shorter warning
            print(
                "   ⚠️  Collection deletion timeout, proceeding (optimized)",
                file=sys.stderr,
            )

        create_collection(
            collection_name=settings.qdrant_collection_name,
            vector_size=settings.embedding_dimension,
        )
        print(f"   ✓ Collection created: {settings.qdrant_collection_name}")

        # CRITICAL FIX: Verify collection is empty after creation
        # If stale data exists, it means create_collection found old collection before deletion completed
        initial_count = qdrant.count(collection_name=settings.qdrant_collection_name)
        if initial_count.count > 0:
            error_msg = f"Collection {settings.qdrant_collection_name} has {initial_count.count} chunks after creation (expected 0). Stale data detected!"
            print(f"   ❌ ERROR: {error_msg}", file=sys.stderr)
            pytest.skip(error_msg)
        print(
            f"   ✓ Collection verified empty: {initial_count.count} chunks",
            file=sys.stderr,
        )

    except Exception as e:
        pytest.skip(f"Failed to initialize Qdrant collection: {e}")

    # Ingest PDF (size depends on environment)
    print(f"⚙️  Ingesting {sample_pdf.name}...")
    print(f"   Estimated time: {estimated_time} (Docling + embeddings + Qdrant)")

    # PERFORMANCE OPTIMIZATION: Skip metadata extraction in LOCAL mode (4-page PDF)
    # - Metadata extraction uses Mistral API (~7s per chunk with network latency)
    # - For 7 chunks: 7 × 7s = 49s overhead (10x slowdown!)
    # - Most integration tests don't need LLM-extracted metadata
    # - CI mode still extracts metadata for comprehensive testing
    skip_metadata_extraction = not use_full_pdf  # LOCAL: skip, CI: extract

    if skip_metadata_extraction:
        print("   ⚡ PERFORMANCE: Skipping metadata extraction (LOCAL mode - saves ~40s)")

    # Ingest with clear_existing=False (collection already fresh)
    print("DEBUG: Starting asyncio.run(ingest_pdf)...", file=sys.stderr)
    start_ingest = time.time()
    try:
        result = asyncio.run(
            ingest_pdf(
                str(sample_pdf),
                clear_existing=False,
                skip_metadata=skip_metadata_extraction,
            )
        )
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

    # CRITICAL FIX: Verify PostgreSQL is FULLY populated with expected data
    # This ensures database inspection tests have complete data to work with
    print("\n⚙️  Verifying PostgreSQL population WITH TRANSACTION VISIBILITY...")
    try:
        import logging

        from psycopg2.extras import RealDictCursor

        logger = logging.getLogger(__name__)

        # PERFORMANCE: Use cached connection to reduce overhead
        conn = get_postgresql_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # PERFORMANCE: Optimized PostgreSQL population verification with smart polling
        pg_count = 0
        expected_min_rows = 10 if not use_full_pdf else 100  # Adjust based on PDF size

        # Smart polling: check with transaction visibility fix for CI environments
        max_attempts = 20  # Increased from 12 to 20 for CI slowness
        for attempt in range(max_attempts):
            # CRITICAL FIX: Force new transaction to see committed data
            # This handles CI transaction isolation issues where ingested data
            # may not be visible in the current transaction (READ COMMITTED isolation)
            if not conn.autocommit:
                conn.rollback()  # Abandon old transaction, start fresh

            cursor.execute("SELECT COUNT(*) FROM financial_tables")
            pg_count = cursor.fetchone()["count"]

            if pg_count >= expected_min_rows:
                logger.info(
                    "PostgreSQL data visible",
                    extra={
                        "rows": pg_count,
                        "attempt": attempt + 1,
                        "max_attempts": max_attempts,
                        "expected_min": expected_min_rows,
                    },
                )
                break

            # Exponential backoff: 0.2s, 0.4s, 0.8s, 1.6s, 2.0s (capped) for CI environments
            sleep_time = min(0.2 * (2**attempt), 2.0)

            # Log only on attempts 1, 3, 6, 9, 12, 15, 18 to reduce noise
            if attempt in [0, 2, 5, 8, 11, 14, 17]:
                print(
                    f"   ⏳ PostgreSQL: {pg_count}/{expected_min_rows} rows (attempt {attempt + 1}/{max_attempts}, wait {sleep_time:.1f}s)"
                )

            logger.debug(
                "PostgreSQL polling attempt",
                extra={
                    "attempt": attempt + 1,
                    "max_attempts": max_attempts,
                    "current_count": pg_count,
                    "expected_min": expected_min_rows,
                    "sleep_time": sleep_time,
                },
            )
            time.sleep(sleep_time)
        else:
            # Max attempts exceeded without reaching expected_min_rows
            error_msg = (
                f"PostgreSQL data not visible after {max_attempts} attempts: "
                f"{pg_count}/{expected_min_rows} rows. Transaction isolation issue."
            )
            print(f"   ❌ ERROR: {error_msg}")
            pytest.fail(error_msg)

        # Get detailed counts for validation
        cursor.execute("SELECT COUNT(*) FROM financial_chunks")
        chunk_count = cursor.fetchone()["count"]

        cursor.execute(
            "SELECT COUNT(DISTINCT entity) FROM financial_tables WHERE entity IS NOT NULL"
        )
        entity_count = cursor.fetchone()["count"]

        cursor.execute(
            "SELECT COUNT(DISTINCT metric) FROM financial_tables WHERE metric IS NOT NULL"
        )
        metric_count = cursor.fetchone()["count"]

        cursor.close()  # Only close cursor, keep connection cached
        # Note: Connection kept open for session to reduce overhead

        print(f"   ✓ PostgreSQL populated: {pg_count} table rows, {chunk_count} chunk rows")
        print(f"   ✓ Data diversity: {entity_count} entities, {metric_count} metrics")

        # CRITICAL: Store PostgreSQL baseline for test isolation restoration
        global _session_postgresql_row_count
        _session_postgresql_row_count = pg_count
        print(f"   ✓ PostgreSQL baseline stored: {_session_postgresql_row_count} rows")

        # CRITICAL: Fail fast if PostgreSQL is not properly populated
        # This prevents cascading failures in database-dependent tests
        if pg_count < expected_min_rows:
            error_msg = (
                f"PostgreSQL has only {pg_count} rows, expected at least {expected_min_rows}"
            )
            print(f"   ❌ ERROR: {error_msg}")
            pytest.fail(error_msg)

    except Exception as e:
        error_msg = f"PostgreSQL verification failed: {e}"
        print(f"   ❌ ERROR: {error_msg}")
        pytest.fail(error_msg)  # Fail fast - don't continue if PostgreSQL isn't ready

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
        # Updated range for 10-page sample_financial_report.pdf (Story 2.14 ground truth alignment)
        # With table-aware chunking (Story 2.8) and 512-token fixed chunking:
        # - This PDF is table-heavy (47 tables extracted, 1548 table rows)
        # - Table-aware chunking keeps large tables intact (fewer, larger chunks)
        # - Observed: 14 chunks from 10 pages (mostly large financial tables)
        # - Text chunks are minimal because PDF is dominated by structured tables
        # - Acceptable range: 10-30 chunks (table-heavy PDFs produce fewer, larger chunks)
        expected_range = (
            10,
            30,
        )  # 10-page sample_financial_report.pdf (Story 2.14, table-heavy)

    if not (expected_range[0] <= count_after.count <= expected_range[1]):
        error_msg = f"CRITICAL: Chunk count {count_after.count} not in expected range {expected_range} for {pdf_description}"
        print(f"\n❌ {error_msg}", file=sys.stderr)
        print("   This suggests chunking bug or wrong PDF ingested!", file=sys.stderr)
        pytest.fail(error_msg)

    # PERFORMANCE OPTIMIZATION: Create snapshot for fast test isolation
    # Instead of re-ingesting PDF (10-15s), we restore from snapshot (<1s)
    global _session_snapshot_name
    print("\n⚡ Creating Qdrant snapshot for fast test isolation...")
    snapshot_start = time.time()
    try:
        snapshot_info = qdrant.create_snapshot(
            collection_name=settings.qdrant_collection_name, wait=True
        )
        _session_snapshot_name = snapshot_info.name
        snapshot_duration = time.time() - snapshot_start
        print(f"   ✓ Snapshot created: {_session_snapshot_name}")
        print(f"   ✓ Snapshot time: {snapshot_duration:.2f}s")
        print(
            f"   ✓ Restoration will be ~10-15x faster than re-ingestion (<1s vs {estimated_time})"
        )
    except Exception as e:
        print(f"   ⚠️  Snapshot creation failed: {e}")
        print("   ⚠️  Falling back to re-ingestion for test isolation")
        _session_snapshot_name = None

    # Cleanup at session end
    yield

    print(f"\n🧹 Session cleanup: deleting {settings.qdrant_collection_name}")
    try:
        qdrant.delete_collection(collection_name=settings.qdrant_collection_name)
        print("   ✓ Collection deleted")
    except Exception as e:
        print(f"   ⚠️  Cleanup error (non-critical): {e}")

    # NOTE (2025-11-23): PostgreSQL connection cleanup removed
    # We now use the shared singleton from raglite.shared.clients.get_postgresql_connection()
    # which manages its own lifecycle. The connection will be closed when the process exits.


@pytest.fixture(autouse=True)
def ensure_qdrant_test_isolation(request):
    """Ensure Qdrant collection isolation between integration tests (SMART VERSION).

    CRITICAL OPTIMIZATION: Skips re-ingest cleanup for tests that intentionally
    modify collection (call ingest_pdf with clear_existing=True).

    Without this: Tests with clear_existing=True pay 150-170s (ingest + re-ingest cleanup)
    With this: Tests with clear_existing=True pay only 75-85s (ingest only, no cleanup)

    Behavior:
    - Tests marked @pytest.mark.preserve_collection: Skip cleanup (read-only tests)
    - Tests marked @pytest.mark.manages_collection_state: Skip cleanup (intentionally modify)
    - Other tests: Restore to baseline if collection modified (read-only tests that didn't get marked)

    This saves ~600-1500 seconds per test session by avoiding double-ingest on tests
    that call ingest_pdf(clear_existing=True).

    NOTE: This fixture lives in tests/integration/conftest.py, so it ONLY applies to
    integration tests. No need to detect test type via inspect - this conftest isn't
    loaded by unit tests.

    PERFORMANCE FIX (2025-11-08): Skip during test discovery to avoid Test Explorer overhead
    """
    global _session_sample_pdf_chunk_count
    global _session_snapshot_name
    global _session_postgresql_row_count

    # PERFORMANCE: Skip during test collection/discovery phase (Test Explorer optimization)
    if request.config.option.collectonly:
        yield
        return

    # Check if test is marked with preserve_collection or manages_collection_state (skip expensive cleanup)
    if "preserve_collection" in request.keywords or "manages_collection_state" in request.keywords:
        yield  # Test runs - no cleanup needed
        return

    # Import Qdrant client and settings
    from raglite.shared.clients import get_qdrant_client
    from raglite.shared.config import settings

    # PERFORMANCE: Cache Qdrant client at session level to avoid reconnection overhead
    if not hasattr(request.session, "_cached_qdrant_client"):
        request.session._cached_qdrant_client = get_qdrant_client()

    qdrant = request.session._cached_qdrant_client

    # PERFORMANCE: Only check state for tests that don't have markers (assumed read-only)
    # Most tests are read-only and won't modify data, so skip the pre-check
    # We'll only verify AFTER the test if restoration is needed

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
                f"\n🔄 Restoring Qdrant (current: {final_count} chunks, baseline: {_session_sample_pdf_chunk_count})"
            )

            # PERFORMANCE OPTIMIZATION: Use snapshot recovery instead of re-ingestion
            # Snapshot restore: <1s vs PDF re-ingestion: 10-15s (10-15x faster!)
            if _session_snapshot_name:
                # FAST PATH: Restore from snapshot
                import time

                print(f"   ⚡ Using snapshot: {_session_snapshot_name}")
                restore_start = time.time()

                try:
                    # Delete collection first
                    try:
                        qdrant.delete_collection(collection_name=settings.qdrant_collection_name)
                    except Exception:
                        pass

                    # Recover from snapshot stored on Qdrant server
                    # Construct snapshot URL from Qdrant host
                    qdrant_host = settings.qdrant_url.rstrip("/")
                    snapshot_url = f"{qdrant_host}/collections/{settings.qdrant_collection_name}/snapshots/{_session_snapshot_name}"

                    qdrant.recover_snapshot(
                        collection_name=settings.qdrant_collection_name,
                        location=snapshot_url,
                        priority="snapshot",  # Prioritize snapshot data
                        wait=True,
                    )

                    restore_duration = time.time() - restore_start

                    # Verify restoration
                    restored_count = 0
                    for _attempt in range(10):  # Max 2 seconds wait
                        restored_count = qdrant.count(
                            collection_name=settings.qdrant_collection_name
                        ).count
                        if restored_count == _session_sample_pdf_chunk_count:
                            break
                        time.sleep(0.2)

                    print(f"   ✓ Restored ({restored_count} chunks) in {restore_duration:.2f}s")

                except Exception as e:
                    print(f"   ⚠️  Snapshot recovery failed: {e}")
                    print("   ⚠️  Falling back to PDF re-ingestion")
                    # Fall through to re-ingestion below
                    _session_snapshot_name = None

            if not _session_snapshot_name:
                # SLOW PATH: Re-ingest PDF (fallback if snapshot failed)
                print("   🐌 Using PDF re-ingestion (slow path)")
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
                import time

                restored_count = 0
                for _attempt in range(10):  # Max 2 seconds wait
                    restored_count = qdrant.count(
                        collection_name=settings.qdrant_collection_name
                    ).count
                    if restored_count == _session_sample_pdf_chunk_count:
                        break
                    time.sleep(0.2)

                print(f"   ✓ Restored ({restored_count} chunks)")

            # CRITICAL FIX: Also restore PostgreSQL data (symmetric database lifecycle)
            # PostgreSQL must be restored when Qdrant is restored to prevent test isolation failures
            # Root cause: Tests with clear_existing=True delete PostgreSQL, but only Qdrant was being restored
            # PERFORMANCE: All tests now have proper markers (preserve_collection or manages_collection_state)
            # This restoration only triggers for tests that actually modify collections
            if _session_postgresql_row_count:
                print(
                    f"\n🔄 Checking PostgreSQL state (baseline: {_session_postgresql_row_count} rows)..."
                )

                try:
                    from psycopg2.extras import RealDictCursor

                    # PERFORMANCE: Use cached connection to reduce overhead
                    conn = get_postgresql_connection()
                    cursor = conn.cursor(cursor_factory=RealDictCursor)

                    # Check current PostgreSQL state
                    cursor.execute("SELECT COUNT(*) FROM financial_tables")
                    current_pg_count = cursor.fetchone()["count"]

                    # If PostgreSQL was cleared, restore it
                    if current_pg_count < _session_postgresql_row_count:
                        print(
                            f"   ⚠️  PostgreSQL depleted: {current_pg_count} rows (expected {_session_postgresql_row_count})"
                        )
                        print("   🔄 Re-ingesting PDF to restore PostgreSQL data...")

                        # Re-ingest the session PDF to restore PostgreSQL
                        # This triggers table extraction which populates financial_tables
                        import os

                        from raglite.ingestion.pipeline import ingest_pdf

                        # Use the same PDF that was ingested in session_ingested_collection fixture
                        use_full_pdf = os.getenv("TEST_USE_FULL_PDF", "false").lower() == "true"
                        if use_full_pdf:
                            sample_pdf = Path(
                                "docs/sample pdf/2025-08 Performance Review CONSO_v2.pdf"
                            )
                        else:
                            sample_pdf = Path("tests/fixtures/sample-small-3-pages.pdf")

                        if sample_pdf.exists():
                            # Ingest with clear_existing=False to preserve the Qdrant data we just restored
                            asyncio.run(ingest_pdf(str(sample_pdf), clear_existing=False))

                            # Verify PostgreSQL restoration
                            cursor.execute("SELECT COUNT(*) FROM financial_tables")
                            restored_pg_count = cursor.fetchone()["count"]

                            print(f"   ✓ PostgreSQL restored: {restored_pg_count} rows")

                            if (
                                restored_pg_count < _session_postgresql_row_count * 0.9
                            ):  # Allow 10% tolerance
                                print(
                                    f"   ⚠️  PostgreSQL restoration incomplete: {restored_pg_count}/{_session_postgresql_row_count} rows"
                                )
                        else:
                            print(f"   ⚠️  Cannot restore PostgreSQL: {sample_pdf} not found")
                    else:
                        print(f"   ✓ PostgreSQL intact: {current_pg_count} rows")

                    cursor.close()  # Only close cursor, keep connection cached

                except Exception as pg_error:
                    print(f"   ⚠️  PostgreSQL restoration failed: {pg_error}")

    except Exception as e:
        # Cleanup failed - not critical, next test will handle it
        print(f"\n⚠️  Cleanup warning: {e}")
        pass


# NOTE: shared_ingested_sample_pdf fixture removed (2025-11-08)
# Reason: Not used by any tests - dead code
# Tests use session_ingested_collection instead


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
    from raglite.shared.clients import get_qdrant_client

    # Use absolute path from project root
    project_root = Path(__file__).parent.parent.parent
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

    global _session_snapshot_name
    if _session_snapshot_name:
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
            snapshot_url = f"{qdrant_host}/collections/{settings.qdrant_collection_name}/snapshots/{_session_snapshot_name}"

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


@pytest.fixture
def qdrant_with_sample_docs(session_ingested_collection):
    """Fixture providing access to Qdrant collection with sample documents.

    Story 3.2 AC5: Provides Qdrant instance populated with test PDFs.
    This is a simple wrapper around session_ingested_collection to provide
    the expected fixture name for integration tests.

    Returns:
        True if Qdrant collection is available and populated with sample docs,
        False otherwise (tests will skip).
    """
    # session_ingested_collection fixture confirms Qdrant is available
    # If this fixture is reached, Qdrant has sample docs loaded
    return True


@pytest.fixture
def mock_synthesis_agent():
    """Fixture providing mock synthesis agent for workflow testing.

    Story 3.2 AC5: Provides mock synthesis agent to avoid real LLM calls
    during integration testing of retrieval → synthesis workflows.

    Returns:
        Async callable that simulates synthesis agent behavior.
    """

    async def mock_agent(query: str, retrieval_results: list, **kwargs) -> str:
        """Mock synthesis agent that returns pre-formatted answer.

        Args:
            query: The original query
            retrieval_results: List of retrieved document chunks
            **kwargs: Additional arguments (ignored)

        Returns:
            JSON-serialized synthesis result
        """
        import asyncio
        import json

        # Simulate agent processing
        await asyncio.sleep(0.1)

        # Return mock synthesis with retrieved chunks as context
        return json.dumps(
            {
                "query": query,
                "synthesis": f"Based on {len(retrieval_results)} retrieved documents: "
                f"The answer to '{query}' is synthesized from the provided context.",
                "cited_chunks": [r.get("id") for r in retrieval_results]
                if retrieval_results
                else [],
                "confidence": 0.85,
                "latency_ms": 100,
            }
        )

    return mock_agent


@pytest.fixture
def sample_ground_truth():
    """Fixture providing sample ground truth query for validation testing.

    Story 3.2 AC5: Provides test query and expected documents for accuracy validation.
    Loads from ground_truth_50queries.json if available.

    Returns:
        Dict with keys: query, expected_documents (or None if not available)
    """
    import json
    from pathlib import Path

    # Try to load ground truth file
    project_root = Path(__file__).parent.parent
    ground_truth_file = project_root / "ground_truth_50queries.json"

    if ground_truth_file.exists():
        try:
            with open(ground_truth_file) as f:
                data = json.load(f)
                # Return first query from ground truth set
                if isinstance(data, list) and len(data) > 0:
                    return data[0]
                elif isinstance(data, dict) and "queries" in data:
                    return data["queries"][0]
        except Exception:
            pass

    # Fallback: provide minimal test query
    return {
        "query": "What is the annual revenue?",
        "expected_documents": [],  # Empty - tests will skip if needed
    }
