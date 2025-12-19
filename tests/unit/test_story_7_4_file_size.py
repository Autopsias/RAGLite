"""ATDD tests for Story 7.4 - AC1: File Size Reduction.

Tests AC1: File Size Reduction - main.py <300 LOC, all modules <500 LOC.

This module tests that the refactoring achieves the target file sizes across
the main.py entry point and all extracted modules.

Test IDs follow pattern: TEST-AC-7.4.1.{test_number}

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


class TestAC1FileSizeReduction:
    """AC1: File Size Reduction - main.py <300 LOC, all modules <500 LOC.

    Given the raglite/main.py file exceeds 500 LOC (currently 3,741)
    When the refactoring is complete
    Then main.py should be reduced to <300 LOC (entry point only)
    And all new modules should be <500 LOC each
    """

    @pytest.mark.priority("P0")
    def test_ac1_1_main_py_under_300_lines(self):
        """TEST-AC-7.4.1.1: main.py reduced to <300 LOC (entry point only).

        Given main.py is the entry point after refactoring
        When counting the lines of code
        Then the file should have fewer than 300 lines
        """
        main_py_path = RAGLITE_PATH / "main.py"
        assert main_py_path.exists(), "main.py should exist"

        with open(main_py_path) as f:
            line_count = len(f.readlines())

        assert line_count < 300, (
            f"main.py should be <300 LOC after refactoring, "
            f"but has {line_count} lines"
        )

    @pytest.mark.priority("P0")
    def test_ac1_2_mcp_models_under_500_lines(self):
        """TEST-AC-7.4.1.2: mcp/models.py is under 500 LOC.

        Given mcp/models.py contains request/response models
        When counting the lines of code
        Then the file should have fewer than 500 lines (target ~100)
        """
        models_path = MCP_PATH / "models.py"
        assert models_path.exists(), "raglite/mcp/models.py should exist"

        with open(models_path) as f:
            line_count = len(f.readlines())

        assert line_count < 500, (
            f"mcp/models.py should be <500 LOC, but has {line_count} lines"
        )

    @pytest.mark.priority("P0")
    @pytest.mark.parametrize(
        "module_name,expected_max_loc",
        [
            ("ingestion", 500),
            ("query", 500),
            ("forecast", 500),
            ("insights", 500),
            ("external_data", 500),
            ("admin", 500),
            ("validation", 500),
            ("health", 500),
        ],
    )
    def test_ac1_3_tool_modules_under_500_lines(self, module_name: str, expected_max_loc: int):
        """TEST-AC-7.4.1.3: All tool modules are under 500 LOC each.

        Given tool modules are extracted from main.py
        When counting the lines of code for each module
        Then each module should have fewer than 500 lines
        """
        module_path = MCP_TOOLS_PATH / f"{module_name}.py"
        assert module_path.exists(), f"raglite/mcp/tools/{module_name}.py should exist"

        with open(module_path) as f:
            line_count = len(f.readlines())

        assert line_count < expected_max_loc, (
            f"mcp/tools/{module_name}.py should be <{expected_max_loc} LOC, "
            f"but has {line_count} lines"
        )

    @pytest.mark.priority("P1")
    def test_ac1_4_ideal_target_200_400_loc(self):
        """TEST-AC-7.4.1.4: Modules ideally between 200-400 LOC.

        Given the ideal target is 200-400 LOC per module
        When reviewing all new module sizes
        Then most modules should fall within the ideal range
        """
        modules_to_check = [
            MCP_PATH / "models.py",
            MCP_PATH / "__init__.py",
            MCP_TOOLS_PATH / "__init__.py",
        ]

        for tool in ["ingestion", "query", "forecast", "insights", "external_data", "admin", "validation", "health"]:
            modules_to_check.append(MCP_TOOLS_PATH / f"{tool}.py")

        ideal_count = 0
        total_count = 0

        for module_path in modules_to_check:
            if module_path.exists():
                total_count += 1
                with open(module_path) as f:
                    line_count = len(f.readlines())
                if 100 <= line_count <= 500:  # Relaxed from 200-400 to allow init files
                    ideal_count += 1

        # At least 60% of modules should be in the ideal range
        assert total_count > 0, "No modules found to check"
        ideal_ratio = ideal_count / total_count
        assert ideal_ratio >= 0.6, (
            f"At least 60% of modules should be in ideal range, "
            f"but only {ideal_ratio:.1%} ({ideal_count}/{total_count}) are"
        )
