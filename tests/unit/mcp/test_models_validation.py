"""Expanded test coverage for Story 7.4: Refactored MCP modules.

This module provides additional tests beyond the ATDD checklist, focusing on:
- Edge cases not covered by ATDD tests
- Error handling paths
- Integration points between components
- Unit tests for complex logic
- Boundary conditions

Priority Definitions:
- P0: Critical path tests (must pass)
- P1: Important scenarios (should pass)
- P2: Edge cases (good to have)
- P3: Future-proofing (optional)

Test Coverage Targets:
- Models: Validation, serialization, edge cases
- Tools: Error handling, input validation, helper functions
- Main: Import chains, server lifecycle
"""

import importlib.util
import json
from datetime import date, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

# Base paths
RAGLITE_PATH = Path(__file__).parent.parent.parent.parent / "raglite"


# Direct import of models module to avoid circular import
# The standard import path triggers circular imports because:
# - raglite.mcp/__init__.py imports from raglite.mcp.tools.*
# - raglite.mcp.tools/* import mcp from raglite.main
# - raglite.main imports from raglite.mcp
# We bypass this by loading the models module directly via spec
def load_models_module():
    """Load models module directly without triggering package __init__."""
    spec = importlib.util.spec_from_file_location(
        "raglite_mcp_models_direct", RAGLITE_PATH / "mcp" / "models.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


models = load_models_module()
ExternalDataPoint = models.ExternalDataPoint
ExternalDataQueryRequest = models.ExternalDataQueryRequest
ExternalDataQueryResponse = models.ExternalDataQueryResponse
ModelWeightAdminRequest = models.ModelWeightAdminRequest
ModelWeightAdminResponse = models.ModelWeightAdminResponse


# =============================================================================
# [P0] Models: Critical Validation Tests
# =============================================================================


class TestModelsValidation:
    """[P0] Test Pydantic model validation and error handling."""

    @pytest.mark.priority("P0")
    def test_external_data_query_request_required_fields(self):
        """Test ExternalDataQueryRequest requires source and date_range.

        Given the ExternalDataQueryRequest model
        When required fields are missing
        Then ValidationError should be raised
        """
        with pytest.raises(ValidationError) as exc_info:
            ExternalDataQueryRequest(source="INE_BuildingPermits")

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("date_range",) for e in errors)

    @pytest.mark.priority("P0")
    def test_external_data_query_request_valid_creation(self):
        """Test ExternalDataQueryRequest with valid data.

        Given valid source and date_range
        When creating ExternalDataQueryRequest
        Then model should be created successfully
        """
        request = ExternalDataQueryRequest(
            source="INE_BuildingPermits",
            date_range="2024-01-01:2024-12-31",
            metric="new_permits",
        )

        assert request.source == "INE_BuildingPermits"
        assert request.date_range == "2024-01-01:2024-12-31"
        assert request.metric == "new_permits"

    @pytest.mark.priority("P0")
    def test_external_data_point_date_validation(self):
        """Test ExternalDataPoint handles date types correctly.

        Given a date value
        When creating ExternalDataPoint
        Then date should be properly typed
        """
        point = ExternalDataPoint(
            date=date(2024, 6, 15),
            metric_name="cement_demand",
            value=1250.5,
            unit="tons",
        )

        assert point.date == date(2024, 6, 15)
        assert point.metric_name == "cement_demand"
        assert point.value == 1250.5
        assert point.unit == "tons"

    @pytest.mark.priority("P1")
    def test_external_data_point_none_unit_allowed(self):
        """Test ExternalDataPoint allows None for unit field.

        Given a data point without a unit
        When creating ExternalDataPoint
        Then unit should be None
        """
        point = ExternalDataPoint(
            date=date(2024, 6, 15),
            metric_name="cement_demand",
            value=1250.5,
            unit=None,
        )

        assert point.unit is None

    @pytest.mark.priority("P0")
    def test_external_data_query_response_serialization(self):
        """Test ExternalDataQueryResponse can be serialized to JSON.

        Given a complete response model
        When serializing to JSON
        Then all fields should be properly converted
        """
        response = ExternalDataQueryResponse(
            source_name="INE_BuildingPermits",
            data_frequency="monthly",
            last_refresh=datetime(2024, 12, 1, 10, 30),
            data_points=[
                ExternalDataPoint(
                    date=date(2024, 6, 1),
                    metric_name="permits",
                    value=150.0,
                    unit="count",
                )
            ],
            visualization_hint="line_chart",
            record_count=1,
        )

        json_str = response.model_dump_json()
        data = json.loads(json_str)

        assert data["source_name"] == "INE_BuildingPermits"
        assert data["record_count"] == 1
        assert len(data["data_points"]) == 1

    @pytest.mark.priority("P0")
    def test_model_weight_admin_request_action_required(self):
        """Test ModelWeightAdminRequest requires action field.

        Given no action specified
        When creating ModelWeightAdminRequest
        Then ValidationError should be raised
        """
        with pytest.raises(ValidationError) as exc_info:
            ModelWeightAdminRequest(metric="cement_demand")

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("action",) for e in errors)

    @pytest.mark.priority("P0")
    def test_model_weight_admin_request_valid_actions(self):
        """Test ModelWeightAdminRequest with valid action values.

        Given valid actions (view, run_backtest, reset)
        When creating ModelWeightAdminRequest
        Then model should accept the action
        """
        for action in ["view", "run_backtest", "reset"]:
            request = ModelWeightAdminRequest(action=action, metric=None)
            assert request.action == action
            assert request.metric is None

    @pytest.mark.priority("P1")
    def test_model_weight_admin_response_with_weights(self):
        """Test ModelWeightAdminResponse can contain weights data.

        Given a successful view action
        When creating response with weights
        Then weights list should be included
        """
        response = ModelWeightAdminResponse(
            action="view",
            success=True,
            message="Weights retrieved",
            weights=[{"metric": "cement_demand", "model": "LinearRegression", "weight": 0.7}],
            backtest_status=None,
        )

        assert response.success is True
        assert response.weights is not None
        assert len(response.weights) == 1
        assert response.weights[0]["metric"] == "cement_demand"


