"""Session-scoped fixtures: database schema, embedding warmup, and PDF ingestion (Django/FastAPI pattern)."""

import os
import sys
import tempfile
import time
from pathlib import Path

import filelock
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


def _should_skip_embedding_warmup(request, worker_id):
    """Determine if embedding model warmup should be skipped.

    Returns:
        tuple[bool, str]: (should_skip, reason_message)
    """
    if request.config.option.collectonly:
        return True, "collectonly mode"

    # CRITICAL FIX (2026-01-25): Conditional worker exclusion for embedding model loading.
    ci_fast = os.environ.get("CI_FAST_EMBEDDING", "").lower() == "true"
    if not ci_fast and worker_id not in ("master", "gw0"):
        # Heavy Fin-E5 mode: Skip non-gw0 workers to prevent OOM
        print(
            f"\n⚡ Worker {worker_id}: Skipping embedding warmup (Fin-E5 mode - gw0 handles it)",
            file=sys.stderr,
        )
        return True, "non-gw0 worker in Fin-E5 mode"
    elif ci_fast and worker_id not in ("master", "gw0"):
        # CI fast mode: All workers load the lightweight MiniLM model
        print(
            f"\n⚡ Worker {worker_id}: Loading embedding model (CI fast mode - MiniLM is lightweight)",
            file=sys.stderr,
        )

    # P0 FIX (2026-01-20): Direct CI_SHARD check FIRST - bypass complex detection
    ci_shard = os.environ.get("CI_SHARD", "")
    print(f"\n🔍 CI_SHARD environment: {ci_shard if ci_shard else 'NOT SET'}", file=sys.stderr)
    if ci_shard.startswith("postgresql") or ci_shard == "mcp":
        print(
            f"\n⚡ CI_SHARD={ci_shard} detected - skipping embedding model warmup", file=sys.stderr
        )
        return True, f"CI_SHARD={ci_shard}"

    # PERFORMANCE FIX (2025-12-18): Skip for unit-only test runs
    if not _has_integration_tests(request):
        print(
            "\n⚡ UNIT TESTS ONLY: Skipping embedding model warmup (saves 60-70s)", file=sys.stderr
        )
        return True, "unit tests only"

    # PERFORMANCE FIX (2025-12-21): Skip for PostgreSQL-only tests (Story 7b-4)
    if _is_postgresql_only_tests(request):
        print("\n⚡ POSTGRESQL ONLY TESTS: Skipping embedding model warmup", file=sys.stderr)
        return True, "postgresql only tests"

    # FIX (2026-01-25): Don't skip embedding model warmup in --skip-ingestion mode.
    skip_ingestion = request.config.getoption("--skip-ingestion", default=False)
    if skip_ingestion:
        print(
            "\n⚡ SKIP INGESTION MODE: Still loading embedding model (required for tests)",
            file=sys.stderr,
        )

    return False, ""


def _load_embedding_model_with_lock(worker_id):
    """Load embedding model with filelock serialization.

    Returns:
        tuple[object, int, float]: (model, dimension, load_duration)
    """
    from raglite.shared.clients import get_embedding_model
    from raglite.shared.config import reset_settings

    # CRITICAL FIX (2026-01-24): Reset settings BEFORE accessing them
    ci_fast_env = os.environ.get("CI_FAST_EMBEDDING", "NOT SET")
    ci_env = os.environ.get("CI", "NOT SET")
    print(
        f"🔍 DEBUG: CI_FAST_EMBEDDING env = {ci_fast_env}, CI env = {ci_env}",
        file=sys.stderr,
    )

    # Force Settings recreation to pick up current env vars
    current_settings = reset_settings()
    print(
        f"🔍 DEBUG: After reset_settings(): ci_fast_embedding_enabled = {current_settings.ci_fast_embedding_enabled}",
        file=sys.stderr,
    )

    # CI Optimization instrumentation: Log which model is being used
    model_name = (
        current_settings.ci_fast_embedding_model
        if current_settings.ci_fast_embedding_enabled
        else current_settings.embedding_model
    )
    print(
        f"🔄 Loading embedding model: {model_name} (CI fast mode: {current_settings.ci_fast_embedding_enabled})",
        file=sys.stderr,
    )

    # CRITICAL FIX (2026-01-25): Serialize model loading across workers with filelock.
    # Use tempfile.gettempdir() for secure temporary directory selection
    import tempfile

    lock_path = str(Path(tempfile.gettempdir()) / "raglite_embedding_model_warmup.lock")
    lock = filelock.FileLock(lock_path, timeout=300)  # 5 min timeout

    print(f"🔒 Worker {worker_id}: Acquiring embedding model lock...", file=sys.stderr)
    with lock:
        print(f"🔒 Worker {worker_id}: Lock acquired, loading model...", file=sys.stderr)
        model_load_start = time.time()
        model = get_embedding_model()
        model_load_duration = time.time() - model_load_start
        dim = model.get_sentence_embedding_dimension()

        # Report performance metrics
        mode_label = "CI fast" if current_settings.ci_fast_embedding_enabled else "Production"
        print(
            f"✅ Embedding model ready: {dim} dimensions ({mode_label}: {model_name})",
            file=sys.stderr,
        )
        print(
            f"📊 MODEL LOAD PERF: {model_name} loaded in {model_load_duration:.1f}s",
            file=sys.stderr,
        )
        print(f"🔓 Worker {worker_id}: Releasing embedding model lock", file=sys.stderr)

    return model, dim, model_load_duration


