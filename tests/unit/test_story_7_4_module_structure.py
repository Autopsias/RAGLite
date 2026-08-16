"""ATDD tests for Story 7.4 - AC2: New Module Structure.

Tests AC2: New Module Structure - raglite/mcp/ package with organized modules.

This module tests that the refactoring creates the correct directory structure
with all required packages and modules in the right locations.

Test IDs follow pattern: TEST-AC-7.4.2.{test_number}

Story: 7-4-refactor-main-py-mcp-module
Epic: 7 - Technical Debt & Code Quality
TDD Phase: RED (tests expected to fail until implementation complete)
"""

from pathlib import Path

import pytest

# Base path for raglite package
RAGLITE_PATH = Path(__file__).parent.parent.parent / "raglite"
MCP_PATH = RAGLITE_PATH / "mcp"
MCP_TOOLS_PATH = MCP_PATH / "tools"


class TestAC2NewModuleStructure:
    """AC2: New Module Structure - raglite/mcp/ package with organized modules.

    Given MCP tools are currently monolithic in main.py
    When creating the new modular structure
    Then create raglite/mcp/ package with organized modules
    """

    @pytest.mark.priority("P0")
    def test_ac2_1_mcp_package_exists(self):
        """TEST-AC-7.4.2.1: raglite/mcp/ package directory exists.

        Given the refactoring requires a new package structure
        When checking the filesystem
        Then raglite/mcp/ directory should exist
        """
        assert MCP_PATH.exists(), "raglite/mcp/ directory should exist"
        assert MCP_PATH.is_dir(), "raglite/mcp/ should be a directory"

    @pytest.mark.priority("P0")
    def test_ac2_2_mcp_init_exists(self):
        """TEST-AC-7.4.2.2: raglite/mcp/__init__.py exists.

        Given the mcp package needs proper initialization
        When checking for __init__.py
        Then raglite/mcp/__init__.py should exist
        """
        init_path = MCP_PATH / "__init__.py"
        assert init_path.exists(), "raglite/mcp/__init__.py should exist"

    @pytest.mark.priority("P0")
    def test_ac2_3_mcp_models_exists(self):
        """TEST-AC-7.4.2.3: raglite/mcp/models.py exists.

        Given request/response models should be extracted
        When checking for models.py
        Then raglite/mcp/models.py should exist
        """
        models_path = MCP_PATH / "models.py"
        assert models_path.exists(), "raglite/mcp/models.py should exist"

    @pytest.mark.priority("P0")
    def test_ac2_4_mcp_tools_package_exists(self):
        """TEST-AC-7.4.2.4: raglite/mcp/tools/ package directory exists.

        Given tools should be organized in a subpackage
        When checking the filesystem
        Then raglite/mcp/tools/ directory should exist
        """
        assert MCP_TOOLS_PATH.exists(), "raglite/mcp/tools/ directory should exist"
        assert MCP_TOOLS_PATH.is_dir(), "raglite/mcp/tools/ should be a directory"

    @pytest.mark.priority("P0")
    def test_ac2_5_mcp_tools_init_exists(self):
        """TEST-AC-7.4.2.5: raglite/mcp/tools/__init__.py exists.

        Given the tools subpackage needs proper initialization
        When checking for __init__.py
        Then raglite/mcp/tools/__init__.py should exist
        """
        init_path = MCP_TOOLS_PATH / "__init__.py"
        assert init_path.exists(), "raglite/mcp/tools/__init__.py should exist"

    @pytest.mark.priority("P0")
    @pytest.mark.parametrize(
        "tool_module",
        [
            "ingestion_tool",
            "query",
            "forecast",
            "insights",
            "admin",
            "validation",
            "health",
        ],
    )
    def test_ac2_6_tool_modules_exist(self, tool_module: str):
        """TEST-AC-7.4.2.6: All required tool modules exist.

        Given specific tool modules are required per the story
        When checking for each module
        Then all tool modules should exist

        Note: external_data module was never created (not in scope for Story 7.4).
        External data functionality exists in raglite/external_data/ package.
        """
        module_path = MCP_TOOLS_PATH / f"{tool_module}.py"
        assert module_path.exists(), f"raglite/mcp/tools/{tool_module}.py should exist"
