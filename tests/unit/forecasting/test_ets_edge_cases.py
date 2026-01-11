"""ATDD Tests for ETS Model Wrapper (Story 7b.1).

This file tests acceptance criteria for fit_ets():
- AC2: fit_ets() Implementation
- AC4: Frequency Handling
- AC5: Return ForecastPoint Compatible Output
- AC6: Graceful Fallback on Failure
- AC7: Unit Test Coverage

Test IDs:
- TEST-AC-2.x: ETS implementation tests
- TEST-AC-4.x: Frequency handling tests (ETS subset)
- TEST-AC-5.x: Output format tests (ETS subset)
- TEST-AC-6.x: Error handling tests (ETS subset)
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

# Skip all tests in this module when running in LIGHTWEIGHT_TESTS mode
# These tests require real statsmodels for ETS model fitting
pytestmark = pytest.mark.skipif(
    os.environ.get("LIGHTWEIGHT_TESTS") == "true",
    reason="ETS tests require real statsmodels (not mocked)",
)

if TYPE_CHECKING:
    pass


# -----------------------------------------------------------------------------
# Test Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
def monthly_series() -> pd.Series:
    """Create a monthly time series with 36 data points (3 years).

    Simulates financial data with trend and seasonality.
    """
    dates = pd.date_range(start="2022-01-01", periods=36, freq="MS")
    # Trend + seasonality + noise
    trend = np.linspace(100, 200, 36)
    seasonality = 20 * np.sin(np.linspace(0, 6 * np.pi, 36))
    noise = np.random.default_rng(42).normal(0, 5, 36)
    values = trend + seasonality + noise
    return pd.Series(values, index=dates, name="revenue")


@pytest.fixture
def quarterly_series() -> pd.Series:
    """Create a quarterly time series with 16 data points (4 years)."""
    dates = pd.date_range(start="2021-01-01", periods=16, freq="QS")
    # Simple trend with some noise
    trend = np.linspace(1000, 1500, 16)
    noise = np.random.default_rng(42).normal(0, 20, 16)
    values = trend + noise
    return pd.Series(values, index=dates, name="ebitda")


@pytest.fixture
def short_series() -> pd.Series:
    """Create a short time series (only 4 data points) for edge case testing."""
    dates = pd.date_range(start="2024-01-01", periods=4, freq="MS")
    values = [100, 110, 105, 115]
    return pd.Series(values, index=dates, name="metric")


# -----------------------------------------------------------------------------
# TEST-AC-2: fit_ets() Implementation
# -----------------------------------------------------------------------------


class TestGracefulFallbackOnFailureEts:
    """AC6: Graceful Fallback on Failure tests for ETS."""

    @pytest.mark.asyncio
    async def test_ac6_3_raise_specific_exception_ets(self, short_series: pd.Series) -> None:
        """TEST-AC-6.3: Return None or raise specific exception (ETS).

        Given: Data that causes ETS fitting to fail
        When: Model fitting fails
        Then: ETSFittingError should be raised (not generic Exception)
        """
        from raglite.forecasting.models.ets_model import ETSFittingError, fit_ets

        with patch("raglite.forecasting.models.ets_model.ExponentialSmoothing") as mock_ets:
            mock_ets.side_effect = Exception("Optimization failed")

            with pytest.raises(ETSFittingError) as exc_info:
                await fit_ets(short_series, forecast_horizon=4, frequency="M")

            assert "Failed to fit ETS" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_ac6_7_handle_singular_matrix_failure(self, monthly_series: pd.Series) -> None:
        """TEST-AC-6.7: Common failure: singular matrix.

        Given: Data that causes singular matrix errors
        When: Fitting fails due to singular matrix
        Then: Should raise specific error with details
        """
        from raglite.forecasting.models.ets_model import ETSFittingError, fit_ets

        with patch("raglite.forecasting.models.ets_model.ExponentialSmoothing") as mock_ets:
            mock_ets.side_effect = Exception("Singular matrix in optimization")

            with pytest.raises(ETSFittingError) as exc_info:
                await fit_ets(monthly_series, forecast_horizon=4, frequency="M")

            assert "Failed to fit ETS" in str(exc_info.value)


# -----------------------------------------------------------------------------
# Module Export Tests (ETS subset)
# -----------------------------------------------------------------------------


class TestModuleExportsEts:
    """Module export tests for ETS."""

    def test_ac7_3_ets_model_exports_fit_ets(self) -> None:
        """TEST-AC-7.3: ets_model.py exports fit_ets.

        Given: The ets_model module
        When: Importing fit_ets
        Then: The function should be importable
        """
        from raglite.forecasting.models.ets_model import fit_ets

        assert callable(fit_ets)

    def test_ac7_4_ets_model_exports_ets_fitting_error(self) -> None:
        """TEST-AC-7.4: ets_model.py exports ETSFittingError.

        Given: The ets_model module
        When: Importing ETSFittingError
        Then: The exception class should be importable
        """
        from raglite.forecasting.models.ets_model import ETSFittingError

        assert issubclass(ETSFittingError, Exception)

    def test_ac7_6_models_package_exports_fit_ets(self) -> None:
        """TEST-AC-7.6: models/__init__.py exports fit_ets.

        Given: The models package
        When: Importing fit_ets from package
        Then: The function should be available at package level
        """
        from raglite.forecasting.models import fit_ets

        assert callable(fit_ets)

    def test_ac7_8_models_package_exports_ets_fitting_error(self) -> None:
        """TEST-AC-7.8: models/__init__.py exports ETSFittingError.

        Given: The models package
        When: Importing ETSFittingError from package
        Then: The exception should be available at package level
        """
        from raglite.forecasting.models import ETSFittingError

        assert issubclass(ETSFittingError, Exception)


# -----------------------------------------------------------------------------
# Edge Cases (ETS subset)
# -----------------------------------------------------------------------------


class TestEdgeCasesEts:
    """Additional edge case tests for ETS robustness."""

    @pytest.mark.asyncio
    async def test_edge_case_all_zeros_series(self) -> None:
        """Test handling of all-zeros series.

        Given: A series with all zero values
        When: Calling fit functions
        Then: Should handle gracefully (may succeed or raise specific error)
        """
        from raglite.forecasting.models.ets_model import fit_ets

        dates = pd.date_range(start="2022-01-01", periods=36, freq="MS")
        zero_series = pd.Series(np.zeros(36), index=dates)

        # Should either work or raise a clear error
        try:
            result = await fit_ets(zero_series, forecast_horizon=4, frequency="M", seasonal=None)
            assert result is not None
        except Exception as e:
            # Should be a clear error, not a cryptic one
            assert isinstance(e, (ValueError, RuntimeError))

    @pytest.mark.asyncio
    async def test_edge_case_negative_values_with_mul(self, monthly_series: pd.Series) -> None:
        """Test handling of negative values with multiplicative components.

        Given: A series with negative values
        When: Calling fit_ets with multiplicative trend
        Then: Should raise appropriate error (multiplicative requires positive)
        """
        from raglite.forecasting.models.ets_model import fit_ets

        # Create series with negative values
        negative_series = monthly_series - 300  # Force some negatives

        # Multiplicative trend/seasonal requires positive values
        with pytest.raises((ValueError, Exception)):
            await fit_ets(negative_series, forecast_horizon=4, frequency="M", trend="mul")

    @pytest.mark.asyncio
    async def test_edge_case_large_forecast_horizon(self, monthly_series: pd.Series) -> None:
        """Test large forecast horizon (12 months).

        Given: A time series
        When: Requesting forecast_horizon=12
        Then: Should return 12 predictions
        """
        from raglite.forecasting.models.ets_model import fit_ets

        _, _, predictions, conf_int = await fit_ets(
            monthly_series, forecast_horizon=12, frequency="M"
        )

        assert len(predictions) == 12
        assert conf_int.shape[0] == 12
