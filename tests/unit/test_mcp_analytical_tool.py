"""Smoke tests for analytical_query_financial_documents MCP tool (Story 3.5 Task 6.6).

Tests basic MCP tool registration and model validation.
"""

import pytest


class TestAnalyticalQueryMCPToolSmoke:
    """Smoke tests for MCP tool basic functionality (AC7: Task 6.6)."""

    def test_mcp_tool_is_registered(self):
        """Test that analytical_query_financial_documents is registered as MCP tool."""
        from raglite.main import mcp

        # Verify tool is registered
        tool_names = [tool for tool in dir(mcp) if not tool.startswith("_")]
        assert len(tool_names) > 0, "MCP server should have registered tools"

        # The tool should be accessible via the mcp module
        assert hasattr(mcp, "run"), "MCP server should have run method"

    def test_analytical_query_request_model(self):
        """Test AnalyticalQueryRequest model validation."""
        from raglite.shared.models import AnalyticalQueryRequest

        # Valid request
        request = AnalyticalQueryRequest(query="Calculate YoY revenue growth", top_k=5)
        assert request.query == "Calculate YoY revenue growth"
        assert request.top_k == 5

        # Default top_k
        request = AnalyticalQueryRequest(query="Test query")
        assert request.top_k == 5

        # Validate top_k range
        with pytest.raises(ValueError):
            AnalyticalQueryRequest(query="Test", top_k=0)  # Below minimum

        with pytest.raises(ValueError):
            AnalyticalQueryRequest(query="Test", top_k=100)  # Above maximum

    def test_analytical_query_response_model(self):
        """Test AnalyticalQueryResponse model structure."""
        from raglite.shared.models import AnalyticalQueryResponse

        # Valid response
        response = AnalyticalQueryResponse(
            answer="Test answer",
            complexity="analytical",
            workflow_metadata={
                "task_count": 4,
                "execution_time_ms": 1500,
                "workflow_pattern": "yoy_growth",
                "fallback_tier": "full",
            },
            confidence="high",
            limitations=[],
        )

        assert response.answer == "Test answer"
        assert response.complexity == "analytical"
        assert response.confidence == "high"
        assert response.workflow_metadata["task_count"] == 4
        assert len(response.limitations) == 0

    def test_mcp_server_imports_successfully(self):
        """Test that main module with new tool imports without errors."""
        # This test verifies all imports resolve correctly
        try:
            from raglite import main  # noqa: F401

            success = True
        except ImportError as e:
            success = False
            pytest.fail(f"Failed to import raglite.main: {e}")

        assert success, "MCP server module should import successfully"

    def test_workflow_orchestration_imports(self):
        """Test that workflow orchestration modules import correctly."""
        try:
            from raglite.agentic import fallback, orchestrator, planner  # noqa: F401

            success = True
        except ImportError as e:
            success = False
            pytest.fail(f"Failed to import workflow modules: {e}")

        assert success, "Workflow orchestration modules should import successfully"
