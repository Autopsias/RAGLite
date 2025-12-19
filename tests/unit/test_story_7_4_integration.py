"""ATDD tests for Story 7.4 - AC5, AC6 & Integrity Tests.

Tests AC5: CI Compatibility - all tests pass, server starts.
Tests AC6: Documentation - module docstrings, architecture updates.
Tests Refactoring Integrity - ensures no functionality is broken.

This module tests CI compatibility, documentation requirements, and integration
integrity after refactoring.

Test IDs follow patterns: TEST-AC-7.4.5.{test_number}, TEST-AC-7.4.6.{test_number},
and TEST-INTEGRITY-7.4.{test_number}

Story: 7-4-refactor-main-py-mcp-module
Epic: 7 - Technical Debt & Code Quality
TDD Phase: RED (tests expected to fail until implementation complete)
"""

import ast
import asyncio
import importlib
from pathlib import Path

import pytest

# Base path for raglite package
RAGLITE_PATH = Path(__file__).parent.parent.parent / "raglite"
MCP_PATH = RAGLITE_PATH / "mcp"
MCP_TOOLS_PATH = MCP_PATH / "tools"


class TestAC5CICompatibility:
    """AC5: CI Compatibility - all tests pass, server starts.

    Given CI pipeline tests MCP server functionality
    When running in GitHub Actions
    Then all unit tests pass and MCP server starts correctly
    """

    @pytest.mark.priority("P0")
    def test_ac5_1_main_module_imports_successfully(self):
        """TEST-AC-7.4.5.1: raglite.main imports without errors.

        Given the refactored main.py should import cleanly
        When importing raglite.main
        Then no import errors should occur
        """
        try:
            import raglite.main

            # Force reload to catch any import issues
            importlib.reload(raglite.main)
            assert True
        except ImportError as e:
            pytest.fail(f"Failed to import raglite.main: {e}")

    @pytest.mark.priority("P0")
    def test_ac5_2_mcp_package_imports_successfully(self):
        """TEST-AC-7.4.5.2: raglite.mcp imports without errors.

        Given the new mcp package should import cleanly
        When importing raglite.mcp
        Then no import errors should occur
        """
        try:
            import raglite.mcp

            assert True
        except ImportError as e:
            pytest.fail(f"Failed to import raglite.mcp: {e}")

    @pytest.mark.priority("P0")
    def test_ac5_3_no_circular_imports(self):
        """TEST-AC-7.4.5.3: No circular imports between modules.

        Given circular imports can break the application
        When importing all mcp modules
        Then no circular import errors should occur
        """
        try:
            # Clear any cached imports
            import sys

            mcp_modules = [
                "raglite.mcp",
                "raglite.mcp.models",
                "raglite.mcp.tools",
                "raglite.mcp.tools.ingestion",
                "raglite.mcp.tools.query",
                "raglite.mcp.tools.forecast",
                "raglite.mcp.tools.insights",
                "raglite.mcp.tools.external_data",
                "raglite.mcp.tools.admin",
                "raglite.mcp.tools.validation",
                "raglite.mcp.tools.health",
            ]

            for module_name in mcp_modules:
                if module_name in sys.modules:
                    del sys.modules[module_name]

            # Now import all modules fresh
            for module_name in mcp_modules:
                importlib.import_module(module_name)

            assert True
        except ImportError as e:
            pytest.fail(f"Circular import detected: {e}")

    @pytest.mark.priority("P0")
    def test_ac5_4_mcp_server_main_function_exists(self):
        """TEST-AC-7.4.5.4: main() function exists for server startup.

        Given the MCP server needs an entry point
        When checking raglite.main
        Then main() function should exist and be callable
        """
        from raglite.main import main

        assert main is not None
        assert callable(main)


