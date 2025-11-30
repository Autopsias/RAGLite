"""Unit tests for scripts/generate_failure_report.py - failure analysis utilities.

Tests cover:
- Failure categorization logic
- Actionable insight generation
- Category classification accuracy
"""

import importlib.util
import sys
from pathlib import Path

import pytest

# Import script with hyphenated name using importlib
script_path = Path(__file__).parent.parent.parent / "scripts" / "generate_failure_report.py"
spec = importlib.util.spec_from_file_location("generate_failure_report", script_path)
generate_failure_report = importlib.util.module_from_spec(spec)
sys.modules["generate_failure_report"] = generate_failure_report
spec.loader.exec_module(generate_failure_report)


class TestCategorizeFailure:
    """Test failure categorization logic."""

    def test_categorize_timeout_failures(self) -> None:
        """Test that timeout-related failures are categorized as 'timeout'."""
        assert generate_failure_report.categorize_failure("Query timeout after 30s") == "timeout"
        assert (
            generate_failure_report.categorize_failure("Execution time exceeded limit") == "timeout"
        )
        assert generate_failure_report.categorize_failure("TIMEOUT ERROR") == "timeout"

    def test_categorize_llm_api_failures(self) -> None:
        """Test that LLM/API failures are categorized as 'llm_api_error'."""
        assert (
            generate_failure_report.categorize_failure("Claude API rate limit") == "llm_api_error"
        )
        assert (
            generate_failure_report.categorize_failure("LLM generation failed") == "llm_api_error"
        )
        assert (
            generate_failure_report.categorize_failure("API connection refused") == "llm_api_error"
        )

    def test_categorize_retrieval_failures(self) -> None:
        """Test that retrieval failures are categorized as 'retrieval_failure'."""
        assert (
            generate_failure_report.categorize_failure("Qdrant connection lost")
            == "retrieval_failure"
        )
        assert (
            generate_failure_report.categorize_failure("PostgreSQL query error")
            == "retrieval_failure"
        )
        assert (
            generate_failure_report.categorize_failure("Retrieval returned no results")
            == "retrieval_failure"
        )

    def test_categorize_accuracy_failures(self) -> None:
        """Test that accuracy issues are categorized as 'accuracy_issue'."""
        assert (
            generate_failure_report.categorize_failure("Answer accuracy below threshold")
            == "accuracy_issue"
        )
        assert (
            generate_failure_report.categorize_failure("Missing citations in response")
            == "accuracy_issue"
        )
        assert (
            generate_failure_report.categorize_failure("Accuracy validation failed")
            == "accuracy_issue"
        )

    def test_categorize_unknown_failures(self) -> None:
        """Test that unknown failures are categorized as 'other'."""
        assert generate_failure_report.categorize_failure("Unknown error occurred") == "other"
        assert generate_failure_report.categorize_failure("Unexpected exception") == "other"
        assert generate_failure_report.categorize_failure("") == "other"

    def test_categorize_case_insensitive(self) -> None:
        """Test that categorization is case-insensitive."""
        assert generate_failure_report.categorize_failure("TIMEOUT ERROR") == "timeout"
        assert generate_failure_report.categorize_failure("llm api failure") == "llm_api_error"
        assert generate_failure_report.categorize_failure("RETRIEVAL FAILED") == "retrieval_failure"

    def test_categorize_partial_matches(self) -> None:
        """Test that categorization works with partial keyword matches."""
        # Timeout matches "time" keyword
        assert generate_failure_report.categorize_failure("Response time too slow") == "timeout"
        # API matches llm_api_error
        assert generate_failure_report.categorize_failure("External API failed") == "llm_api_error"


