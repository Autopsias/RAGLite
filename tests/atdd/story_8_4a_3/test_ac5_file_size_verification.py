"""[P1] ATDD tests for AC-8.4a-3.5: All resulting files <500 LOC verified.

Given the file size limits are enforced by CI
When the refactoring is complete
Then all new test files are verified under 500 LOC by check_file_sizes.py

These tests verify file size compliance using the project's check_file_sizes.py script.
"""

import json
import subprocess
from pathlib import Path

import pytest

from .conftest import MODERATE_PRIORITY_FILES, count_lines


class TestAC5FileSizeVerification:
    """[P1] Tests for AC-8.4a-3.5 - File size verification."""

    @pytest.mark.atdd
    def test_ac_8_4a_3_5_1_check_file_sizes_no_violations(self) -> None:
        """TEST-AC-8.4a-3.5.1: check_file_sizes.py reports no new violations."""
        project_root = Path(__file__).parent.parent.parent.parent
        script_path = project_root / "scripts" / "check_file_sizes.py"

        if not script_path.exists():
            pytest.skip("check_file_sizes.py script not found")

        result = subprocess.run(
            ["python", str(script_path)],
            capture_output=True,
            text=True,
            cwd=str(project_root),
            timeout=60,
        )
        # Script returns 0 if no new violations
        assert result.returncode == 0, (
            f"File size violations detected:\n{result.stdout}\n{result.stderr}"
        )

    @pytest.mark.atdd
    def test_ac_8_4a_3_5_2_forecasting_files_under_limit(
        self, tests_unit_path: Path, file_size_limit: int
    ) -> None:
        """TEST-AC-8.4a-3.5.2: Forecasting test files all under 500 LOC."""
        forecasting_path = tests_unit_path / "forecasting"
        if not forecasting_path.exists():
            pytest.skip("Forecasting directory not yet created")

        violations = []
        for test_file in forecasting_path.rglob("test_*.py"):
            loc = count_lines(test_file)
            if loc > file_size_limit:
                violations.append(f"{test_file.name}: {loc} LOC")

        assert not violations, f"Forecasting files exceeding {file_size_limit} LOC:\n" + "\n".join(
            violations
        )

    @pytest.mark.atdd
    def test_ac_8_4a_3_5_3_external_data_files_under_limit(
        self, tests_unit_path: Path, file_size_limit: int
    ) -> None:
        """TEST-AC-8.4a-3.5.3: External data test files all under 500 LOC."""
        external_path = tests_unit_path / "external_data"
        if not external_path.exists():
            pytest.skip("External data directory not yet created")

        violations = []
        for test_file in external_path.rglob("test_*.py"):
            loc = count_lines(test_file)
            if loc > file_size_limit:
                violations.append(f"{test_file.name}: {loc} LOC")

        assert not violations, (
            f"External data files exceeding {file_size_limit} LOC:\n" + "\n".join(violations)
        )

    @pytest.mark.atdd
    def test_ac_8_4a_3_5_4_ingestion_files_under_limit(
        self, tests_unit_path: Path, file_size_limit: int
    ) -> None:
        """TEST-AC-8.4a-3.5.4: Ingestion test files all under 500 LOC."""
        ingestion_path = tests_unit_path / "ingestion"
        if not ingestion_path.exists():
            pytest.skip("Ingestion directory not yet created")

        violations = []
        for test_file in ingestion_path.rglob("test_*.py"):
            loc = count_lines(test_file)
            if loc > file_size_limit:
                violations.append(f"{test_file.name}: {loc} LOC")

        assert not violations, f"Ingestion files exceeding {file_size_limit} LOC:\n" + "\n".join(
            violations
        )

    @pytest.mark.atdd
    def test_ac_8_4a_3_5_5_insights_files_under_limit(
        self, tests_unit_path: Path, file_size_limit: int
    ) -> None:
        """TEST-AC-8.4a-3.5.5: Insights test files all under 500 LOC."""
        insights_path = tests_unit_path / "insights"
        if not insights_path.exists():
            pytest.skip("Insights directory not yet created")

        violations = []
        for test_file in insights_path.rglob("test_*.py"):
            loc = count_lines(test_file)
            if loc > file_size_limit:
                violations.append(f"{test_file.name}: {loc} LOC")

        assert not violations, f"Insights files exceeding {file_size_limit} LOC:\n" + "\n".join(
            violations
        )

    @pytest.mark.atdd
    def test_ac_8_4a_3_5_6_retrieval_files_under_limit(
        self, tests_unit_path: Path, file_size_limit: int
    ) -> None:
        """TEST-AC-8.4a-3.5.6: Retrieval test files all under 500 LOC."""
        retrieval_path = tests_unit_path / "retrieval"
        if not retrieval_path.exists():
            pytest.skip("Retrieval directory not yet created")

        violations = []
        for test_file in retrieval_path.rglob("test_*.py"):
            loc = count_lines(test_file)
            if loc > file_size_limit:
                violations.append(f"{test_file.name}: {loc} LOC")

        assert not violations, f"Retrieval files exceeding {file_size_limit} LOC:\n" + "\n".join(
            violations
        )

    @pytest.mark.atdd
    def test_ac_8_4a_3_5_7_shared_files_under_limit(
        self, tests_unit_path: Path, file_size_limit: int
    ) -> None:
        """TEST-AC-8.4a-3.5.7: Shared test files all under 500 LOC."""
        shared_path = tests_unit_path / "shared"
        if not shared_path.exists():
            pytest.skip("Shared directory not yet created")

        violations = []
        for test_file in shared_path.rglob("test_*.py"):
            loc = count_lines(test_file)
            if loc > file_size_limit:
                violations.append(f"{test_file.name}: {loc} LOC")

        assert not violations, f"Shared files exceeding {file_size_limit} LOC:\n" + "\n".join(
            violations
        )

    @pytest.mark.atdd
    def test_ac_8_4a_3_5_8_no_new_exceptions_added(self) -> None:
        """TEST-AC-8.4a-3.5.8: No new file size exceptions added for these files."""
        project_root = Path(__file__).parent.parent.parent.parent
        exceptions_file = project_root / ".file-size-exceptions"

        if not exceptions_file.exists():
            # No exceptions file means no exceptions - that's fine
            return

        try:
            content = exceptions_file.read_text()
            exceptions_data = json.loads(content) if content.strip() else {}
        except json.JSONDecodeError:
            # If not valid JSON, try parsing as simple list
            exceptions_data = {}

        # Check if any of our 31 files are in exceptions
        moderate_filenames = {entry.filename for entry in MODERATE_PRIORITY_FILES}
        new_exceptions = []

        for filepath in exceptions_data.keys():
            filename = Path(filepath).name
            if filename in moderate_filenames:
                new_exceptions.append(filename)

        assert not new_exceptions, (
            "New exceptions added for refactored files (should be split instead):\n"
            + "\n".join(new_exceptions)
        )

    @pytest.mark.atdd
    def test_ac_8_4a_3_5_summary_all_moderate_files_verified(
        self, tests_unit_path: Path, file_size_limit: int
    ) -> None:
        """TEST-AC-8.4a-3.5.SUMMARY: All 31 moderate priority files verified."""
        violations = []

        # Check each of the 31 moderate priority files
        for entry in MODERATE_PRIORITY_FILES:
            # Find the file in tests/unit or subdirectories
            for test_file in tests_unit_path.rglob(entry.filename):
                loc = count_lines(test_file)
                if loc > file_size_limit:
                    violations.append(
                        f"{entry.filename}: {loc} LOC "
                        f"(original: {entry.original_loc}, limit: {file_size_limit})"
                    )

            # If original file not found, it may have been split/renamed
            # That's acceptable as long as there are no violations

        assert not violations, f"Files still exceeding {file_size_limit} LOC limit:\n" + "\n".join(
            violations
        )
