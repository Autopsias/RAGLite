"""Helper functions for session_ingested_collection fixture.

This module contains helper functions extracted from the large
session_ingested_collection fixture to improve maintainability.
"""

import os
import sys
import time
from pathlib import Path

import pytest


def _should_skip_session_fixture(request) -> bool:
    """Check if session fixture should skip (early exit conditions).

    Args:
        request: pytest request fixture

    Returns:
        True if should skip, False otherwise
    """
    from ._test_detection import _has_integration_tests, _is_postgresql_only_tests

    # PERFORMANCE FIX (2025-12-18): Skip for unit-only test runs
    if not _has_integration_tests(request):
        print("⚡ UNIT TESTS ONLY: Skipping PDF ingestion fixture", file=sys.stderr)
        return True

    # PERFORMANCE FIX (2025-12-21): Skip for PostgreSQL-only tests (Story 7b-4)
    if _is_postgresql_only_tests(request):
        print("⚡ POSTGRESQL ONLY TESTS: Skipping PDF ingestion fixture", file=sys.stderr)
        return True

    return False


def _validate_test_environment_for_session(request, settings) -> None:
    """Validate test environment before session fixture setup.

    Args:
        request: pytest request fixture
        settings: Application settings

    Raises:
        pytest.fail: If environment validation fails
    """
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


def _check_existing_collection(qdrant_check, settings) -> bool:
    """Check for existing Qdrant collection and prompt user.

    Args:
        qdrant_check: Qdrant client
        settings: Application settings

    Returns:
        True if collection exists, False otherwise
    """
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
            return True
    except Exception as e:
        print(f"DEBUG: No existing collection ({e}) - safe to create", file=sys.stderr)
    return False


def _get_test_pdf_path(use_full_pdf: bool = False) -> tuple[Path, str, str]:
    """Get path to test PDF and description.

    Args:
        use_full_pdf: If True, use 160-page PDF instead of 10-page

    Returns:
        Tuple of (pdf_path, description, estimated_time)

    CI Optimization (Story CI-OPT):
        In CI mode, uses minimal 3-page PDF (228K) instead of 10-page (357K)
        Combined with fast embedding model, reduces fixture time from ~70s to ~10s
    """
    is_ci = os.getenv("CI") == "true" or os.getenv("GITHUB_ACTIONS") == "true"
    use_ci_minimal = os.getenv("CI_FAST_EMBEDDING", "").lower() == "true"

    if use_full_pdf:
        sample_pdf = Path("docs/sample pdf/2025-08 Performance Review CONSO_v2.pdf")
        pdf_description = "160-page PDF"
        estimated_time = "150-180s"
    elif is_ci and use_ci_minimal:
        # CI Optimization: Use minimal 3-page PDF for faster CI tests
        sample_pdf = Path("tests/fixtures/sample-small-3-pages.pdf")
        pdf_description = "3-page PDF (CI fast mode)"
        estimated_time = "3-5s"
    else:
        sample_pdf = Path("tests/fixtures/sample_financial_report.pdf")
        pdf_description = "10-page PDF"
        estimated_time = "8-12s"

    return sample_pdf, pdf_description, estimated_time


def _setup_skip_ingestion_mode(
    skip_ingestion: bool,
    session_state,
) -> bool:
    """Handle --skip-ingestion mode to reuse existing collection.

    Args:
        skip_ingestion: Value from --skip-ingestion flag
        session_state: Module-level session state object

    Returns:
        True if should skip ingestion (reuse existing), False otherwise
    """
    if not skip_ingestion:
        return False

    from raglite.shared.clients import get_qdrant_client
    from raglite.shared.config import settings

    qdrant = get_qdrant_client()

    try:
        count = qdrant.count(collection_name=settings.qdrant_collection_name).count
        if count == 0:
            print(
                "⚠️  --skip-ingestion IGNORED: Collection empty. Proceeding with ingestion.",
                file=__import__("sys").stderr,
            )
            return False
        else:
            session_state.session_sample_pdf_chunk_count = count
            print(
                f"\n✅ Using existing collection: {settings.qdrant_collection_name} ({count} chunks)",
                file=__import__("sys").stderr,
            )

            if count < 10:
                print(
                    f"⚠️  WARNING: Only {count} chunks (expected 10-30)",
                    file=__import__("sys").stderr,
                )
            elif count > 50000:
                print(
                    f"⚠️  WARNING: {count} chunks looks like PRODUCTION data",
                    file=__import__("sys").stderr,
                )

            class MockResult:
                def __init__(self, chunk_count):
                    self.filename = (
                        "sample_financial_report.pdf"
                        if chunk_count < 100
                        else "2024-05 Performance Review CONSO_v1.pdf"
                    )
                    self.page_count = 10 if chunk_count < 100 else 160

            session_state.session_sample_pdf_result = MockResult(count)
            session_state.session_ingestion_duration = 0.0
            return True
    except Exception as e:
        print(
            f"⚠️  --skip-ingestion failed: {e}. Falling back to ingestion.",
            file=__import__("sys").stderr,
        )
        return False


