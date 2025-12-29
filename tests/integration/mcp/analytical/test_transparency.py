"""Tests for reasoning transparency and metadata."""

import pytest

from raglite.shared.models import AnalyticalQueryRequest

pytestmark = [pytest.mark.integration, pytest.mark.preserve_collection, pytest.mark.slow]


@pytest.mark.integration
@pytest.mark.priority("P0")
class TestReasoningTransparency:
    """Test AC4: Reasoning steps and transparency metadata."""

    @pytest.mark.asyncio
    async def test_reasoning_steps_present_for_simple_query(
        self, session_ingested_collection, analytical_query_tool
    ):
        """Simple query responses must include reasoning steps (AC4)."""
        request = AnalyticalQueryRequest(query="What is total revenue?", top_k=5)

        response = await analytical_query_tool(request)

        # AC4: Reasoning steps must be present and informative
        assert len(response.reasoning_steps) >= 2
        assert isinstance(response.reasoning_steps, list)
        assert all(isinstance(step, str) for step in response.reasoning_steps)

        # Verify step numbering
        assert response.reasoning_steps[0].startswith("1.")

        # Verify steps describe the workflow
        steps_text = " ".join(response.reasoning_steps).lower()
        assert "classified" in steps_text or "retrieval" in steps_text

    @pytest.mark.asyncio
    async def test_reasoning_steps_present_for_analytical_query(
        self, session_ingested_collection, analytical_query_tool
    ):
        """Analytical query responses must include detailed reasoning steps (AC4)."""
        request = AnalyticalQueryRequest(
            query="Explain the variance in operating expenses", top_k=5
        )

        response = await analytical_query_tool(request)

        # AC4: Reasoning steps must detail workflow execution
        assert len(response.reasoning_steps) >= 2
        assert isinstance(response.reasoning_steps, list)

        # Verify steps are numbered and descriptive
        for i, step in enumerate(response.reasoning_steps, start=1):
            assert step.startswith(f"{i}.")

        # Verify workflow steps mentioned
        steps_text = " ".join(response.reasoning_steps).lower()
        assert "analytical" in steps_text or "workflow" in steps_text

    @pytest.mark.asyncio
    async def test_workflow_metadata_transparency(
        self, session_ingested_collection, analytical_query_tool
    ):
        """Workflow metadata must provide execution details (AC4)."""
        request = AnalyticalQueryRequest(
            query="Calculate revenue growth and analyze trends", top_k=5
        )

        response = await analytical_query_tool(request)

        # AC4: Workflow metadata must include execution details
        assert "task_count" in response.workflow_metadata
        assert "execution_time_ms" in response.workflow_metadata
        assert "workflow_pattern" in response.workflow_metadata
        assert "fallback_tier" in response.workflow_metadata

        # Verify values are reasonable
        assert response.workflow_metadata["task_count"] >= 1
        assert response.workflow_metadata["execution_time_ms"] >= 0
        assert response.workflow_metadata["workflow_pattern"] in [
            "simple_retrieval",
            "yoy_growth",
            "variance_analysis",
            "trend_analysis",
            "generic_analytical",
            "fallback",
        ]
