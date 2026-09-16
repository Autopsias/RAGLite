"""Shared fixtures for Story 2.14 validation tests."""

import json
from dataclasses import dataclass
from pathlib import Path

import pytest


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


@pytest.fixture(scope="session")
def excerpt_ground_truth():
    """Load excerpt-specific ground truth from JSON file."""
    ground_truth_path = (
        Path(__file__).parent.parent.parent.parent
        / "docs/validation/story-2.14-excerpt-ground-truth.json"
    )
    with open(ground_truth_path) as f:
        return json.load(f)


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
        elif passed:
            # Calculate how close to middle of range
            range_mid = (expected_min + expected_max) / 2
            deviation = abs(actual_results - range_mid) / range_mid
            confidence = max(0.8, 1.0 - (deviation * 0.2))
        else:
            confidence = 0.2

        return ExcerptTestResult(
            query_id=query_id,
            category=category,
            natural_query=query,
            expected_min=expected_min,
            expected_max=expected_max,
            actual_results=actual_results,
            passed=passed,
            error=None,
            confidence=min(confidence, 1.0),
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
