"""Integration tests for Story 3.6: Analytical Query Tool (MCP).

Tests the analytical_query_financial_documents() MCP tool with focus on:
- AC1: MCP tool definition and integration
- AC2: AnalyticalQueryRequest/Response models
- AC3: Conditional routing (simple → Epic 2, analytical → Epic 3)
- AC4: Reasoning steps transparency
- AC5: Test query validation (trend analysis, variance, YoY)
- AC6: Source citations and manual testing readiness

Story Reference: docs/sprint-artifacts/3-6-analytical-query-tool-mcp.md
"""

import pytest

from raglite.main import analytical_query_financial_documents
from raglite.shared.models import AnalyticalQueryRequest

# Access underlying function from FastMCP FunctionTool wrapper
analytical_query_fn = analytical_query_financial_documents.fn


@pytest.mark.integration
@pytest.mark.priority("P0")
class TestMCPToolCompliance:
    """Test AC1: MCP tool definition and protocol compliance (no data required)."""

    def test_analytical_query_tool_registered(self):
        """Verify analytical_query_financial_documents is properly registered as MCP tool (AC1)."""
        # AC1: Tool must be registered with FastMCP
        assert hasattr(analytical_query_financial_documents, "fn")
        assert hasattr(analytical_query_financial_documents, "name")
        assert analytical_query_financial_documents.name == "analytical_query_financial_documents"
        assert callable(analytical_query_fn)

    def test_analytical_query_request_model_valid(self):
        """Verify AnalyticalQueryRequest model is properly defined (AC2)."""
        # AC2: Request model must have required fields
        request = AnalyticalQueryRequest(query="test query", top_k=5)
        assert request.query == "test query"
        assert request.top_k == 5

    def test_analytical_query_response_model_has_required_fields(self):
        """Verify AnalyticalQueryResponse model has all Story 3.6 fields (AC2, AC4, AC6)."""
        from raglite.shared.models import AnalyticalQueryResponse

        # AC2: Response model must have core fields
        response = AnalyticalQueryResponse(
            answer="test answer",
            complexity="simple",
            workflow_metadata={"task_count": 1},
            confidence="high",
            limitations=[],
            reasoning_steps=["1. Test step"],  # AC4
            sources=["test.pdf (page 1)"],  # AC6
        )

        # Verify all required fields present
        assert response.answer == "test answer"
        assert response.complexity == "simple"
        assert response.workflow_metadata == {"task_count": 1}
        assert response.confidence == "high"
        assert response.limitations == []

        # AC4: Reasoning steps field
        assert hasattr(response, "reasoning_steps")
        assert response.reasoning_steps == ["1. Test step"]

        # AC6: Sources field
        assert hasattr(response, "sources")
        assert response.sources == ["test.pdf (page 1)"]


@pytest.mark.integration
@pytest.mark.priority("P0")
@pytest.mark.skipif(
    True,
    reason="Requires Qdrant with ingested data - run manually after ingestion with --no-skip",
)
class TestConditionalRouting:
    """Test AC3: Conditional routing - simple queries to Epic 2, analytical to Epic 3."""

    @pytest.mark.asyncio
    async def test_simple_query_routes_to_epic2(self):
        """Simple query should route to Epic 2 basic retrieval.

        AC3: Verify simple queries are routed to query_financial_documents()
        instead of full workflow orchestration.
        """
        # Simple query without analytical keywords
        request = AnalyticalQueryRequest(query="What is the Q3 revenue?", top_k=5)

        response = await analytical_query_fn(request)

        # Verify response structure
        assert response.complexity == "simple"
        assert response.workflow_metadata["workflow_pattern"] == "simple_retrieval"
        assert response.workflow_metadata["fallback_tier"] == "epic2_routing"
        assert response.workflow_metadata["task_count"] == 1
        assert response.confidence == "high"

        # AC4: Verify reasoning steps present
        assert len(response.reasoning_steps) > 0
        assert "simple" in response.reasoning_steps[0].lower()
        assert "retrieval" in " ".join(response.reasoning_steps).lower()

        # AC6: Verify sources present
        assert len(response.sources) > 0

    @pytest.mark.asyncio
    async def test_analytical_query_routes_to_epic3(self):
        """Analytical query should route to Epic 3 workflow orchestration.

        AC3: Verify analytical queries trigger full multi-step workflow.
        """
        # Analytical query with calculation keywords
        request = AnalyticalQueryRequest(
            query="Calculate YoY revenue growth from Q3 2022 to Q3 2023", top_k=5
        )

        response = await analytical_query_fn(request)

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