def _ingest_with_worker_lock(request, worker_id, qdrant, settings, sample_pdf):
    """Ingest PDF with filelock serialization across workers.

    Returns:
        int: Number of chunks ingested
    """
    use_full_pdf = os.getenv("TEST_USE_FULL_PDF", "false").lower() == "true"
    _, pdf_description, _ = _get_test_pdf_path(use_full_pdf)

    # CRITICAL FIX (2026-01-25): Serialize PDF ingestion across workers with filelock.
    # Use tempfile.gettempdir() for secure temporary directory selection
    ingestion_lock_path = str(Path(tempfile.gettempdir()) / "raglite_pdf_ingestion.lock")
    ingestion_lock = filelock.FileLock(ingestion_lock_path, timeout=600)  # 10 min timeout

    print(f"🔒 Worker {worker_id}: Acquiring PDF ingestion lock...", file=sys.stderr)
    with ingestion_lock:
        print(
            f"🔒 Worker {worker_id}: Lock acquired, checking for existing data...",
            file=sys.stderr,
        )

        # Check if another worker already ingested (AFTER acquiring lock)
        already_ingested = False
        try:
            collection_info = qdrant.get_collection(settings.qdrant_collection_name)
            existing_count = collection_info.points_count
            if existing_count > 0:
                print(
                    f"✅ Worker {worker_id}: Collection already has {existing_count} points "
                    f"(ingested by another worker)",
                    file=sys.stderr,
                )
                already_ingested = True
                chunk_count = existing_count
        except Exception:
            # Collection doesn't exist - will be created below
            pass

        # Only ingest if no existing data
        if not already_ingested:
            _check_existing_collection(qdrant, settings)

            print(
                f"SESSION FIXTURE: Ingesting {pdf_description} ONCE (production pattern)",
                file=sys.stderr,
            )

            # Initialize Qdrant collection
            # CI FIX (2026-01-21): In CI mode, collection is pre-created by scripts/init-ci-qdrant.py
            from raglite.shared.safety import SafetyGuard

            guard = SafetyGuard()
            is_ci = os.getenv("CI") == "true"
            if not is_ci:
                _initialize_qdrant_collection(settings, guard, qdrant)
            else:
                print(
                    "CI mode: Using pre-created collection (scripts/init-ci-qdrant.py)",
                    file=sys.stderr,
                )

            # Ingest test PDF
            skip_metadata_extraction = not use_full_pdf
            _ingest_test_pdf(sample_pdf, skip_metadata_extraction, settings)

            # Get chunk count after ingestion
            collection_info = qdrant.get_collection(settings.qdrant_collection_name)
            chunk_count = collection_info.points_count

        print(f"🔓 Worker {worker_id}: Releasing PDF ingestion lock", file=sys.stderr)

    return chunk_count


@pytest.fixture(scope="session", autouse=True)
@pytest.mark.timeout(180)  # P0 FIX (2026-01-23): 3 min max for DB schema init
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
@pytest.mark.timeout(
    300
)  # P0 FIX (2026-01-23): 5 min max for embedding model load (typical: 60-70s)
def warmup_embedding_model(request, worker_id):
    """Pre-warm Fin-E5 model (60-70s) before PDF ingestion. Skipped if --skip-ingestion.

    CRITICAL FIX (2026-01-24): Worker-exclusive model loading to prevent OOM crashes.
    Research finding: Session fixtures run PER-WORKER in xdist, not globally.
    With 2 workers each loading 80MB model, OOM can occur (2x 2GB = 4GB for Fin-E5).
    Solution: Only gw0 loads the model, other workers skip.
    """
    # Check if warmup should be skipped
    should_skip, reason = _should_skip_embedding_warmup(request, worker_id)
    if should_skip:
        yield
        return

    check_and_skip_if_unavailable()

    # Load model with filelock serialization
    _load_embedding_model_with_lock(worker_id)

    yield


@pytest.fixture(scope="session", autouse=True)
@pytest.mark.timeout(
    600
)  # P0 FIX (2026-01-23): 10 min max (CI uses --skip-ingestion, local: 5-10 min)
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

    # Get worker_id from request config
    worker_id = getattr(request.config, "workerinput", {}).get("workerid", "master")

    # Get test PDF path
    use_full_pdf = os.getenv("TEST_USE_FULL_PDF", "false").lower() == "true"
    sample_pdf, pdf_description, estimated_time = _get_test_pdf_path(use_full_pdf)

    if not sample_pdf.exists():
        pytest.skip(f"Test PDF not found at {sample_pdf}")
        return

    # Get Qdrant client
    qdrant = get_qdrant_client()

    # Ingest with worker lock
    _ingest_with_worker_lock(request, worker_id, qdrant, settings, sample_pdf)

    # Verify Qdrant data (outside lock - all workers verify)
    if use_full_pdf:
        expected_range = (150, 220)
    elif "3-page" in pdf_description:
        expected_range = (15, 35)  # CI fast mode: 3-page PDF produces ~21 chunks
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
    # CI FIX (2026-01-21): Skip cleanup in CI to avoid race conditions with xdist workers
    is_ci_cleanup = os.getenv("CI") == "true"
    if not is_ci_cleanup:
        try:
            qdrant.delete_collection(collection_name=settings.qdrant_collection_name)
        except Exception:
            pass
