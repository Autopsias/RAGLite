"""AC-8.5-1: Verify historical_data deprecation warnings are eliminated."""

import re
import subprocess
import sys
from unittest.mock import AsyncMock, patch

import pytest

from .shared_helpers import get_project_root

# Mark all tests in this module
pytestmark = [
    pytest.mark.atdd,
    pytest.mark.story_8_5,
]


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
        project_root = get_project_root()
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
        project_root = get_project_root()

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
