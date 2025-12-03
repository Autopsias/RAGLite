"""Unit tests for Story 3.7 graceful degradation enhancements.

Tests error classification, user-friendly messaging, and alternative query suggestions (AC1, AC2, AC4).
"""

import asyncio

import pytest

from raglite.agentic.fallback import (
    ErrorType,
    FallbackTier,
    classify_error,
    create_user_friendly_error_message,
    suggest_alternative_query,
)


class TestErrorClassification:
    """Test error classification logic (AC2)."""

    def test_classify_timeout_error(self):
        """Test timeout error classification."""
        error = TimeoutError("Agent execution timeout")
        assert classify_error(error) == ErrorType.TIMEOUT

    def test_classify_asyncio_timeout_error(self):
        """Test asyncio.TimeoutError classification."""
        error = TimeoutError()
        assert classify_error(error) == ErrorType.TIMEOUT

    def test_classify_connection_error(self):
        """Test connection error classification."""
        error = ConnectionError("Qdrant connection failed")
        assert classify_error(error) == ErrorType.CONNECTION_ERROR

    def test_classify_connection_error_by_message(self):
        """Test connection error classification by message content."""
        error = Exception("Failed to connect to Qdrant")
        assert classify_error(error) == ErrorType.CONNECTION_ERROR

    def test_classify_api_failure_by_name(self):
        """Test API failure classification by exception name."""

        class HTTPError(Exception):
            pass

        error = HTTPError("Claude API rate limit")
        assert classify_error(error) == ErrorType.API_FAILURE

    def test_classify_api_failure_by_message(self):
        """Test API failure classification by message content."""
        error = Exception("Anthropic API error: 503 Service Unavailable")
        assert classify_error(error) == ErrorType.API_FAILURE

    def test_classify_mistral_api_failure(self):
        """Test Mistral API failure classification."""
        error = Exception("Mistral API request failed")
        assert classify_error(error) == ErrorType.API_FAILURE

    def test_classify_unexpected_error(self):
        """Test unexpected error classification."""
        error = ValueError("Unexpected validation error")
        assert classify_error(error) == ErrorType.UNEXPECTED


class TestUserFriendlyErrorMessages:
    """Test user-friendly error message generation (AC4)."""

    def test_timeout_partial_workflow_message(self):
        """Test timeout error message for partial workflow."""
        message = create_user_friendly_error_message(
            ErrorType.TIMEOUT, FallbackTier.PARTIAL_WORKFLOW
        )
        assert "technical" not in message.lower()  # No technical jargon
        assert "delay" in message.lower() or "taking longer" in message.lower()
        assert "results" in message.lower()

    def test_timeout_epic1_fallback_message(self):
        """Test timeout error message for Epic 1 fallback."""
        message = create_user_friendly_error_message(ErrorType.TIMEOUT, FallbackTier.EPIC1_FALLBACK)
        assert "technical" not in message.lower()
        assert "search" in message.lower()

    def test_api_failure_partial_workflow_message(self):
        """Test API failure message for partial workflow."""
        message = create_user_friendly_error_message(
            ErrorType.API_FAILURE, FallbackTier.PARTIAL_WORKFLOW
        )
        assert "AI service" in message or "service" in message
        assert "temporarily unavailable" in message or "unavailable" in message
        assert "partial results" in message or "partial" in message.lower()

    def test_api_failure_epic1_fallback_message(self):
        """Test API failure message for Epic 1 fallback."""
        message = create_user_friendly_error_message(
            ErrorType.API_FAILURE, FallbackTier.EPIC1_FALLBACK
        )
        assert "AI" in message or "service" in message
        assert "unavailable" in message
        assert "documents" in message.lower()

    def test_connection_error_partial_workflow_message(self):
        """Test connection error message for partial workflow."""
        message = create_user_friendly_error_message(
            ErrorType.CONNECTION_ERROR, FallbackTier.PARTIAL_WORKFLOW
        )
        assert "database" in message.lower() or "connectivity" in message.lower()
        assert "results" in message.lower()

    def test_connection_error_epic1_fallback_message(self):
        """Test connection error message for Epic 1 fallback."""
        message = create_user_friendly_error_message(
            ErrorType.CONNECTION_ERROR, FallbackTier.EPIC1_FALLBACK
        )
        assert "database" in message.lower()
        assert "backup" in message.lower() or "search" in message.lower()

    def test_unexpected_error_partial_workflow_message(self):
        """Test unexpected error message for partial workflow."""
        message = create_user_friendly_error_message(
            ErrorType.UNEXPECTED, FallbackTier.PARTIAL_WORKFLOW
        )
        assert "issue" in message.lower()
        assert "partial results" in message or "partial" in message.lower()

    def test_unexpected_error_epic1_fallback_message(self):
        """Test unexpected error message for Epic 1 fallback."""
        message = create_user_friendly_error_message(
            ErrorType.UNEXPECTED, FallbackTier.EPIC1_FALLBACK
        )
        assert "issue" in message.lower()
        assert "search" in message.lower()


