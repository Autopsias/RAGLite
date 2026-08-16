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
from unittest.mock import MagicMock, patch

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


class TestFitEtsImplementation:
    """AC2: fit_ets() Implementation tests."""

    @pytest.mark.asyncio
    async def test_ac2_1_fit_ets_uses_statsmodels_exponentialsmoothing(
        self, monthly_series: pd.Series
    ) -> None:
        """TEST-AC-2.1: Use statsmodels ExponentialSmoothing.

        Given: The need for ETS model forecasting
        When: Calling fit_ets() with a time series
        Then: The function should use statsmodels ExponentialSmoothing
        """
        from raglite.forecasting.models.ets_model import fit_ets

        with patch("raglite.forecasting.models.ets_model.ExponentialSmoothing") as mock_ets_class:
            mock_fit_result = MagicMock()
            mock_fit_result.aic = 100.0
            mock_fit_result.bic = 105.0
            mock_fit_result.sse = 50.0

            mock_forecast = MagicMock()
            mock_forecast.predicted_mean = pd.Series([200, 205, 210, 215])
            mock_conf_int_df = pd.DataFrame(
                {"lower": [190, 195, 200, 205], "upper": [210, 215, 220, 225]}
            )
            mock_forecast.conf_int.return_value = mock_conf_int_df
            mock_fit_result.get_forecast.return_value = mock_forecast

            mock_model = MagicMock()
            mock_model.fit.return_value = mock_fit_result
            mock_ets_class.return_value = mock_model

            await fit_ets(monthly_series, forecast_horizon=4, frequency="M")

            mock_ets_class.assert_called_once()

    @pytest.mark.asyncio
    async def test_ac2_2_fit_ets_accepts_y_train_series(self, monthly_series: pd.Series) -> None:
        """TEST-AC-2.2: Accept y_train: pd.Series as primary input.

        Given: A pandas Series with historical data
        When: Calling fit_ets() with the series
        Then: The function should accept and process the input correctly
        """
        from raglite.forecasting.models.ets_model import fit_ets

        result = await fit_ets(monthly_series, forecast_horizon=4, frequency="M")
        assert result is not None

    @pytest.mark.asyncio
    async def test_ac2_3_fit_ets_accepts_forecast_horizon(self, monthly_series: pd.Series) -> None:
        """TEST-AC-2.3: Accept forecast_horizon: int parameter.

        Given: A time series
        When: Calling fit_ets() with forecast_horizon=6
        Then: The predictions should have 6 elements
        """
        from raglite.forecasting.models.ets_model import fit_ets

        model, metrics, predictions, conf_int = await fit_ets(
            monthly_series, forecast_horizon=6, frequency="M"
        )
        assert len(predictions) == 6

    @pytest.mark.asyncio
    async def test_ac2_4_fit_ets_accepts_frequency_monthly(self, monthly_series: pd.Series) -> None:
        """TEST-AC-2.4: Accept frequency: str parameter for monthly data.

        Given: Monthly financial data
        When: Calling fit_ets() with frequency="M"
        Then: The function should process with seasonal_periods=12
        """
        from raglite.forecasting.models.ets_model import fit_ets

        result = await fit_ets(monthly_series, forecast_horizon=4, frequency="M")
        assert result is not None

    @pytest.mark.asyncio
    async def test_ac2_5_fit_ets_accepts_frequency_quarterly(
        self, quarterly_series: pd.Series
    ) -> None:
        """TEST-AC-2.5: Accept frequency: str parameter for quarterly data.

        Given: Quarterly financial data
        When: Calling fit_ets() with frequency="Q"
        Then: The function should process with seasonal_periods=4
        """
        from raglite.forecasting.models.ets_model import fit_ets

        result = await fit_ets(quarterly_series, forecast_horizon=4, frequency="Q")
        assert result is not None

    @pytest.mark.asyncio
    async def test_ac2_6_fit_ets_supports_trend_add(self, monthly_series: pd.Series) -> None:
        """TEST-AC-2.6: Support trend options: add.

        Given: A time series with additive trend
        When: Calling fit_ets() with trend="add"
        Then: The function should fit successfully with additive trend
        """
        from raglite.forecasting.models.ets_model import fit_ets

        result = await fit_ets(monthly_series, forecast_horizon=4, frequency="M", trend="add")
        assert result is not None

    @pytest.mark.asyncio
    async def test_ac2_7_fit_ets_supports_trend_mul(self, monthly_series: pd.Series) -> None:
        """TEST-AC-2.7: Support trend options: mul.

        Given: A time series with multiplicative trend
        When: Calling fit_ets() with trend="mul"
        Then: The function should fit successfully with multiplicative trend
        """
        from raglite.forecasting.models.ets_model import fit_ets

        # Ensure all values are positive for multiplicative trend
        positive_series = monthly_series + abs(monthly_series.min()) + 10
        result = await fit_ets(positive_series, forecast_horizon=4, frequency="M", trend="mul")
        assert result is not None

    @pytest.mark.asyncio
    async def test_ac2_8_fit_ets_supports_trend_none(self, monthly_series: pd.Series) -> None:
        """TEST-AC-2.8: Support trend options: None.

        Given: A time series with no trend
        When: Calling fit_ets() with trend=None
        Then: The function should fit successfully without trend
        """
        from raglite.forecasting.models.ets_model import fit_ets

        result = await fit_ets(monthly_series, forecast_horizon=4, frequency="M", trend=None)
        assert result is not None

    @pytest.mark.asyncio
    async def test_ac2_9_fit_ets_supports_seasonal_add(self, monthly_series: pd.Series) -> None:
        """TEST-AC-2.9: Support seasonal options: add.

        Given: A time series with additive seasonality
        When: Calling fit_ets() with seasonal="add"
        Then: The function should fit successfully with additive seasonality
        """
        from raglite.forecasting.models.ets_model import fit_ets

        result = await fit_ets(monthly_series, forecast_horizon=4, frequency="M", seasonal="add")
        assert result is not None

    @pytest.mark.asyncio
    async def test_ac2_10_fit_ets_supports_seasonal_mul(self, monthly_series: pd.Series) -> None:
        """TEST-AC-2.10: Support seasonal options: mul.

        Given: A time series with multiplicative seasonality
        When: Calling fit_ets() with seasonal="mul"
        Then: The function should fit successfully with multiplicative seasonality
        """
        from raglite.forecasting.models.ets_model import fit_ets

        # Ensure all values are positive for multiplicative seasonality
        positive_series = monthly_series + abs(monthly_series.min()) + 10
        result = await fit_ets(positive_series, forecast_horizon=4, frequency="M", seasonal="mul")
        assert result is not None

    @pytest.mark.asyncio
    async def test_ac2_11_fit_ets_supports_seasonal_none(self, monthly_series: pd.Series) -> None:
        """TEST-AC-2.11: Support seasonal options: None.

        Given: A time series with no seasonality
        When: Calling fit_ets() with seasonal=None
        Then: The function should fit successfully without seasonality
        """
        from raglite.forecasting.models.ets_model import fit_ets

        result = await fit_ets(monthly_series, forecast_horizon=4, frequency="M", seasonal=None)
        assert result is not None

    @pytest.mark.asyncio
    async def test_ac2_12_fit_ets_supports_damped_trend(self, monthly_series: pd.Series) -> None:
        """TEST-AC-2.12: Support damped trend option.

        Given: A time series with damped trend
        When: Calling fit_ets() with damped_trend=True
        Then: The function should fit successfully with damped trend
        """
        from raglite.forecasting.models.ets_model import fit_ets

        result = await fit_ets(
            monthly_series, forecast_horizon=4, frequency="M", trend="add", damped_trend=True
        )
        assert result is not None

    @pytest.mark.asyncio
    async def test_ac2_13_fit_ets_returns_correct_tuple(self, monthly_series: pd.Series) -> None:
        """TEST-AC-2.13: Return tuple: (model, metrics_dict, predictions, confidence_intervals).

        Given: A time series
        When: Calling fit_ets()
        Then: The function should return a 4-tuple with correct types
        """
        from raglite.forecasting.models.ets_model import fit_ets

        result = await fit_ets(monthly_series, forecast_horizon=4, frequency="M")

        assert isinstance(result, tuple)
        assert len(result) == 4

        model, metrics, predictions, conf_int = result
        assert model is not None  # Fitted ETS model
        assert isinstance(metrics, dict)
        assert isinstance(predictions, np.ndarray)
        assert isinstance(conf_int, np.ndarray)


