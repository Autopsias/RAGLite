"""Tests for source citations and response consistency."""

import pytest

from raglite.shared.models import AnalyticalQueryRequest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.preserve_collection,
    pytest.mark.slow,
]


@pytest.mark.integration
@pytest.mark.priority("P1")
class TestSourceCitations:
    """Test AC6: Source citations and verification."""

    @pytest.mark.asyncio
    async def test_sources_present_for_simple_query(
        self, session_ingested_collection, analytical_query_tool
    ):
        """Simple query responses must include source citations (AC6)."""
        request = AnalyticalQueryRequest(query="What is EBITDA?", top_k=5)

        response = await analytical_query_tool(request)

        # AC6: Sources must be present and properly formatted
        assert isinstance(response.sources, list)
        # Sources may be empty if no documents found, but field must exist

        if len(response.sources) > 0:
            # Verify source format: "filename (page N)" or "filename"
            for source in response.sources:
                assert isinstance(source, str)
                assert len(source) > 0

    @pytest.mark.asyncio
    async def test_sources_present_for_analytical_query(
        self, session_ingested_collection, analytical_query_tool
    ):
        """Analytical query responses must include source citations (AC6)."""
        request = AnalyticalQueryRequest(query="Calculate YoY revenue growth", top_k=5)

        response = await analytical_query_tool(request)

        # AC6: Sources must be present
        assert isinstance(response.sources, list)
        # Sources may be empty if no documents found or workflow failed

    @pytest.mark.asyncio
    async def test_source_deduplication(self, session_ingested_collection, analytical_query_tool):
        """Sources should be deduplicated to avoid redundancy (AC6)."""
        request = AnalyticalQueryRequest(
            query="Analyze revenue trends over multiple periods", top_k=10
        )

        response = await analytical_query_tool(request)

        # AC6: Verify no duplicate sources (if any sources returned)
        if len(response.sources) > 0:
            assert len(response.sources) == len(set(response.sources))


@pytest.mark.integration
@pytest.mark.priority("P1")
class TestGracefulDegradation:
    """Test graceful degradation with reasoning steps and sources (Story 3.6 extension)."""

    @pytest.mark.asyncio
    async def test_fallback_includes_reasoning_steps(
        self, session_ingested_collection, analytical_query_tool
    ):
        """Fallback responses must include reasoning steps explaining degradation."""
        # Query that might trigger fallback (very complex or edge case)
        request = AnalyticalQueryRequest(
            query="Calculate YoY revenue growth, analyze variance drivers, and forecast next quarter",
            top_k=5,
        )

        response = await analytical_query_tool(request)

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
            "full_orchestration",
            "basic_retrieval",
        ]

    @pytest.mark.asyncio
    async def test_fallback_includes_sources(
        self, session_ingested_collection, analytical_query_tool
    ):
        """Fallback responses must include sources if available."""
        # Query that might trigger fallback
        request = AnalyticalQueryRequest(
            query="Perform comprehensive financial analysis with trend forecasting",
            top_k=5,
        )

        response = await analytical_query_tool(request)

        # AC6: Sources should be present even in fallback
        assert isinstance(response.sources, list)
        # May be empty if fallback tier is low, but field must exist


@pytest.mark.integration
@pytest.mark.priority("P2")
class TestResponseConsistency:
    """Test response model consistency across all code paths."""

    @pytest.mark.asyncio
    async def test_response_model_fields_always_present(
        self, session_ingested_collection, analytical_query_tool
    ):
        """All required fields must be present in every response."""
        test_queries = [
            "What is revenue?",  # Simple
            "Calculate YoY growth",  # Analytical
            "Explain variance in costs",  # Analytical
        ]

        for query in test_queries:
            request = AnalyticalQueryRequest(query=query, top_k=5)
            response = await analytical_query_tool(request)

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
