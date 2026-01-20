"""Session-scoped fixtures: database schema, embedding warmup, and PDF ingestion (Django/FastAPI pattern)."""

import os
import sys
import time

import pytest

# Import session state globals
from . import session_state
from ._ingestion_helpers import (
    _check_existing_collection,
    _create_qdrant_snapshot,
    _get_test_pdf_path,
    _ingest_test_pdf,
    _initialize_qdrant_collection,
    _setup_skip_ingestion_mode,
    _should_skip_session_fixture,
    _validate_test_environment_for_session,
    _verify_postgresql_data,
    _verify_qdrant_data,
)
from ._test_detection import _has_integration_tests, _is_postgresql_only_tests
from .service_checking import check_and_skip_if_unavailable


@pytest.fixture(scope="session", autouse=True)
def ensure_test_database_schema(request):
    """Ensure PostgreSQL schema exists before tests (Story 4.0.5).

    CRITICAL FIX (2026-01-20): PostgreSQL schema must be initialized for ALL integration tests,
    including PostgreSQL-only tests (model_selection, forecasting). These tests need ORM tables
    like model_selection, model_weights, etc.
    """
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

        # Check if ORM tables exist (model_selection is critical for Story 7b-4)
        cursor.execute(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'model_selection');"
        )
        model_selection_exists = cursor.fetchone()[0]

        if not model_selection_exists:
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
            logger.info("✅ Test database schema already exists (model_selection table found)")
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
    from raglite.shared.config import settings

    # CI Optimization instrumentation: Log which model is being used
    model_name = (
        settings.ci_fast_embedding_model
        if settings.ci_fast_embedding_enabled
        else settings.embedding_model
    )
    print(
        f"🔄 Loading embedding model: {model_name} (CI fast mode: {settings.ci_fast_embedding_enabled})",
        file=sys.stderr,
    )

    model_load_start = time.time()
    model = get_embedding_model()
    model_load_duration = time.time() - model_load_start
    dim = model.get_sentence_embedding_dimension()

    # Report performance metrics
    mode_label = "CI fast" if settings.ci_fast_embedding_enabled else "Production"
    print(
        f"✅ Embedding model ready: {dim} dimensions ({mode_label}: {model_name})",
        file=sys.stderr,
    )
    print(f"📊 MODEL LOAD PERF: {model_name} loaded in {model_load_duration:.1f}s", file=sys.stderr)
    yield


@pytest.fixture(scope="session", autouse=True)
def session_ingested_collection(request, warmup_embedding_model):
    """Ingest test PDF once per session (Django/FastAPI pattern). Use --skip-ingestion to reuse existing data."""
    if request.config.option.collectonly:
        yield
        return

    # Early exit checks (unit-only, postgresql-only)
    if _should_skip_session_fixture(request):
        yield
        return

    _session_pid = os.getpid()
    print(f"\n📊 SESSION FIXTURE START: PID={_session_pid}", file=sys.stderr)

    skip_ingestion = request.config.getoption("--skip-ingestion")

    # Handle --skip-ingestion mode
    if _setup_skip_ingestion_mode(skip_ingestion, session_state):
        yield
        return

    print("DEBUG: Proceeding with full ingestion", file=sys.stderr)

    from raglite.shared.clients import get_qdrant_client
    from raglite.shared.config import settings

    # Validate test environment
    _validate_test_environment_for_session(request, settings)

    # Check for existing collection
    qdrant_check = get_qdrant_client()
    _check_existing_collection(qdrant_check, settings)

    # Get test PDF path
    use_full_pdf = os.getenv("TEST_USE_FULL_PDF", "false").lower() == "true"
    sample_pdf, pdf_description, estimated_time = _get_test_pdf_path(use_full_pdf)

    if not sample_pdf.exists():
        pytest.skip(f"Test PDF not found at {sample_pdf}")
        return

    print(
        f"SESSION FIXTURE: Ingesting {pdf_description} ONCE (production pattern)", file=sys.stderr
    )
    qdrant = get_qdrant_client()

    # Initialize Qdrant collection
    from raglite.shared.safety import SafetyGuard

    guard = SafetyGuard()
    _initialize_qdrant_collection(settings, guard, qdrant)

    # Ingest test PDF
    skip_metadata_extraction = not use_full_pdf
    _ingest_test_pdf(sample_pdf, skip_metadata_extraction, settings)

    # Verify Qdrant data
    # Expected chunks vary by PDF size:
    #   160-page: 150-220 chunks
    #   10-page:  10-55 chunks (~42 typical)
    #   3-page:   15-35 chunks (CI fast mode with table-aware chunking)
    if use_full_pdf:
        expected_range = (150, 220)
    elif "3-page" in pdf_description:
        expected_range = (5, 15)  # CI fast mode: table-aware chunking produces fewer, larger chunks
    else:
        expected_range = (10, 55)  # Standard 10-page test PDF
    count_after = _verify_qdrant_data(qdrant, settings, expected_range)
    session_state.session_sample_pdf_chunk_count = count_after

    # Verify PostgreSQL data
    _verify_postgresql_data(use_full_pdf, session_state)

    # Report completion
    print("\n✅ Session fixture complete:", file=sys.stderr)
    print(
        f"   Ready for {len(request.session.items) if hasattr(request.session, 'items') else '?'} tests",
        file=sys.stderr,
    )

    # Create snapshot for fast restoration
    _create_qdrant_snapshot(qdrant, settings, session_state, estimated_time)

    yield

    # Cleanup
    try:
        qdrant.delete_collection(collection_name=settings.qdrant_collection_name)
    except Exception:
        pass
