"""Input validation and edge case tests for model selection cache.

Story 7b-4: Model Selection Cache in PostgreSQL
M4 input validation tests and edge cases
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

# Mark all tests as integration and PostgreSQL-only
pytestmark = [
    pytest.mark.integration,
    pytest.mark.postgresql_only,
    pytest.mark.slow,
]


class TestInputValidationIntegration:
    """[P0] M4 input validation integration tests with real database."""

    @pytest.mark.preserve_collection
    def test_m4_get_cached_empty_variable_name_integration(
        self,
        cleanup_model_selection,
    ) -> None:
        """[P0] M4: get_cached_model_selection rejects empty variable_name (real DB)."""
        from raglite.external_data.storage import get_cached_model_selection

        with pytest.raises(ValueError, match="variable_name cannot be empty"):
            get_cached_model_selection("")

    @pytest.mark.preserve_collection
    def test_m4_get_cached_whitespace_only_integration(
        self,
        cleanup_model_selection,
    ) -> None:
        """[P0] M4: get_cached_model_selection rejects whitespace-only variable_name (real DB)."""
        from raglite.external_data.storage import get_cached_model_selection

        with pytest.raises(ValueError, match="variable_name cannot be empty"):
            get_cached_model_selection("   \t\n  ")

    @pytest.mark.preserve_collection
    def test_m4_get_cached_exceeds_100_chars_integration(
        self,
        cleanup_model_selection,
    ) -> None:
        """[P0] M4: get_cached_model_selection rejects >100 char variable_name (real DB)."""
        from raglite.external_data.storage import get_cached_model_selection

        long_name = "a" * 101
        with pytest.raises(ValueError, match="variable_name cannot exceed 100 characters"):
            get_cached_model_selection(long_name)

    @pytest.mark.preserve_collection
    def test_m4_invalidate_empty_variable_name_integration(
        self,
        cleanup_model_selection,
    ) -> None:
        """[P0] M4: invalidate_model_selection rejects empty variable_name (real DB)."""
        from raglite.external_data.storage import invalidate_model_selection

        with pytest.raises(ValueError, match="variable_name cannot be empty"):
            invalidate_model_selection("")

    @pytest.mark.preserve_collection
    def test_m4_invalidate_whitespace_only_integration(
        self,
        cleanup_model_selection,
    ) -> None:
        """[P0] M4: invalidate_model_selection rejects whitespace-only variable_name (real DB)."""
        from raglite.external_data.storage import invalidate_model_selection

        with pytest.raises(ValueError, match="variable_name cannot be empty"):
            invalidate_model_selection("   \t\n  ")

    @pytest.mark.preserve_collection
    def test_m4_invalidate_exceeds_100_chars_integration(
        self,
        cleanup_model_selection,
    ) -> None:
        """[P0] M4: invalidate_model_selection rejects >100 char variable_name (real DB)."""
        from raglite.external_data.storage import invalidate_model_selection

        long_name = "a" * 101
        with pytest.raises(ValueError, match="variable_name cannot exceed 100 characters"):
            invalidate_model_selection(long_name)


class TestEdgeCasesIntegration:
    """[P1] Edge case integration tests with real database."""

    @pytest.mark.manages_collection_state
    def test_cache_and_retrieve_with_none_data_characteristics(
        self,
        db_session: Session,
        cleanup_model_selection,
    ) -> None:
        """[P1] cache_model_selection stores None data_characteristics correctly."""
        from raglite.external_data.storage import (
            cache_model_selection,
            get_cached_model_selection,
        )
        from raglite.forecasting.model_selection import ModelSelectionResult

        result = ModelSelectionResult(
            variable_name="test_none_chars",
            best_model="prophet",
            best_mape=5.0,
            best_mase=0.8,
            best_with_regressors=False,
            best_regressor_set=[],
            candidate_results={},
            data_characteristics=None,  # Edge case: None
            cv_folds=5,
            runtime_seconds=30.0,
        )

        cache_model_selection(result)

        cached = get_cached_model_selection("test_none_chars")
        assert cached is not None
        assert cached.data_characteristics is None

    @pytest.mark.manages_collection_state
    def test_cache_and_retrieve_with_empty_regressor_list(
        self,
        db_session: Session,
        cleanup_model_selection,
    ) -> None:
        """[P1] cache_model_selection stores empty regressor_list correctly."""
        from raglite.external_data.storage import (
            cache_model_selection,
            get_cached_model_selection,
        )
        from raglite.forecasting.model_selection import ModelSelectionResult

        result = ModelSelectionResult(
            variable_name="test_empty_regressors",
            best_model="xgboost",
            best_mape=6.0,
            best_mase=0.9,
            best_with_regressors=False,
            best_regressor_set=[],  # Edge case: empty list
            candidate_results={},
            data_characteristics=None,
            cv_folds=5,
            runtime_seconds=30.0,
        )

        cache_model_selection(result)

        cached = get_cached_model_selection("test_empty_regressors")
        assert cached is not None
        assert cached.regressor_list == []

    @pytest.mark.manages_collection_state
    def test_cache_and_retrieve_with_large_candidate_results(
        self,
        db_session: Session,
        cleanup_model_selection,
    ) -> None:
        """[P2] cache_model_selection handles large candidate_results JSON."""
        from raglite.external_data.storage import (
            cache_model_selection,
            get_cached_model_selection,
        )
        from raglite.forecasting.model_selection import ModelSelectionResult

        # Simulate large candidate_results (50+ entries)
        large_results = {
            f"model_{i}_regressors_{i % 2}": {"mape": 5.0 + i * 0.1, "mase": 0.8 + i * 0.01}
            for i in range(50)
        }

        result = ModelSelectionResult(
            variable_name="test_large_results",
            best_model="prophet",
            best_mape=5.0,
            best_mase=0.8,
            best_with_regressors=True,
            best_regressor_set=["reg1", "reg2"],
            candidate_results=large_results,
            data_characteristics=None,
            cv_folds=5,
            runtime_seconds=30.0,
        )

        cache_model_selection(result)

        cached = get_cached_model_selection("test_large_results")
        assert cached is not None
        assert len(cached.candidate_results) == 50

    @pytest.mark.manages_collection_state
    def test_cache_and_retrieve_with_very_long_regressor_list(
        self,
        db_session: Session,
        cleanup_model_selection,
    ) -> None:
        """[P2] cache_model_selection handles very long regressor list."""
        from raglite.external_data.storage import (
            cache_model_selection,
            get_cached_model_selection,
        )
        from raglite.forecasting.model_selection import ModelSelectionResult

        # Edge case: 20+ regressors
        long_regressors = [f"regressor_{i}" for i in range(20)]

        result = ModelSelectionResult(
            variable_name="test_long_regressors",
            best_model="prophet",
            best_mape=5.0,
            best_mase=0.8,
            best_with_regressors=True,
            best_regressor_set=long_regressors,
            candidate_results={},
            data_characteristics=None,
            cv_folds=5,
            runtime_seconds=30.0,
        )

        cache_model_selection(result)

        cached = get_cached_model_selection("test_long_regressors")
        assert cached is not None
        assert len(cached.regressor_list) == 20

    @pytest.mark.manages_collection_state
    def test_cache_and_retrieve_with_unicode_variable_name(
        self,
        db_session: Session,
        cleanup_model_selection,
    ) -> None:
        """[P2] cache_model_selection handles Unicode variable names."""
        from raglite.external_data.storage import (
            cache_model_selection,
            get_cached_model_selection,
        )
        from raglite.forecasting.model_selection import ModelSelectionResult

        unicode_name = "变量名称"  # Chinese characters

        result = ModelSelectionResult(
            variable_name=unicode_name,
            best_model="prophet",
            best_mape=5.0,
            best_mase=0.8,
            best_with_regressors=False,
            best_regressor_set=[],
            candidate_results={},
            data_characteristics=None,
            cv_folds=5,
            runtime_seconds=30.0,
        )

        cache_model_selection(result)

        cached = get_cached_model_selection(unicode_name)
        assert cached is not None
        assert cached.variable_name == unicode_name

    @pytest.mark.manages_collection_state
    def test_cache_and_retrieve_with_special_chars_variable_name(
        self,
        db_session: Session,
        cleanup_model_selection,
    ) -> None:
        """[P2] cache_model_selection handles special characters in variable name."""
        from raglite.external_data.storage import (
            cache_model_selection,
            get_cached_model_selection,
        )
        from raglite.forecasting.model_selection import ModelSelectionResult

        special_name = "var_name-with.special@chars#123"

        result = ModelSelectionResult(
            variable_name=special_name,
            best_model="prophet",
            best_mape=5.0,
            best_mase=0.8,
            best_with_regressors=False,
            best_regressor_set=[],
            candidate_results={},
            data_characteristics=None,
            cv_folds=5,
            runtime_seconds=30.0,
        )

        cache_model_selection(result)

        cached = get_cached_model_selection(special_name)
        assert cached is not None
        assert cached.variable_name == special_name

    @pytest.mark.manages_collection_state
    def test_cache_and_retrieve_with_none_best_mase(
        self,
        db_session: Session,
        cleanup_model_selection,
    ) -> None:
        """[P1] M3: CachedModelSelection preserves None for best_mase."""
        from raglite.external_data.orm_models import ModelSelectionORM
        from raglite.external_data.storage import get_cached_model_selection

        now = datetime.utcnow()

        # Insert directly with None best_mase
        entry = ModelSelectionORM(
            variable_name="test_none_mase",
            best_model="prophet",
            best_mape=5.0,
            best_mase=None,  # M3: Can be None
            use_regressors=False,
            regressor_list=[],
            candidate_results={},
            data_characteristics=None,
            selected_at=now,
            expires_at=now + timedelta(days=7),
        )
        db_session.add(entry)
        db_session.commit()

        cached = get_cached_model_selection("test_none_mase")
        assert cached is not None
        assert cached.best_mase is None

    @pytest.mark.manages_collection_state
    def test_variable_name_exactly_100_chars(
        self,
        db_session: Session,
        cleanup_model_selection,
    ) -> None:
        """[P1] M4: Cache and retrieve variable_name at 100 char boundary."""
        from raglite.external_data.storage import (
            cache_model_selection,
            get_cached_model_selection,
        )
        from raglite.forecasting.model_selection import ModelSelectionResult

        exactly_100 = "a" * 100

        result = ModelSelectionResult(
            variable_name=exactly_100,
            best_model="prophet",
            best_mape=5.0,
            best_mase=0.8,
            best_with_regressors=False,
            best_regressor_set=[],
            candidate_results={},
            data_characteristics=None,
            cv_folds=5,
            runtime_seconds=30.0,
        )

        cache_model_selection(result)

        cached = get_cached_model_selection(exactly_100)
        assert cached is not None
        assert cached.variable_name == exactly_100
        assert len(cached.variable_name) == 100
