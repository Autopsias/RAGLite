"""Test isolation fixture with lazy restoration (P0 strategic fix).

This fixture implements lazy Qdrant collection restoration to prevent O(N)
restoration overhead while maintaining test isolation.

Root Cause (Story 8 Analysis):
- Previous implementation: restore after EVERY manages_collection_state test
- With 509 tests, this caused 42+ seconds of pure restoration overhead
- State transitions are rare (<5%), making per-test restoration wasteful

Lazy Restoration Pattern:
1. preserve_collection tests: Skip ALL cleanup checks (default for ~425 tests)
2. manages_collection_state tests: Mark dirty, defer restoration
3. Other tests: Restore BEFORE if dirty, check AFTER for unexpected changes

Performance Impact:
- Before: O(N) restorations where N = number of managing tests (~50)
- After: O(transitions) restorations where transitions << N (~2-5)
- Result: 42+ seconds saved per test run

Fixture: ensure_qdrant_test_isolation
    Autouse fixture that enforces test isolation with lazy restoration.
    Uses session_state globals to track baseline and restoration needs.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from qdrant_client import QdrantClient

# Import session state tracking
from . import session_state

# Lazy imports (after service check)
# from raglite.shared.config import settings
# from raglite.shared.safety import SafetyGuard


@pytest.fixture(autouse=True)
def ensure_qdrant_test_isolation(request):
    """Ensure Qdrant collection isolation with lazy restoration (P0 fix).

    This fixture implements lazy restoration pattern:
    - preserve_collection tests (default): Skip all cleanup
    - manages_collection_state tests: Mark dirty, defer restoration
    - Other tests: Restore BEFORE first test after dirty state

    Args:
        request: pytest fixture request (for markers)

    Yields:
        None (autouse fixture applies to all tests)
    """
    # Skip for unit tests (no Qdrant dependency)
    if "integration" not in str(request.node.fspath):
        yield
        return

    # Check markers
    markers = [m.name for m in request.node.iter_markers()]
    preserve_collection = "preserve_collection" in markers
    manages_collection = "manages_collection_state" in markers

    # Lazy imports (only if integration test)
    from raglite.shared.config import settings
    from raglite.shared.safety import SafetyGuard

    guard = SafetyGuard()
    guard.validate_test_environment("ensure_qdrant_test_isolation")

    from qdrant_client import QdrantClient

    qdrant = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)

    # LAZY RESTORATION: Only restore if previous test marked state dirty
    needs_restoration = getattr(session_state, "session_collection_dirty", False)

    if needs_restoration and not manages_collection:
        # First clean-state test after managing test: RESTORE NOW
        if session_state.session_snapshot_name:
            _restore_from_snapshot(qdrant, session_state.session_snapshot_name)
            session_state.session_collection_dirty = False
        elif session_state.session_sample_pdf_chunk_count:
            _restore_by_reingestion(request)
            session_state.session_collection_dirty = False

    # Execute test
    yield

    # POST-TEST: Mark dirty if test manages collection state
    if manages_collection:
        session_state.session_collection_dirty = True
        # No restoration here - deferred to next clean-state test

    # POST-TEST: Validate no unexpected changes (for unmarked tests)
    if not preserve_collection and not manages_collection:
        _validate_no_unexpected_changes(qdrant, request.node.name)


def _restore_from_snapshot(qdrant: QdrantClient, snapshot_name: str) -> None:
    """Restore Qdrant collection from snapshot.

    Args:
        qdrant: Qdrant client
        snapshot_name: Snapshot filename to restore
    """
    from raglite.shared.config import settings

    collection_name = settings.qdrant_collection

    try:
        # Delete existing collection
        qdrant.delete_collection(collection_name)

        # Restore from snapshot
        qdrant.recover_collection(
            collection_name=collection_name,
            snapshot_name=snapshot_name,
        )

        print(f"[ensure_qdrant_test_isolation] Restored from snapshot: {snapshot_name}")
    except Exception as e:
        print(f"[ensure_qdrant_test_isolation] Snapshot restore failed: {e}")


def _restore_by_reingestion(request) -> None:
    """Restore by re-ingesting session PDF (fallback if no snapshot).

    Args:
        request: pytest fixture request (for session fixtures)
    """
    print("[ensure_qdrant_test_isolation] No snapshot available, marking for re-ingestion")

    # Set flag to trigger re-ingestion in session_ingested_collection fixture
    session_state.session_needs_reingestion = True


def _validate_no_unexpected_changes(qdrant: QdrantClient, test_name: str) -> None:
    """Validate that test didn't unexpectedly modify collection.

    Args:
        qdrant: Qdrant client
        test_name: Test name (for logging)
    """
    from raglite.shared.config import settings

    collection_name = settings.qdrant_collection
    baseline_count = session_state.session_sample_pdf_chunk_count

    if baseline_count is None:
        return  # No baseline set yet

    try:
        current_count = qdrant.count(collection_name).count

        if current_count != baseline_count:
            print(
                f"[ensure_qdrant_test_isolation] WARNING: {test_name} "
                f"modified chunk count: {baseline_count} -> {current_count}. "
                f"Consider adding @pytest.mark.preserve_collection or "
                f"@pytest.mark.manages_collection_state"
            )
    except Exception as e:
        print(f"[ensure_qdrant_test_isolation] Validation failed: {e}")