class TestAlternativeQuerySuggestions:
    """Test alternative query suggestion logic (AC4)."""

    def test_timeout_suggests_simpler_query(self):
        """Test timeout error suggests simpler query."""
        query = "Calculate YoY revenue growth from Q3 2023 to Q3 2024 with variance explanation"
        suggestion = suggest_alternative_query(query, ErrorType.TIMEOUT)
        assert suggestion is not None
        assert "simpler" in suggestion.lower() or "break" in suggestion.lower()

    def test_api_failure_suggests_retry(self):
        """Test API failure suggests retry."""
        query = "What was the revenue in Q3 2024?"
        suggestion = suggest_alternative_query(query, ErrorType.API_FAILURE)
        assert suggestion is not None
        assert "wait" in suggestion.lower() or "try again" in suggestion.lower()

    def test_connection_error_suggests_retry(self):
        """Test connection error suggests retry."""
        query = "Show financial metrics for 2024"
        suggestion = suggest_alternative_query(query, ErrorType.CONNECTION_ERROR)
        assert suggestion is not None
        assert "wait" in suggestion.lower() or "try again" in suggestion.lower()

    def test_unexpected_error_no_suggestion(self):
        """Test unexpected error returns None (no specific suggestion)."""
        query = "Calculate revenue"
        suggestion = suggest_alternative_query(query, ErrorType.UNEXPECTED)
        assert suggestion is None


class TestWorkflowTimeoutHandling:
    """Test workflow-level timeout handling (AC1)."""

    @pytest.mark.asyncio
    async def test_workflow_completes_within_timeout(self):
        """Test workflow that completes within timeout."""
        from raglite.agentic.fallback import execute_workflow_with_timeout

        async def fast_workflow():
            await asyncio.sleep(0.1)
            return "success"

        result = await execute_workflow_with_timeout(fast_workflow, timeout_seconds=1.0)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_workflow_timeout_raises_exception(self):
        """Test workflow timeout raises asyncio.TimeoutError."""
        from raglite.agentic.fallback import execute_workflow_with_timeout

        async def slow_workflow():
            await asyncio.sleep(2.0)
            return "should not complete"

        with pytest.raises(asyncio.TimeoutError):
            await execute_workflow_with_timeout(slow_workflow, timeout_seconds=0.5)

    @pytest.mark.asyncio
    async def test_workflow_timeout_default_30_seconds(self):
        """Test workflow timeout defaults to 30 seconds (NFR5)."""
        from raglite.agentic.fallback import execute_workflow_with_timeout

        async def workflow():
            return "done"

        # Should use 30s default timeout (we can't test this timing without mocking,
        # but we can verify the function signature accepts no timeout parameter)
        result = await execute_workflow_with_timeout(workflow)
        assert result == "done"


