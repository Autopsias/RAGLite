"""Tests for MCP tool compliance and model validation."""

import pytest

from raglite.main import analytical_query_financial_documents
from raglite.shared.models import AnalyticalQueryRequest, AnalyticalQueryResponse

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
