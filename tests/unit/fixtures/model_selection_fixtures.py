"""
Shared fixtures for model_selection_job tests.

This module contains common fixtures used across all model_selection_job test files.
Fixtures are auto-discovered by pytest through the tests/unit/conftest.py import.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pandas as pd
import pytest

if TYPE_CHECKING:
    pass


@pytest.fixture
def mock_historical_data():
    """Provide mock historical data with 15 points."""
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

    @contextmanager
    def _mocks(output_dir: str):
        with (
            patch(
                "raglite.forecasting.model_selection_job.fetch_historical_data",
                new_callable=AsyncMock,
                return_value=mock_historical_data,
            ),
            patch(
                "raglite.forecasting.model_selection_job.fetch_regressors_with_date_range",
                new_callable=AsyncMock,
                return_value={},
            ),
            patch(
                "raglite.forecasting.model_selection_job.select_best_model",
                new_callable=AsyncMock,
                return_value=mock_model_result,
            ),
            patch(
                "raglite.forecasting.model_selection_job.cache_model_selection",
                new_callable=Mock,
            ),
        ):
            yield

    return _mocks


@pytest.fixture
def single_selection_mocks(mock_historical_data, mock_model_result):
    """Context manager for single variable selection tests with cache tracking."""

    @contextmanager
    def _mocks():
        mock_cache = Mock()
        with (
            patch(
                "raglite.forecasting.model_selection_job.fetch_historical_data",
                new_callable=AsyncMock,
                return_value=mock_historical_data,
            ),
            patch(
                "raglite.forecasting.model_selection_job.fetch_regressors_with_date_range",
                new_callable=AsyncMock,
                return_value={},
            ),
            patch(
                "raglite.forecasting.model_selection_job.select_best_model",
                new_callable=AsyncMock,
                return_value=mock_model_result,
            ),
            patch(
                "raglite.forecasting.model_selection_job.cache_model_selection",
                mock_cache,
            ),
        ):
            yield mock_cache

    return _mocks
