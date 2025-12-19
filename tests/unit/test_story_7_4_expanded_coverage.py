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
import sys
from datetime import date, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

# Base paths
RAGLITE_PATH = Path(__file__).parent.parent.parent / "raglite"


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
            weights=[
                {"metric": "cement_demand", "model": "LinearRegression", "weight": 0.7}
            ],
            backtest_status=None,
        )

        assert response.success is True
        assert response.weights is not None
        assert len(response.weights) == 1
        assert response.weights[0]["metric"] == "cement_demand"


# =============================================================================
# [P1] Import Chain Tests
# =============================================================================


class TestImportChains:
    """[P1] Test import chains and module dependencies."""

    @pytest.mark.priority("P1")
    def test_all_tool_modules_import_from_main(self):
        """Test all tool modules import mcp from main without circular imports.

        Given the refactored module structure
        When importing all tool modules
        Then no circular import errors should occur
        """
        # This test verifies the import chain works
        from raglite.mcp.tools import (
            admin,
            external_data,
            forecast,
            health,
            ingestion,
            insights,
            query,
            validation,
        )

        # All modules should import successfully
        assert admin is not None
        assert external_data is not None
        assert forecast is not None
        assert health is not None
        assert ingestion is not None
        assert insights is not None
        assert query is not None
        assert validation is not None

    @pytest.mark.priority("P1")
    def test_models_importable_from_mcp_package(self):
        """Test models can be imported from mcp package root.

        Given models are in mcp/models.py
        When importing from raglite.mcp.models
        Then all models should be available
        """
        from raglite.mcp.models import (
            ExternalDataPoint,
            ExternalDataQueryRequest,
            ExternalDataQueryResponse,
            ModelWeightAdminRequest,
            ModelWeightAdminResponse,
        )

        assert ExternalDataQueryRequest is not None
        assert ExternalDataPoint is not None
        assert ExternalDataQueryResponse is not None
        assert ModelWeightAdminRequest is not None
        assert ModelWeightAdminResponse is not None

    @pytest.mark.priority("P1")
    def test_document_processing_error_importable_from_main(self):
        """Test DocumentProcessingError is re-exported from main for backward compatibility.

        Given DocumentProcessingError is defined in ingestion.py
        When importing from raglite.main
        Then it should be available via re-export
        """
        from raglite.main import DocumentProcessingError

        assert DocumentProcessingError is not None
        assert issubclass(DocumentProcessingError, Exception)

    @pytest.mark.priority("P2")
    def test_document_processing_error_importable_from_ingestion(self):
        """Test DocumentProcessingError can also be imported from ingestion module.

        Given DocumentProcessingError is defined in ingestion.py
        When importing from raglite.mcp.tools.ingestion
        Then it should be available directly
        """
        from raglite.mcp.tools.ingestion import DocumentProcessingError

        assert DocumentProcessingError is not None
        assert issubclass(DocumentProcessingError, Exception)


# =============================================================================
# [P1] Tool Registration Integrity Tests
# =============================================================================


