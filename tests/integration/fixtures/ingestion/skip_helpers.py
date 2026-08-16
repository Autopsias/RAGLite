"""Helper functions for skip logic in session_ingested_collection fixture."""

import sys

from ..test_detection import has_integration_tests, is_postgresql_only_tests


def should_skip_ingestion(request) -> tuple[bool, str | None]:
    """Check if ingestion should be skipped based on test configuration.

    Args:
        request: pytest request object

    Returns:
        Tuple of (should_skip, reason) where reason is None if not skipping
    """
    # Skip for collection-only runs
    if request.config.option.collectonly:
        return True, "collectonly"

    # PERFORMANCE FIX (2025-12-18): Skip for unit-only test runs
    if not has_integration_tests(request):
        return True, "unit tests only"

    # PERFORMANCE FIX (2025-12-21): Skip for PostgreSQL-only tests
    if is_postgresql_only_tests(request):
        return True, "postgresql only tests"

    return False, None


def handle_skip_ingestion(request):
    """Handle --skip-ingestion flag by reusing existing collection data.

    Args:
        request: pytest request object

    Returns:
        bool: True if skip was successful and fixture should yield immediately
    """
    skip_ingestion = request.config.getoption("--skip-ingestion")
    if not skip_ingestion:
        return False

    from raglite.shared.clients import get_qdrant_client
    from raglite.shared.config import settings

    from .. import session_state

    qdrant = get_qdrant_client()

    try:
        count = qdrant.count(collection_name=settings.qdrant_collection_name).count
        if count == 0:
            print(
                "⚠️  --skip-ingestion IGNORED: Collection empty. Proceeding with ingestion.",
                file=sys.stderr,
            )
            return False
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

            # Create mock result
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
            return True
    except Exception as e:
        print(f"⚠️  --skip-ingestion failed: {e}. Falling back to ingestion.", file=sys.stderr)
        return False
