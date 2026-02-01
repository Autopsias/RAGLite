"""Unit tests for Model Router Implementations.

Tests for model router functions (Prophet, Chronos, etc.) that delegate
to appropriate forecast generation functions.

NOTE: These tests are currently skipped due to Story 8-5 deprecation.
"""

from unittest.mock import AsyncMock, patch

import pandas as pd
import pytest

# =============================================================================
# Test Model Routers
# =============================================================================


class TestModelRouters:
    """Tests for model router implementations."""

    @pytest.mark.skip(
        reason="Story 8-5: Router functions still use deprecated historical_data parameter. "
        "These tests will be updated when router functions are migrated in future story.",
    )
    @pytest.mark.asyncio
    async def test_prophet_router_delegates_to_generate_forecast(
        self,
        sample_historical_data,
        sample_forecast_result,
    ) -> None:
        """Prophet router should delegate to generate_forecast."""
        from raglite.forecasting.hybrid import _generate_prophet_forecast

        with patch(
            "raglite.forecasting.hybrid.generate_forecast",
            new_callable=AsyncMock,
        ) as mock_forecast:
            mock_forecast.return_value = sample_forecast_result

            await _generate_prophet_forecast(
                metric="test_metric",
                historical_data=sample_historical_data,
                periods_ahead=4,
                external_regressors=None,
            )

            # Verify generate_forecast was called with use_model_selection=False
            mock_forecast.assert_called_once()
            call_kwargs = mock_forecast.call_args.kwargs
            assert call_kwargs["use_model_selection"] is False

    @pytest.mark.skip(
        reason="Story 8-5: Router functions still use deprecated historical_data parameter. "
        "These tests will be updated when router functions are migrated in future story.",
    )
    @pytest.mark.asyncio
    async def test_chronos_router_delegates_to_cold_start(
        self,
        sample_historical_data,
        sample_forecast_result,
    ) -> None:
        """Chronos router should delegate to generate_chronos_cold_start_forecast."""
        from raglite.forecasting.hybrid import _generate_chronos_forecast

        # Patch where the function is used (imported at module level in ensemble)
        with patch(
            "raglite.forecasting.hybrid.ensemble.generate_chronos_cold_start_forecast",
            new_callable=AsyncMock,
        ) as mock_chronos:
            mock_chronos.return_value = sample_forecast_result

            await _generate_chronos_forecast(
                metric="test_metric",
                historical_data=sample_historical_data,
                periods_ahead=4,
                external_regressors={"ignored": pd.Series([1, 2, 3])},  # Should be ignored
            )

            # Verify cold_start was called (regressors ignored for Chronos)
            mock_chronos.assert_called_once()
            call_kwargs = mock_chronos.call_args.kwargs
            assert "external_regressors" not in call_kwargs
