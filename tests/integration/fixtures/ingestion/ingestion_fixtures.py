"""PDF ingestion fixture for integration tests.

Ingests test PDF once per session using production-proven session-scoped pattern.
"""

import os
import sys

import pytest

from raglite.shared.clients import get_qdrant_client
from raglite.shared.config import settings
from raglite.shared.safety import SafetyGuard

from .. import session_state
from .collection_helpers import (
    check_existing_collection,
    get_test_pdf_path,
    initialize_clean_collection,
    validate_test_environment,
)
from .skip_helpers import handle_skip_ingestion, should_skip_ingestion
from .verification_helpers import (
    create_collection_snapshot,
    execute_ingestion,
    verify_postgresql_data,
    verify_qdrant_data,
)


def print_session_start():
    """Print session fixture start message."""
    _session_pid = os.getpid()
    print(f"\n📊 SESSION FIXTURE START: PID={_session_pid}", file=sys.stderr)


def print_session_complete(request):
    """Print session fixture complete message."""
    print("\n✅ Session fixture complete:", file=sys.stderr)
    print(
        f"   Ready for {len(request.session.items) if hasattr(request.session, 'items') else '?'} tests",
        file=sys.stderr,
    )


def run_ingestion_pipeline(sample_pdf, use_full_pdf):
    """Execute the full ingestion pipeline.

    Args:
        sample_pdf: Path to test PDF
        use_full_pdf: Whether full PDF is being used

    Returns:
        tuple: (count_after, expected_range)
    """
    skip_metadata_extraction = not use_full_pdf
    if skip_metadata_extraction:
        print("   ℹ️  Skipping LLM metadata extraction (LOCAL mode)", file=sys.stderr)

    execute_ingestion(sample_pdf, skip_metadata_extraction)

    expected_range = (150, 220) if use_full_pdf else (10, 30)
    count_after = verify_qdrant_data(expected_range)

    verify_postgresql_data(use_full_pdf)

    return count_after, expected_range


@pytest.fixture(scope="session", autouse=True)
def session_ingested_collection(request, warmup_embedding_model):
    """Ingest test PDF once per session (Django/FastAPI pattern). Use --skip-ingestion to reuse existing data."""
    # Check if we should skip this fixture entirely
    should_skip, reason = should_skip_ingestion(request)
    if should_skip:
        if reason == "collectonly":
            yield
            return
        print(
            f"⚡ {reason.upper().replace('_', ' ')}: Skipping PDF ingestion fixture",
            file=sys.stderr,
        )
        yield
        return

    print_session_start()

    # Handle --skip-ingestion flag (reuse existing collection)
    if handle_skip_ingestion(request):
        yield
        return

    print("DEBUG: Proceeding with full ingestion", file=sys.stderr)

    # Validate test environment
    validate_test_environment()

    # Check existing collection
    check_existing_collection()

    # Get test PDF path
    sample_pdf, pdf_description, estimated_time = get_test_pdf_path()

    print(
        f"SESSION FIXTURE: Ingesting {pdf_description} ONCE (production pattern)", file=sys.stderr
    )

    # Initialize clean collection
    guard = SafetyGuard()
    initialize_clean_collection(guard)

    # Execute ingestion pipeline
    use_full_pdf = os.getenv("TEST_USE_FULL_PDF", "false").lower() == "true"
    run_ingestion_pipeline(sample_pdf, use_full_pdf)

    print_session_complete(request)

    # Create snapshot for fast restoration
    snapshot_name = create_collection_snapshot(estimated_time)
    session_state.session_snapshot_name = snapshot_name

    # Yield to tests
    qdrant = get_qdrant_client()
    yield

    # Cleanup
    try:
        qdrant.delete_collection(collection_name=settings.qdrant_collection_name)
    except Exception:
        pass
