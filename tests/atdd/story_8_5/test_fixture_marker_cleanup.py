"""AC-8.5.3 Tests: Fixture Marker Cleanup (pytest 9.0 compatibility).

These tests verify that fixture markers are removed for pytest 9.0 compatibility.

Story: docs/stories/8-5-deprecation-cleanup.md
Epic: 8 - Technical Debt Reduction
"""

import ast
import subprocess
import sys
from pathlib import Path

import pytest


class TestAC853FixtureMarkerCleanup:
    """AC-8.5-3: Verify fixture markers are removed for pytest 9.0 compatibility."""

    CHUNKING_TEST_FILES = [
        "tests/integration/test_chunking_slow.py",
        "tests/integration/test_chunking_core.py",
        "tests/integration/test_chunking_extended.py",
    ]

    @pytest.mark.priority("P0")
    @pytest.mark.parametrize("test_file", CHUNKING_TEST_FILES)
    def test_ac_8_5_3_1_no_marker_on_fixtures(self, test_file: str):
        """TEST-AC-8.5.3.1: Fixtures should not have pytest.mark decorators.

        Given: Test file with fixture definitions
        When: The fixtures are analyzed for pytest.mark decorators
        Then: No pytest.mark.* should be applied to @pytest.fixture functions
        """
        project_root = Path(__file__).parent.parent.parent.parent
        file_path = project_root / test_file

        if not file_path.exists():
            # Skip if test file was removed during refactoring
            pytest.skip(f"Test file not found: {test_file}")

        content = file_path.read_text()

        # Parse the file to find fixture functions with markers
        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            pytest.fail(f"Failed to parse {test_file}: {e}")

        violations = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                decorators = node.decorator_list
                has_fixture = False
                has_mark = False
                mark_names = []

                for dec in decorators:
                    # Check for @pytest.fixture
                    if isinstance(dec, ast.Attribute):
                        if dec.attr == "fixture":
                            has_fixture = True
                    elif isinstance(dec, ast.Call):
                        if isinstance(dec.func, ast.Attribute):
                            if dec.func.attr == "fixture":
                                has_fixture = True

                    # Check for @pytest.mark.*
                    if isinstance(dec, ast.Attribute):
                        if isinstance(dec.value, ast.Attribute):
                            if dec.value.attr == "mark":
                                has_mark = True
                                mark_names.append(dec.attr)
                    elif isinstance(dec, ast.Call):
                        if isinstance(dec.func, ast.Attribute):
                            if isinstance(dec.func.value, ast.Attribute):
                                if dec.func.value.attr == "mark":
                                    has_mark = True
                                    mark_names.append(dec.func.attr)

                if has_fixture and has_mark:
                    violations.append(f"{node.name} (marks: {mark_names})")

        assert len(violations) == 0, (
            f"Found fixtures with pytest.mark decorators in {test_file}:\n"
            + "\n".join(f"  - {v}" for v in violations)
            + "\n\npytest 9.0 will error on marks applied to fixtures. "
            "Remove the @pytest.mark.* decorator from fixture functions."
        )

    @pytest.mark.priority("P1")
    def test_ac_8_5_3_2_no_pytest_removed_in_9_warning(self):
        """TEST-AC-8.5.3.2: Running chunking tests should not produce PytestRemovedIn9Warning.

        Given: The chunking test files
        When: Tests are collected with warnings enabled
        Then: No PytestRemovedIn9Warning should appear in output
        """
        project_root = Path(__file__).parent.parent.parent.parent

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                str(project_root / "tests/integration/test_chunking_core.py"),
                str(project_root / "tests/integration/test_chunking_slow.py"),
                str(project_root / "tests/integration/test_chunking_extended.py"),
                "--collect-only",
                "-W",
                "default",
                "-q",
            ],
            capture_output=True,
            text=True,
            cwd=str(project_root),
            timeout=60,
        )

        combined_output = result.stdout + result.stderr

        # Check for PytestRemovedIn9Warning
        warning_count = combined_output.count("PytestRemovedIn9Warning")

        assert warning_count == 0, (
            f"Found {warning_count} PytestRemovedIn9Warning warning(s) in chunking tests.\n"
            f"Remove @pytest.mark.* decorators from fixture functions.\n"
            f"Output: {combined_output[:1000]}"
        )