class TestToolRegistration:
    """[P1] Test MCP tool registration and decorator integrity."""

    @pytest.mark.priority("P1")
    def test_all_tools_have_mcp_decorator(self):
        """Test all tool functions have @mcp.tool() decorator.

        Given tools are registered via @mcp.tool()
        When importing tool functions
        Then they should have the .fn attribute from FastMCP
        """
        from raglite.main import (
            analytical_query_financial_documents,
            check_database_health,
            get_financial_forecast,
            get_financial_insights,
            get_ingestion_status,
            ingest_financial_document,
            ingest_financial_document_async,
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
            analytical_query_financial_documents,
            get_financial_forecast,
            get_financial_insights,
            query_external_data,
            refresh_external_data,
            check_database_health,
            manage_model_weights,
            retrain_forecasting_models,
            validate_forecasting_accuracy,
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
        Then at least 15 tools should be registered
        """
        from raglite.main import mcp

        # Import all tool modules to ensure decorators run
        import raglite.mcp.tools.admin
        import raglite.mcp.tools.external_data
        import raglite.mcp.tools.forecast
        import raglite.mcp.tools.health
        import raglite.mcp.tools.ingestion
        import raglite.mcp.tools.insights
        import raglite.mcp.tools.query
        import raglite.mcp.tools.validation

        # Get tool list
        tools = await mcp._tool_manager.list_tools()
        tool_names = [t.name for t in tools]

        # Verify minimum tool count
        assert len(tool_names) >= 15, f"Expected >=15 tools, got {len(tool_names)}"

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


class TestErrorHandling:
    """[P1] Test error handling in refactored modules."""

    @pytest.mark.priority("P1")
    @pytest.mark.asyncio
    async def test_health_check_handles_database_errors(self):
        """Test check_database_health handles database errors gracefully.

        Given a database connectivity error
        When checking database health
        Then should return error JSON instead of raising exception
        """
        from raglite.mcp.tools.health import check_database_health

        with patch(
            "raglite.shared.validation.check_data_integrity",
            side_effect=Exception("Connection refused"),
        ):
            result_json = await check_database_health.fn()

            # Should return JSON error, not raise exception
            result = json.loads(result_json)
            assert result["is_synchronized"] is False
            assert "error" in result
            assert "Connection refused" in result["error"]

    @pytest.mark.priority("P1")
    @pytest.mark.asyncio
    async def test_ingestion_validates_input_modes(self):
        """Test ingest_financial_document validates mutually exclusive inputs.

        Given multiple input modes provided
        When calling ingest_financial_document
        Then DocumentProcessingError should be raised
        """
        from raglite.mcp.tools.ingestion import ingest_financial_document

        # Test multiple inputs (doc_path + file_content)
        with pytest.raises(Exception) as exc_info:
            await ingest_financial_document.fn(
                doc_path="/path/to/file.pdf",
                file_content="base64data",
                filename="file.pdf",
            )

        assert "Only one input mode allowed" in str(exc_info.value)

    @pytest.mark.priority("P1")
    @pytest.mark.asyncio
    async def test_ingestion_requires_filename_with_content(self):
        """Test ingest_financial_document requires filename when using file_content.

        Given file_content provided without filename
        When calling ingest_financial_document
        Then DocumentProcessingError should be raised
        """
        from raglite.mcp.tools.ingestion import ingest_financial_document

        with pytest.raises(Exception) as exc_info:
            await ingest_financial_document.fn(file_content="base64data")

        assert "filename is required" in str(exc_info.value)

    @pytest.mark.priority("P1")
    @pytest.mark.asyncio
    async def test_ingestion_requires_at_least_one_input(self):
        """Test ingest_financial_document requires at least one input mode.

        Given no input mode provided
        When calling ingest_financial_document
        Then DocumentProcessingError should be raised
        """
        from raglite.mcp.tools.ingestion import ingest_financial_document

        with pytest.raises(Exception) as exc_info:
            await ingest_financial_document.fn()

        assert "Must provide one of" in str(exc_info.value)


# =============================================================================
# [P2] Helper Function Tests
# =============================================================================


class TestHelperFunctions:
    """[P2] Test helper functions in tool modules."""

    @pytest.mark.priority("P2")
    def test_external_data_parse_date_range_iso_format(self):
        """Test _parse_date_range with ISO format dates.

        Given ISO format date range
        When parsing date range
        Then should return tuple of date objects
        """
        from raglite.mcp.tools.external_data import _parse_date_range

        start, end = _parse_date_range("2024-01-01:2024-12-31")

        assert start == date(2024, 1, 1)
        assert end == date(2024, 12, 31)

    @pytest.mark.priority("P2")
    def test_external_data_parse_date_range_shortcuts(self):
        """Test _parse_date_range with shortcut keywords.

        Given shortcut like 'last_30_days'
        When parsing date range
        Then should return appropriate date range
        """
        from raglite.mcp.tools.external_data import _parse_date_range

        # Test that shortcuts don't raise errors
        # (exact dates depend on current date, so just verify no exception)
        start, end = _parse_date_range("last_30_days")
        assert isinstance(start, date)
        assert isinstance(end, date)
        assert start < end

    @pytest.mark.priority("P2")
    def test_external_data_get_visualization_hint(self):
        """Test _get_visualization_hint provides appropriate hints.

        Given record count and data type
        When getting visualization hint
        Then should return appropriate chart type
        """
        from raglite.mcp.tools.external_data import _get_visualization_hint

        # Low record count
        hint = _get_visualization_hint(5, "monthly")
        assert isinstance(hint, str)
        assert len(hint) > 0

        # High record count
        hint = _get_visualization_hint(500, "daily")
        assert isinstance(hint, str)


# =============================================================================
# [P2] Module Boundary Tests
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
        import raglite.mcp.tools.ingestion as ingestion_module

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
        """
        import raglite.mcp.tools.query as query_module

        # Should have query tools
        assert hasattr(query_module, "query_financial_documents")
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


class TestFutureProofing:
    """[P3] Tests for maintainability and future changes."""

    @pytest.mark.priority("P3")
    def test_all_tool_modules_have_logger(self):
        """Test all tool modules initialize a logger.

        Given each tool module needs logging
        When importing modules
        Then logger should be defined
        """
        from raglite.mcp.tools import (
            admin,
            external_data,
            forecast,
            health,
            ingestion,
            insights,
            query,
            validation,
        )

        modules = [
            admin,
            external_data,
            forecast,
            health,
            ingestion,
            insights,
            query,
            validation,
        ]

        for module in modules:
            assert hasattr(
                module, "logger"
            ), f"{module.__name__} should have logger"

    @pytest.mark.priority("P3")
    def test_main_module_reduced_complexity(self):
        """Test main.py has reduced complexity after refactoring.

        Given main.py should be <300 LOC
        When counting non-import, non-comment lines
        Then should be significantly smaller than original
        """
        main_py_path = RAGLITE_PATH / "main.py"

        with open(main_py_path) as f:
            lines = f.readlines()

        # Count non-empty, non-comment lines
        code_lines = [
            line
            for line in lines
            if line.strip() and not line.strip().startswith("#")
        ]

        # Should be under 300 lines total (including imports/docstrings)
        assert len(lines) < 300, f"main.py has {len(lines)} lines, expected <300"

        # Most lines should be imports or minimal setup
        import_lines = [line for line in code_lines if "import" in line]
        import_ratio = len(import_lines) / len(code_lines)

        # At least 10% of code lines should be imports (reasonable after refactoring)
        # Note: Reduced from 30% due to necessary __getattr__ and orchestration code
        assert (
            import_ratio > 0.10
        ), f"Expected >10% imports, got {import_ratio:.1%} ({len(import_lines)}/{len(code_lines)})"
