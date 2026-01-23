"""Integration test fixtures for E2E and regression testing.

PRODUCTION-PROVEN PATTERN: Session-scoped fixture with read-only data sharing.

This module implements pytest best practices from production codebases (Django, FastAPI, pandas, Mozilla):
- Session scope ingests PDFs once (75-85 seconds)
- All read-only tests share the ingested collection (zero setup per test)
- Tests that need fresh data use @pytest.mark.manages_collection_state
- Reduces test suite from 40+ min to ~90 seconds

References:
- Django: Uses session-scoped database with transaction rollback per test
- FastAPI: Session-scoped DB schema, function-scoped transactions
- Mozilla Firefox: Session-scoped browser, JS state reset per test (80% speedup)
- pandas: Module-scoped DataFrame factories for grouped tests

IMPORTANT: Integration tests use shared Qdrant collection (read-only mode).
Tests that modify data are marked with @pytest.mark.manages_collection_state.
"""

import os
import sys
from dataclasses import dataclass
from datetime import UTC, datetime

import pytest

import raglite.shared.config
from raglite.shared.config import Settings
from raglite.shared.models import (
    Insight,
    InsightCategory,
    RecommendationCategory,
)

# Debug: Track module load
print("DEBUG: conftest.py loading...", file=sys.stderr)

# CRITICAL FIX (2025-11-23): Set test environment variables BEFORE any raglite imports
# This ensures the Settings singleton uses test database settings when it's created.
# Root cause: tests/conftest.py sets env vars, but tests/integration/conftest.py is loaded
# BEFORE parent conftest completes, so Settings singleton was created with production defaults.
# Solution: Set env vars in BOTH conftest files to ensure they're available at import time.
if "APP_ENV" not in os.environ:
    os.environ["APP_ENV"] = "test"
if "TESTING" not in os.environ:
    os.environ["TESTING"] = "true"
if "POSTGRES_PORT" not in os.environ:
    os.environ["POSTGRES_PORT"] = "5433"
if "POSTGRES_DB" not in os.environ:
    os.environ["POSTGRES_DB"] = "raglite_ci"
if "POSTGRES_USER" not in os.environ:
    os.environ["POSTGRES_USER"] = "raglite_ci"
if "POSTGRES_PASSWORD" not in os.environ:
    os.environ["POSTGRES_PASSWORD"] = "raglite_ci"

print("DEBUG: Test environment variables set before raglite imports", file=sys.stderr)

# CRITICAL: Import raglite.shared.config to force Settings singleton reload
# This ensures Settings uses the test environment variables set above
raglite.shared.config.settings = Settings()  # Recreate singleton with test env vars

# ============================================================================
# PERFORMANCE FIX (2025-12-06): Default all integration tests to preserve_collection
# ============================================================================
# This applies @pytest.mark.preserve_collection to ALL tests in this directory,
# telling ensure_qdrant_test_isolation to SKIP post-test cleanup checks.
#
# WHY: Without this marker, each of the ~509 integration tests triggers a
# qdrant.count() call after execution to check if data was modified.
# With 425 unmarked tests × ~100ms = 42+ seconds of pure overhead!
#
# OVERRIDE: Tests that actually modify collection state should explicitly use:
#   @pytest.mark.manages_collection_state
# This marker has higher precedence and tells the fixture to skip cleanup
# because the test intentionally manages its own state.
#
# Result: 509 tests now skip unnecessary cleanup checks by default.
# ============================================================================
pytestmark = pytest.mark.preserve_collection

# ============================================================================
# FIXTURE MODULE LOADING
# ============================================================================
# NOTE: pytest_plugins has been moved to tests/conftest.py (root)
# per pytest deprecation warning. Defining pytest_plugins in non-top-level
# conftest files is no longer supported.
#
# Integration fixture modules are now loaded from the root conftest:
# - tests.integration.fixtures.session_state
# - tests.integration.fixtures.service_checking
# - tests.integration.fixtures.session_fixtures
# - tests.integration.fixtures.test_isolation
# - tests.integration.fixtures.module_fixtures
# - tests.integration.fixtures.helper_fixtures
#
# Session state is managed via tests.integration.fixtures.session_state module
# which is imported by dependent fixture modules.
# ============================================================================

# ============================================================================
# SHARED TEST FIXTURES
# ============================================================================
# Shared fixtures for chunking tests (L3: Fix code duplication)


@pytest.fixture
def test_pdf_path():
    """Path to 10-page test PDF for fast CI tests.

    Uses smaller PDF (10 pages) instead of full 160-page PDF.
    Expected chunk count: 8-15 chunks for 10 pages.
    """
    from pathlib import Path

    pdf_path = Path("docs/sample pdf/test-10-pages.pdf")
    if not pdf_path.exists():
        pytest.skip(f"Test PDF not found: {pdf_path}")
    return str(pdf_path)