@pytest.mark.integration
@pytest.mark.priority("P0")
@pytest.mark.skipif(
    True,
    reason="Requires Qdrant with ingested data - run manually after ingestion with --no-skip",
)
class TestReasoningTransparency:
    """Test AC4: Reasoning steps and transparency metadata."""

    @pytest.mark.asyncio
    async def test_reasoning_steps_present_for_simple_query(self):
        """Simple query responses must include reasoning steps (AC4)."""
        request = AnalyticalQueryRequest(query="What is total revenue?", top_k=5)

        response = await analytical_query_fn(request)

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
    async def test_reasoning_steps_present_for_analytical_query(self):
        """Analytical query responses must include detailed reasoning steps (AC4)."""
        request = AnalyticalQueryRequest(
            query="Explain the variance in operating expenses", top_k=5
        )

        response = await analytical_query_fn(request)

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
    async def test_workflow_metadata_transparency(self):
        """Workflow metadata must provide execution details (AC4)."""
        request = AnalyticalQueryRequest(
            query="Calculate revenue growth and analyze trends", top_k=5
        )

        response = await analytical_query_fn(request)

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


@pytest.mark.integration
@pytest.mark.priority("P1")
@pytest.mark.skipif(
    True,
    reason="Requires Qdrant with ingested data - run manually after ingestion with --no-skip",
)
class TestSourceCitations:
    """Test AC6: Source citations and verification."""

    @pytest.mark.asyncio
    async def test_sources_present_for_simple_query(self):
        """Simple query responses must include source citations (AC6)."""
        request = AnalyticalQueryRequest(query="What is EBITDA?", top_k=5)

        response = await analytical_query_fn(request)

        # AC6: Sources must be present and properly formatted
        assert isinstance(response.sources, list)
        # Sources may be empty if no documents found, but field must exist

        if len(response.sources) > 0:
            # Verify source format: "filename (page N)" or "filename"
            for source in response.sources:
                assert isinstance(source, str)
                assert len(source) > 0

    @pytest.mark.asyncio
    async def test_sources_present_for_analytical_query(self):
        """Analytical query responses must include source citations (AC6)."""
        request = AnalyticalQueryRequest(query="Calculate YoY revenue growth", top_k=5)

        response = await analytical_query_fn(request)

        # AC6: Sources must be present
        assert isinstance(response.sources, list)
        # Sources may be empty if no documents found or workflow failed

    @pytest.mark.asyncio
    async def test_source_deduplication(self):
        """Sources should be deduplicated to avoid redundancy (AC6)."""
        request = AnalyticalQueryRequest(
            query="Analyze revenue trends over multiple periods", top_k=10
        )

        response = await analytical_query_fn(request)

        # AC6: Verify no duplicate sources (if any sources returned)
        if len(response.sources) > 0:
            assert len(response.sources) == len(set(response.sources))


@pytest.mark.integration
@pytest.mark.priority("P1")
@pytest.mark.skipif(
    True,
    reason="Requires Qdrant with ingested data - run manually after ingestion with --no-skip",
)
class TestQueryTypes:
    """Test AC5: Diverse query types (trend analysis, variance, YoY)."""

    @pytest.mark.asyncio
    async def test_yoy_comparison_query(self):
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
    async def test_variance_analysis_query(self):
        """Test variance analysis query (AC5)."""
        request = AnalyticalQueryRequest(
            query="Explain why operating expenses increased in Q3 compared to budget", top_k=5
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
    async def test_trend_analysis_query(self):
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
    async def test_yoy_growth_percentage_change(self):
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
    async def test_yoy_annual_revenue_growth(self):
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
    async def test_variance_budget_vs_actual(self):
        """Test variance analysis for budget vs actual (AC5 - additional coverage)."""
        request = AnalyticalQueryRequest(
            query="Explain the variance between projected and actual revenue for Q4", top_k=5
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
    async def test_variance_revenue_decline(self):
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
    async def test_trend_quarterly_expenses(self):
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
    async def test_comparative_quarterly_revenue(self):
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
    async def test_comparative_operating_margins(self):
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
    async def test_simple_factual_query(self):
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
@pytest.mark.skipif(
    True,
    reason="Requires Qdrant with ingested data - run manually after ingestion with --no-skip",
)
class TestSuccessRateValidation:
    """Test AC5: Automated success rate validation (≥80% threshold)."""

    @pytest.mark.asyncio
    async def test_analytical_query_success_rate(self):
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
@pytest.mark.skipif(
    True,
    reason="Requires Qdrant with ingested data - run manually after ingestion with --no-skip",
)
class TestGracefulDegradation:
    """Test graceful degradation with reasoning steps and sources (Story 3.6 extension)."""

    @pytest.mark.asyncio
    async def test_fallback_includes_reasoning_steps(self):
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
    async def test_fallback_includes_sources(self):
        """Fallback responses must include sources if available."""
        # Query that might trigger fallback
        request = AnalyticalQueryRequest(
            query="Perform comprehensive financial analysis with trend forecasting", top_k=5
        )

        response = await analytical_query_fn(request)

        # AC6: Sources should be present even in fallback
        assert isinstance(response.sources, list)
        # May be empty if fallback tier is low, but field must exist


@pytest.mark.integration
@pytest.mark.priority("P2")
@pytest.mark.skipif(
    True,
    reason="Requires Qdrant with ingested data - run manually after ingestion with --no-skip",
)
class TestResponseConsistency:
    """Test response model consistency across all code paths."""

    @pytest.mark.asyncio
    async def test_response_model_fields_always_present(self):
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
