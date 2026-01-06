from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import numpy as np
import pandas as pd
import pytest

from raglite.external_data.clients.atic import ATICClient


# Shared fixtures for mocking batch model selection dependencies
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
def short_series() -> pd.Series:
    """Create a short time series (only 4 data points) for edge case testing."""
    dates = pd.date_range(start="2024-01-01", periods=4, freq="MS")
    values = [100, 110, 105, 115]
    return pd.Series(values, index=dates, name="metric")


# Shared fixtures for mocking batch model selection dependencies
@pytest.fixture
def mock_historical_data():
    """Provide mock historical data with 15 points."""
    import pandas as pd

    return pd.Series(
        [100.0 + i * 5 for i in range(15)],
        index=pd.date_range("2023-01-01", periods=15, freq="MS"),
    )


@pytest.fixture
def mock_model_result():
    """Provide mock model selection result."""
    mock_result = MagicMock()
    mock_result.best_model = "arima"
    mock_result.best_mape = 0.05
    mock_result.best_mase = 0.8
    mock_result.best_with_regressors = False
    mock_result.best_regressor_set = None
    mock_result.cv_folds = 5
    mock_result.runtime_seconds = 10.0
    mock_result.candidate_results = {}
    return mock_result


@pytest.fixture
def batch_selection_mocks(mock_historical_data, mock_model_result):
    """Context manager providing all mocks needed for batch model selection tests."""
    from contextlib import contextmanager

    @contextmanager
    def _mocks(output_dir: str):
        with (
            patch.object(
                ATICClient,
                "fetch_historical_data",
                new_callable=AsyncMock,
                return_value=mock_historical_data,
            ),
            patch(
                "raglite.forecasting.regressor_fetch.fetch_regressors_with_date_range",
                new_callable=AsyncMock,
                return_value={},
            ),
            patch(
                "raglite.forecasting.model_selection.select_best_model",
                new_callable=AsyncMock,
                return_value=mock_model_result,
            ),
            patch(
                "raglite.external_data.storage.model_selection.cache_model_selection",
                new_callable=Mock,
            ),
        ):
            yield

    return _mocks


@pytest.fixture
def single_selection_mocks(mock_historical_data, mock_model_result):
    """Context manager for single variable selection tests with cache tracking."""
    from contextlib import contextmanager

    @contextmanager
    def _mocks():
        mock_cache = Mock()
        with (
            patch.object(
                ATICClient,
                "fetch_historical_data",
                new_callable=AsyncMock,
                return_value=mock_historical_data,
            ),
            patch(
                "raglite.forecasting.regressor_fetch.fetch_regressors_with_date_range",
                new_callable=AsyncMock,
                return_value={},
            ),
            patch(
                "raglite.forecasting.model_selection.select_best_model",
                new_callable=AsyncMock,
                return_value=mock_model_result,
            ),
            patch(
                "raglite.external_data.storage.model_selection.cache_model_selection",
                mock_cache,
            ),
        ):
            yield mock_cache

    return _mocks
