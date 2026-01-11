"""Model selection performance tests.

Story 7b-3: Per-Variable Model Selection via Cross-Validation
TEST-AC-7b.3.7.x: Runtime performance tests
"""

from __future__ import annotations

import time

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.slow, pytest.mark.preserve_collection]


@pytest.mark.slow
class TestAC_7b_3_7_RuntimePerformance:
    """[P0] AC-7b.3.7: Runtime Performance.

    Given model selection is running for a single variable
    When all 9 models are cross-validated with 5 folds
    Then total runtime is less than 10 minutes per variable.
    """

    @pytest.mark.asyncio
    async def test_ac_7b_3_7_1_selection_completes_under_10_minutes(
        self, sample_time_series
    ) -> None:
        """TEST-AC-7b.3.7.1: Single variable selection completes in <10 minutes."""
        from raglite.forecasting.model_selection import select_best_model

        start_time = time.time()

        result = await select_best_model(
            variable_name="test_metric",
            historical_data=sample_time_series,
        )

        elapsed_time = time.time() - start_time

        # Must complete in under 10 minutes (600 seconds)
        assert elapsed_time < 600, f"Selection took {elapsed_time:.1f}s, exceeds 10 min limit"

        # Also verify the result tracks its own runtime
        assert result.runtime_seconds < 600

    @pytest.mark.asyncio
    async def test_ac_7b_3_7_2_runtime_tracked_in_result(self, sample_time_series) -> None:
        """TEST-AC-7b.3.7.2: Runtime is tracked in ModelSelectionResult."""
        from raglite.forecasting.model_selection import select_best_model

        start_time = time.time()

        result = await select_best_model(
            variable_name="test_metric",
            historical_data=sample_time_series,
        )

        elapsed_time = time.time() - start_time

        # Result's runtime should roughly match actual elapsed time
        # (allow some margin for overhead)
        assert result.runtime_seconds > 0
        assert abs(result.runtime_seconds - elapsed_time) < 5  # Within 5 seconds
