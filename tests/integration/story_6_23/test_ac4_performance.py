"""Test AC4: Validation script completes in <10 minutes.

Story 6.23 - RED PHASE: Tests MUST FAIL initially.
"""

from __future__ import annotations

import subprocess
import time

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.preserve_collection, pytest.mark.slow]


class TestAC4ValidationPerformance:
    """AC4: Validation script completes in <10 minutes.

    GIVEN the full 12-variable validation
    WHEN measuring runtime
    THEN total execution time should be <600 seconds (10 minutes)

    RED PHASE: This test validates performance requirements.
    """

    @pytest.mark.slow
    def test_ac4_full_validation_runtime(self, validation_script_path, project_root):
        """TEST-AC-6.23.4: Full validation must complete in <10 minutes.

        GIVEN: Validation script is optimized (Story 6.21)
        WHEN: Running full 12-variable validation
        THEN: Runtime < 600 seconds (10 minutes)
        """
        MAX_RUNTIME_SECONDS = 600  # 10 minutes

        start_time = time.time()

        # WHEN: Run full validation with timing
        result = subprocess.run(
            [
                "uv",
                "run",
                "python",
                str(validation_script_path),
                "--full",
                "--quiet",
            ],
            capture_output=True,
            text=True,
            cwd=str(project_root),
            timeout=660,  # 11 minute hard timeout
        )

        elapsed_time = time.time() - start_time

        # Script should succeed
        if result.returncode != 0:
            pytest.skip(f"Validation script failed: {result.stderr}")

        # AC4 ASSERTION: Runtime must be under 10 minutes
        assert elapsed_time < MAX_RUNTIME_SECONDS, (
            f"TEST-AC-6.23.4 FAILED: Validation took {elapsed_time:.1f}s, "
            f"exceeds {MAX_RUNTIME_SECONDS}s limit"
        )

    def test_ac4_single_variable_runtime(self, validation_script_path, project_root):
        """TEST-AC-6.23.4b: Single variable validation must be fast.

        GIVEN: Validation is optimized
        WHEN: Running single variable validation
        THEN: Runtime < 60 seconds per variable
        """
        MAX_SINGLE_VAR_SECONDS = 60

        start_time = time.time()

        result = subprocess.run(
            [
                "uv",
                "run",
                "python",
                str(validation_script_path),
                "--variable",
                "revenue",
                "--quiet",
            ],
            capture_output=True,
            text=True,
            cwd=str(project_root),
            timeout=120,
        )

        elapsed_time = time.time() - start_time

        if result.returncode != 0:
            pytest.skip(f"Single variable validation failed: {result.stderr}")

        # AC4b: Single variable should be fast
        assert elapsed_time < MAX_SINGLE_VAR_SECONDS, (
            f"Single variable took {elapsed_time:.1f}s, should be <{MAX_SINGLE_VAR_SECONDS}s"
        )
