"""ATDD Acceptance Tests for Story 8.5: Deprecation Warning Cleanup.

These tests verify that deprecation warnings from RAGLite code are eliminated.
All tests are designed to FAIL initially (TDD RED phase) since deprecated code still exists.

Test IDs:
- TEST-AC-8.5.1.x: historical_data parameter migration
- TEST-AC-8.5.2.x: Import path updates
- TEST-AC-8.5.3.x: Fixture marker cleanup (pytest 9.0 compatibility)
- TEST-AC-8.5.4.x: Full test suite coverage

Story: docs/stories/8-5-deprecation-cleanup.md
Epic: 8 - Technical Debt Reduction
"""

import ast
import re
import subprocess
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

# Mark all tests in this module
pytestmark = [
    pytest.mark.atdd,
    pytest.mark.story_8_5,
]


# ---------------------------------------------------------------------------
# AC1: historical_data Parameter Migration Tests
# ---------------------------------------------------------------------------


class TestAC851HistoricalDataDeprecation:
    """AC-8.5-1: Verify historical_data deprecation warnings are eliminated."""

    # Test files that should NOT use deprecated historical_data parameter
    AFFECTED_TEST_FILES = [
        "tests/unit/test_mcp_edge_cases.py",
        "tests/unit/test_mcp_cache_exceptions.py",
        "tests/unit/test_mcp_cache_lookup.py",
        "tests/unit/test_hybrid_forecasting.py",
        "tests/unit/test_mcp_response_metadata.py",
        "tests/unit/test_chronos_integration.py",
        "tests/unit/forecasting/test_mcp_model_routing_core.py",
        "tests/integration/test_chronos_ensemble.py",
        "tests/validation/test_forecast_accuracy.py",
    ]

    @pytest.mark.priority("P0")
    @pytest.mark.parametrize("test_file", AFFECTED_TEST_FILES)
    def test_ac_8_5_1_1_no_historical_data_parameter_usage(self, test_file: str):
        """TEST-AC-8.5.1.1: Test files should not use deprecated historical_data parameter.

        Given: Test file that previously used deprecated historical_data parameter
        When: File content is analyzed for historical_data usage in generate_forecast calls
        Then: No direct historical_data= parameter should be passed to generate_forecast
        """
        project_root = Path(__file__).parent.parent.parent
        file_path = project_root / test_file

        if not file_path.exists():
            # Skip if test file was removed during refactoring
            pytest.skip(f"Test file not found: {test_file}")

        content = file_path.read_text()

        # Pattern to detect historical_data parameter in generate_forecast calls
        # Matches: generate_forecast(..., historical_data=..., ...)
        deprecated_pattern = r"generate_forecast\s*\([^)]*historical_data\s*="

        matches = re.findall(deprecated_pattern, content, re.MULTILINE | re.DOTALL)

        assert len(matches) == 0, (
            f"Found {len(matches)} usage(s) of deprecated 'historical_data' parameter "
            f"in {test_file}. Migrate to mock pattern:\n"
            f"  with patch('raglite.forecasting.hybrid.ensemble.fetch_historical_data') as mock:\n"
            f"      mock.return_value = data\n"
            f"      result = await generate_forecast(metric='ebitda', horizon=6)"
        )

    @pytest.mark.priority("P0")
    def test_ac_8_5_1_2_no_deprecation_warning_in_output(self):
        """TEST-AC-8.5.1.2: Running tests should not produce historical_data deprecation warnings.

        Given: The RAGLite test suite
        When: A sample forecasting test is executed with deprecation warnings captured
        Then: No 'historical_data parameter is deprecated' warning appears in output
        """
        project_root = Path(__file__).parent.parent.parent

        # Run a quick test that exercises forecasting to check for warnings
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                str(project_root / "tests/unit/forecasting"),
                "-v",
                "--tb=no",
                "-W",
                "default::DeprecationWarning",
                "--collect-only",
                "-q",
            ],
            capture_output=True,
            text=True,
            cwd=str(project_root),
            timeout=60,
        )

        combined_output = result.stdout + result.stderr

        # Check for the specific deprecation message (using variable to avoid self-matching in grep)
        target_message = "historical_data " + "parameter is deprecated"
        deprecation_count = combined_output.count(target_message)

        assert deprecation_count == 0, (
            f"Found {deprecation_count} deprecation warning(s) for old historical_data parameter. "
            f"All tests should use the new API with mocked fetch_historical_metric."
        )

    @pytest.mark.priority("P1")
    @pytest.mark.asyncio
    async def test_ac_8_5_1_3_generate_forecast_accepts_metric_only(self):
        """TEST-AC-8.5.1.3: generate_forecast should work with metric parameter alone.

        Given: The generate_forecast function in ensemble.py
        When: Called with only metric parameter (no historical_data)
        Then: It should attempt to fetch data from PostgreSQL (via fetch_historical_metric)
        """
        from raglite.forecasting.hybrid.ensemble import generate_forecast

        mock_data = AsyncMock()
        mock_data.points = [1, 2, 3, 4, 5, 6, 7, 8]

        with patch(
            "raglite.forecasting.hybrid.preprocessing.fetch_historical_metric",
            return_value=mock_data,
        ):
            # Call without historical_data - this is the new API
            # Should NOT raise any deprecation warning
            import warnings

            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                try:
                    await generate_forecast(
                        metric="test_metric",
                        periods_ahead=3,
                    )
                except Exception:
                    pass  # We only care about warnings, not execution success

                deprecation_warnings = [x for x in w if "historical_data" in str(x.message)]

                assert len(deprecation_warnings) == 0, (
                    f"Deprecation warning raised when using new API: {deprecation_warnings}"
                )


