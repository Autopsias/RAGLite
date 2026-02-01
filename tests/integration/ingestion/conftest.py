"""Shared fixtures for ingestion integration tests.

This conftest.py is intentionally minimal (fixtures shared from parent).

Marker Strategy:
- integration: All tests require Qdrant/PostgreSQL infrastructure
- preserve_collection: Read-only tests (skip cleanup overhead)
- slow: All ingestion tests involve PDF processing (>1s per test)

Why minimal?
- Shared database fixtures are loaded via pytest_plugins in tests/conftest.py
- Document fixtures are in tests/fixtures/sample_data.py
- This file only applies markers appropriate for ALL tests in ingestion/
"""

import pytest

# Mark all tests in this module as integration tests that preserve collection state by default
# Individual classes can override with @pytest.mark.manages_collection_state if they modify data
pytestmark = [pytest.mark.integration, pytest.mark.preserve_collection, pytest.mark.slow]


@pytest.fixture
def sample_pdf_path():
    """Path to sample 10-page PDF for ingestion tests."""
    from pathlib import Path

    pdf_path = Path("docs/sample pdf/sample_financial_report.pdf")
    if not pdf_path.exists():
        pytest.skip(f"Sample PDF not found: {pdf_path}")
    return str(pdf_path)
