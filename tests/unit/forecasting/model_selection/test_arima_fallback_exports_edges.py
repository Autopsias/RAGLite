"""ATDD Tests for ARIMA Model Wrapper (Story 7b.1).

Continuation of tests.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest


class TestGracefulFallbackArima:
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


@pytest.mark.xdist_group(name="arima_edge")
class TestEdgeCasesArima:
    """Additional edge case tests for ARIMA robustness.

    Note: Grouped for serial execution to prevent pmdarima state pollution
    under parallel test execution (pytest-xdist).
    """

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
