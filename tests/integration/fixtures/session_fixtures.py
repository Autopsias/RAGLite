"""Session-scoped fixtures: database schema, embedding warmup, and PDF ingestion (Django/FastAPI pattern)."""

import os
import sys
import time

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
    if request.config.option.collectonly:
        yield
        return

    # CRITICAL FIX (2026-01-25): Conditional worker exclusion for embedding model loading.
    #
    # Worker Distribution Logic:
    # - Fin-E5 mode (2GB model): Only gw0/master loads to prevent OOM (2x 2GB = 4GB > 3.5GB runner RAM)
    # - CI fast mode (80MB MiniLM): ALL workers can load safely (2x 80MB = 160MB << 7GB runner RAM)
    #
    # With CI_FAST_EMBEDDING=true, tests distribute across both workers instead of serializing to gw0.
    # This cuts retrieval shard time from 25min (timeout) to ~12-15min.
    ci_fast = os.environ.get("CI_FAST_EMBEDDING", "").lower() == "true"
    if not ci_fast and worker_id not in ("master", "gw0"):
        # Heavy Fin-E5 mode: Skip non-gw0 workers to prevent OOM
        print(
            f"\n⚡ Worker {worker_id}: Skipping embedding warmup (Fin-E5 mode - gw0 handles it)",
            file=sys.stderr,
        )
        yield
        return
    elif ci_fast and worker_id not in ("master", "gw0"):
        # CI fast mode: All workers load the lightweight MiniLM model
        print(
            f"\n⚡ Worker {worker_id}: Loading embedding model (CI fast mode - MiniLM is lightweight)",
            file=sys.stderr,
        )

    # P0 FIX (2026-01-20): Direct CI_SHARD check FIRST - bypass complex detection
    # This prevents xdist workers from loading 2GB model when not needed (240s overhead)
    ci_shard = os.environ.get("CI_SHARD", "")
    print(f"\n🔍 CI_SHARD environment: {ci_shard if ci_shard else 'NOT SET'}", file=sys.stderr)
    if ci_shard.startswith("postgresql") or ci_shard == "mcp":
        print(
            f"\n⚡ CI_SHARD={ci_shard} detected - skipping embedding model warmup", file=sys.stderr
        )
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

    # FIX (2026-01-25): Don't skip embedding model warmup in --skip-ingestion mode.
    # The warmup with filelock is CRITICAL to prevent worker crashes when both workers
    # try to load the model simultaneously. The skip-ingestion flag only skips PDF ingestion.
    skip_ingestion = request.config.getoption("--skip-ingestion", default=False)
    if skip_ingestion:
        print(
            "\n⚡ SKIP INGESTION MODE: Still loading embedding model (required for tests)",
            file=sys.stderr,
        )
        # Fall through to load the model with filelock - don't return early!

    check_and_skip_if_unavailable()

    # CRITICAL FIX (2026-01-24): Reset settings BEFORE accessing them to ensure
    # CI_FAST_EMBEDDING env var is picked up in xdist workers.
    # Without this, the Settings singleton may have been created before the env var was set.
    from raglite.shared.config import reset_settings

    # Diagnostic: Log env var state BEFORE reset
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

    from raglite.shared.clients import get_embedding_model

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
    # Problem: When both workers load the embedding model simultaneously, resource contention
    # causes crashes ("worker crashed and worker restarting disabled").
    # Solution: Use file lock to serialize model loading. Even though the model is cached,
    # the initial HuggingFace/SentenceTransformer loading process is not thread-safe.
    # With lock: gw0 loads -> releases -> gw1 loads (sequential, safe)
    # Without lock: gw0 and gw1 load simultaneously (race condition, crashes)
    lock_path = "/tmp/raglite_embedding_model_warmup.lock"
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

    # Get worker_id from request config (may be passed from warmup_embedding_model)
    worker_id = getattr(request.config, "workerinput", {}).get("workerid", "master")

    # Get test PDF path (outside lock - needed for verification too)
    use_full_pdf = os.getenv("TEST_USE_FULL_PDF", "false").lower() == "true"
    sample_pdf, pdf_description, estimated_time = _get_test_pdf_path(use_full_pdf)

    if not sample_pdf.exists():
        pytest.skip(f"Test PDF not found at {sample_pdf}")
        return

    # Get Qdrant client (reused throughout fixture)
    qdrant = get_qdrant_client()

    # CRITICAL FIX (2026-01-25): Serialize PDF ingestion across workers with filelock.
    # Problem: When multiple workers run session fixtures simultaneously, Docling converter
    # initialization races cause crashes ("node down: Not properly terminated").
    # The Docling/pypdfium backend is NOT thread-safe for concurrent initialization.
    # Solution: Use file lock to ensure only one worker ingests at a time.
    # After first worker completes, other workers check if data exists before re-ingesting.
    ingestion_lock_path = "/tmp/raglite_pdf_ingestion.lock"
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
                session_state.session_sample_pdf_chunk_count = existing_count
                already_ingested = True
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
            # This prevents xdist race conditions where workers access collection before it's created
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

        print(f"🔓 Worker {worker_id}: Releasing PDF ingestion lock", file=sys.stderr)

    # Verify Qdrant data (outside lock - all workers verify)
    # Expected chunks vary by PDF size:
    #   160-page: 150-220 chunks
    #   10-page:  10-55 chunks (~42 typical)
    #   3-page:   15-35 chunks (CI fast mode with table-aware chunking)
    # Note: Actual chunk counts observed in CI (2026-01-22): ~21 chunks for 3-page PDF
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
    # CI containers are ephemeral so no cleanup needed
    is_ci_cleanup = os.getenv("CI") == "true"
    if not is_ci_cleanup:
        try:
            qdrant.delete_collection(collection_name=settings.qdrant_collection_name)
        except Exception:
            pass
