"""Test isolation fixtures for Qdrant collection state management.

This module provides per-test isolation ensuring tests don't interfere with each other.
Uses lazy restoration pattern to optimize performance.

Functions:
    _do_restoration: Helper function to restore Qdrant collection to session baseline
    ensure_qdrant_test_isolation: Per-test fixture for collection state isolation

LAZY RESTORATION PATTERN:
- Tests marked @pytest.mark.preserve_collection skip all cleanup (read-only)
- Tests marked @pytest.mark.manages_collection_state mark session dirty, defer restoration
- Other tests restore BEFORE if session is dirty, then run test
"""

import asyncio
import time
from pathlib import Path

import pytest

# Import session state globals
from . import session_state
from .session_fixtures import _has_integration_tests


def _do_restoration(qdrant, settings):
    """Helper function to restore Qdrant collection to session baseline.

    PERFORMANCE OPTIMIZATION (2025-12-07): Extracted to enable lazy restoration.
    Called from ensure_qdrant_test_isolation when restoration is needed.

    Uses snapshot recovery (fast path, <1s) or PDF re-ingestion (slow path, 10-45s).
    """
    # PERFORMANCE OPTIMIZATION: Use snapshot recovery instead of re-ingestion
    # Snapshot restore: <1s vs PDF re-ingestion: 10-15s (10-15x faster!)
    if session_state.session_snapshot_name:
        # FAST PATH: Restore from snapshot
        print(f"   ⚡ Using snapshot: {session_state.session_snapshot_name}")
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
            snapshot_url = f"{qdrant_host}/collections/{settings.qdrant_collection_name}/snapshots/{session_state.session_snapshot_name}"

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
                restored_count = qdrant.count(collection_name=settings.qdrant_collection_name).count
                if restored_count == session_state.session_sample_pdf_chunk_count:
                    break
                time.sleep(0.2)

            print(f"   ✓ Restored ({restored_count} chunks) in {restore_duration:.2f}s")
            return  # Success - exit early

        except Exception as e:
            print(f"   ⚠️  Snapshot recovery failed: {e}")
            print("   ⚠️  Falling back to PDF re-ingestion")
            # Fall through to re-ingestion below

    # SLOW PATH: Re-ingest PDF (fallback if snapshot failed or doesn't exist)
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
    restored_count = 0
    for _attempt in range(10):  # Max 2 seconds wait
        restored_count = qdrant.count(collection_name=settings.qdrant_collection_name).count
        if restored_count == session_state.session_sample_pdf_chunk_count:
            break
        time.sleep(0.2)

    print(f"   ✓ Restored ({restored_count} chunks)")


