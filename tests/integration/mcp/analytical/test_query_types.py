"""Tests for diverse query types (AC5)."""

import pytest

from raglite.shared.models import AnalyticalQueryRequest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.preserve_collection,
    pytest.mark.slow,
]


@pytest.mark.integration
@pytest.mark.priority("P1")
class TestQueryTypes:
    """Test AC5: Diverse query types (trend analysis, variance, YoY)."""

    @pytest.mark.asyncio
    async def test_yoy_comparison_query(self, session_ingested_collection, analytical_query_tool):
        """Test YoY comparison analytical query (AC5)."""
        request = AnalyticalQueryRequest(
            query="Compare Q3 2023 revenue to Q3 2022 and calculate year-over-year growth",
            top_k=5,
        )

        response = await analytical_query_tool(request)

        # AC5: YoY queries should be classified as analytical
        assert response.complexity == "analytical"
        assert response.workflow_metadata["workflow_pattern"] in [
            "yoy_growth",
            "generic_analytical",
        ]

        # Verify response structure
        assert len(response.answer) > 0
        assert len(response.reasoning_steps) >= 2
        assert response.confidence in ["high", "medium", "low"]

    @pytest.mark.asyncio
    async def test_variance_analysis_query(
        self, session_ingested_collection, analytical_query_tool
    ):
        """Test variance analysis query (AC5)."""
        request = AnalyticalQueryRequest(
            query="Explain why operating expenses increased in Q3 compared to budget",
            top_k=5,
        )

        response = await analytical_query_tool(request)

        # AC5: Variance queries should be classified as analytical
        assert response.complexity == "analytical"
        assert response.workflow_metadata["workflow_pattern"] in [
            "variance_analysis",
            "generic_analytical",
        ]

        # Verify response includes analysis
        assert len(response.answer) > 0
        assert len(response.reasoning_steps) >= 2

    @pytest.mark.asyncio
    async def test_trend_analysis_query(self, session_ingested_collection, analytical_query_tool):
        """Test trend analysis query (AC5)."""
        request = AnalyticalQueryRequest(
            query="Analyze revenue trends over the past 4 quarters", top_k=5
        )

        response = await analytical_query_tool(request)

        # AC5: Trend queries should be classified as analytical
        assert response.complexity == "analytical"
        assert response.workflow_metadata["workflow_pattern"] in [
            "trend_analysis",
            "generic_analytical",
        ]

        # Verify response includes trend analysis
        assert len(response.answer) > 0
        assert len(response.reasoning_steps) >= 2

    @pytest.mark.asyncio
    async def test_simple_factual_query(self, session_ingested_collection, analytical_query_tool):
        """Test simple factual query routed to Epic 2 (AC5)."""
        request = AnalyticalQueryRequest(query="What is the company's total debt?", top_k=5)

        response = await analytical_query_tool(request)

        # AC5: Factual queries should be classified as simple
        assert response.complexity == "simple"
        assert response.workflow_metadata["workflow_pattern"] == "simple_retrieval"

        # Verify response structure
        assert len(response.answer) > 0
        assert response.confidence == "high"


@pytest.mark.integration
@pytest.mark.priority("P0")
class TestSuccessRateValidation:
    """Test AC5: Automated success rate validation (≥80% threshold)."""

    @pytest.mark.asyncio
    async def test_analytical_query_success_rate(
        self, session_ingested_collection, analytical_query_tool
    ):
        """Test that ≥80% of diverse analytical queries succeed (AC5 - Task 4.8)."""
        # Test set of 10+ analytical queries covering all types (AC5)
        test_queries = [
            # YoY growth (3 queries)
            "Compare Q3 2023 revenue to Q3 2022 and calculate year-over-year growth",
            "What is the YoY percentage change in operating expenses from 2022 to 2023?",
            "Compare annual revenue 2022 vs 2023 and calculate growth rate",
            # Variance analysis (3 queries)
            "Explain why operating expenses increased in Q3 compared to budget",
            "Explain the variance between projected and actual revenue for Q4",
            "What caused the revenue decline from Q2 to Q3?",
            # Trend analysis (2 queries)
            "Analyze revenue trends over the past 4 quarters",
            "Analyze the quarterly expense trend for 2023",
            # Comparative (2 queries)
            "Compare Q3 2023 revenue with Q3 2024 revenue",
            "How do 2023 operating margins compare to 2022?",
        ]

        successful_queries = 0
        total_queries = len(test_queries)
        failed_queries = []

        for query in test_queries:
            try:
                request = AnalyticalQueryRequest(query=query, top_k=5)
                response = await analytical_query_tool(request)

                # Success criteria: response has answer and reasoning steps
                if (
                    response.answer
                    and len(response.answer) > 0
                    and response.reasoning_steps
                    and len(response.reasoning_steps) >= 2
                ):
                    successful_queries += 1
                else:
                    failed_queries.append((query, "Incomplete response"))
            except Exception as e:
                failed_queries.append((query, str(e)))

        success_rate = (successful_queries / total_queries) * 100

        # AC5: Success rate must be ≥80%
        assert success_rate >= 80.0, (
            f"Success rate {success_rate:.1f}% is below 80% threshold. "
            f"Successful: {successful_queries}/{total_queries}. "
            f"Failed queries: {failed_queries}"
        )
