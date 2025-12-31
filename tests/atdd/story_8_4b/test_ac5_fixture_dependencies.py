"""[P0] ATDD tests for AC-8.4b.5: Fixture Dependencies Preserved.

Given integration tests have complex fixture dependencies in conftest.py
When the refactoring is complete
Then all fixture dependencies are preserved and working

These tests verify fixture organization after refactoring.
"""

import subprocess
from pathlib import Path

import pytest

from .conftest import directory_exists


class TestAC5FixtureDependencies:
    """[P0] Tests for AC-8.4b.5 - Fixture preservation."""

    @pytest.mark.atdd
    def test_ac_8_4b_5_1_root_conftest_exists(self, tests_integration_path: Path) -> None:
        """TEST-AC-8.4b.5.1: Root integration conftest.py exists."""
        root_conftest = tests_integration_path / "conftest.py"
        assert root_conftest.exists(), "Root conftest.py missing"

    @pytest.mark.atdd
    @pytest.mark.slow
    @pytest.mark.timeout(0)  # Disable timeout - subprocess has own timeout
    def test_ac_8_4b_5_2_fixtures_available(self, tests_integration_path: Path) -> None:
        """TEST-AC-8.4b.5.2: All fixtures available via pytest --fixtures."""
        result = subprocess.run(
            [
                "uv",
                "run",
                "pytest",
                str(tests_integration_path),
                "--fixtures",
                "-q",
            ],
            capture_output=True,
            text=True,
            cwd=tests_integration_path.parent.parent,
            timeout=180,  # 3 min subprocess timeout
        )

        output = result.stdout + result.stderr
        # Should not have fixture resolution errors
        assert "fixture" not in output.lower() or "error" not in output.lower(), (
            f"Fixture resolution errors: {output}"
        )

    @pytest.mark.atdd
    def test_ac_8_4b_5_3_no_circular_dependencies(self, tests_integration_path: Path) -> None:
        """TEST-AC-8.4b.5.3: No circular import dependencies in conftest files."""
        conftest_files = list(tests_integration_path.rglob("conftest.py"))
        circular_imports = []

        for conftest in conftest_files:
            content = conftest.read_text()
            # Check for imports that could cause circularity
            # (importing from sibling conftest files)
            lines = content.split("\n")
            for line in lines:
                if "from .conftest" in line or "import conftest" in line:
                    circular_imports.append(f"{conftest}: {line.strip()}")

        assert len(circular_imports) == 0, f"Potential circular imports: {circular_imports}"

    @pytest.mark.atdd
    def test_ac_8_4b_5_4_session_fixtures_in_correct_scope(
        self, tests_integration_path: Path
    ) -> None:
        """TEST-AC-8.4b.5.4: Session-scoped fixtures remain in appropriate location."""
        fixtures_dir = tests_integration_path / "fixtures"
        if not fixtures_dir.exists():
            pytest.fail("fixtures/ directory missing")

        session_fixtures = fixtures_dir / "session_fixtures.py"
        assert session_fixtures.exists(), "session_fixtures.py missing"

        content = session_fixtures.read_text()
        # Session fixtures should have session scope
        assert 'scope="session"' in content or "scope='session'" in content, (
            "session_fixtures.py should contain session-scoped fixtures"
        )

    @pytest.mark.atdd
    def test_ac_8_4b_5_5_subdirectory_conftest_structure(
        self, tests_integration_path: Path
    ) -> None:
        """TEST-AC-8.4b.5.5: Each new subdirectory has properly structured conftest."""
        subdirs = ["forecasting", "ingestion", "model_selection"]
        invalid_conftest = []

        for subdir in subdirs:
            if directory_exists(tests_integration_path, subdir):
                conftest_path = tests_integration_path / subdir / "conftest.py"
                if conftest_path.exists():
                    content = conftest_path.read_text()
                    # Should have proper imports
                    has_pytest_import = "import pytest" in content
                    has_docstring = '"""' in content or "'''" in content

                    if not has_pytest_import:
                        invalid_conftest.append(f"{subdir}/conftest.py: missing pytest import")
                    if not has_docstring:
                        invalid_conftest.append(f"{subdir}/conftest.py: missing docstring")
                else:
                    invalid_conftest.append(f"{subdir}/conftest.py: file missing")

        assert len(invalid_conftest) == 0, f"Conftest issues: {invalid_conftest}"

    @pytest.mark.atdd
    @pytest.mark.slow
    def test_ac_8_4b_5_6_shared_fixtures_accessible(self, tests_integration_path: Path) -> None:
        """TEST-AC-8.4b.5.6: Shared fixtures accessible from subdirectories."""
        # Run a quick collection to verify fixture inheritance works
        subdirs = ["forecasting", "ingestion", "model_selection"]

        for subdir in subdirs:
            if directory_exists(tests_integration_path, subdir):
                subdir_path = tests_integration_path / subdir
                # Use a timeout for subprocess call to prevent hanging
                result = subprocess.run(
                    [
                        "uv",
                        "run",
                        "pytest",
                        str(subdir_path),
                        "--collect-only",
                        "-q",
                    ],
                    capture_output=True,
                    text=True,
                    cwd=tests_integration_path.parent.parent,
                    timeout=180,  # 3 min subprocess timeout
                )

                output = result.stdout + result.stderr
                # Should not have fixture-not-found errors
                assert "fixture" not in output or "not found" not in output.lower(), (
                    f"Fixture access error in {subdir}: {output}"
                )


