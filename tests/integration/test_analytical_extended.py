"""Integration tests for Story 3.6: Analytical Query Tool (MCP) - Extended Tests.

Tests AC5 (Diverse query types), AC6 (Success rate validation), and graceful degradation.

Story Reference: docs/sprint-artifacts/3-6-analytical-query-tool-mcp.md
"""

import pytest

from raglite.main import analytical_query_financial_documents
from raglite.shared.models import AnalyticalQueryRequest

# Mark all tests in this module as integration tests that preserve collection state
pytestmark = [
    pytest.mark.integration,
    pytest.mark.preserve_collection,
    pytest.mark.slow,
    pytest.mark.xdist_group(name="embedding_model"),
]

# analytical_query_financial_documents is a plain async function, not wrapped by FastMCP
analytical_query_fn = analytical_query_financial_documents


@pytest.mark.integration
@pytest.mark.priority("P1")
class TestQueryTypes:
    """Test AC5: Diverse query types (trend analysis, variance, YoY)."""

    @pytest.mark.asyncio
    async def test_yoy_comparison_query(self, session_ingested_collection):
        """Test YoY comparison analytical query (AC5)."""
        request = AnalyticalQueryRequest(
            query="Compare Q3 2023 revenue to Q3 2022 and calculate year-over-year growth",
            top_k=5,
        )

        response = await analytical_query_fn(request)

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
    async def test_variance_analysis_query(self, session_ingested_collection):
        """Test variance analysis query (AC5)."""
        request = AnalyticalQueryRequest(
            query="Explain why operating expenses increased in Q3 compared to budget",
            top_k=5,
        )

        response = await analytical_query_fn(request)

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
    async def test_trend_analysis_query(self, session_ingested_collection):
        """Test trend analysis query (AC5)."""
        request = AnalyticalQueryRequest(
            query="Analyze revenue trends over the past 4 quarters", top_k=5
        )

        response = await analytical_query_fn(request)

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
    async def test_yoy_growth_percentage_change(self, session_ingested_collection):
        """Test YoY percentage change analytical query (AC5 - additional coverage)."""
        request = AnalyticalQueryRequest(
            query="What is the YoY percentage change in operating expenses from 2022 to 2023?",
            top_k=5,
        )

        response = await analytical_query_fn(request)

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
    async def test_yoy_annual_revenue_growth(self, session_ingested_collection):
        """Test YoY annual revenue growth calculation (AC5 - additional coverage)."""
        request = AnalyticalQueryRequest(
            query="Compare annual revenue 2022 vs 2023 and calculate growth rate",
            top_k=5,
        )

        response = await analytical_query_fn(request)

        # AC5: YoY queries should be classified as analytical
        assert response.complexity == "analytical"
        assert response.workflow_metadata["workflow_pattern"] in [
            "yoy_growth",
            "generic_analytical",
        ]

        # Verify response includes growth calculation
        assert len(response.answer) > 0
        assert len(response.reasoning_steps) >= 2
        assert response.confidence in ["high", "medium", "low"]

    @pytest.mark.asyncio
    async def test_variance_budget_vs_actual(self, session_ingested_collection):
        """Test variance analysis for budget vs actual (AC5 - additional coverage)."""
        request = AnalyticalQueryRequest(
            query="Explain the variance between projected and actual revenue for Q4",
            top_k=5,
        )

        response = await analytical_query_fn(request)

        # AC5: Variance queries should be classified as analytical
        assert response.complexity == "analytical"
        assert response.workflow_metadata["workflow_pattern"] in [
            "variance_analysis",
            "generic_analytical",
        ]

        # Verify response includes variance explanation
        assert len(response.answer) > 0
        assert len(response.reasoning_steps) >= 2

    @pytest.mark.asyncio
    async def test_variance_revenue_decline(self, session_ingested_collection):
        """Test variance analysis for revenue decline (AC5 - additional coverage)."""
        request = AnalyticalQueryRequest(
            query="What caused the revenue decline from Q2 to Q3?", top_k=5
        )

        response = await analytical_query_fn(request)

        # AC5: Variance queries should be classified as analytical
        assert response.complexity == "analytical"
        assert response.workflow_metadata["workflow_pattern"] in [
            "variance_analysis",
            "generic_analytical",
        ]

        # Verify response includes decline analysis
        assert len(response.answer) > 0
        assert len(response.reasoning_steps) >= 2

    @pytest.mark.asyncio
    async def test_trend_quarterly_expenses(self, session_ingested_collection):
        """Test trend analysis for quarterly expenses (AC5 - additional coverage)."""
        request = AnalyticalQueryRequest(
            query="Analyze the quarterly expense trend for 2023", top_k=5
        )

        response = await analytical_query_fn(request)

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
    async def test_comparative_quarterly_revenue(self, session_ingested_collection):
        """Test comparative query for quarterly revenue (AC5 - NEW comparative test)."""
        request = AnalyticalQueryRequest(
            query="Compare Q3 2023 revenue with Q3 2024 revenue", top_k=5
        )

        response = await analytical_query_fn(request)

        # AC5: Comparative queries should be classified as analytical
        assert response.complexity == "analytical"
        assert response.workflow_metadata["workflow_pattern"] in [
            "yoy_growth",
            "generic_analytical",
        ]

        # Verify response includes comparison
        assert len(response.answer) > 0
        assert len(response.reasoning_steps) >= 2
        assert response.confidence in ["high", "medium", "low"]

    @pytest.mark.asyncio
    async def test_comparative_operating_margins(self, session_ingested_collection):
        """Test comparative query for operating margins (AC5 - NEW comparative test)."""
        request = AnalyticalQueryRequest(
            query="How do 2023 operating margins compare to 2022?", top_k=5
        )

        response = await analytical_query_fn(request)

        # AC5: Comparative queries should be classified as analytical
        assert response.complexity == "analytical"
        assert response.workflow_metadata["workflow_pattern"] in [
            "yoy_growth",
            "variance_analysis",
            "generic_analytical",
        ]

        # Verify response includes margin comparison
        assert len(response.answer) > 0
        assert len(response.reasoning_steps) >= 2

    @pytest.mark.asyncio
    async def test_simple_factual_query(self, session_ingested_collection):
        """Test simple factual query routed to Epic 2 (AC5)."""
        request = AnalyticalQueryRequest(query="What is the company's total debt?", top_k=5)

        response = await analytical_query_fn(request)

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
    async def test_analytical_query_success_rate(self, session_ingested_collection):
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
                response = await analytical_query_fn(request)

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


