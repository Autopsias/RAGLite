"""Tests with real external data and NFR validation."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

if TYPE_CHECKING:
    from raglite.shared.models import TimeSeriesData

from tests.integration.epic6.conftest import MAPE_CI_GATE, calculate_mape

# Set DYLD_LIBRARY_PATH for XGBoost on macOS
os.environ.setdefault("DYLD_LIBRARY_PATH", "/opt/homebrew/opt/libomp/lib")

pytestmark = [pytest.mark.integration, pytest.mark.preserve_collection, pytest.mark.slow]


class TestRealExternalData:
    """Tests with real external data from Story 6.1 API clients."""

    @pytest.mark.asyncio
    @pytest.mark.slow  # Requires network access to INE API
    async def test_accuracy_with_real_external_data(
        self,
        train_time_series: TimeSeriesData,
        train_test_split: tuple[pd.DataFrame, pd.DataFrame],
        real_external_regressors: dict[str, pd.Series] | None,
    ) -> None:
        """AC6: Accuracy gate with real INE Construction Output data.

        This test uses real external data from Story 6.1 API clients.
        Marked as @slow since it requires network access.

        When real data is available, this is the true accuracy validation.
        The MAPE should be <= 12% to pass the Epic 6 accuracy gate.
        """
        if real_external_regressors is None:
            pytest.skip("Real external data unavailable (network/API issues)")

        from raglite.forecasting.hybrid import generate_ensemble_forecast

        _, test_df = train_test_split

        with patch("raglite.forecasting.hybrid.fetch_historical_data") as mock_fetch:
            mock_fetch.return_value = train_time_series
            result = await generate_ensemble_forecast(
                metric="cement_demand",
                external_regressors=real_external_regressors,
                periods_ahead=len(test_df),
                fast_mode=True,
            )

        # Calculate MAPE
        predicted = np.array([p.value for p in result.forecast[: len(test_df)]])
        actual = test_df["actual_value"].values
        mape = calculate_mape(actual, predicted)

        print(f"\nReal External Data MAPE: {mape:.1%}")
        print(f"Regressors used: {list(real_external_regressors.keys())}")

        # AC6: CI gate - fail if MAPE > 12%
        assert mape <= MAPE_CI_GATE, (
            f"Epic 6 accuracy gate FAILED! MAPE={mape:.1%} exceeds threshold {MAPE_CI_GATE:.0%}. "
            f"Consider triggering Story 6.8 (Tier 2 data sources)."
        )


class TestValidationScript:
    """Tests for the validation script itself."""

    def test_validation_script_exists(self) -> None:
        """AC4: Validation script must exist."""
        script_path = Path("scripts/validate-epic6-accuracy.py")
        assert script_path.exists(), f"Validation script not found: {script_path}"

    def test_validation_script_is_executable(self) -> None:
        """AC4: Validation script must be executable."""
        script_path = Path("scripts/validate-epic6-accuracy.py")
        assert os.access(script_path, os.X_OK), f"Validation script not executable: {script_path}"


class TestNFRs:
    """Non-functional requirement tests."""

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_validation_completes_within_5_minutes(
        self,
        train_time_series: TimeSeriesData,
        train_test_split: tuple[pd.DataFrame, pd.DataFrame],
        synthetic_regressors: dict[str, pd.Series],
    ) -> None:
        """NFR: Full validation must complete in < 5 minutes.

        This test runs all 3 models and validates total time.
        Marked as slow since it runs the full validation.
        """
        from raglite.forecasting.hybrid import generate_ensemble_forecast, generate_forecast

        start_time = time.time()

        _, test_df = train_test_split
        periods = len(test_df)

        # Run all 3 models (baseline, multivariate, ensemble)
        with patch("raglite.forecasting.hybrid.fetch_historical_data") as mock_fetch:
            mock_fetch.return_value = train_time_series
            await generate_forecast(
                metric="cement_demand",
                periods_ahead=periods,
                external_regressors=None,
                frequency="M",
            )

        with patch("raglite.forecasting.hybrid.fetch_historical_data") as mock_fetch:
            mock_fetch.return_value = train_time_series
            await generate_forecast(
                metric="cement_demand",
                periods_ahead=periods,
                external_regressors=synthetic_regressors,
                frequency="M",
            )

        with patch("raglite.forecasting.hybrid.fetch_historical_data") as mock_fetch:
            mock_fetch.return_value = train_time_series
            await generate_ensemble_forecast(
                metric="cement_demand",
                external_regressors=synthetic_regressors,
                periods_ahead=periods,
                fast_mode=True,
            )

        execution_time = time.time() - start_time

        # NFR: < 5 minutes (300 seconds)
        assert execution_time < 300, (
            f"Validation took {execution_time:.1f}s, exceeds 5 minute NFR. "
            f"Optimize forecasting or reduce test data."
        )
