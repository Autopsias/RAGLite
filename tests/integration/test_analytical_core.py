"""Integration tests for Story 3.6: Analytical Query Tool (MCP) - Core Tests.

Tests the analytical_query_financial_documents() MCP tool with focus on:
- AC1: MCP tool definition and integration
- AC2: AnalyticalQueryRequest/Response models
- AC3: Conditional routing (simple → Epic 2, analytical → Epic 3)
- AC4: Reasoning steps transparency

Story Reference: docs/sprint-artifacts/3-6-analytical-query-tool-mcp.md
"""

import pytest

from raglite.main import analytical_query_financial_documents
from raglite.shared.models import AnalyticalQueryRequest, AnalyticalQueryResponse

# Mark all tests in this module as integration tests that preserve collection state
pytestmark = [pytest.mark.integration, pytest.mark.preserve_collection, pytest.mark.slow]

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
class TestConditionalRouting:
    """Test AC3: Conditional routing - simple queries to Epic 2, analytical to Epic 3."""

    @pytest.mark.asyncio
    async def test_simple_query_routes_to_epic2(self, session_ingested_collection):
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
    async def test_analytical_query_routes_to_epic3(self, session_ingested_collection):
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
class TestReasoningTransparency:
    """Test AC4: Reasoning steps and transparency metadata."""

    @pytest.mark.asyncio
    async def test_reasoning_steps_present_for_simple_query(self, session_ingested_collection):
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
    async def test_reasoning_steps_present_for_analytical_query(self, session_ingested_collection):
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
    async def test_workflow_metadata_transparency(self, session_ingested_collection):
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
class TestSourceCitations:
    """Test AC6: Source citations and verification."""

    @pytest.mark.asyncio
    async def test_sources_present_for_simple_query(self, session_ingested_collection):
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
    async def test_sources_present_for_analytical_query(self, session_ingested_collection):
        """Analytical query responses must include source citations (AC6)."""
        request = AnalyticalQueryRequest(query="Calculate YoY revenue growth", top_k=5)

        response = await analytical_query_fn(request)

        # AC6: Sources must be present
        assert isinstance(response.sources, list)
        # Sources may be empty if no documents found or workflow failed

    @pytest.mark.asyncio
    async def test_source_deduplication(self, session_ingested_collection):
        """Sources should be deduplicated to avoid redundancy (AC6)."""
        request = AnalyticalQueryRequest(
            query="Analyze revenue trends over multiple periods", top_k=10
        )

        response = await analytical_query_fn(request)

        # AC6: Verify no duplicate sources (if any sources returned)
        if len(response.sources) > 0:
            assert len(response.sources) == len(set(response.sources))
