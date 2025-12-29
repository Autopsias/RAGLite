"""Unit tests for Chronos-2 integration.

Story 6.13: Chronos-2 Cold-Start & Ensemble Member

Test Coverage:
- Lazy-loading pattern and caching (AC1, AC5)
- Cold-start path detection (<6 data points) (AC2)
- Fallback weight boosting logic (AC4)
- Model inference timeout handling (AC6)
- Configuration parameters (AC2, AC3, AC6)
"""

from __future__ import annotations

import os
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
import torch  # noqa: E402

from raglite.forecasting.adaptive_weights import (  # noqa: E402
    _adjust_weights_no_regressors,
    _get_static_weights,
)
from raglite.forecasting.hybrid import generate_forecast  # noqa: E402
from raglite.forecasting.models.base import MIN_DATA_POINTS, InsufficientDataError  # noqa: E402
from raglite.forecasting.models.chronos_model import (  # noqa: E402
    _get_chronos_pipeline,
    generate_chronos_cold_start_forecast,
)
from raglite.shared.config import settings  # noqa: E402
from raglite.shared.models import TimeSeriesData, TimeSeriesPoint  # noqa: E402

# Skip all tests in this module when running in LIGHTWEIGHT_TESTS mode
# These tests require real PyTorch/Chronos libraries
pytestmark = pytest.mark.skipif(
    os.environ.get("LIGHTWEIGHT_TESTS") == "true",
    reason="Chronos tests require real PyTorch/Chronos (not mocked)",
)

# =============================================================================
# AC1, AC5: Lazy-Loading Pattern and Caching
# =============================================================================


def test_chronos_pipeline_lazy_loading() -> None:
    """Test Chronos-2 pipeline lazy-loads on first use."""
    # Reset global cache for test isolation
    import raglite.forecasting.models.chronos_model as chronos_module

    original_pipeline = chronos_module._chronos_pipeline
    chronos_module._chronos_pipeline = None

    try:
        with patch("chronos.BaseChronosPipeline") as mock_class:
            mock_pipeline = MagicMock()
            mock_class.from_pretrained.return_value = mock_pipeline

            # First call should load model
            pipeline1 = _get_chronos_pipeline()
            assert pipeline1 is mock_pipeline
            mock_class.from_pretrained.assert_called_once_with(
                "amazon/chronos-bolt-small",
                device_map="cpu",
            )

            # Second call should use cached instance (no new call)
            pipeline2 = _get_chronos_pipeline()
            assert pipeline2 is mock_pipeline
            assert mock_class.from_pretrained.call_count == 1  # Still 1, not 2

    finally:
        chronos_module._chronos_pipeline = original_pipeline


def test_chronos_pipeline_import_error() -> None:
    """Test Chronos-2 raises helpful error if package not installed."""
    import raglite.forecasting.models.chronos_model as chronos_module

    original_pipeline = chronos_module._chronos_pipeline
    chronos_module._chronos_pipeline = None

    try:
        # Patch the import itself to simulate ImportError
        with patch("builtins.__import__", side_effect=ImportError("No module named chronos")):
            with pytest.raises(ImportError, match="chronos-forecasting"):
                _get_chronos_pipeline()

    finally:
        chronos_module._chronos_pipeline = original_pipeline


# =============================================================================
# AC2: Cold-Start Path Detection
# =============================================================================


@pytest.mark.asyncio
async def test_cold_start_detection_with_insufficient_data() -> None:
    """Test cold-start path when data points < MIN_DATA_POINTS."""
    # Create minimal data (5 points, < MIN_DATA_POINTS=6)
    points = [
        TimeSeriesPoint(date=datetime(2024, i, 1), value=100.0 + i * 5, label=f"M{i}")
        for i in range(1, 6)
    ]
    data = TimeSeriesData(metric_name="test_metric", points=points, interval="monthly")

    with patch(
        "raglite.forecasting.hybrid.ensemble.generate_chronos_cold_start_forecast"
    ) as mock_cold_start:
        # Mock return value
        from raglite.shared.models import ForecastResult

        mock_cold_start.return_value = ForecastResult(
            metric_name="test_metric",
            forecast=[],
            model_type="chronos-2-zero-shot",
            confidence_reasoning="Cold-start test",
        )

        # Call generate_forecast with insufficient data
        with patch(
            "raglite.forecasting.hybrid.preprocessing.fetch_historical_metric"
        ) as mock_fetch:
            mock_fetch.return_value = data  # Use the data variable defined above
            result = await generate_forecast(
                metric="test_metric",
                periods_ahead=3,
            )

        # Verify cold-start path was triggered
        mock_cold_start.assert_called_once()
        assert result.model_type == "chronos-2-zero-shot"


