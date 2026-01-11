"""AC-8.5.4 Tests: Full Test Suite Coverage.

These tests verify that the full test suite has no raglite deprecation warnings.

Story: docs/stories/8-5-deprecation-cleanup.md
Epic: 8 - Technical Debt Reduction
"""

import subprocess
import sys
from pathlib import Path

import pytest


class TestAC854FullSuiteCoverage:
    """AC-8.5-4: Verify full test suite has no raglite deprecation warnings."""

    @pytest.mark.priority("P1")
    def test_ac_8_5_4_1_no_raglite_deprecation_in_unit_tests(self):
        """TEST-AC-8.5.4.1: Unit tests should not emit raglite deprecation warnings.

        Given: The unit test suite
        When: Tests are collected with deprecation warnings enabled
        Then: No deprecation warnings from raglite code should appear
        """
        project_root = Path(__file__).parent.parent.parent.parent

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                str(project_root / "tests/unit"),
                "--collect-only",
                "-W",
                "default::DeprecationWarning",
                "-q",
            ],
            capture_output=True,
            text=True,
            cwd=str(project_root),
            timeout=120,
        )

        combined_output = result.stdout + result.stderr

        # Check for raglite-specific deprecation warnings
        raglite_deprecations = []

        for line in combined_output.split("\n"):
            if "DeprecationWarning" in line and "raglite" in line.lower():
                raglite_deprecations.append(line.strip())

        assert len(raglite_deprecations) == 0, (
            f"Found {len(raglite_deprecations)} raglite deprecation warning(s):\n"
            + "\n".join(raglite_deprecations[:10])
        )

    @pytest.mark.priority("P1")
    def test_ac_8_5_4_2_historical_data_warnings_count_zero(self):
        """TEST-AC-8.5.4.2: Grep for historical_data warnings should return 0 matches.

        Given: The test suite source code
        When: Searching for deprecated historical_data usage patterns
        Then: Count of deprecated usages should be 0
        """
        project_root = Path(__file__).parent.parent.parent.parent
        tests_dir = project_root / "tests"

        # Count files with historical_data parameter usage in DEPRECATED functions
        # Only generate_forecast() and generate_ensemble_forecast() are deprecated
        deprecated_usage_count = 0
        files_with_usage = []

        for py_file in tests_dir.rglob("*.py"):
            if py_file.name.startswith("test_story_8_5"):
                continue  # Skip this ATDD file

            content = py_file.read_text()

            # Pattern: Check for historical_data in generate_forecast/generate_ensemble_forecast calls
            # We need to look back a few lines to see the function being called
            lines = content.split("\n")
            for i, line in enumerate(lines, 1):
                # Skip comments and string literals
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                if stripped.startswith('"""') or stripped.startswith("'''"):
                    continue

                # Check if this line has historical_data=
                if "historical_data=" in line:
                    # Exclude mock return values, docstrings, dict/list definitions
                    if "return_value" in line or "mock" in line.lower():
                        continue
                    if "deprecated" in line.lower():
                        continue
                    if line.strip().startswith("historical_data=") and "[" in line:
                        continue

                    # Look back up to 10 lines to find the function call
                    context_start = max(0, i - 11)
                    context = "\n".join(lines[context_start:i])

                    # Only flag if calling generate_forecast (historical_data is optional there)
                    # NOTE: generate_ensemble_forecast() REQUIRES historical_data as positional arg,
                    # so those calls are NOT deprecated - they must pass it.
                    # Exclude private _generate_* functions and other internal functions
                    if (
                        "generate_forecast(" in context
                        and "generate_ensemble_forecast(" not in context
                    ):
                        # Make sure it's not _generate_forecast (private)
                        if not ("_generate_forecast(" in context or "_generate_" in context):
                            deprecated_usage_count += 1
                            rel_path = py_file.relative_to(project_root)
                            files_with_usage.append(f"{rel_path}:{i}")

        assert deprecated_usage_count == 0, (
            f"Found {deprecated_usage_count} deprecated historical_data= usage(s):\n"
            + "\n".join(files_with_usage[:20])
        )

    @pytest.mark.priority("P0")
    def test_ac_8_5_4_3_verification_commands_pass(self):
        """TEST-AC-8.5.4.3: All AC verification commands from story should pass.

        Given: The verification commands specified in Story 8.5
        When: Each command is executed
        Then: All commands should return success/zero counts
        """
        project_root = Path(__file__).parent.parent.parent.parent

        # Command 1: No PytestRemovedIn9Warning in chunking tests
        result1 = subprocess.run(
            [
                "bash",
                "-c",
                f"cd {project_root} && "
                f"{sys.executable} -m pytest tests/integration/test_chunking_*.py "
                f"-W error --collect-only -q 2>&1 | grep -c PytestRemovedIn9Warning || echo 0",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )

        pytest_removed_count = int(result1.stdout.strip().split("\n")[-1])

        # Command 2: No historical_data deprecation warnings
        result2 = subprocess.run(
            [
                "bash",
                "-c",
                f"cd {project_root} && "
                f"{sys.executable} -m pytest tests/unit/forecasting -W default --collect-only -q 2>&1 | "
                f"grep -c 'historical_data' || echo 0",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )

        historical_data_count = int(result2.stdout.strip().split("\n")[-1])

        # Command 3: Import verification (no deprecation on import)
        result3 = subprocess.run(
            [
                sys.executable,
                "-W",
                "error::DeprecationWarning",
                "-c",
                "from raglite.ingestion.document_ingestion import ingest_document",
            ],
            capture_output=True,
            text=True,
            cwd=str(project_root),
            timeout=30,
        )

        import_success = result3.returncode == 0

        # Aggregate results
        failures = []
        if pytest_removed_count > 0:
            failures.append(f"PytestRemovedIn9Warning count: {pytest_removed_count}")
        if historical_data_count > 0:
            failures.append(f"historical_data warning count: {historical_data_count}")
        if not import_success:
            failures.append(f"Import verification failed: {result3.stderr}")

        assert len(failures) == 0, "Verification commands failed:\n" + "\n".join(failures)
