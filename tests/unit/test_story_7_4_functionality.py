"""ATDD tests for Story 7.4 - AC3 & AC4: Functionality & Compatibility.

Tests AC3: Functionality Preserved - all 16 MCP tools remain functional.
Tests AC4: Backward Compatibility - re-exports, no breaking changes.

This module tests that tools are importable, functional, and maintain backward
compatibility after refactoring.

Test IDs follow patterns: TEST-AC-7.4.3.{test_number} and TEST-AC-7.4.4.{test_number}

Story: 7-4-refactor-main-py-mcp-module
Epic: 7 - Technical Debt & Code Quality
TDD Phase: RED (tests expected to fail until implementation complete)
"""

import pytest


class TestAC3FunctionalityPreserved:
    """AC3: Functionality Preserved - all 16 MCP tools remain functional.

    Given the existing MCP tools serve production traffic
    When tool extraction is complete
    Then all 16 MCP tools should remain functional
    """

    # List of all 16 MCP tools that must be preserved
    MCP_TOOLS = [
        "ingest_financial_document",
        "ingest_financial_document_async",
        "get_ingestion_status",
        "query_financial_documents",
        "analytical_query_financial_documents",
        "get_financial_forecast",
        "get_financial_insights",
        "query_external_data",
        "refresh_external_data",
        "check_database_health",
        "manage_model_weights",
        "retrain_forecasting_models",
        "validate_forecasting_accuracy",
        "list_available_regressors",
        "get_regressor_data",
    ]

    @pytest.mark.priority("P0")
    def test_ac3_1_mcp_server_instance_available(self):
        """TEST-AC-7.4.3.1: FastMCP server instance is available.

        Given the MCP server should be accessible after refactoring
        When importing from raglite.main
        Then the mcp instance should be available
        """
        from raglite.main import mcp

        assert mcp is not None, "mcp instance should be available"
        assert mcp.name == "RAGLite", "mcp server should be named 'RAGLite'"

    @pytest.mark.priority("P0")
    def test_ac3_2_all_tools_importable_from_main(self):
        """TEST-AC-7.4.3.2: All MCP tools are importable from raglite.main.

        Given tools may be imported from main.py for backward compatibility
        When importing tools from raglite.main
        Then all 16 tools should be importable
        """
        from raglite import main

        for tool_name in self.MCP_TOOLS:
            assert hasattr(main, tool_name), (
                f"Tool '{tool_name}' should be importable from raglite.main"
            )

    @pytest.mark.priority("P0")
    def test_ac3_3_tools_have_fn_attribute(self):
        """TEST-AC-7.4.3.3: All MCP tools have the .fn attribute (FastMCP decorator).

        Given FastMCP decorators add a .fn attribute to tools
        When checking tool attributes
        Then all tools should have callable .fn attribute
        """
        from raglite import main

        for tool_name in self.MCP_TOOLS:
            tool = getattr(main, tool_name)
            assert hasattr(tool, "fn"), (
                f"Tool '{tool_name}' should have .fn attribute from FastMCP decorator"
            )
            assert callable(tool.fn), f"Tool '{tool_name}'.fn should be callable"

    @pytest.mark.priority("P0")
    def test_ac3_4_tool_count_preserved(self):
        """TEST-AC-7.4.3.4: Total tool count is preserved (15+ tools).

        Given the story documents 16 tools (15 unique names listed)
        When counting registered tools
        Then at least 15 tools should be available
        """
        from raglite import main

        available_tools = [tool_name for tool_name in self.MCP_TOOLS if hasattr(main, tool_name)]

        assert len(available_tools) >= 15, (
            f"At least 15 MCP tools should be available, "
            f"but only found {len(available_tools)}: {available_tools}"
        )

    @pytest.mark.priority("P1")
    def test_ac3_5_document_processing_error_available(self):
        """TEST-AC-7.4.3.5: DocumentProcessingError exception is available.

        Given DocumentProcessingError is used by tools
        When importing from raglite.main
        Then DocumentProcessingError should be available
        """
        from raglite.main import DocumentProcessingError

        assert DocumentProcessingError is not None
        assert issubclass(DocumentProcessingError, Exception)


class TestAC4BackwardCompatibility:
    """AC4: Backward Compatibility - re-exports, no breaking changes.

    Given other modules may import from raglite.main
    When refactoring the module structure
    Then backward-compatible re-exports should be added
    """

    @pytest.mark.priority("P0")
    def test_ac4_1_document_processing_error_reexport(self):
        """TEST-AC-7.4.4.1: DocumentProcessingError re-exported from main.py.

        Given DocumentProcessingError is imported by other modules
        When importing from raglite.main
        Then it should still be available for backward compatibility
        """
        from raglite.main import DocumentProcessingError

        assert DocumentProcessingError is not None
        assert issubclass(DocumentProcessingError, Exception)

    @pytest.mark.priority("P0")
    def test_ac4_2_mcp_instance_available_from_main(self):
        """TEST-AC-7.4.4.2: mcp instance available from raglite.main.

        Given the mcp instance is used by other modules
        When importing from raglite.main
        Then the mcp instance should be available
        """
        from raglite.main import mcp

        assert mcp is not None
        assert mcp.name == "RAGLite"

    @pytest.mark.priority("P1")
    def test_ac4_3_models_available_from_mcp_package(self):
        """TEST-AC-7.4.4.3: Models available from raglite.mcp package.

        Given models should be available from the new mcp package
        When importing from raglite.mcp
        Then request/response models should be available
        """
        from raglite.mcp.models import (
            ExternalDataPoint,
            ExternalDataQueryRequest,
            ExternalDataQueryResponse,
        )

        assert ExternalDataQueryRequest is not None
        assert ExternalDataPoint is not None
        assert ExternalDataQueryResponse is not None

    @pytest.mark.priority("P1")
    def test_ac4_4_tools_available_from_mcp_tools(self):
        """TEST-AC-7.4.4.4: Tools available from raglite.mcp.tools.

        Given tools should be available from the new package structure
        When importing from raglite.mcp.tools
        Then at least some tools should be importable
        """
        from raglite.mcp.tools.health import check_database_health
        from raglite.mcp.tools.ingestion import ingest_financial_document
        from raglite.mcp.tools.query import query_financial_documents

        assert ingest_financial_document is not None
        assert query_financial_documents is not None
        assert check_database_health is not None