@pytest.mark.integration
@pytest.mark.priority("P1")
class TestGracefulDegradation:
    """Test graceful degradation with reasoning steps and sources (Story 3.6 extension)."""

    @pytest.mark.asyncio
    async def test_fallback_includes_reasoning_steps(self, session_ingested_collection):
        """Fallback responses must include reasoning steps explaining degradation."""
        # Query that might trigger fallback (very complex or edge case)
        request = AnalyticalQueryRequest(
            query="Calculate YoY revenue growth, analyze variance drivers, and forecast next quarter",
            top_k=5,
        )

        response = await analytical_query_fn(request)

        # AC4: Even fallback responses must have reasoning steps
        assert len(response.reasoning_steps) > 0
        assert isinstance(response.reasoning_steps, list)

        # Verify fallback tier is tracked
        assert "fallback_tier" in response.workflow_metadata
        assert response.workflow_metadata["fallback_tier"] in [
            "full",
            "partial",
            "epic1_fallback",
            "epic2_routing",
        ]

    @pytest.mark.asyncio
    async def test_fallback_includes_sources(self, session_ingested_collection):
        """Fallback responses must include sources if available."""
        # Query that might trigger fallback
        request = AnalyticalQueryRequest(
            query="Perform comprehensive financial analysis with trend forecasting",
            top_k=5,
        )

        response = await analytical_query_fn(request)

        # AC6: Sources should be present even in fallback
        assert isinstance(response.sources, list)
        # May be empty if fallback tier is low, but field must exist


@pytest.mark.integration
@pytest.mark.priority("P2")
class TestResponseConsistency:
    """Test response model consistency across all code paths."""

    @pytest.mark.asyncio
    async def test_response_model_fields_always_present(self, session_ingested_collection):
        """All required fields must be present in every response."""
        test_queries = [
            "What is revenue?",  # Simple
            "Calculate YoY growth",  # Analytical
            "Explain variance in costs",  # Analytical
        ]

        for query in test_queries:
            request = AnalyticalQueryRequest(query=query, top_k=5)
            response = await analytical_query_fn(request)

            # Verify all required fields present
            assert hasattr(response, "answer")
            assert hasattr(response, "complexity")
            assert hasattr(response, "workflow_metadata")
            assert hasattr(response, "confidence")
            assert hasattr(response, "limitations")
            assert hasattr(response, "reasoning_steps")  # Story 3.6 AC4
            assert hasattr(response, "sources")  # Story 3.6 AC6

            # Verify field types
            assert isinstance(response.answer, str)
            assert isinstance(response.complexity, str)
            assert isinstance(response.workflow_metadata, dict)
            assert isinstance(response.confidence, str)
            assert isinstance(response.limitations, list)
            assert isinstance(response.reasoning_steps, list)
            assert isinstance(response.sources, list)

            # Verify non-empty critical fields
            assert len(response.answer) > 0
            assert response.complexity in ["simple", "analytical"]
            assert response.confidence in ["high", "medium", "low"]