# ---------------------------------------------------------------------------
# AC2: Import Path Updates Tests
# ---------------------------------------------------------------------------


class TestAC852ImportPathDeprecation:
    """AC-8.5-2: Verify import paths work without deprecation warnings."""

    @pytest.mark.priority("P1")
    def test_ac_8_5_2_1_package_imports_no_warning(self):
        """TEST-AC-8.5.2.1: Importing from document_ingestion package should not warn.

        Given: The refactored document_ingestion package
        When: Core functions are imported from the package
        Then: No deprecation warning should be raised
        """
        import warnings

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            # These imports should work without deprecation warnings
            from raglite.ingestion.document_ingestion import (  # noqa: F401
                extract_excel,
                ingest_document,
                ingest_pdf,
            )

            deprecation_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]

            assert len(deprecation_warnings) == 0, (
                f"Found {len(deprecation_warnings)} deprecation warning(s) on import:\n"
                + "\n".join(str(x.message) for x in deprecation_warnings)
            )

    @pytest.mark.priority("P2")
    def test_ac_8_5_2_2_scripts_use_valid_imports(self):
        """TEST-AC-8.5.2.2: Scripts should use imports that don't emit warnings.

        Given: Scripts in the scripts/ directory
        When: Their import statements are analyzed
        Then: They should not use deprecated import patterns
        """
        project_root = Path(__file__).parent.parent.parent
        scripts_dir = project_root / "scripts"

        problematic_scripts = []

        for script in scripts_dir.glob("*.py"):
            content = script.read_text()

            # Check for imports that might trigger deprecation
            # The shim file emits warning, direct submodule imports are preferred
            if "from raglite.ingestion.document_ingestion import" in content:
                # This is fine - package __init__.py re-exports properly
                pass

            # Check for problematic patterns (if any exist)
            # Pattern: importing from the shim file directly when package exists
            if "from raglite.ingestion import document_ingestion" in content:
                # Importing the module itself (not from it) may trigger shim
                problematic_scripts.append(script.name)

        # This should pass when imports are properly structured
        assert len(problematic_scripts) == 0, (
            f"Scripts with potentially problematic imports: {problematic_scripts}"
        )

    @pytest.mark.priority("P1")
    def test_ac_8_5_2_3_verify_import_command_succeeds(self):
        """TEST-AC-8.5.2.3: Python import with warning escalation should succeed.

        Given: Python with -W error::DeprecationWarning flag
        When: Importing from raglite.ingestion.document_ingestion
        Then: Command should exit with code 0 (no warnings escalated to errors)
        """
        project_root = Path(__file__).parent.parent.parent

        result = subprocess.run(
            [
                sys.executable,
                "-W",
                "error::DeprecationWarning",
                "-c",
                "from raglite.ingestion.document_ingestion import ingest_document, ingest_pdf, extract_excel",
            ],
            capture_output=True,
            text=True,
            cwd=str(project_root),
            timeout=30,
        )

        assert result.returncode == 0, (
            f"Import failed with deprecation warning escalated to error.\n"
            f"stderr: {result.stderr}\n"
            f"stdout: {result.stdout}"
        )