@pytest.mark.asyncio
async def test_cold_start_with_absolute_minimum() -> None:
    """Test cold-start succeeds with 3 data points (absolute minimum)."""
    points = [
        TimeSeriesPoint(date=datetime(2024, i, 1), value=100.0, label=f"M{i}") for i in range(1, 4)
    ]
    data = TimeSeriesData(metric_name="test_metric", points=points, interval="monthly")

    with patch(
        "raglite.forecasting.models.chronos_model._get_chronos_pipeline"
    ) as mock_get_pipeline:
        mock_pipeline = MagicMock()
        mock_get_pipeline.return_value = mock_pipeline

        # Mock forecast output
        mock_forecast = torch.randn(1, 100, 3)  # (batch, samples, periods)
        mock_pipeline.predict.return_value = mock_forecast

        result = await generate_chronos_cold_start_forecast(
            metric="test_metric",
            historical_data=data,
            periods_ahead=3,
        )

        assert result.model_type == "chronos-2-zero-shot"
        assert len(result.forecast) == 3
        assert "cold-start" in result.confidence_reasoning.lower()
        mock_pipeline.predict.assert_called_once()


@pytest.mark.asyncio
async def test_cold_start_fails_below_absolute_minimum() -> None:
    """Test cold-start raises error with <3 data points."""
    points = [
        TimeSeriesPoint(date=datetime(2024, i, 1), value=100.0, label=f"M{i}")
        for i in range(1, 3)  # Only 2 points
    ]
    data = TimeSeriesData(metric_name="test_metric", points=points, interval="monthly")

    with pytest.raises(InsufficientDataError, match="minimum 3 data points"):
        await generate_chronos_cold_start_forecast(
            metric="test_metric",
            historical_data=data,
            periods_ahead=3,
        )


def test_min_data_points_constant() -> None:
    """Test MIN_DATA_POINTS constant is set correctly (AC2)."""
    assert MIN_DATA_POINTS == 6


# =============================================================================
# AC4: Fallback Weight Boosting Logic
# =============================================================================


def test_weight_boosting_no_regressors() -> None:
    """Test Chronos-2 weight boosted when no regressors available."""
    weights = {
        "prophet": 0.24,
        "chronos": 0.12,
        "linear": 0.12,
        "xgboost": 0.15,
        "lightgbm": 0.15,
    }

    adjusted = _adjust_weights_no_regressors(weights)

    # Chronos should be boosted (x2)
    # Prophet should be boosted (x2)
    # Others should be reduced (x0.3)
    assert adjusted["chronos"] > weights["chronos"]
    assert adjusted["prophet"] > weights["prophet"]
    assert adjusted["linear"] < weights["linear"]
    assert adjusted["xgboost"] < weights["xgboost"]

    # Weights should sum to 1.0
    assert abs(sum(adjusted.values()) - 1.0) < 0.001


def test_static_weights_include_chronos() -> None:
    """Test static weights include Chronos-2 (AC3)."""
    weights = _get_static_weights()

    assert "chronos" in weights
    assert weights["chronos"] == settings.ensemble_weight_chronos
    assert weights["chronos"] == 0.12  # Default from config


# =============================================================================
# AC6: Configuration Parameters
# =============================================================================


def test_chronos_config_parameters() -> None:
    """Test Chronos-2 configuration parameters exist."""
    assert hasattr(settings, "ensemble_weight_chronos")
    assert hasattr(settings, "min_data_points_for_ensemble")
    assert hasattr(settings, "chronos_model_name")
    assert hasattr(settings, "chronos_inference_timeout")

    assert settings.ensemble_weight_chronos == 0.12
    assert settings.min_data_points_for_ensemble == 6
    assert settings.chronos_model_name == "amazon/chronos-bolt-small"
    assert settings.chronos_inference_timeout == 2.0


def test_chronos_in_forecasting_models() -> None:
    """Test chronos is included in default forecasting_models."""
    models = settings.forecasting_models.split(",")
    assert "chronos" in models
