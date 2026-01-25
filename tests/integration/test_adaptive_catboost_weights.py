"""Integration tests for adaptive CatBoost weights with static fallback.

Tests for AC4: Adaptive weight behavior when no regressors are provided.
When no external regressors are available, CatBoost should be excluded
from the ensemble, falling back to Prophet-only forecasting.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

import numpy as np
import pytest

from raglite.forecasting.ensemble import generate_ensemble_forecast

# Set test environment before importing
os.environ["APP_ENV"] = "test"

# Set DYLD_LIBRARY_PATH for XGBoost/CatBoost on macOS
os.environ.setdefault("DYLD_LIBRARY_PATH", "/opt/homebrew/opt/libomp/lib")

if TYPE_CHECKING:
    from raglite.shared.models import TimeSeriesData

# Skip all tests in this module if not running integration tests
# requires_ml_stack: Loads CatBoost, ensemble forecasting (~3-4GB)
pytestmark = [
    pytest.mark.integration,
    pytest.mark.preserve_collection,
    pytest.mark.slow,
    pytest.mark.requires_ml_stack,
]


@pytest.fixture
def sample_historical_data() -> TimeSeriesData:
    """Create sample historical data with 20 data points for ML models."""
    from raglite.shared.models import TimeSeriesData, TimeSeriesPoint

    # Generate 20 monthly data points (more than minimum 12 for proper train/test split)
    # Use timezone-naive datetimes for Prophet compatibility
    base_date = datetime(2023, 1, 1)  # No timezone for Prophet
    np.random.seed(42)  # Reproducible random values
    points = [
        TimeSeriesPoint(
            date=base_date + timedelta(days=30 * i),
            value=1000.0 + i * 50.0 + np.random.uniform(-10, 10),  # noqa: S311
            label=f"Month {i + 1}",
        )
        for i in range(20)
    ]
    return TimeSeriesData(
        metric_name="cement_demand",
        points=points,
        interval="monthly",
        source_documents=["test_financial_report.pdf"],
    )


class TestAdaptiveCatBoostWeights:
    """Tests for adaptive CatBoost weights with static fallback."""

    @pytest.mark.asyncio
    async def test_adaptive_catboost_weights_with_static_fallback(
        self,
        sample_historical_data: TimeSeriesData,
    ) -> None:
        """Test that CatBoost is excluded when no regressors provided.

        When no external regressors are available, CatBoost cannot run
        (it requires features). The ensemble should fall back to Prophet-only
        forecasting with weight 1.0.
        """
        # Epic 8 API change: historical_data is now a required positional parameter
        result = await generate_ensemble_forecast(
            metric="cement_demand",
            historical_data=sample_historical_data,  # Required param (Epic 8)
            external_regressors=None,  # No regressors - CatBoost can't run
            periods_ahead=4,
            models=["prophet", "catboost"],  # Explicitly include CatBoost in request
            fast_mode=True,
        )

        # Should have forecasts
        assert len(result.forecast) == 4

        # When no regressors, CatBoost should be excluded from ensemble
        assert "catboost" not in result.ensemble_models

        # Prophet should be the only model in the ensemble (static fallback)
        assert len(result.ensemble_models) == 1
        assert "prophet" in result.ensemble_models

        # Prophet should have weight 1.0 when it's the only model
        # Note: Weights are re-normalized via handle_model_failure() when CatBoost
        # is excluded due to missing regressors (Story 6.12 AC4)
        assert result.ensemble_weights.get("prophet", 0) == 1.0