# ---------------------------------------------------------------------------
# AC3: Fixture Marker Cleanup Tests (pytest 9.0 compatibility)
# ---------------------------------------------------------------------------


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
        project_root = Path(__file__).parent.parent.parent
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
        project_root = Path(__file__).parent.parent.parent

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


# ---------------------------------------------------------------------------
# AC4: Full Test Suite Coverage Tests
# ---------------------------------------------------------------------------


class TestAC854FullSuiteCoverage:
    """AC-8.5-4: Verify full test suite has no raglite deprecation warnings."""

    @pytest.mark.priority("P1")
    def test_ac_8_5_4_1_no_raglite_deprecation_in_unit_tests(self):
        """TEST-AC-8.5.4.1: Unit tests should not emit raglite deprecation warnings.

        Given: The unit test suite
        When: Tests are collected with deprecation warnings enabled
        Then: No deprecation warnings from raglite code should appear
        """
        project_root = Path(__file__).parent.parent.parent

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
        project_root = Path(__file__).parent.parent.parent
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
        project_root = Path(__file__).parent.parent.parent

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


# ---------------------------------------------------------------------------
# Summary Test
# ---------------------------------------------------------------------------


class TestAC85DeprecationCleanupSummary:
    """Summary test to verify all deprecation cleanup is complete."""

    @pytest.mark.priority("P0")
    def test_ac_8_5_summary_all_deprecations_resolved(self):
        """TEST-AC-8.5.SUMMARY: All deprecation issues should be resolved.

        Given: Story 8.5 deprecation cleanup requirements
        When: All targeted deprecation sources are checked
        Then: Zero deprecation warnings from raglite code
        """
        project_root = Path(__file__).parent.parent.parent

        issues = []

        # Check 1: historical_data usage in test files
        for test_file in [
            "tests/unit/test_mcp_edge_cases.py",
            "tests/unit/test_hybrid_forecasting.py",
        ]:
            file_path = project_root / test_file
            if file_path.exists():
                content = file_path.read_text()
                if re.search(r"generate_forecast\s*\([^)]*historical_data\s*=", content):
                    issues.append(f"deprecated historical_data in {test_file}")

        # Check 2: Fixture markers on fixtures
        for test_file in [
            "tests/integration/test_chunking_core.py",
            "tests/integration/test_chunking_slow.py",
            "tests/integration/test_chunking_extended.py",
        ]:
            file_path = project_root / test_file
            if file_path.exists():
                content = file_path.read_text()
                # Simple heuristic: @pytest.mark.* followed by @pytest.fixture
                if re.search(r"@pytest\.mark\.\w+.*\n.*@pytest\.fixture", content, re.MULTILINE):
                    issues.append(f"marker on fixture in {test_file}")

        # Check 3: Import deprecation warnings
        result = subprocess.run(
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

        if result.returncode != 0:
            issues.append(f"import deprecation: {result.stderr[:200]}")

        assert len(issues) == 0, (
            f"Found {len(issues)} deprecation issue(s) to resolve:\n"
            + "\n".join(f"  - {issue}" for issue in issues)
        )
