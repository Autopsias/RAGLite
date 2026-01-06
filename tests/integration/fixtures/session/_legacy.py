"""Session-scoped fixtures: database schema, embedding warmup, and PDF ingestion (Django/FastAPI pattern)."""

import asyncio
import os
import sys
import time
from pathlib import Path

import pytest

# Import session state globals
from tests.integration.fixtures import session_state
from tests.integration.fixtures.service_checking import check_and_skip_if_unavailable

# Import test detection functions
from .test_detection import _has_integration_tests, _is_postgresql_only_tests

# Lazy imports (after service check)
# from raglite.shared.config import settings
# from raglite.shared.safety import SafetyGuard, ProductionProtectionError
# from raglite.ingestion.pipeline import create_collection, ingest_pdf


@pytest.fixture(scope="session", autouse=True)
def ensure_test_database_schema(request):
    """Ensure PostgreSQL schema exists before tests (Story 4.0.5)."""
    if request.config.option.collectonly:
        yield
        return

    # PERFORMANCE FIX: Skip for unit-only test runs
    if not _has_integration_tests(request):
        yield
        return

    import logging

    logger = logging.getLogger(__name__)
    check_and_skip_if_unavailable()
    logger.info("🔧 Ensuring test database schema exists...")

    try:
        from raglite.shared.clients import get_postgresql_connection

        conn = get_postgresql_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'financial_chunks');"
        )
        table_exists = cursor.fetchone()[0]

        if not table_exists:
            logger.warning("⚠️  Test database schema not found - initializing")
            import subprocess

            result = subprocess.run(
                ["uv", "run", "python", "scripts/init-test-postgresql.py"],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                pytest.fail(f"Failed to initialize test database schema:\n{result.stderr}")
            logger.info("✅ Test database schema initialized")
        else:
            logger.info("✅ Test database schema already exists")
        cursor.close()
    except Exception as e:
        pytest.fail(f"Failed to verify/initialize test database schema: {e}")
    yield


@pytest.fixture(scope="session", autouse=True)
def warmup_embedding_model(request):
    """Pre-warm Fin-E5 model (60-70s) before PDF ingestion. Skipped if --skip-ingestion."""
    if request.config.option.collectonly:
        yield
        return

    # PERFORMANCE FIX (2025-12-18): Skip for unit-only test runs
    # This saves 60-70s and 2GB memory when running only unit tests
    if not _has_integration_tests(request):
        print(
            "\n⚡ UNIT TESTS ONLY: Skipping embedding model warmup (saves 60-70s)", file=sys.stderr
        )
        yield
        return

    # PERFORMANCE FIX (2025-12-21): Skip for PostgreSQL-only tests (Story 7b-4)
    # These tests don't need Qdrant or embedding model
    if _is_postgresql_only_tests(request):
        print("\n⚡ POSTGRESQL ONLY TESTS: Skipping embedding model warmup", file=sys.stderr)
        yield
        return

    skip_ingestion = request.config.getoption("--skip-ingestion", default=False)
    if skip_ingestion:
        print(
            "\n⚡ SKIP INGESTION MODE: Skipping embedding model warmup (saves 60-70s)",
            file=sys.stderr,
        )
        yield
        return

    check_and_skip_if_unavailable()
    from raglite.shared.clients import get_embedding_model

    model_load_start = time.time()
    model = get_embedding_model()
    model_load_duration = time.time() - model_load_start
    dim = model.get_sentence_embedding_dimension()
    print(
        f"✅ Embedding model ready: {dim} dimensions (Fin-E5 loaded in {model_load_duration:.1f}s)",
        file=sys.stderr,
    )
    print(f"📊 MODEL LOAD PERF: Model loading took {model_load_duration:.1f}s", file=sys.stderr)
    yield


@pytest.fixture(scope="session", autouse=True)
def session_ingested_collection(request, warmup_embedding_model):
    """Ingest test PDF once per session (Django/FastAPI pattern). Use --skip-ingestion to reuse existing data."""
    if request.config.option.collectonly:
        yield
        return

    # PERFORMANCE FIX (2025-12-18): Skip for unit-only test runs
    if not _has_integration_tests(request):
        print("⚡ UNIT TESTS ONLY: Skipping PDF ingestion fixture", file=sys.stderr)
        yield
        return

    # PERFORMANCE FIX (2025-12-21): Skip for PostgreSQL-only tests (Story 7b-4)
    # These tests don't need Qdrant at all
    if _is_postgresql_only_tests(request):
        print("⚡ POSTGRESQL ONLY TESTS: Skipping PDF ingestion fixture", file=sys.stderr)
        yield
        return

    _session_pid = os.getpid()
    print(f"\n📊 SESSION FIXTURE START: PID={_session_pid}", file=sys.stderr)

    skip_ingestion = request.config.getoption("--skip-ingestion")
    if skip_ingestion:
        from raglite.shared.clients import get_qdrant_client
        from raglite.shared.config import settings

        qdrant = get_qdrant_client()

        try:
            count = qdrant.count(collection_name=settings.qdrant_collection_name).count
            if count == 0:
                print(
                    "⚠️  --skip-ingestion IGNORED: Collection empty. Proceeding with ingestion.",
                    file=sys.stderr,
                )
            else:
                session_state.session_sample_pdf_chunk_count = count
                print(
                    f"\n✅ Using existing collection: {settings.qdrant_collection_name} ({count} chunks)",
                    file=sys.stderr,
                )

                if count < 10:
                    print(f"⚠️  WARNING: Only {count} chunks (expected 10-30)", file=sys.stderr)
                elif count > 50000:
                    print(f"⚠️  WARNING: {count} chunks looks like PRODUCTION data", file=sys.stderr)

                class MockResult:
                    def __init__(self, chunk_count):
                        self.filename = (
                            "sample_financial_report.pdf"
                            if chunk_count < 100
                            else "2024-05 Performance Review CONSO_v1.pdf"
                        )
                        self.page_count = 10 if chunk_count < 100 else 160

                session_state.session_sample_pdf_chunk_count = count
                session_state.session_sample_pdf_result = MockResult(count)
                session_state.session_ingestion_duration = 0.0
                yield
                return
        except Exception as e:
            print(f"⚠️  --skip-ingestion failed: {e}. Falling back to ingestion.", file=sys.stderr)

    print("DEBUG: Proceeding with full ingestion", file=sys.stderr)

    from raglite.ingestion.pipeline import create_collection, ingest_pdf
    from raglite.shared.clients import get_postgresql_connection, get_qdrant_client
    from raglite.shared.config import settings
    from raglite.shared.safety import ProductionProtectionError, SafetyGuard

    guard = SafetyGuard()
    try:
        guard.validate_test_environment("session_ingested_collection fixture")
        print(
            f"DEBUG: Test environment validated - Qdrant:{settings.qdrant_port}, PostgreSQL:{settings.postgres_port}",
            file=sys.stderr,
        )
    except ProductionProtectionError as e:
        pytest.fail(
            f"CRITICAL: TEST ISOLATION FAILURE\n{e}\nSet APP_ENV=test or use --skip-ingestion"
        )

    qdrant_check = get_qdrant_client()
    try:
        existing_count = qdrant_check.count(collection_name=settings.qdrant_collection_name).count
        if existing_count > 0:
            is_ci = os.getenv("CI") == "true" or os.getenv("GITHUB_ACTIONS") == "true"
            if is_ci:
                print("DEBUG: CI mode - proceeding with re-ingestion", file=sys.stderr)
            elif not sys.stdin.isatty():
                print(
                    "DEBUG: Non-interactive (VS Code/IDE) - proceeding with re-ingestion",
                    file=sys.stderr,
                )
            else:
                print(
                    f"⚠️  WARNING: Collection has {existing_count} chunks - will delete and re-ingest",
                    file=sys.stderr,
                )
    except Exception as e:
        print(f"DEBUG: No existing collection ({e}) - safe to create", file=sys.stderr)
    use_full_pdf = os.getenv("TEST_USE_FULL_PDF", "false").lower() == "true"
    if use_full_pdf:
        sample_pdf = Path("docs/sample pdf/2025-08 Performance Review CONSO_v2.pdf")
        pdf_description = "160-page PDF"
        estimated_time = "150-180s"
    else:
        sample_pdf = Path("tests/fixtures/sample_financial_report.pdf")
        pdf_description = "10-page PDF"
        estimated_time = "8-12s"

    if not sample_pdf.exists():
        pytest.skip(f"Test PDF not found at {sample_pdf}")
        return

    print(
        f"SESSION FIXTURE: Ingesting {pdf_description} ONCE (production pattern)", file=sys.stderr
    )
    qdrant = get_qdrant_client()

    try:
        try:
            qdrant.delete_collection(collection_name=settings.qdrant_collection_name)
            print("   ✓ Deleted existing collection", file=sys.stderr)
        except Exception:
            pass

        try:
            guard.validate_test_environment("postgresql_cleanup_before_delete")
            conn = get_postgresql_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM financial_chunks")
            chunks_deleted = cursor.rowcount
            cursor.execute("DELETE FROM financial_tables")
            tables_deleted = cursor.rowcount
            print(
                f"   ✓ Cleared PostgreSQL: {tables_deleted} table rows, {chunks_deleted} chunk rows",
                file=sys.stderr,
            )
        except Exception:
            pass

        deletion_confirmed = False
        for attempt in range(8):
            try:
                collections = qdrant.get_collections().collections
                existing = [c.name for c in collections]
                if settings.qdrant_collection_name not in existing:
                    print("   ✓ Collection deletion confirmed", file=sys.stderr)
                    deletion_confirmed = True
                    break
            except Exception:
                deletion_confirmed = True
                break
            sleep_time = min(0.1 * (2**attempt), 0.5)
            time.sleep(sleep_time)

        if not deletion_confirmed:
            print("   ⚠️  Collection deletion timeout, proceeding", file=sys.stderr)

        create_collection(
            collection_name=settings.qdrant_collection_name,
            vector_size=settings.embedding_dimension,
        )

        initial_count = qdrant.count(collection_name=settings.qdrant_collection_name)
        if initial_count.count > 0:
            pytest.skip(f"Collection has {initial_count.count} chunks after creation (expected 0)")
        print("   ✓ Collection verified empty", file=sys.stderr)
    except Exception as e:
        pytest.skip(f"Failed to initialize Qdrant collection: {e}")

    skip_metadata_extraction = not use_full_pdf
    if skip_metadata_extraction:
        print("   ℹ️  Skipping LLM metadata extraction (LOCAL mode)", file=sys.stderr)

    start_ingest = time.time()
    try:
        asyncio.run(
            ingest_pdf(
                str(sample_pdf), clear_existing=False, skip_metadata=skip_metadata_extraction
            )
        )
        time.time() - start_ingest
    except Exception:
        raise

    for _attempt in range(10):
        count_after = qdrant.count(collection_name=settings.qdrant_collection_name)
        if count_after.count > 0:
            break
        time.sleep(0.2)

    session_state.session_sample_pdf_chunk_count = count_after.count

    try:
        import logging

        from psycopg2.extras import RealDictCursor

        logger = logging.getLogger(__name__)

        conn = get_postgresql_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        pg_count = 0
        expected_min_rows = 10 if not use_full_pdf else 100

        max_attempts = 20
        for attempt in range(max_attempts):
            if not conn.autocommit:
                conn.rollback()
            cursor.execute("SELECT COUNT(*) FROM financial_tables")
            pg_count = cursor.fetchone()["count"]

            if pg_count >= expected_min_rows:
                logger.info(
                    "PostgreSQL data visible", extra={"rows": pg_count, "attempt": attempt + 1}
                )
                break

            sleep_time = min(0.2 * (2**attempt), 2.0)
            if attempt in [0, 2, 5, 8, 11, 14, 17]:
                print(
                    f"   ⏳ PostgreSQL: {pg_count}/{expected_min_rows} rows (attempt {attempt + 1}/{max_attempts})",
                    file=sys.stderr,
                )
            time.sleep(sleep_time)
        else:
            pytest.fail(
                f"PostgreSQL data not visible after {max_attempts} attempts: {pg_count}/{expected_min_rows} rows"
            )

        cursor.close()

        session_state.session_postgresql_row_count = pg_count

        if pg_count < expected_min_rows:
            pytest.fail(
                f"PostgreSQL has only {pg_count} rows, expected at least {expected_min_rows}"
            )
    except Exception as e:
        pytest.fail(f"PostgreSQL verification failed: {e}")

    print("\n✅ Session fixture complete:", file=sys.stderr)
    print(
        f"   Ready for {len(request.session.items) if hasattr(request.session, 'items') else '?'} tests",
        file=sys.stderr,
    )

    expected_range = (150, 220) if use_full_pdf else (10, 30)
    if not (expected_range[0] <= count_after.count <= expected_range[1]):
        pytest.fail(
            f"CRITICAL: Chunk count {count_after.count} not in expected range {expected_range}"
        )

    snapshot_start = time.time()
    try:
        snapshot_info = qdrant.create_snapshot(
            collection_name=settings.qdrant_collection_name, wait=True
        )
        session_state.session_snapshot_name = snapshot_info.name
        time.time() - snapshot_start
        print(
            f"   ✓ Snapshot created for fast restoration (<1s vs {estimated_time})", file=sys.stderr
        )
    except Exception:
        session_state.session_snapshot_name = None

    yield
    try:
        qdrant.delete_collection(collection_name=settings.qdrant_collection_name)
    except Exception:
        pass