# =============================================================================
# [P1] Import Chain Tests
# =============================================================================


class TestToolRegistration:
    """[P1] Test MCP tool registration and decorator integrity."""

    @pytest.mark.priority("P1")
    def test_all_tools_have_mcp_decorator(self):
        """Test all tool functions have @mcp.tool() decorator.

        Given tools are registered via @mcp.tool()
        When importing tool functions
        Then they should have the .fn attribute from FastMCP

        Note: analytical_query_financial_documents is NOT decorated with @mcp.tool()
        as it's an internal helper called by the agentic workflow, not a direct MCP tool.
        """
        from raglite.main import (
            check_database_health,
            get_financial_forecast,
            get_financial_insights,
            get_ingestion_status,
            get_regressor_data,
            ingest_financial_document,
            ingest_financial_document_async,
            list_available_regressors,
            manage_model_weights,
            query_external_data,
            query_financial_documents,
            refresh_external_data,
            retrain_forecasting_models,
            validate_forecasting_accuracy,
        )

        tools = [
            ingest_financial_document,
            ingest_financial_document_async,
            get_ingestion_status,
            query_financial_documents,
            get_financial_forecast,
            get_financial_insights,
            query_external_data,
            refresh_external_data,
            check_database_health,
            manage_model_weights,
            retrain_forecasting_models,
            validate_forecasting_accuracy,
            list_available_regressors,
            get_regressor_data,
        ]

        for tool in tools:
            assert hasattr(tool, "fn"), f"{tool.__name__} missing .fn attribute"
            assert callable(tool.fn), f"{tool.__name__}.fn should be callable"

    @pytest.mark.priority("P1")
    @pytest.mark.asyncio
    async def test_mcp_tool_manager_lists_all_tools(self):
        """Test FastMCP tool manager contains all registered tools.

        Given tools are registered via decorators
        When listing tools from mcp._tool_manager
        Then at least 14 tools should be registered (current count as of Epic 8)

        Note: Using >= instead of exact count to allow for future expansion
        without breaking tests every time a new tool is added.
        """
        # Import all tool modules to ensure decorators run
        from raglite.main import mcp

        # Get tool list
        tools = await mcp._tool_manager.list_tools()
        tool_names = [t.name for t in tools]

        # Verify minimum tool count (14 as of Epic 8)
        assert len(tool_names) >= 14, f"Expected >=14 tools, got {len(tool_names)}"

        # Verify key tools are registered
        expected_tools = [
            "ingest_financial_document",
            "query_financial_documents",
            "check_database_health",
        ]

        for expected in expected_tools:
            assert expected in tool_names, f"Tool '{expected}' not registered"


# =============================================================================
# [P1] Error Handling Tests
# =============================================================================


class TestModuleBoundaries:
    """[P2] Test module boundaries and separation of concerns."""

    @pytest.mark.priority("P2")
    def test_ingestion_module_contains_ingestion_tools_only(self):
        """Test ingestion module only exposes ingestion-related tools.

        Given the ingestion module
        When inspecting public functions
        Then only ingestion tools should be exported
        """
        import raglite.mcp.tools.ingestion_tool as ingestion_module

        # Should have ingestion tools
        assert hasattr(ingestion_module, "ingest_financial_document")
        assert hasattr(ingestion_module, "ingest_financial_document_async")
        assert hasattr(ingestion_module, "get_ingestion_status")

        # Should not have query or other tools
        assert not hasattr(ingestion_module, "query_financial_documents")
        assert not hasattr(ingestion_module, "check_database_health")

    @pytest.mark.priority("P2")
    def test_query_module_contains_query_tools_only(self):
        """Test query module only exposes query-related tools.

        Given the query module
        When inspecting public functions
        Then only query tools should be exported

        Note: analytical_query_financial_documents is an internal helper, not an MCP tool.
        """
        import raglite.mcp.tools.query as query_module

        # Should have query tool (MCP-decorated)
        assert hasattr(query_module, "query_financial_documents")

        # Should have internal helper (not MCP-decorated, used by agentic workflow)
        assert hasattr(query_module, "analytical_query_financial_documents")

        # Should not have ingestion or other tools
        assert not hasattr(query_module, "ingest_financial_document")
        assert not hasattr(query_module, "check_database_health")

    @pytest.mark.priority("P2")
    def test_health_module_contains_health_tools_only(self):
        """Test health module only exposes health-related tools.

        Given the health module
        When inspecting public functions
        Then only health check tool should be exported
        """
        import raglite.mcp.tools.health as health_module

        # Should have health tool
        assert hasattr(health_module, "check_database_health")

        # Should not have other tools
        assert not hasattr(health_module, "ingest_financial_document")
        assert not hasattr(health_module, "query_financial_documents")


# =============================================================================
# [P3] Future-Proofing Tests
# =============================================================================
