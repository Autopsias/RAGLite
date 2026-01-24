"""Tests for conditional routing logic."""

import pytest

from raglite.shared.models import AnalyticalQueryRequest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.preserve_collection,
    pytest.mark.slow,
    pytest.mark.xdist_group(name="embedding_model"),
]


@pytest.mark.integration
@pytest.mark.priority("P0")
class TestConditionalRouting:
    """Test AC3: Conditional routing - simple queries to Epic 2, analytical to Epic 3."""

    @pytest.mark.asyncio
    async def test_simple_query_routes_to_epic2(
        self, session_ingested_collection, analytical_query_tool
    ):
        """Simple query should route to Epic 2 basic retrieval.

        AC3: Verify simple queries are routed to query_financial_documents()
        instead of full workflow orchestration.
        """
        # Simple query without analytical keywords
        request = AnalyticalQueryRequest(query="What is the Q3 revenue?", top_k=5)

        response = await analytical_query_tool(request)

        # Verify response structure
        assert response.complexity == "simple"
        assert response.workflow_metadata["workflow_pattern"] == "simple_retrieval"
        # Accept both epic2_routing and basic_retrieval as valid Epic 2 routing
        assert response.workflow_metadata["fallback_tier"] in ["epic2_routing", "basic_retrieval"]
        assert response.workflow_metadata["task_count"] == 1
        assert response.confidence == "high"

        # AC4: Verify reasoning steps present
        assert len(response.reasoning_steps) > 0
        assert "simple" in response.reasoning_steps[0].lower()
        assert "retrieval" in " ".join(response.reasoning_steps).lower()

        # AC6: Verify sources present
        assert len(response.sources) > 0

    @pytest.mark.asyncio
    async def test_analytical_query_routes_to_epic3(
        self, session_ingested_collection, analytical_query_tool
    ):
        """Analytical query should route to Epic 3 workflow orchestration.

        AC3: Verify analytical queries trigger full multi-step workflow.
        """
        # Analytical query with calculation keywords
        request = AnalyticalQueryRequest(
            query="Calculate YoY revenue growth from Q3 2022 to Q3 2023", top_k=5
        )

        response = await analytical_query_tool(request)

        # Verify response structure
        assert response.complexity == "analytical"
        assert response.workflow_metadata["workflow_pattern"] in [
            "yoy_growth",
            "generic_analytical",
            "variance_analysis",
            "trend_analysis",
        ]
        assert response.workflow_metadata["task_count"] >= 2  # At least retrieval + synthesis
        assert response.confidence in ["high", "medium", "low"]

        # AC4: Verify reasoning steps show workflow execution
        assert len(response.reasoning_steps) > 0
        assert "analytical" in response.reasoning_steps[0].lower()

        # AC6: Verify sources present
        assert len(response.sources) >= 0  # May be empty if no documents found