class TestAC6Documentation:
    """AC6: Documentation - module docstrings, architecture updates.

    Given the refactored structure changes module organization
    When updating documentation
    Then module docstrings should explain tool purposes
    """

    @pytest.mark.priority("P1")
    def test_ac6_1_main_py_has_docstring(self):
        """TEST-AC-7.4.6.1: main.py has module docstring.

        Given main.py is the entry point
        When checking for documentation
        Then it should have a module docstring explaining its purpose
        """
        main_py_path = RAGLITE_PATH / "main.py"
        assert main_py_path.exists()

        with open(main_py_path) as f:
            content = f.read()

        tree = ast.parse(content)
        docstring = ast.get_docstring(tree)

        assert docstring is not None, "main.py should have a module docstring"
        assert len(docstring) > 50, "main.py docstring should be descriptive"

    @pytest.mark.priority("P1")
    def test_ac6_2_mcp_init_has_docstring(self):
        """TEST-AC-7.4.6.2: mcp/__init__.py has module docstring.

        Given mcp package provides the tool exports
        When checking for documentation
        Then it should have a module docstring explaining exports
        """
        init_path = MCP_PATH / "__init__.py"
        assert init_path.exists(), "mcp/__init__.py should exist"

        with open(init_path) as f:
            content = f.read()

        tree = ast.parse(content)
        docstring = ast.get_docstring(tree)

        assert docstring is not None, "mcp/__init__.py should have a module docstring"

    @pytest.mark.priority("P1")
    @pytest.mark.parametrize(
        "tool_module",
        [
            "ingestion",
            "query",
            "forecast",
            "insights",
            "external_data",
            "admin",
            "validation",
            "health",
        ],
    )
    def test_ac6_3_tool_modules_have_docstrings(self, tool_module: str):
        """TEST-AC-7.4.6.3: All tool modules have docstrings.

        Given tool modules need documentation for maintainability
        When checking each tool module
        Then it should have a module docstring explaining its purpose
        """
        module_path = MCP_TOOLS_PATH / f"{tool_module}.py"
        assert module_path.exists(), f"mcp/tools/{tool_module}.py should exist"

        with open(module_path) as f:
            content = f.read()

        tree = ast.parse(content)
        docstring = ast.get_docstring(tree)

        assert docstring is not None, (
            f"mcp/tools/{tool_module}.py should have a module docstring"
        )


class TestRefactoringIntegrity:
    """Integration tests to ensure refactoring does not break functionality.

    These tests verify that the refactored code maintains the same behavior
    as the original monolithic main.py.
    """

    @pytest.mark.priority("P0")
    def test_integrity_1_all_tools_registered_to_mcp(self):
        """TEST-INTEGRITY-7.4.1: All tools are registered with FastMCP instance.

        Given tools use @mcp.tool() decorator
        When importing all tool modules
        Then all tools should be registered with the mcp instance
        """
        from raglite.main import mcp

        # Import all tool modules to trigger decorator registration
        import raglite.mcp.tools.ingestion
        import raglite.mcp.tools.query
        import raglite.mcp.tools.forecast
        import raglite.mcp.tools.insights
        import raglite.mcp.tools.external_data
        import raglite.mcp.tools.admin
        import raglite.mcp.tools.validation
        import raglite.mcp.tools.health

        # Check that tools are registered
        # FastMCP stores tools in _tool_manager
        assert hasattr(mcp, "_tool_manager"), "mcp should have _tool_manager attribute"

        # At least 15 tools should be registered
        # Use async list_tools() to get tool count
        tools = asyncio.run(mcp._tool_manager.list_tools())
        tool_count = len(tools)
        assert tool_count >= 15, (
            f"At least 15 tools should be registered with mcp, "
            f"but only {tool_count} found: {[t.name for t in tools]}"
        )

    @pytest.mark.priority("P1")
    def test_integrity_2_models_have_correct_fields(self):
        """TEST-INTEGRITY-7.4.2: Extracted models have correct fields.

        Given models are extracted to mcp/models.py
        When checking model fields
        Then they should match the original definitions
        """
        from raglite.mcp.models import (
            ExternalDataQueryRequest,
            ExternalDataPoint,
            ExternalDataQueryResponse,
        )

        # Check ExternalDataQueryRequest fields
        request_fields = ExternalDataQueryRequest.model_fields
        assert "source" in request_fields
        assert "date_range" in request_fields
        assert "metric" in request_fields

        # Check ExternalDataPoint fields
        point_fields = ExternalDataPoint.model_fields
        assert "date" in point_fields
        assert "metric_name" in point_fields
        assert "value" in point_fields
        assert "unit" in point_fields

        # Check ExternalDataQueryResponse fields
        response_fields = ExternalDataQueryResponse.model_fields
        assert "source_name" in response_fields
        assert "data_points" in response_fields
        assert "record_count" in response_fields