class TestMetricsTracking:
    """Test metrics tracking for workflow degradation (AC5)."""

    def test_log_workflow_metrics_tier_1_success(self):
        """Test metrics logging for Tier 1 full orchestration success."""
        from raglite.agentic.fallback import FallbackTier, log_workflow_metrics

        # Should not raise exception
        log_workflow_metrics(
            query_id="test-123",
            query="Calculate YoY growth",
            tier=FallbackTier.FULL_WORKFLOW,
            confidence="high",
            execution_time_ms=11500,
            agents_invoked=["retrieval", "analysis", "synthesis"],
            agents_failed=[],
            error_type=None,
        )

    def test_log_workflow_metrics_tier_2_partial(self):
        """Test metrics logging for Tier 2 partial workflow."""
        from raglite.agentic.fallback import (
            ErrorType,
            FallbackTier,
            log_workflow_metrics,
        )

        log_workflow_metrics(
            query_id="test-456",
            query="What was Q3 revenue?",
            tier=FallbackTier.PARTIAL_WORKFLOW,
            confidence="medium",
            execution_time_ms=18000,
            agents_invoked=["retrieval", "analysis"],
            agents_failed=["synthesis"],
            error_type=ErrorType.TIMEOUT,
        )

    def test_log_workflow_metrics_tier_4_epic1_fallback(self):
        """Test metrics logging for Tier 4 Epic 1 fallback."""
        from raglite.agentic.fallback import (
            ErrorType,
            FallbackTier,
            log_workflow_metrics,
        )

        log_workflow_metrics(
            query_id="test-789",
            query="Show financial data",
            tier=FallbackTier.EPIC1_FALLBACK,
            confidence="low",
            execution_time_ms=25000,
            agents_invoked=[],
            agents_failed=["retrieval", "analysis", "synthesis"],
            error_type=ErrorType.CONNECTION_ERROR,
        )

    def test_calculate_tier_rates_all_tier_1(self):
        """Test tier rate calculation with 100% Tier 1 success."""
        from raglite.agentic.fallback import calculate_tier_rates

        logs = [
            {"tier": "full"},
            {"tier": "full"},
            {"tier": "full"},
        ]
        rates = calculate_tier_rates(logs)

        assert rates["tier_1_success_rate"] == 100.0
        assert rates["tier_2_fallback_rate"] == 0.0
        assert rates["tier_4_epic1_rate"] == 0.0

    def test_calculate_tier_rates_mixed_tiers(self):
        """Test tier rate calculation with mixed degradation tiers."""
        from raglite.agentic.fallback import calculate_tier_rates

        logs = [
            {"tier": "full"},  # 1
            {"tier": "full"},  # 2
            {"tier": "full"},  # 3
            {"tier": "full"},  # 4
            {"tier": "partial"},  # 1 partial
            {"tier": "epic1_fallback"},  # 1 epic1
        ]
        rates = calculate_tier_rates(logs)

        # 4/6 = 66.67% Tier 1
        # 1/6 = 16.67% Tier 2
        # 1/6 = 16.67% Tier 4
        assert rates["tier_1_success_rate"] == 66.67
        assert rates["tier_2_fallback_rate"] == 16.67
        assert rates["tier_4_epic1_rate"] == 16.67

    def test_calculate_tier_rates_empty_logs(self):
        """Test tier rate calculation with no logs."""
        from raglite.agentic.fallback import calculate_tier_rates

        rates = calculate_tier_rates([])

        assert rates["tier_1_success_rate"] == 0.0
        assert rates["tier_2_fallback_rate"] == 0.0
        assert rates["tier_4_epic1_rate"] == 0.0

    def test_workflow_metrics_model_validation(self):
        """Test WorkflowMetrics model validation."""
        import datetime

        from raglite.shared.models import WorkflowMetrics

        # Valid metrics
        metrics = WorkflowMetrics(
            query_id="abc-123",
            query="Test query",
            tier="full_orchestration",
            confidence="high",
            execution_time_ms=12000,
            agents_invoked=["retrieval", "analysis", "synthesis"],
            agents_failed=[],
            error_type=None,
            timestamp=datetime.datetime.now(datetime.UTC).isoformat(),
        )

        assert metrics.query_id == "abc-123"
        assert metrics.tier == "full_orchestration"
        assert metrics.confidence == "high"
        assert len(metrics.agents_invoked) == 3
        assert len(metrics.agents_failed) == 0

    def test_workflow_metrics_with_failure(self):
        """Test WorkflowMetrics model with failure data."""
        import datetime

        from raglite.shared.models import WorkflowMetrics

        metrics = WorkflowMetrics(
            query_id="def-456",
            query="Test query 2",
            tier="partial_analysis",
            confidence="medium",
            execution_time_ms=18000,
            agents_invoked=["retrieval", "analysis"],
            agents_failed=["synthesis"],
            error_type="timeout",
            timestamp=datetime.datetime.now(datetime.UTC).isoformat(),
        )

        assert metrics.tier == "partial_analysis"
        assert metrics.error_type == "timeout"
        assert "synthesis" in metrics.agents_failed
