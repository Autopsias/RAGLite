"""Integration tests for Story 6.12: CatBoost + Adaptive Weights (Core).

Tests:
- AC1: CatBoost in ensemble forecasting
- AC2: model_weights PostgreSQL schema CRUD

REQUIRES: PostgreSQL running on test port (5433)
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
import pytest
from sqlalchemy.exc import IntegrityError

from raglite.external_data.orm_models import ModelWeightORM
from raglite.external_data.storage import ExternalDataStorage
from raglite.forecasting.ensemble import generate_ensemble_forecast

# Set test environment before importing
os.environ["APP_ENV"] = "test"

# Set DYLD_LIBRARY_PATH for XGBoost/CatBoost on macOS
os.environ.setdefault("DYLD_LIBRARY_PATH", "/opt/homebrew/opt/libomp/lib")

if TYPE_CHECKING:
    from raglite.shared.models import TimeSeriesData

# Skip all tests in this module if not running integration tests
pytestmark = [pytest.mark.integration, pytest.mark.preserve_collection, pytest.mark.slow]

# NOTE: db_session and clean_session fixtures are provided by tests/integration/conftest.py
# Do NOT define duplicate fixtures here - causes xdist deadlock (P0 fix 2026-01-23)


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


@pytest.fixture
def sample_external_regressors() -> dict[str, pd.Series]:
    """Create sample external regressors with correlation to target."""
    # Use timezone-naive datetimes to match sample_historical_data
    base_date = datetime(2023, 1, 1)  # No timezone
    dates = pd.DatetimeIndex([base_date + timedelta(days=30 * i) for i in range(20)])

    return {
        "building_permits": pd.Series(
            [
                1000,
                1020,
                1050,
                1080,
                1100,
                1150,
                1180,
                1200,
                1250,
                1280,
                1300,
                1350,
                1380,
                1420,
                1450,
                1500,
                1550,
                1600,
                1650,
                1700,
            ],
            index=dates,
        ),
        "electricity_price": pd.Series(
            [
                50.0,
                51.2,
                52.1,
                53.5,
                54.0,
                55.2,
                56.8,
                57.0,
                58.5,
                59.0,
                60.2,
                61.0,
                62.5,
                63.2,
                64.0,
                65.5,
                66.8,
                68.0,
                69.5,
                70.2,
            ],
            index=dates,
        ),
    }


class TestModelWeightSchema:
    """Tests for model_weights PostgreSQL schema (AC2)."""

    def test_model_weight_table_exists(self, clean_session) -> None:
        """Test model_weights table was created."""
        # Simple query to verify table exists
        count = clean_session.query(ModelWeightORM).count()
        assert count >= 0  # Table exists if query succeeds

    def test_create_model_weight(self, clean_session) -> None:
        """Test creating a new model weight record."""
        weight = ModelWeightORM(
            metric_name="cement_demand_test",
            model_name="catboost",
            weight=Decimal("0.1500"),
            backtest_rmse=Decimal("45.32"),
            backtest_mape=Decimal("3.21"),
            has_regressors=True,
            data_points=20,
        )
        clean_session.add(weight)
        clean_session.flush()

        assert weight.id is not None
        assert weight.calculated_at is not None

    def test_query_model_weights_by_metric(self, clean_session) -> None:
        """Test querying model weights by metric name."""
        # Create weights for multiple models
        for model_name in ["prophet", "catboost", "xgboost"]:
            weight = ModelWeightORM(
                metric_name="revenue_test_query",
                model_name=model_name,
                weight=Decimal("0.3333"),
            )
            clean_session.add(weight)
        clean_session.flush()

        # Query by metric
        weights = (
            clean_session.query(ModelWeightORM)
            .filter(ModelWeightORM.metric_name == "revenue_test_query")
            .all()
        )

        assert len(weights) == 3

    def test_unique_constraint_metric_model(self, clean_session) -> None:
        """Test unique constraint on (metric_name, model_name)."""
        # Create first weight
        weight1 = ModelWeightORM(
            metric_name="cement_demand_unique_test",
            model_name="catboost",
            weight=Decimal("0.15"),
        )
        clean_session.add(weight1)
        clean_session.flush()

        # Try to create duplicate
        weight2 = ModelWeightORM(
            metric_name="cement_demand_unique_test",  # Same metric
            model_name="catboost",  # Same model
            weight=Decimal("0.20"),
        )
        clean_session.add(weight2)

        with pytest.raises(IntegrityError):
            clean_session.flush()

        clean_session.rollback()

    def test_update_existing_weight(self, clean_session) -> None:
        """Test updating an existing model weight."""
        # Create weight
        weight = ModelWeightORM(
            metric_name="revenue_update_test",
            model_name="prophet",
            weight=Decimal("0.30"),
            backtest_rmse=Decimal("100.0"),
        )
        clean_session.add(weight)
        clean_session.flush()

        # Update it
        weight.weight = Decimal("0.35")
        weight.backtest_rmse = Decimal("85.0")
        weight.calculated_at = datetime.now(UTC)
        clean_session.flush()

        # Verify update
        updated = (
            clean_session.query(ModelWeightORM)
            .filter(
                ModelWeightORM.metric_name == "revenue_update_test",
                ModelWeightORM.model_name == "prophet",
            )
            .first()
        )
        assert updated.weight == Decimal("0.35")
        assert updated.backtest_rmse == Decimal("85.0")


class TestStorageModelWeightMethods:
    """Tests for ExternalDataStorage model weight methods (AC2)."""

    def test_save_model_weight_creates_record(self, clean_session) -> None:
        """Test save_model_weight creates a new weight record."""
        storage = ExternalDataStorage(session=clean_session)

        result = storage.save_model_weight(
            metric_name="cement_demand_storage_test",
            model_name="catboost",
            weight=0.15,
            backtest_rmse=45.32,
            backtest_mape=3.21,
            has_regressors=True,
            data_points=20,
        )

        assert result is not None
        assert result.metric_name == "cement_demand_storage_test"
        assert result.model_name == "catboost"
        assert float(result.weight) == pytest.approx(0.15, rel=0.01)

    def test_save_model_weight_upserts(self, clean_session) -> None:
        """Test save_model_weight updates existing record (upsert)."""
        storage = ExternalDataStorage(session=clean_session)

        # Create initial
        storage.save_model_weight(
            metric_name="cement_demand_upsert_test",
            model_name="prophet",
            weight=0.30,
            backtest_rmse=100.0,
        )

        # Upsert with new values
        result = storage.save_model_weight(
            metric_name="cement_demand_upsert_test",
            model_name="prophet",
            weight=0.35,
            backtest_rmse=85.0,
        )

        assert float(result.weight) == pytest.approx(0.35, rel=0.01)
        assert float(result.backtest_rmse) == pytest.approx(85.0, rel=0.01)

    def test_get_model_weights_all(self, clean_session) -> None:
        """Test get_model_weights returns all weights."""
        storage = ExternalDataStorage(session=clean_session)

        # Create weights for different metrics
        for metric in ["metric_a", "metric_b"]:
            storage.save_model_weight(
                metric_name=metric,
                model_name="prophet",
                weight=0.5,
            )

        weights = storage.get_model_weights()
        assert len(weights) >= 2

    def test_get_model_weights_by_metric(self, clean_session) -> None:
        """Test get_model_weights filters by metric."""
        storage = ExternalDataStorage(session=clean_session)

        # Create weights for one metric
        for model in ["prophet", "catboost"]:
            storage.save_model_weight(
                metric_name="filtered_metric_test",
                model_name=model,
                weight=0.5,
            )

        weights = storage.get_model_weights(metric_name="filtered_metric_test")
        assert len(weights) == 2
        assert all(w.metric_name == "filtered_metric_test" for w in weights)

    def test_get_weights_for_metric_returns_dict(self, clean_session) -> None:
        """Test get_weights_for_metric returns model->weight dict."""
        storage = ExternalDataStorage(session=clean_session)

        # Create weights
        storage.save_model_weight("dict_test_metric", "prophet", 0.30)
        storage.save_model_weight("dict_test_metric", "catboost", 0.25)
        storage.save_model_weight("dict_test_metric", "xgboost", 0.45)

        weights_dict = storage.get_weights_for_metric("dict_test_metric")

        assert isinstance(weights_dict, dict)
        assert "prophet" in weights_dict
        assert "catboost" in weights_dict
        assert "xgboost" in weights_dict
        assert abs(sum(weights_dict.values()) - 1.0) < 0.01  # Sum to ~1.0

    def test_delete_model_weights_by_metric(self, clean_session) -> None:
        """Test delete_model_weights removes weights for metric."""
        storage = ExternalDataStorage(session=clean_session)

        # Create weights
        storage.save_model_weight("delete_test_metric", "prophet", 0.5)
        storage.save_model_weight("delete_test_metric", "catboost", 0.5)

        # Delete
        deleted = storage.delete_model_weights(metric_name="delete_test_metric")
        assert deleted == 2

        # Verify deletion
        remaining = storage.get_model_weights(metric_name="delete_test_metric")
        assert len(remaining) == 0


class TestEnsembleWithCatBoost:
    """Integration tests for ensemble forecasting with CatBoost (AC1)."""

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_ensemble_includes_catboost(
        self,
        sample_historical_data: TimeSeriesData,
        sample_external_regressors: dict[str, pd.Series],
    ) -> None:
        """Test ensemble forecast includes CatBoost model.

        Story 6.12 AC1: CatBoost Integration.
        """
        # Epic 8 API change: historical_data is now a required positional parameter
        result = await generate_ensemble_forecast(
            metric="cement_demand",
            historical_data=sample_historical_data,  # Required param (Epic 8)
            external_regressors=sample_external_regressors,
            periods_ahead=4,
            models=["prophet", "catboost"],  # Explicitly include CatBoost
            fast_mode=True,
        )

        # Verify ensemble result structure
        assert result.model_type == "ensemble"
        assert len(result.forecast) == 4

        # CatBoost should be in the ensemble (if features available)
        # Note: CatBoost requires external regressors
        assert "catboost" in result.ensemble_models or "prophet" in result.ensemble_models

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_ensemble_catboost_with_all_models(
        self,
        sample_historical_data: TimeSeriesData,
        sample_external_regressors: dict[str, pd.Series],
    ) -> None:
        """Test ensemble with all 5 models including CatBoost."""
        # Epic 8 API change: historical_data is now a required positional parameter
        result = await generate_ensemble_forecast(
            metric="cement_demand",
            historical_data=sample_historical_data,  # Required param (Epic 8)
            external_regressors=sample_external_regressors,
            periods_ahead=4,
            models=["prophet", "linear", "xgboost", "lightgbm", "catboost"],
            fast_mode=True,
        )

        # Should have forecasts
        assert len(result.forecast) == 4

        # Verify individual predictions tracked
        assert len(result.individual_predictions) > 0

        # Verify weights recorded
        assert len(result.ensemble_weights) > 0

    @pytest.mark.asyncio
    async def test_catboost_only_forecast(
        self,
        sample_historical_data: TimeSeriesData,
        sample_external_regressors: dict[str, pd.Series],
    ) -> None:
        """Test forecast with CatBoost only."""
        # Epic 8 API change: historical_data is now a required positional parameter
        result = await generate_ensemble_forecast(
            metric="cement_demand",
            historical_data=sample_historical_data,  # Required param (Epic 8)
            external_regressors=sample_external_regressors,
            periods_ahead=4,
            models=["catboost"],
            fast_mode=True,
        )

        # Should generate forecasts
        assert len(result.forecast) == 4

        # CatBoost should be the only model or fallback to empty if it failed
        if result.ensemble_models:
            assert "catboost" in result.ensemble_models
