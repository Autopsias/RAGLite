"""Cache operations tests for model selection.

Story 7b-4: Model Selection Cache in PostgreSQL
TEST-AC-7b.4.2.x: cache_model_selection tests
TEST-AC-7b.4.3.x: get_cached_model_selection tests
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

# Mark all tests as integration and PostgreSQL-only
# 'postgresql_only' marker: These tests use ONLY PostgreSQL, not Qdrant
# Used for filtering test runs when troubleshooting database-specific issues
pytestmark = [
    pytest.mark.integration,
    pytest.mark.postgresql_only,
    pytest.mark.slow,
]


class TestCacheModelSelectionIntegration:
    """[P0] AC-7b.4.2: Integration tests for cache_model_selection."""

    @pytest.mark.manages_collection_state
    def test_ac_7b_4_2_4_cache_stores_result_in_database(
        self,
        db_session: Session,
        sample_model_selection_result,
        cleanup_model_selection,
    ) -> None:
        """TEST-AC-7b.4.2.4: cache_model_selection stores result in database."""
        from raglite.external_data.orm_models import ModelSelectionORM
        from raglite.external_data.storage import cache_model_selection

        cache_model_selection(sample_model_selection_result)

        # Verify record exists
        record = (
            db_session.query(ModelSelectionORM)
            .filter(ModelSelectionORM.variable_name == "ebitda")
            .first()
        )

        assert record is not None
        assert record.variable_name == "ebitda"
        assert record.best_model == "prophet"
        assert float(record.best_mape) == pytest.approx(5.5, rel=0.01)
        assert float(record.best_mase) == pytest.approx(0.8, rel=0.01)
        assert record.use_regressors is True

    @pytest.mark.manages_collection_state
    def test_ac_7b_4_2_5_cache_upsert_updates_existing(
        self,
        db_session: Session,
        sample_model_selection_result,
        cleanup_model_selection,
    ) -> None:
        """TEST-AC-7b.4.2.5: cache_model_selection upserts (updates existing)."""
        from raglite.external_data.orm_models import ModelSelectionORM
        from raglite.external_data.storage import cache_model_selection
        from raglite.forecasting.model_selection import ModelSelectionResult

        # First cache
        cache_model_selection(sample_model_selection_result)

        # Modify and cache again
        updated_result = ModelSelectionResult(
            variable_name="ebitda",  # Same variable
            best_model="xgboost",  # Different model
            best_mape=4.5,  # Better MAPE
            best_mase=0.7,
            best_with_regressors=False,
            best_regressor_set=[],
            candidate_results={},
            data_characteristics=None,
            cv_folds=5,
            runtime_seconds=30.0,
        )
        cache_model_selection(updated_result)

        # Verify only one record exists
        count = (
            db_session.query(ModelSelectionORM)
            .filter(ModelSelectionORM.variable_name == "ebitda")
            .count()
        )
        assert count == 1

        # Verify it's the updated one
        record = (
            db_session.query(ModelSelectionORM)
            .filter(ModelSelectionORM.variable_name == "ebitda")
            .first()
        )
        assert record.best_model == "xgboost"
        assert float(record.best_mape) == pytest.approx(4.5, rel=0.01)

    @pytest.mark.manages_collection_state
    def test_ac_7b_4_2_6_cache_stores_regressor_list_as_json(
        self,
        db_session: Session,
        sample_model_selection_result,
        cleanup_model_selection,
    ) -> None:
        """TEST-AC-7b.4.2.6: regressor_list is stored as JSONB array."""
        from raglite.external_data.orm_models import ModelSelectionORM
        from raglite.external_data.storage import cache_model_selection

        cache_model_selection(sample_model_selection_result)

        record = (
            db_session.query(ModelSelectionORM)
            .filter(ModelSelectionORM.variable_name == "ebitda")
            .first()
        )

        assert record.regressor_list == ["gas_price", "euribor"]

    @pytest.mark.manages_collection_state
    def test_ac_7b_4_2_7_cache_stores_candidate_results_as_json(
        self,
        db_session: Session,
        sample_model_selection_result,
        cleanup_model_selection,
    ) -> None:
        """TEST-AC-7b.4.2.7: candidate_results is stored as JSONB."""
        from raglite.external_data.orm_models import ModelSelectionORM
        from raglite.external_data.storage import cache_model_selection

        cache_model_selection(sample_model_selection_result)

        record = (
            db_session.query(ModelSelectionORM)
            .filter(ModelSelectionORM.variable_name == "ebitda")
            .first()
        )

        assert "prophet_True" in record.candidate_results
        assert record.candidate_results["prophet_True"]["mape"] == 5.5


class TestGetCachedModelSelectionIntegration:
    """[P0] AC-7b.4.3: Integration tests for get_cached_model_selection."""

    @pytest.mark.manages_collection_state
    def test_ac_7b_4_3_7_get_returns_cached_model_selection(
        self,
        db_session: Session,
        sample_model_selection_result,
        cleanup_model_selection,
    ) -> None:
        """TEST-AC-7b.4.3.7: get_cached_model_selection returns CachedModelSelection."""
        from raglite.external_data.storage import (
            cache_model_selection,
            get_cached_model_selection,
        )

        cache_model_selection(sample_model_selection_result)
        result = get_cached_model_selection("ebitda")

        assert result is not None
        assert result.__class__.__name__ == "CachedModelSelection"
        assert result.variable_name == "ebitda"
        assert result.best_model == "prophet"
        assert result.best_mape == pytest.approx(5.5, rel=0.01)
        assert result.use_regressors is True
        assert result.regressor_list == ["gas_price", "euribor"]

    @pytest.mark.preserve_collection
    def test_ac_7b_4_3_8_get_returns_none_for_missing(
        self,
        cleanup_model_selection,
    ) -> None:
        """TEST-AC-7b.4.3.8: get_cached_model_selection returns None for missing."""
        from raglite.external_data.storage import get_cached_model_selection

        result = get_cached_model_selection("nonexistent_variable")
        assert result is None

    @pytest.mark.manages_collection_state
    def test_ac_7b_4_3_9_get_performance_under_100ms(
        self,
        db_session: Session,
        sample_model_selection_result,
        cleanup_model_selection,
    ) -> None:
        """TEST-AC-7b.4.3.9: get_cached_model_selection completes in <100ms."""
        from raglite.external_data.storage import (
            cache_model_selection,
            get_cached_model_selection,
        )

        # First cache the result
        cache_model_selection(sample_model_selection_result)

        # Measure lookup time
        start = time.time()
        result = get_cached_model_selection("ebitda")
        elapsed_ms = (time.time() - start) * 1000

        assert result is not None
        assert elapsed_ms < 100, f"Lookup took {elapsed_ms:.1f}ms, exceeds 100ms target"

    @pytest.mark.manages_collection_state
    def test_ac_7b_4_3_10_get_returns_expired_with_flag(
        self,
        db_session: Session,
        cleanup_model_selection,
    ) -> None:
        """TEST-AC-7b.4.3.10: get_cached_model_selection returns expired entry with is_expired=True."""
        from datetime import datetime, timedelta

        from raglite.external_data.orm_models import ModelSelectionORM
        from raglite.external_data.storage import get_cached_model_selection

        # Insert expired entry directly
        now = datetime.utcnow()
        expired_entry = ModelSelectionORM(
            variable_name="expired_var",
            best_model="prophet",
            best_mape=5.0,
            best_mase=0.8,
            use_regressors=False,
            regressor_list=[],
            candidate_results={},
            data_characteristics=None,
            selected_at=now - timedelta(days=8),
            expires_at=now - timedelta(days=1),  # Expired yesterday
        )
        db_session.add(expired_entry)
        db_session.commit()

        result = get_cached_model_selection("expired_var")

        assert result is not None
        assert result.is_expired is True