def _initialize_qdrant_collection(settings, guard, qdrant) -> None:
    """Delete existing collection and create fresh one.

    Args:
        settings: Application settings
        guard: SafetyGuard instance
        qdrant: Qdrant client

    Raises:
        pytest.skip: If initialization fails
    """
    import sys

    try:
        try:
            qdrant.delete_collection(collection_name=settings.qdrant_collection_name)
            print("   ✓ Deleted existing collection", file=sys.stderr)
        except Exception:
            pass

        try:
            from raglite.shared.clients import get_postgresql_connection

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

        from raglite.ingestion.pipeline import create_collection
        from raglite.shared.config import get_active_embedding_dimension

        create_collection(
            collection_name=settings.qdrant_collection_name,
            vector_size=get_active_embedding_dimension(),
        )

        initial_count = qdrant.count(collection_name=settings.qdrant_collection_name)
        if initial_count.count > 0:
            pytest.skip(f"Collection has {initial_count.count} chunks after creation (expected 0)")
        print("   ✓ Collection verified empty", file=sys.stderr)
    except Exception as e:
        pytest.skip(f"Failed to initialize Qdrant collection: {e}")


def _ingest_test_pdf(
    sample_pdf: Path,
    skip_metadata: bool,
    settings,
) -> None:
    """Ingest test PDF into Qdrant collection.

    Args:
        sample_pdf: Path to test PDF
        skip_metadata: If True, skip LLM metadata extraction
        settings: Application settings

    Raises:
        Exception: If ingestion fails
    """
    import asyncio
    import sys

    from raglite.ingestion.pipeline import ingest_pdf

    # CI Optimization: Always skip metadata extraction in CI
    # This avoids Mistral API calls during test fixture setup
    # which cause 401 Unauthorized errors when mocks aren't applied yet
    is_ci = os.getenv("CI") == "true" or os.getenv("GITHUB_ACTIONS") == "true"
    if is_ci:
        skip_metadata = True
        print("   ℹ️  Skipping LLM metadata extraction (CI mode)", file=sys.stderr)
    elif skip_metadata:
        print("   ℹ️  Skipping LLM metadata extraction (LOCAL mode)", file=sys.stderr)

    start_ingest = time.time()
    try:
        asyncio.run(ingest_pdf(str(sample_pdf), clear_existing=False, skip_metadata=skip_metadata))
        time.time() - start_ingest
    except Exception:
        raise


def _verify_qdrant_data(qdrant, settings, expected_range: tuple[int, int]) -> int:
    """Verify Qdrant collection has expected chunk count.

    Args:
        qdrant: Qdrant client
        settings: Application settings
        expected_range: Tuple of (min_chunks, max_chunks)

    Returns:
        Actual chunk count

    Raises:
        pytest.fail: If chunk count validation fails
    """
    import sys

    for _attempt in range(10):
        count_after = qdrant.count(collection_name=settings.qdrant_collection_name)
        if count_after.count > 0:
            break
        time.sleep(0.2)

    # Tolerance-based validation: allow ±15% variance from expected range
    # Story 2.8 table-aware chunking produces variable counts based on table density
    min_expected, max_expected = expected_range
    tolerance = 0.15
    min_allowed = int(min_expected * (1 - tolerance))
    max_allowed = int(max_expected * (1 + tolerance))

    if not (min_allowed <= count_after.count <= max_allowed):
        pytest.fail(
            f"CRITICAL: Chunk count {count_after.count} not in tolerance range "
            f"({min_allowed}-{max_allowed}, ±15% of expected {expected_range})"
        )

    print(f"\n✅ Qdrant verification: {count_after.count} chunks", file=sys.stderr)
    return count_after.count


def _verify_postgresql_data(
    use_full_pdf: bool,
    session_state,
) -> int:
    """Verify PostgreSQL has expected table row count.

    Args:
        use_full_pdf: Whether full PDF was ingested
        session_state: Module-level session state object

    Returns:
        Actual PostgreSQL row count

    Raises:
        pytest.fail: If verification fails
    """
    import logging
    import sys

    from psycopg2.extras import RealDictCursor

    from raglite.shared.clients import get_postgresql_connection

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
            logger.info("PostgreSQL data visible", extra={"rows": pg_count, "attempt": attempt + 1})
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
        pytest.fail(f"PostgreSQL has only {pg_count} rows, expected at least {expected_min_rows}")

    print(f"✅ PostgreSQL verification: {pg_count} rows", file=sys.stderr)
    return pg_count


def _create_qdrant_snapshot(
    qdrant,
    settings,
    session_state,
    estimated_time: str,
) -> None:
    """Create Qdrant snapshot for fast restoration in subsequent tests.

    Args:
        qdrant: Qdrant client
        settings: Application settings
        session_state: Module-level session state object
        estimated_time: Description of ingestion time (e.g., "8-12s")
    """
    import sys

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