@pytest.fixture(autouse=True)
def ensure_qdrant_test_isolation(request):
    """Ensure Qdrant collection isolation between integration tests (SMART VERSION).

    CRITICAL OPTIMIZATION: Skips re-ingest cleanup for tests that intentionally
    modify collection (call ingest_pdf with clear_existing=True).

    Without this: Tests with clear_existing=True pay 150-170s (ingest + re-ingest cleanup)
    With this: Tests with clear_existing=True pay only 75-85s (ingest only, no cleanup)

    Behavior:
    - Tests marked @pytest.mark.preserve_collection: Skip cleanup (read-only tests)
    - Tests marked @pytest.mark.manages_collection_state: Mark session dirty, defer restoration
    - Other tests: Restore BEFORE test if session is dirty, then run test

    LAZY RESTORATION (2025-12-07): Instead of restoring after EVERY `manages_collection_state`
    test, we now use lazy restoration:
    1. `manages_collection_state` tests just mark session as "dirty" (no immediate restoration)
    2. Restoration only happens BEFORE a test that NEEDS clean state
    3. This reduces restoration overhead from O(N) to O(transitions)

    Performance improvement: ~400 seconds saved by batching restorations.

    NOTE: This fixture lives in tests/integration/conftest.py, so it ONLY applies to
    integration tests. No need to detect test type via inspect - this conftest isn't
    loaded by unit tests.

    PERFORMANCE FIX (2025-11-08): Skip during test discovery to avoid Test Explorer overhead
    """
    # PERFORMANCE: Skip during test collection/discovery phase (Test Explorer optimization)
    if request.config.option.collectonly:
        yield
        return

    # CRITICAL FIX (2025-12-19): Skip for unit-only test runs
    # This prevents Qdrant connection attempts during unit tests
    if not _has_integration_tests(request):
        yield
        return

    # Initialize dirty flag at session level (tracks if collection was modified)
    if not hasattr(request.session, "_collection_dirty"):
        request.session._collection_dirty = False

    # Read-only tests: Skip all cleanup/restore (preserve_collection marker)
    # These tests don't care if collection is dirty - they just read
    if "preserve_collection" in request.keywords:
        yield  # Test runs - no cleanup needed (read-only)
        return

    # Tests that manage their own state: Mark dirty but don't restore yet (lazy restoration)
    manages_state = "manages_collection_state" in request.keywords

    if manages_state:
        # LAZY RESTORATION: Don't restore after this test, just mark dirty
        # Restoration will happen BEFORE the next test that needs clean state
        yield  # Test runs and modifies collection
        request.session._collection_dirty = True  # Mark dirty for lazy restoration
        return

    # --- Tests that need clean state (no marker) ---
    # Import Qdrant client and settings
    from raglite.shared.clients import get_qdrant_client
    from raglite.shared.config import settings

    # PERFORMANCE: Cache Qdrant client at session level to avoid reconnection overhead
    if not hasattr(request.session, "_cached_qdrant_client"):
        request.session._cached_qdrant_client = get_qdrant_client()

    qdrant = request.session._cached_qdrant_client

    # LAZY RESTORATION: Restore BEFORE this test if session is dirty
    # This batches all restorations - only restore when transitioning from dirty to clean
    if (
        request.session._collection_dirty
        and session_state.session_sample_pdf_chunk_count is not None
    ):
        print(
            f"\n🔄 [lazy restoration] Restoring session baseline BEFORE test: {request.node.name}"
        )
        _do_restoration(qdrant, settings)
        request.session._collection_dirty = False

    yield  # Test runs here

    # Check state after test - restore if unexpectedly modified
    try:
        final_count = qdrant.count(collection_name=settings.qdrant_collection_name).count

        # Only restore if count changed unexpectedly (test without marker modified data)
        if session_state.session_sample_pdf_chunk_count is not None:
            should_restore = final_count != session_state.session_sample_pdf_chunk_count
        else:
            # No baseline set yet - don't restore
            should_restore = False

        if should_restore:
            # Test modified Qdrant collection - restore to clean state
            print(
                f"\n🔄 Restoring Qdrant (current: {final_count} chunks, baseline: {session_state.session_sample_pdf_chunk_count})"
            )
            _do_restoration(qdrant, settings)

            # CRITICAL FIX: Also restore PostgreSQL data (symmetric database lifecycle)
            # PostgreSQL must be restored when Qdrant is restored to prevent test isolation failures
            # Root cause: Tests with clear_existing=True delete PostgreSQL, but only Qdrant was being restored
            # PERFORMANCE: All tests now have proper markers (preserve_collection or manages_collection_state)
            # This restoration only triggers for tests that actually modify collections
            if session_state.session_postgresql_row_count:
                print(
                    f"\n🔄 Checking PostgreSQL state (baseline: {session_state.session_postgresql_row_count} rows)..."
                )

                try:
                    from psycopg2.extras import RealDictCursor

                    from raglite.shared.clients import get_postgresql_connection

                    # PERFORMANCE: Use cached connection to reduce overhead
                    conn = get_postgresql_connection()
                    cursor = conn.cursor(cursor_factory=RealDictCursor)

                    # Check current PostgreSQL state
                    cursor.execute("SELECT COUNT(*) FROM financial_tables")
                    current_pg_count = cursor.fetchone()["count"]

                    # If PostgreSQL was cleared, restore it
                    if current_pg_count < session_state.session_postgresql_row_count:
                        print(
                            f"   ⚠️  PostgreSQL depleted: {current_pg_count} rows (expected {session_state.session_postgresql_row_count})"
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
                                restored_pg_count < session_state.session_postgresql_row_count * 0.9
                            ):  # Allow 10% tolerance
                                print(
                                    f"   ⚠️  PostgreSQL restoration incomplete: {restored_pg_count}/{session_state.session_postgresql_row_count} rows"
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
