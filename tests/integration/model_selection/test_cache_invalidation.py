"""Cache invalidation tests for model selection.

Story 7b-4: Model Selection Cache in PostgreSQL
TEST-AC-7b.4.4.x: invalidate_model_selection tests
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from raglite.external_data.storage import (
    cache_model_selection,
    get_cached_model_selection,
    invalidate_model_selection,
)
from raglite.forecasting.model_selection import ModelSelectionResult

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

# Mark all tests as integration and PostgreSQL-only
pytestmark = [
    pytest.mark.integration,
    pytest.mark.postgresql_only,
    pytest.mark.slow,
    pytest.mark.xdist_group(
        name="model_selection_cache"
    ),  # Prevent race conditions with test_cache_operations.py
]


class TestInvalidateModelSelectionIntegration:
    """[P0] AC-7b.4.4: Integration tests for invalidate_model_selection."""

    @pytest.mark.manages_collection_state
    def test_ac_7b_4_4_5_invalidate_deletes_single_variable(
        self,
        db_session: Session,
        sample_model_selection_result,
        cleanup_model_selection,
    ) -> None:
        """TEST-AC-7b.4.4.5: invalidate_model_selection deletes single variable."""
        # Cache the result
        cache_model_selection(sample_model_selection_result)

        # Verify it exists
        result = get_cached_model_selection("ebitda")
        assert result is not None

        # Invalidate
        count = invalidate_model_selection("ebitda")
        assert count == 1

        # Verify it's gone
        result = get_cached_model_selection("ebitda")
        assert result is None

    @pytest.mark.manages_collection_state
    def test_ac_7b_4_4_6_invalidate_all_deletes_all_entries(
        self,
        db_session: Session,
        cleanup_model_selection,
    ) -> None:
        """TEST-AC-7b.4.4.6: invalidate_model_selection(None) deletes all entries."""
        # Cache multiple results
        for i, var in enumerate(["var1", "var2", "var3"]):
            result = ModelSelectionResult(
                variable_name=var,
                best_model="prophet",
                best_mape=5.0 + i,
                best_mase=0.8,
                best_with_regressors=False,
                best_regressor_set=[],
                candidate_results={},
                data_characteristics=None,
                cv_folds=5,
                runtime_seconds=30.0,
            )
            cache_model_selection(result)

        # Invalidate all
        count = invalidate_model_selection(None)
        assert count == 3

        # Verify all are gone
        for var in ["var1", "var2", "var3"]:
            result = get_cached_model_selection(var)
            assert result is None

    @pytest.mark.preserve_collection
    def test_ac_7b_4_4_7_invalidate_returns_zero_for_nonexistent(
        self,
        cleanup_model_selection,
    ) -> None:
        """TEST-AC-7b.4.4.7: invalidate_model_selection returns 0 for nonexistent variable."""
        count = invalidate_model_selection("nonexistent")
        assert count == 0


class TestErrorHandlingIntegration:
    """[P1] Error handling integration tests with real database."""

    @pytest.mark.manages_collection_state
    def test_get_cached_returns_none_after_invalidation(
        self,
        db_session: Session,
        sample_model_selection_result,
        cleanup_model_selection,
    ) -> None:
        """[P1] get_cached_model_selection returns None after invalidation."""
        cache_model_selection(sample_model_selection_result)

        # Verify it exists
        cached = get_cached_model_selection("ebitda")
        assert cached is not None

        # Invalidate
        invalidate_model_selection("ebitda")

        # Verify it's gone
        cached_after = get_cached_model_selection("ebitda")
        assert cached_after is None

    @pytest.mark.preserve_collection
    def test_invalidate_nonexistent_variable_returns_zero(
        self,
        cleanup_model_selection,
    ) -> None:
        """[P1] invalidate_model_selection returns 0 for nonexistent variable."""
        count = invalidate_model_selection("nonexistent_variable_xyz")
        assert count == 0