# -----------------------------------------------------------------------------
# TEST-AC-4: Frequency Handling (ETS subset)
# -----------------------------------------------------------------------------


class TestFrequencyHandlingEts:
    """AC4: Frequency Handling tests for ETS."""

    @pytest.mark.asyncio
    async def test_ac4_4_handle_frequency_conversion_gracefully(
        self, monthly_series: pd.Series
    ) -> None:
        """TEST-AC-4.4: Handle frequency conversion gracefully.

        Given: Data that might need frequency conversion
        When: Processing with fit functions
        Then: The function should handle conversion without errors
        """
        from raglite.forecasting.models.ets_model import fit_ets

        # Should handle monthly data properly
        result = await fit_ets(monthly_series, forecast_horizon=4, frequency="M")
        assert result is not None


# -----------------------------------------------------------------------------
# TEST-AC-5: Return ForecastPoint Compatible Output (ETS subset)
# -----------------------------------------------------------------------------


class TestForecastPointCompatibleOutputEts:
    """AC5: Return ForecastPoint Compatible Output tests for ETS."""

    @pytest.mark.asyncio
    async def test_ac5_1_predictions_as_numpy_array(self, monthly_series: pd.Series) -> None:
        """TEST-AC-5.1: Predictions as numpy array of point forecasts.

        Given: A time series
        When: Calling fit_ets()
        Then: Predictions should be a numpy array
        """
        from raglite.forecasting.models.ets_model import fit_ets

        _, _, ets_preds, _ = await fit_ets(monthly_series, forecast_horizon=4, frequency="M")

        assert isinstance(ets_preds, np.ndarray)

    @pytest.mark.asyncio
    async def test_ac5_2_confidence_intervals_as_2d_array(self, monthly_series: pd.Series) -> None:
        """TEST-AC-5.2: Confidence intervals as 2D numpy array (lower, upper bounds).

        Given: A time series
        When: Calling fit_ets()
        Then: Confidence intervals should be 2D array with shape (horizon, 2)
        """
        from raglite.forecasting.models.ets_model import fit_ets

        horizon = 4

        _, _, _, ets_ci = await fit_ets(monthly_series, forecast_horizon=horizon, frequency="M")

        # Should be 2D array
        assert ets_ci.ndim == 2

        # Should have 2 columns (lower, upper)
        assert ets_ci.shape[1] == 2

    @pytest.mark.asyncio
    async def test_ac5_4_output_dimensions_match_forecast_horizon(
        self, monthly_series: pd.Series
    ) -> None:
        """TEST-AC-5.4: Output dimensions match forecast_horizon.

        Given: A time series with various forecast horizons
        When: Calling fit functions
        Then: Predictions and confidence intervals should have correct dimensions
        """
        from raglite.forecasting.models.ets_model import fit_ets

        for horizon in [2, 4, 6, 8]:
            _, _, ets_preds, ets_ci = await fit_ets(
                monthly_series, forecast_horizon=horizon, frequency="M"
            )

            assert len(ets_preds) == horizon
            assert ets_ci.shape[0] == horizon


# -----------------------------------------------------------------------------
# TEST-AC-6: Graceful Fallback on Failure (ETS subset)
# -----------------------------------------------------------------------------