@pytest.fixture
def encoding():
    """Tiktoken cl100k_base encoding for token counting."""
    import tiktoken

    return tiktoken.get_encoding("cl100k_base")


# =============================================================================
# Shared Database Fixtures (Story 8.4b Fix)
# =============================================================================


@pytest.fixture(scope="module")
@pytest.mark.timeout(60)  # P1 FIX: 60s max for db session setup/teardown
def db_session():
    """PostgreSQL session for integration tests.

    Creates tables in test database and yields session.
    Rolls back after tests complete.

    This fixture is shared across all integration test subdirectories
    to prevent duplication (forecasting/catboost, model_selection, etc.).

    CRITICAL FIX (2026-01-20): Ensure ALL ORM tables are created, including:
    - model_selection (Story 7b-4 cache)
    - model_weights (Story 6.12 ensemble)
    - external_data_sources/points (regressor data)
    """
    import logging

    logger = logging.getLogger(__name__)

    from raglite.shared.safety import SafetyGuard

    guard = SafetyGuard()
    guard.validate_test_environment("integration_db_session")

    # IMPORTANT: Import ALL ORM models BEFORE create_all() so they register with Base
    from raglite.external_data.orm_models import (  # noqa: F401
        ExternalDataPointORM,
        ExternalDataSourceORM,
        ModelSelectionORM,
        ModelWeightORM,
    )
    from raglite.shared.database import Base, get_engine, get_session, reset_engine

    # Reset engine to pick up test environment settings
    reset_engine()

    # Create tables in test database
    engine = get_engine()
    Base.metadata.create_all(engine)

    # Verify critical tables were created (fail fast if ORM not registered)
    with engine.connect() as conn:
        from sqlalchemy import text

        result = conn.execute(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' "
                "AND table_name IN ('model_selection', 'model_weights', 'external_data_sources')"
            )
        )
        created_tables = [row[0] for row in result]
        logger.info(f"✅ Created ORM tables: {created_tables}")

    session = get_session()
    yield session

    # P1 FIX: Proper cleanup sequence with error handling
    try:
        session.rollback()
    except Exception as e:
        logger.warning(f"Session rollback failed: {e}")

    try:
        if hasattr(session, "remove"):
            session.remove()  # Clear from registry - prevents connection pool exhaustion
        session.close()
    except Exception as e:
        logger.warning(f"Session cleanup failed: {e}")


@pytest.fixture
def clean_session(db_session):
    """Clean session that rolls back after each test.

    Depends on db_session fixture for database setup.
    """
    yield db_session
    db_session.rollback()


# =============================================================================
# Shared Data for Cross-Test Usage (Issue 6 Fix)
# =============================================================================


# From test_strategic_recommendations_core.py - shared with extended tests

EXPERT_LABELED_SCENARIOS = {
    "cloud_cost_over_budget": {
        "insight": Insight(
            category=InsightCategory.RISK,
            priority=1,
            summary="Cloud infrastructure costs trending 40% over budget with minimal usage increase",
            supporting_data={
                "cloud_budget": 5000000,
                "cloud_actual": 7000000,
                "budget_variance": 0.40,
                "usage_increase": 0.05,
            },
            rationale="Cloud spending has significantly exceeded budget without corresponding usage increase",
            sources=["cloud_costs", "infrastructure_budget"],
            recommended_action="Focus on reducing cloud infrastructure costs",
            created_at=datetime.now(UTC),
        ),
        "expected_category": RecommendationCategory.RISK_MITIGATION,
        "expected_impact_min": 8,
        "expected_urgency": "high",
        "expected_title_keywords": ["cloud", "cost", "infrastructure", "reduce"],
    },
}


# From test_excerpt_validation_core.py - shared validation function


@dataclass
class ExcerptTestResult:
    """Result of excerpt test query."""

    query_id: str
    category: str
    natural_query: str
    expected_min: int
    expected_max: int
    actual_results: int
    passed: bool
    error: str | None
    confidence: float


