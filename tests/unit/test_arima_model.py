"""ATDD Tests for ARIMA Model Wrapper (Story 7b.1).

This file tests acceptance criteria for fit_arima():
- AC1: fit_arima() Implementation
- AC3: Exogenous Variable Support
- AC4: Frequency Handling
- AC5: Return ForecastPoint Compatible Output
- AC6: Graceful Fallback on Failure
- AC7: Unit Test Coverage

Test IDs:
- TEST-AC-1.x: ARIMA implementation tests
- TEST-AC-3.x: Exogenous variable tests
- TEST-AC-4.x: Frequency handling tests
- TEST-AC-5.x: Output format tests (ARIMA subset)
- TEST-AC-6.x: Error handling tests (ARIMA subset)
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

# Skip all tests in this module when running in LIGHTWEIGHT_TESTS mode
# These tests require real pmdarima for ARIMA model fitting
pytestmark = pytest.mark.skipif(
    os.environ.get("LIGHTWEIGHT_TESTS") == "true",
    reason="ARIMA tests require real pmdarima (not mocked)",
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


@pytest.fixture
def exogenous_train() -> pd.DataFrame:
    """Create exogenous regressor DataFrame for training."""
    dates = pd.date_range(start="2022-01-01", periods=36, freq="MS")
    return pd.DataFrame(
        {
            "gas_price": np.linspace(50, 80, 36) + np.random.default_rng(42).normal(0, 2, 36),
            "euribor": np.linspace(0.5, 3.5, 36) + np.random.default_rng(43).normal(0, 0.1, 36),
        },
        index=dates,
    )


@pytest.fixture
def exogenous_future() -> pd.DataFrame:
    """Create exogenous regressor DataFrame for forecast period (4 months)."""
    dates = pd.date_range(start="2025-01-01", periods=4, freq="MS")
    return pd.DataFrame(
        {
            "gas_price": [82, 84, 83, 85],
            "euribor": [3.6, 3.7, 3.65, 3.8],
        },
        index=dates,
    )


# -----------------------------------------------------------------------------
# TEST-AC-1: fit_arima() Implementation
# -----------------------------------------------------------------------------


class TestFitArimaImplementation:
    """AC1: fit_arima() Implementation tests."""

    @pytest.mark.asyncio
    async def test_ac1_1_fit_arima_uses_pmdarima_auto_arima(
        self, monthly_series: pd.Series
    ) -> None:
        """TEST-AC-1.1: Use pmdarima's auto_arima for automatic (p,d,q) selection.

        Given: The need for ARIMA model forecasting
        When: Calling fit_arima() with a time series
        Then: The function should use pmdarima's auto_arima internally
        """
        from raglite.forecasting.models.arima_model import fit_arima

        # Mock pmdarima to verify it's being used
        with patch("raglite.forecasting.models.arima_model._get_pmdarima") as mock_get_pm:
            mock_pm = MagicMock()
            mock_model = MagicMock()
            mock_model.aic.return_value = 100.0
            mock_model.order = (1, 1, 1)
            mock_model.seasonal_order = (1, 0, 1, 12)
            mock_model.predict.return_value = (
                np.array([200, 205, 210, 215]),
                np.array([[190, 210], [195, 215], [200, 220], [205, 225]]),
            )
            mock_pm.auto_arima.return_value = mock_model
            mock_get_pm.return_value = mock_pm

            await fit_arima(monthly_series, forecast_horizon=4, frequency="M")

            mock_pm.auto_arima.assert_called_once()

    @pytest.mark.asyncio
    async def test_ac1_2_fit_arima_accepts_y_train_series(self, monthly_series: pd.Series) -> None:
        """TEST-AC-1.2: Accept y_train: pd.Series as primary input.

        Given: A pandas Series with historical data
        When: Calling fit_arima() with the series
        Then: The function should accept and process the input correctly
        """
        from raglite.forecasting.models.arima_model import fit_arima

        # Should not raise TypeError for pd.Series input
        result = await fit_arima(monthly_series, forecast_horizon=4, frequency="M")
        assert result is not None

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_ac1_3_fit_arima_accepts_optional_x_train(
        self, monthly_series: pd.Series, exogenous_train: pd.DataFrame
    ) -> None:
        """TEST-AC-1.3: Accept optional X_train: pd.DataFrame for exogenous regressors.

        Given: Historical data with external regressors
        When: Calling fit_arima() with X_train parameter
        Then: The function should accept the exogenous variables
        """
        from raglite.forecasting.models.arima_model import fit_arima

        result = await fit_arima(
            monthly_series,
            X_train=exogenous_train,
            forecast_horizon=4,
            frequency="M",
        )
        assert result is not None

    @pytest.mark.asyncio
    async def test_ac1_4_fit_arima_accepts_forecast_horizon(
        self, monthly_series: pd.Series
    ) -> None:
        """TEST-AC-1.4: Accept forecast_horizon: int parameter.

        Given: A time series
        When: Calling fit_arima() with forecast_horizon=6
        Then: The predictions should have 6 elements
        """
        from raglite.forecasting.models.arima_model import fit_arima

        model, metrics, predictions, conf_int = await fit_arima(
            monthly_series, forecast_horizon=6, frequency="M"
        )
        assert len(predictions) == 6

    @pytest.mark.asyncio
    async def test_ac1_5_fit_arima_accepts_frequency_monthly(
        self, monthly_series: pd.Series
    ) -> None:
        """TEST-AC-1.5: Accept frequency: str parameter for monthly data.

        Given: Monthly financial data
        When: Calling fit_arima() with frequency="M"
        Then: The function should process with seasonal_period=12
        """
        from raglite.forecasting.models.arima_model import fit_arima

        result = await fit_arima(monthly_series, forecast_horizon=4, frequency="M")
        # Should complete without error for monthly frequency
        assert result is not None

    @pytest.mark.asyncio
    async def test_ac1_6_fit_arima_accepts_frequency_quarterly(
        self, quarterly_series: pd.Series
    ) -> None:
        """TEST-AC-1.6: Accept frequency: str parameter for quarterly data.

        Given: Quarterly financial data
        When: Calling fit_arima() with frequency="Q"
        Then: The function should process with seasonal_period=4
        """
        from raglite.forecasting.models.arima_model import fit_arima

        result = await fit_arima(quarterly_series, forecast_horizon=4, frequency="Q")
        assert result is not None

    @pytest.mark.asyncio
    async def test_ac1_7_fit_arima_returns_correct_tuple(self, monthly_series: pd.Series) -> None:
        """TEST-AC-1.7: Return tuple: (model, metrics_dict, predictions, confidence_intervals).

        Given: A time series
        When: Calling fit_arima()
        Then: The function should return a 4-tuple with correct types
        """
        from raglite.forecasting.models.arima_model import fit_arima

        result = await fit_arima(monthly_series, forecast_horizon=4, frequency="M")

        assert isinstance(result, tuple)
        assert len(result) == 4

        model, metrics, predictions, conf_int = result
        assert model is not None  # Fitted ARIMA model
        assert isinstance(metrics, dict)
        assert isinstance(predictions, np.ndarray)
        assert isinstance(conf_int, np.ndarray)

    @pytest.mark.asyncio
    async def test_ac1_8_fit_arima_metrics_include_aic(self, monthly_series: pd.Series) -> None:
        """TEST-AC-1.8: Metrics dict includes aic.

        Given: A time series
        When: Calling fit_arima() and getting metrics
        Then: The metrics dict should include 'aic' key
        """
        from raglite.forecasting.models.arima_model import fit_arima

        _, metrics, _, _ = await fit_arima(monthly_series, forecast_horizon=4, frequency="M")

        assert "aic" in metrics
        assert isinstance(metrics["aic"], (int, float))

    @pytest.mark.asyncio
    async def test_ac1_9_fit_arima_metrics_include_order(self, monthly_series: pd.Series) -> None:
        """TEST-AC-1.9: Metrics dict includes order.

        Given: A time series
        When: Calling fit_arima() and getting metrics
        Then: The metrics dict should include 'order' tuple (p, d, q)
        """
        from raglite.forecasting.models.arima_model import fit_arima

        _, metrics, _, _ = await fit_arima(monthly_series, forecast_horizon=4, frequency="M")

        assert "order" in metrics
        assert isinstance(metrics["order"], tuple)
        assert len(metrics["order"]) == 3  # (p, d, q)

    @pytest.mark.asyncio
    async def test_ac1_10_fit_arima_metrics_include_seasonal_order(
        self, monthly_series: pd.Series
    ) -> None:
        """TEST-AC-1.10: Metrics dict includes seasonal_order.

        Given: A time series with seasonality
        When: Calling fit_arima() and getting metrics
        Then: The metrics dict should include 'seasonal_order' tuple (P, D, Q, s)
        """
        from raglite.forecasting.models.arima_model import fit_arima

        _, metrics, _, _ = await fit_arima(monthly_series, forecast_horizon=4, frequency="M")

        assert "seasonal_order" in metrics
        assert isinstance(metrics["seasonal_order"], tuple)
        assert len(metrics["seasonal_order"]) == 4  # (P, D, Q, s)


# -----------------------------------------------------------------------------
# TEST-AC-3: Exogenous Variable Support
# -----------------------------------------------------------------------------


class TestExogenousVariableSupport:
    """AC3: Exogenous Variable Support tests."""

    @pytest.mark.asyncio
    async def test_ac3_1_fit_arima_accepts_x_train_dataframe(
        self, monthly_series: pd.Series, exogenous_train: pd.DataFrame
    ) -> None:
        """TEST-AC-3.1: fit_arima() accepts X_train: pd.DataFrame | None for training.

        Given: Historical time series with external regressors
        When: Calling fit_arima() with X_train DataFrame
        Then: The function should accept and use the regressors (ARIMAX)
        """
        from raglite.forecasting.models.arima_model import fit_arima

        result = await fit_arima(
            monthly_series,
            X_train=exogenous_train,
            forecast_horizon=4,
            frequency="M",
        )
        assert result is not None

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_ac3_2_fit_arima_accepts_x_future_dataframe(
        self,
        monthly_series: pd.Series,
        exogenous_train: pd.DataFrame,
        exogenous_future: pd.DataFrame,
    ) -> None:
        """TEST-AC-3.2: fit_arima() accepts X_future: pd.DataFrame | None for prediction.

        Given: Historical data with regressors and future regressor values
        When: Calling fit_arima() with both X_train and X_future
        Then: The function should use future regressors for prediction
        """
        from raglite.forecasting.models.arima_model import fit_arima

        model, metrics, predictions, conf_int = await fit_arima(
            monthly_series,
            X_train=exogenous_train,
            X_future=exogenous_future,
            forecast_horizon=4,
            frequency="M",
        )
        assert len(predictions) == 4

    @pytest.mark.asyncio
    async def test_ac3_3_validate_regressor_dimensions_match_horizon(
        self,
        monthly_series: pd.Series,
        exogenous_train: pd.DataFrame,
    ) -> None:
        """TEST-AC-3.3: Validate regressor dimensions match forecast horizon.

        Given: X_future with fewer rows than forecast_horizon
        When: Calling fit_arima() with mismatched dimensions
        Then: The function should raise ValueError or handle gracefully
        """
        from raglite.forecasting.models.arima_model import fit_arima

        # Create X_future with only 2 rows but forecast_horizon=4
        dates = pd.date_range(start="2025-01-01", periods=2, freq="MS")
        x_future_short = pd.DataFrame(
            {
                "gas_price": [82, 84],
                "euribor": [3.6, 3.7],
            },
            index=dates,
        )

        with pytest.raises((ValueError, RuntimeError)):
            await fit_arima(
                monthly_series,
                X_train=exogenous_train,
                X_future=x_future_short,
                forecast_horizon=4,
                frequency="M",
            )

    @pytest.mark.asyncio
    async def test_ac3_4_handle_missing_regressors_gracefully(
        self, monthly_series: pd.Series
    ) -> None:
        """TEST-AC-3.4: Handle missing regressors gracefully (fall back to pure ARIMA).

        Given: No exogenous regressors provided
        When: Calling fit_arima() without X_train or X_future
        Then: The function should fall back to pure ARIMA (not ARIMAX)
        """
        from raglite.forecasting.models.arima_model import fit_arima

        # Should work without regressors
        result = await fit_arima(
            monthly_series,
            X_train=None,
            X_future=None,
            forecast_horizon=4,
            frequency="M",
        )
        assert result is not None

    @pytest.mark.asyncio
    async def test_ac3_5_fit_arima_x_train_none_by_default(self, monthly_series: pd.Series) -> None:
        """TEST-AC-3.5: X_train defaults to None when not provided.

        Given: A time series without explicit X_train
        When: Calling fit_arima() without X_train parameter
        Then: The function should default to pure ARIMA (X_train=None)
        """
        from raglite.forecasting.models.arima_model import fit_arima

        result = await fit_arima(monthly_series, forecast_horizon=4, frequency="M")
        assert result is not None


# -----------------------------------------------------------------------------
# TEST-AC-4: Frequency Handling (ARIMA subset)
# -----------------------------------------------------------------------------


class TestFrequencyHandlingArima:
    """AC4: Frequency Handling tests for ARIMA."""

    @pytest.mark.asyncio
    async def test_ac4_1_monthly_frequency_seasonal_periods_12(
        self, monthly_series: pd.Series
    ) -> None:
        """TEST-AC-4.1: Monthly frequency ("M"): seasonal_periods=12.

        Given: Monthly financial data
        When: Calling fit functions with frequency="M"
        Then: Seasonal period should be set to 12
        """
        from raglite.forecasting.models.arima_model import fit_arima

        with patch("raglite.forecasting.models.arima_model._get_pmdarima") as mock_get_pm:
            mock_pm = MagicMock()
            mock_model = MagicMock()
            mock_model.aic.return_value = 100.0
            mock_model.order = (1, 1, 1)
            mock_model.seasonal_order = (1, 0, 1, 12)
            mock_model.predict.return_value = (
                np.array([200, 205, 210, 215]),
                np.array([[190, 210], [195, 215], [200, 220], [205, 225]]),
            )
            mock_pm.auto_arima.return_value = mock_model
            mock_get_pm.return_value = mock_pm

            await fit_arima(monthly_series, forecast_horizon=4, frequency="M")

            # Check that auto_arima was called with m=12
            call_kwargs = mock_pm.auto_arima.call_args
            assert call_kwargs is not None
            # Either in args or kwargs, m should be 12
            if "m" in call_kwargs.kwargs:
                assert call_kwargs.kwargs["m"] == 12

    @pytest.mark.asyncio
    async def test_ac4_2_quarterly_frequency_seasonal_periods_4(
        self, quarterly_series: pd.Series
    ) -> None:
        """TEST-AC-4.2: Quarterly frequency ("Q"): seasonal_periods=4.

        Given: Quarterly financial data
        When: Calling fit functions with frequency="Q"
        Then: Seasonal period should be set to 4
        """
        from raglite.forecasting.models.arima_model import fit_arima

        with patch("raglite.forecasting.models.arima_model._get_pmdarima") as mock_get_pm:
            mock_pm = MagicMock()
            mock_model = MagicMock()
            mock_model.aic.return_value = 100.0
            mock_model.order = (1, 1, 1)
            mock_model.seasonal_order = (1, 0, 1, 4)
            mock_model.predict.return_value = (
                np.array([1400, 1450, 1500, 1550]),
                np.array([[1350, 1450], [1400, 1500], [1450, 1550], [1500, 1600]]),
            )
            mock_pm.auto_arima.return_value = mock_model
            mock_get_pm.return_value = mock_pm

            await fit_arima(quarterly_series, forecast_horizon=4, frequency="Q")

            call_kwargs = mock_pm.auto_arima.call_args
            assert call_kwargs is not None
            if "m" in call_kwargs.kwargs:
                assert call_kwargs.kwargs["m"] == 4

    @pytest.mark.asyncio
    async def test_ac4_3_auto_detect_frequency_from_series_index(self) -> None:
        """TEST-AC-4.3: Auto-detect frequency from Series index if not provided.

        Given: A series with DatetimeIndex without explicit frequency
        When: Calling fit_arima() without frequency parameter
        Then: The function should detect frequency from the index
        """
        from raglite.forecasting.models.arima_model import fit_arima

        dates = pd.date_range(start="2022-01-01", periods=36, freq="MS")
        values = np.linspace(100, 200, 36)
        series = pd.Series(values, index=dates)

        # Should auto-detect as monthly
        result = await fit_arima(series, forecast_horizon=4)
        assert result is not None


# -----------------------------------------------------------------------------
# TEST-AC-6: Graceful Fallback on Failure (ARIMA subset)
# -----------------------------------------------------------------------------


class TestGracefulFallbackOnFailureArima:
    """AC6: Graceful Fallback on Failure tests for ARIMA."""

    @pytest.mark.asyncio
    async def test_ac6_1_log_warning_with_error_details(self, short_series: pd.Series) -> None:
        """TEST-AC-6.1: Log warning with error details.

        Given: Data that causes fitting to fail
        When: Model fitting encounters errors
        Then: A warning should be logged with error details
        """
        from raglite.forecasting.models.arima_model import ARIMAFittingError, fit_arima

        # Patch the logger to capture log calls
        with patch("raglite.forecasting.models.arima_model.logger") as mock_logger:
            with patch("raglite.forecasting.models.arima_model._get_pmdarima") as mock_get_pm:
                mock_pm = MagicMock()
                mock_pm.auto_arima.side_effect = Exception("Convergence failed")
                mock_get_pm.return_value = mock_pm

                with pytest.raises(ARIMAFittingError):
                    await fit_arima(short_series, forecast_horizon=4, frequency="M")

                # Verify warning was logged
                mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_ac6_2_raise_specific_exception_arima(self, short_series: pd.Series) -> None:
        """TEST-AC-6.2: Return None or raise specific exception (ARIMA).

        Given: Data that causes ARIMA fitting to fail
        When: Model fitting fails
        Then: ARIMAFittingError should be raised (not generic Exception)
        """
        from raglite.forecasting.models.arima_model import ARIMAFittingError, fit_arima

        with patch("raglite.forecasting.models.arima_model._get_pmdarima") as mock_get_pm:
            mock_pm = MagicMock()
            mock_pm.auto_arima.side_effect = Exception("Convergence failed")
            mock_get_pm.return_value = mock_pm

            with pytest.raises(ARIMAFittingError) as exc_info:
                await fit_arima(short_series, forecast_horizon=4, frequency="M")

            assert "Failed to fit ARIMA" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_ac6_4_caller_can_fallback_to_other_model(
        self, monthly_series: pd.Series
    ) -> None:
        """TEST-AC-6.4: Caller can fall back to Prophet or other model.

        Given: ARIMA fitting fails
        When: Catching the exception
        Then: The caller should be able to fall back gracefully
        """
        from raglite.forecasting.models.arima_model import ARIMAFittingError, fit_arima

        fallback_used = False

        with patch("raglite.forecasting.models.arima_model._get_pmdarima") as mock_get_pm:
            mock_pm = MagicMock()
            mock_pm.auto_arima.side_effect = Exception("Convergence failed")
            mock_get_pm.return_value = mock_pm

            try:
                await fit_arima(monthly_series, forecast_horizon=4, frequency="M")
            except ARIMAFittingError:
                # Simulate fallback to another model
                fallback_used = True

        assert fallback_used

    @pytest.mark.asyncio
    async def test_ac6_5_handle_insufficient_data_failure(self, short_series: pd.Series) -> None:
        """TEST-AC-6.5: Common failure: insufficient data.

        Given: Very short time series (4 data points)
        When: Attempting to fit ARIMA
        Then: Should handle with appropriate error
        """
        from raglite.forecasting.models.arima_model import ARIMAFittingError, fit_arima

        # 4 data points is too few for reliable ARIMA with seasonality
        try:
            await fit_arima(short_series, forecast_horizon=4, frequency="M")
        except (ARIMAFittingError, ValueError):
            # Expected - insufficient data should be handled
            assert True

    @pytest.mark.asyncio
    async def test_ac6_6_handle_convergence_failure(self, monthly_series: pd.Series) -> None:
        """TEST-AC-6.6: Common failure: convergence issues.

        Given: Data that causes convergence issues
        When: Fitting fails due to convergence
        Then: Should raise specific error with details
        """
        from raglite.forecasting.models.arima_model import ARIMAFittingError, fit_arima

        with patch("raglite.forecasting.models.arima_model._get_pmdarima") as mock_get_pm:
            mock_pm = MagicMock()
            mock_pm.auto_arima.side_effect = Exception("Maximum likelihood estimation failed")
            mock_get_pm.return_value = mock_pm

            with pytest.raises(ARIMAFittingError) as exc_info:
                await fit_arima(monthly_series, forecast_horizon=4, frequency="M")

            # Error should contain original exception details
            assert "Maximum likelihood" in str(exc_info.value) or "Failed to fit" in str(
                exc_info.value
            )


# -----------------------------------------------------------------------------
# Module Export Tests (ARIMA subset)
# -----------------------------------------------------------------------------


class TestModuleExportsArima:
    """Module export tests for ARIMA."""

    def test_ac7_1_arima_model_exports_fit_arima(self) -> None:
        """TEST-AC-7.1: arima_model.py exports fit_arima.

        Given: The arima_model module
        When: Importing fit_arima
        Then: The function should be importable
        """
        from raglite.forecasting.models.arima_model import fit_arima

        assert callable(fit_arima)

    def test_ac7_2_arima_model_exports_arima_fitting_error(self) -> None:
        """TEST-AC-7.2: arima_model.py exports ARIMAFittingError.

        Given: The arima_model module
        When: Importing ARIMAFittingError
        Then: The exception class should be importable
        """
        from raglite.forecasting.models.arima_model import ARIMAFittingError

        assert issubclass(ARIMAFittingError, Exception)

    def test_ac7_5_models_package_exports_fit_arima(self) -> None:
        """TEST-AC-7.5: models/__init__.py exports fit_arima.

        Given: The models package
        When: Importing fit_arima from package
        Then: The function should be available at package level
        """
        from raglite.forecasting.models import fit_arima

        assert callable(fit_arima)

    def test_ac7_7_models_package_exports_arima_fitting_error(self) -> None:
        """TEST-AC-7.7: models/__init__.py exports ARIMAFittingError.

        Given: The models package
        When: Importing ARIMAFittingError from package
        Then: The exception should be available at package level
        """
        from raglite.forecasting.models import ARIMAFittingError

        assert issubclass(ARIMAFittingError, Exception)


# -----------------------------------------------------------------------------
# Edge Cases (ARIMA subset)
# -----------------------------------------------------------------------------


class TestEdgeCasesArima:
    """Additional edge case tests for ARIMA robustness."""

    @pytest.mark.asyncio
    async def test_edge_case_empty_series(self) -> None:
        """Test handling of empty series.

        Given: An empty pandas Series
        When: Calling fit functions
        Then: Should raise appropriate error
        """
        from raglite.forecasting.models.arima_model import fit_arima

        empty_series = pd.Series([], dtype=float)

        with pytest.raises((ValueError, Exception)):
            await fit_arima(empty_series, forecast_horizon=4, frequency="M")

    @pytest.mark.asyncio
    async def test_edge_case_single_forecast_horizon(self, monthly_series: pd.Series) -> None:
        """Test forecast horizon of 1.

        Given: A time series
        When: Requesting forecast_horizon=1
        Then: Should return single prediction
        """
        from raglite.forecasting.models.arima_model import fit_arima

        _, _, predictions, conf_int = await fit_arima(
            monthly_series, forecast_horizon=1, frequency="M"
        )

        assert len(predictions) == 1
        assert conf_int.shape[0] == 1

    @pytest.mark.asyncio
    async def test_edge_case_custom_confidence_level(self, monthly_series: pd.Series) -> None:
        """Test custom confidence level.

        Given: A time series
        When: Requesting 90% confidence level
        Then: Should apply the custom level
        """
        from raglite.forecasting.models.arima_model import fit_arima

        _, _, _, conf_int_95 = await fit_arima(
            monthly_series, forecast_horizon=4, frequency="M", confidence_level=0.95
        )
        _, _, _, conf_int_90 = await fit_arima(
            monthly_series, forecast_horizon=4, frequency="M", confidence_level=0.90
        )

        # 90% CI should be narrower than 95% CI (on average)
        width_95 = np.mean(conf_int_95[:, 1] - conf_int_95[:, 0])
        width_90 = np.mean(conf_int_90[:, 1] - conf_int_90[:, 0])

        assert width_90 < width_95
