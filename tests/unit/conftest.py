"""Shared fixtures for unit tests."""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import AsyncMock, Mock, patch

import pandas as pd
import pytest

from raglite.forecasting.model_selection import ModelSelectionResult


@pytest.fixture
def mock_historical_data():
    """Provide mock historical data with 15 points."""
    return pd.Series(
        [100.0 + i * 5 for i in range(15)],
        index=pd.date_range("2023-01-01", periods=15, freq="MS"),
    )


@pytest.fixture
def mock_model_result():
    """Provide mock model selection result as actual dataclass instance."""
    return ModelSelectionResult(
        variable_name="test_var",
        best_model="arima",
        best_mape=0.05,
        best_mase=0.8,
        best_with_regressors=False,
        best_regressor_set=[],
        cv_folds=5,
        runtime_seconds=10.0,
        candidate_results={},
        data_characteristics=None,
    )


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
                Mock(),
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
