"""Integration tests for model_weights PostgreSQL schema (Story 6.12 AC2)."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from raglite.external_data.orm_models import ModelWeightORM
from raglite.external_data.storage import ExternalDataStorage

# Mark all tests in this module as integration tests
pytestmark = [
    pytest.mark.integration,
    pytest.mark.preserve_collection,
    pytest.mark.slow,
    pytest.mark.xdist_group(name="database_writes"),
]


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