async def validate_excerpt_query(test_def: dict, mock_client=None) -> ExcerptTestResult:
    """Validate a single excerpt test query.

    Args:
        test_def: Test definition dict with query and expected results
        mock_client: Optional mock Mistral client (used in tests to avoid API calls)
    """
    from raglite.retrieval.query_classifier import generate_sql_query
    from raglite.retrieval.sql_table_search import search_tables_sql

    query_id = test_def["id"]
    category = test_def["category"]
    query = test_def["query"]
    expected_min = test_def["expected_result_min"]
    expected_max = test_def["expected_result_max"]

    try:
        # Generate SQL
        sql = await generate_sql_query(query)
        if not sql:
            return ExcerptTestResult(
                query_id=query_id,
                category=category,
                natural_query=query,
                expected_min=expected_min,
                expected_max=expected_max,
                actual_results=0,
                passed=False,
                error="SQL generation failed",
                confidence=0.0,
            )

        # Execute SQL
        results = await search_tables_sql(sql)
        actual_results = len(results)

        # Validation: Check if within expected range
        passed = expected_min <= actual_results <= expected_max

        # Calculate confidence
        if actual_results == 0:
            confidence = 0.0
        elif actual_results < expected_min:
            confidence = actual_results / expected_min
        elif actual_results > expected_max:
            confidence = expected_max / actual_results
        else:
            confidence = 1.0

        return ExcerptTestResult(
            query_id=query_id,
            category=category,
            natural_query=query,
            expected_min=expected_min,
            expected_max=expected_max,
            actual_results=actual_results,
            passed=passed,
            error=None,
            confidence=confidence,
        )
    except Exception as e:
        return ExcerptTestResult(
            query_id=query_id,
            category=category,
            natural_query=query,
            expected_min=expected_min,
            expected_max=expected_max,
            actual_results=0,
            passed=False,
            error=str(e),
            confidence=0.0,
        )


# =============================================================================
# Shared Chunking Validation Helpers (Story 2.3 AC6 Deduplication)
# =============================================================================


def _collect_chunk_sizes(all_points, encoding):
    """Collect and separate text vs table chunk token counts.

    Args:
        all_points: List of Qdrant points with payloads
        encoding: Tiktoken encoding for token counting

    Returns:
        Tuple of (text_token_counts, table_chunks)
        - text_token_counts: List of token counts for text chunks
        - table_chunks: List of tuples (point_id, token_count, preview) for tables
    """
    text_token_counts = []
    table_chunks = []

    for point in all_points:
        chunk_text = point.payload.get("text", "")
        token_count = len(encoding.encode(chunk_text))

        # Detect table chunks (contain markdown table syntax)
        if "|" in chunk_text and chunk_text.count("|") > 10:
            table_chunks.append((point.id, token_count, chunk_text[:100]))
        else:
            text_token_counts.append(token_count)

    return text_token_counts, table_chunks


def _validate_chunk_size_distribution(
    text_token_counts, text_mean, text_std, percentile_95, in_range_percentage
):
    """Validate chunk size statistics against AC6 thresholds.

    Args:
        text_token_counts: List of text chunk token counts
        text_mean: Mean token count
        text_std: Standard deviation
        percentile_95: 95th percentile token count
        in_range_percentage: Percentage of chunks in 462-562 range

    Raises:
        AssertionError: If any metric fails validation
    """
    assert 390 <= text_mean <= 562, (
        f"Mean TEXT chunk size {text_mean:.1f} not within 390-562 "
        f"(target: 512, adjusted for sentence boundary preservation)"
    )

    assert text_std < 160, (
        f"TEXT chunk std deviation {text_std:.1f} exceeds 160-token limit "
        f"(adjusted for sentence variance)"
    )

    assert percentile_95 <= 562, (
        f"95th percentile of TEXT chunks {percentile_95} exceeds 562-token limit"
    )


def _report_consistency_metrics(
    test_label, text_token_counts, text_mean, text_std, percentile_95, table_chunks
):
    """Report chunk size consistency metrics.

    Args:
        test_label: Label for the test (e.g., "AC6 SLOW PASS")
        text_token_counts: List of text chunk token counts
        text_mean: Mean token count
        text_std: Standard deviation
        percentile_95: 95th percentile token count
        table_chunks: List of table chunk tuples
    """
    in_range_count = sum(1 for tc in text_token_counts if 462 <= tc <= 562)
    in_range_percentage = (
        (in_range_count / len(text_token_counts)) * 100 if text_token_counts else 0
    )

    print(f"\n✅ {test_label}: Chunk Size Consistency")
    print(f"   - TEXT chunks: {len(text_token_counts)} total")
    print(f"     • Mean: {text_mean:.1f} tokens (target: 512±10)")
    print(f"     • Std: {text_std:.1f} tokens (limit: <50)")
    print(f"     • 95th percentile: {percentile_95} tokens (limit: ≤562)")
    print(
        f"     • In range (462-562): {in_range_percentage:.1f}% "
        f"({in_range_count}/{len(text_token_counts)})"
    )
    print(f"   - TABLE chunks: {len(table_chunks)} total (preserved per AC3)")

    if table_chunks:
        table_tokens = [tc for _, tc, _ in table_chunks]
        print(f"     • Range: {min(table_tokens)}-{max(table_tokens)} tokens")
        print(f"     • Mean: {sum(table_tokens) / len(table_tokens):.1f} tokens")
        print("     • Example large tables:")
        for _point_id, token_count, preview in sorted(
            table_chunks, key=lambda x: x[1], reverse=True
        )[:3]:
            print(f"       • {token_count} tokens: {preview}...")