class TestGetActionableInsight:
    """Test actionable insight generation."""

    def test_insight_for_timeout(self) -> None:
        """Test actionable insight for timeout failures."""
        insight = generate_failure_report.get_actionable_insight("timeout", "Query timeout")
        assert "Optimize agent latency" in insight
        assert "Parallel retrieval" in insight
        assert "Claude Haiku" in insight

    def test_insight_for_llm_api_error(self) -> None:
        """Test actionable insight for LLM API errors."""
        insight = generate_failure_report.get_actionable_insight("llm_api_error", "API failed")
        assert "LLM API failures gracefully" in insight
        assert "Retry logic" in insight
        assert "exponential backoff" in insight

    def test_insight_for_retrieval_failure(self) -> None:
        """Test actionable insight for retrieval failures."""
        insight = generate_failure_report.get_actionable_insight(
            "retrieval_failure", "Qdrant error"
        )
        assert "retrieval reliability" in insight
        assert "Connection pooling" in insight
        assert "Retry transient errors" in insight

    def test_insight_for_accuracy_issue(self) -> None:
        """Test actionable insight for accuracy issues."""
        insight = generate_failure_report.get_actionable_insight("accuracy_issue", "Answer wrong")
        assert "workflow accuracy" in insight
        assert "agent prompts" in insight
        assert "cross-encoder re-ranking" in insight

    def test_insight_for_other_category(self) -> None:
        """Test actionable insight for unknown failures."""
        insight = generate_failure_report.get_actionable_insight("other", "Unknown error")
        assert "Review error logs" in insight
        assert "stack trace" in insight
        assert "bug report" in insight

    def test_insight_default_fallback(self) -> None:
        """Test that unknown categories fall back to 'other' insight."""
        insight = generate_failure_report.get_actionable_insight("invalid_category", "error")
        assert "Review error logs" in insight  # Same as "other" category

    def test_insights_contain_multiple_recommendations(self) -> None:
        """Test that insights provide multiple actionable recommendations."""
        for category in ["timeout", "llm_api_error", "retrieval_failure", "accuracy_issue"]:
            insight = generate_failure_report.get_actionable_insight(category, "test error")
            # Each insight should have numbered recommendations (1), (2), (3), etc.
            assert "(1)" in insight
            assert "(2)" in insight
            # Most have 4 recommendations
            if category != "other":
                assert "(3)" in insight


class TestEndToEndCategorization:
    """Test end-to-end failure categorization + insight generation."""

    @pytest.mark.parametrize(
        "failure_reason,expected_category,expected_insight_keywords",
        [
            (
                "Workflow timeout after 45 seconds",
                "timeout",
                ["Optimize", "Parallel", "Haiku"],
            ),
            (
                "Claude API rate limit exceeded (429)",
                "llm_api_error",
                ["Retry", "backoff", "circuit breaker"],
            ),
            (
                "PostgreSQL connection pool exhausted",
                "retrieval_failure",
                ["Connection pooling", "Retry", "database health"],
            ),
            (
                "Answer accuracy 75% below 90% threshold",
                "accuracy_issue",
                ["accuracy", "prompts", "re-ranking"],
            ),
            (
                "Memory allocation failed",
                "other",
                ["Review error logs", "stack trace"],
            ),
        ],
    )
    def test_categorization_and_insight_flow(
        self,
        failure_reason: str,
        expected_category: str,
        expected_insight_keywords: list[str],
    ) -> None:
        """Test complete flow: failure reason → category → actionable insight."""
        category = generate_failure_report.categorize_failure(failure_reason)
        assert category == expected_category

        insight = generate_failure_report.get_actionable_insight(category, failure_reason)
        for keyword in expected_insight_keywords:
            assert keyword in insight


class TestModuleFunctions:
    """Test that required module functions exist."""

    def test_categorize_failure_function_exists(self) -> None:
        """Test that categorize_failure function is callable."""
        assert callable(generate_failure_report.categorize_failure)

    def test_get_actionable_insight_function_exists(self) -> None:
        """Test that get_actionable_insight function is callable."""
        assert callable(generate_failure_report.get_actionable_insight)

    def test_categorize_failure_signature(self) -> None:
        """Test categorize_failure accepts string and returns string."""
        result = generate_failure_report.categorize_failure("test")
        assert isinstance(result, str)

    def test_get_actionable_insight_signature(self) -> None:
        """Test get_actionable_insight accepts two strings and returns string."""
        result = generate_failure_report.get_actionable_insight("timeout", "test error")
        assert isinstance(result, str)