class TestAC5FixtureOrganization:
    """[P1] Tests for proper fixture organization."""

    @pytest.mark.atdd
    def test_ac_8_4b_5_7_forecasting_fixtures_isolated(self, tests_integration_path: Path) -> None:
        """TEST-AC-8.4b.5.7: Forecasting-specific fixtures in forecasting/conftest.py."""
        forecasting_path = tests_integration_path / "forecasting"
        if not directory_exists(tests_integration_path, "forecasting"):
            pytest.fail("forecasting/ directory not created yet")

        conftest_path = forecasting_path / "conftest.py"
        assert conftest_path.exists(), "forecasting/conftest.py missing"

        content = conftest_path.read_text()
        # Should have at least one fixture
        assert "@pytest.fixture" in content, "forecasting/conftest.py has no fixtures defined"

    @pytest.mark.atdd
    def test_ac_8_4b_5_8_ingestion_fixtures_isolated(self, tests_integration_path: Path) -> None:
        """TEST-AC-8.4b.5.8: Ingestion-specific fixtures in ingestion/conftest.py."""
        ingestion_path = tests_integration_path / "ingestion"
        if not directory_exists(tests_integration_path, "ingestion"):
            pytest.fail("ingestion/ directory not created yet")

        conftest_path = ingestion_path / "conftest.py"
        assert conftest_path.exists(), "ingestion/conftest.py missing"

        content = conftest_path.read_text()
        assert "@pytest.fixture" in content, "ingestion/conftest.py has no fixtures defined"

    @pytest.mark.atdd
    def test_ac_8_4b_5_9_model_selection_fixtures_isolated(
        self, tests_integration_path: Path
    ) -> None:
        """TEST-AC-8.4b.5.9: Model selection fixtures in model_selection/conftest.py."""
        model_selection_path = tests_integration_path / "model_selection"
        if not directory_exists(tests_integration_path, "model_selection"):
            pytest.fail("model_selection/ directory not created yet")

        conftest_path = model_selection_path / "conftest.py"
        assert conftest_path.exists(), "model_selection/conftest.py missing"

        content = conftest_path.read_text()
        assert "@pytest.fixture" in content, "model_selection/conftest.py has no fixtures defined"

    @pytest.mark.atdd
    def test_ac_8_4b_5_10_no_fixture_duplication_across_modules(
        self, tests_integration_path: Path
    ) -> None:
        """TEST-AC-8.4b.5.10: No duplicate fixtures between subdirs and root."""
        root_conftest = tests_integration_path / "conftest.py"
        if not root_conftest.exists():
            pytest.fail("Root conftest.py missing")

        # Get fixtures from root
        root_content = root_conftest.read_text()
        root_fixtures = set()

        lines = root_content.split("\n")
        for i, line in enumerate(lines):
            if "@pytest.fixture" in line:
                for j in range(i + 1, min(i + 5, len(lines))):
                    next_line = lines[j].strip()
                    if next_line.startswith("def ") or next_line.startswith("async def "):
                        func_name = (
                            next_line.split("(")[0]
                            .replace("def ", "")
                            .replace("async ", "")
                            .strip()
                        )
                        root_fixtures.add(func_name)
                        break

        # Check subdirectory conftest files for duplicates
        duplicates = []
        subdirs = ["forecasting", "ingestion", "model_selection"]

        for subdir in subdirs:
            conftest_path = tests_integration_path / subdir / "conftest.py"
            if conftest_path.exists():
                content = conftest_path.read_text()
                lines = content.split("\n")
                for i, line in enumerate(lines):
                    if "@pytest.fixture" in line:
                        for j in range(i + 1, min(i + 5, len(lines))):
                            next_line = lines[j].strip()
                            if next_line.startswith("def ") or next_line.startswith("async def "):
                                func_name = (
                                    next_line.split("(")[0]
                                    .replace("def ", "")
                                    .replace("async ", "")
                                    .strip()
                                )
                                if func_name in root_fixtures:
                                    duplicates.append(f"{subdir}/{func_name}")
                                break

        assert len(duplicates) == 0, f"Fixtures duplicated from root: {duplicates}"
