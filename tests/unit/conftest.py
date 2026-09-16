"""Shared fixtures for unit tests."""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import AsyncMock, Mock, patch

import pandas as pd
import pytest

from raglite.forecasting.model_selection import ModelSelectionResult


@pytest.fixture(scope="session", autouse=True)
def block_external_apis_in_unit_tests():
    """Prevent unit tests from making real external API calls.

    This fixture blocks external API calls to:
    - Mistral AI (embedding, classification)
    - Claude API (synthesis, LLM calls)
    - PostgreSQL (database connections)
    - Qdrant (vector database)

    Any unit test attempting real API calls will fail fast with a clear error
    message instead of timing out mysteriously.

    Why this matters:
    - Unit tests should NEVER hit real external services
    - Real API calls cause 5-15s timeout overhead per test
    - Fail-fast approach prevents mysterious CI hangs
    - Forces proper mocking discipline

    Related Issues:
    - Strategic Analysis: 39% of commits are CI fixes
    - Root Cause: Incomplete mocks allow real API calls in unit tests
    - Prevention: Block at session level, fail immediately with helpful error
    """
    # Block Mistral AI client
    with patch("raglite.shared.clients.get_mistral_client") as mock_mistral:
        mock_mistral.side_effect = RuntimeError(
            "❌ Unit test attempted to call Mistral API!\n"
            "Unit tests must mock get_mistral_client().\n"
            "Add: patch('raglite.shared.clients.get_mistral_client', return_value=MockClient())"
        )

        # Block Claude API client
        with patch("raglite.shared.clients.get_claude_client") as mock_claude:
            mock_claude.side_effect = RuntimeError(
                "❌ Unit test attempted to call Claude API!\n"
                "Unit tests must mock get_claude_client().\n"
                "Add: patch('raglite.shared.clients.get_claude_client', return_value=MockClient())"
            )

            # Block PostgreSQL client
            with patch("raglite.shared.clients.get_postgresql_connection") as mock_pg:
                mock_pg.side_effect = RuntimeError(
                    "❌ Unit test attempted to connect to PostgreSQL!\n"
                    "Unit tests must mock get_postgresql_connection().\n"
                    "Add: patch('raglite.shared.clients.get_postgresql_connection', return_value=MockConnection())"
                )

                # Block Qdrant client
                with patch("raglite.shared.clients.get_qdrant_client") as mock_qdrant:
                    mock_qdrant.side_effect = RuntimeError(
                        "❌ Unit test attempted to connect to Qdrant!\n"
                        "Unit tests must mock get_qdrant_client().\n"
                        "Add: patch('raglite.shared.clients.get_qdrant_client', return_value=MockClient())"
                    )

                    yield


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
