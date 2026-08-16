"""Unit tests for model selection cache in PostgreSQL.

Story 7b-4: Model Selection Cache in PostgreSQL

TDD Phase: RED - These tests are expected to FAIL until implementation complete.

The following do NOT exist yet:
- CachedModelSelection dataclass in storage.py
- cache_model_selection() function in storage.py
- get_cached_model_selection() function in storage.py
- invalidate_model_selection() function in storage.py
- cleanup_expired_model_selections() function in storage.py
- ModelSelectionORM in orm_models.py
- MODEL_SELECTION_TTL_DAYS constant in storage.py

Test IDs map to Acceptance Criteria:
- TEST-AC-7b.4.1.x: Table/schema tests (covered in integration)
- TEST-AC-7b.4.2.x: cache_model_selection tests
- TEST-AC-7b.4.3.x: get_cached_model_selection tests
- TEST-AC-7b.4.4.x: invalidate_model_selection tests
- TEST-AC-7b.4.5.x: TTL/expiration tests
- TEST-AC-7b.4.6.x: Migration tests (covered in integration)
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.exc import IntegrityError

# Mark all tests in this module as unit tests
pytestmark = [pytest.mark.unit]

if TYPE_CHECKING:
    pass


class TestEdgeCases:
    """[P1] Edge case tests for model selection cache."""

    def test_cache_result_with_none_data_characteristics(self) -> None:
        """[P1] cache_model_selection handles None data_characteristics."""
        from raglite.external_data.storage import cache_model_selection
        from raglite.forecasting.model_selection import ModelSelectionResult

        result = ModelSelectionResult(
            variable_name="test_var",
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

        with patch("raglite.external_data.storage.model_selection.get_session") as mock_get_session:
            mock_session = MagicMock()
            mock_get_session.return_value = mock_session

            cache_model_selection(result)

            call_args = mock_session.add.call_args
            assert call_args is not None
            orm_obj = call_args[0][0]
            assert orm_obj.data_characteristics is None

    def test_cache_result_with_empty_regressor_list(self) -> None:
        """[P1] cache_model_selection handles empty regressor_list."""
        from raglite.external_data.storage import cache_model_selection
        from raglite.forecasting.model_selection import ModelSelectionResult

        result = ModelSelectionResult(
            variable_name="test_var",
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

        with patch("raglite.external_data.storage.model_selection.get_session") as mock_get_session:
            mock_session = MagicMock()
            mock_get_session.return_value = mock_session

            cache_model_selection(result)

            call_args = mock_session.add.call_args
            assert call_args is not None
            orm_obj = call_args[0][0]
            assert orm_obj.regressor_list == []

    def test_cache_result_with_large_candidate_results(self) -> None:
        """[P2] cache_model_selection handles large candidate_results JSON."""
        from raglite.external_data.storage import cache_model_selection
        from raglite.forecasting.model_selection import ModelSelectionResult

        # Simulate large candidate_results (100+ entries)
        large_results = {
            f"model_{i}_regressors_{i % 2}": {"mape": 5.0 + i * 0.1, "mase": 0.8 + i * 0.01}
            for i in range(100)
        }

        result = ModelSelectionResult(
            variable_name="test_var",
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

        with patch("raglite.external_data.storage.model_selection.get_session") as mock_get_session:
            mock_session = MagicMock()
            mock_get_session.return_value = mock_session

            cache_model_selection(result)

            call_args = mock_session.add.call_args
            assert call_args is not None
            orm_obj = call_args[0][0]
            assert len(orm_obj.candidate_results) == 100

    def test_cache_result_with_very_long_regressor_list(self) -> None:
        """[P2] cache_model_selection handles very long regressor list."""
        from raglite.external_data.storage import cache_model_selection
        from raglite.forecasting.model_selection import ModelSelectionResult

        # Edge case: 20+ regressors
        long_regressors = [f"regressor_{i}" for i in range(25)]

        result = ModelSelectionResult(
            variable_name="test_var",
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

        with patch("raglite.external_data.storage.model_selection.get_session") as mock_get_session:
            mock_session = MagicMock()
            mock_get_session.return_value = mock_session

            cache_model_selection(result)

            call_args = mock_session.add.call_args
            assert call_args is not None
            orm_obj = call_args[0][0]
            assert len(orm_obj.regressor_list) == 25

    def test_get_cached_with_unicode_variable_name(self) -> None:
        """[P2] get_cached_model_selection handles Unicode variable names."""
        from raglite.external_data.storage import get_cached_model_selection

        with patch("raglite.external_data.storage.model_selection.get_session") as mock_get_session:
            mock_session = MagicMock()
            mock_query = MagicMock()
            mock_query.filter.return_value.first.return_value = None
            mock_session.query.return_value = mock_query
            mock_get_session.return_value = mock_session

            unicode_name = "变量名称"  # Chinese characters
            result = get_cached_model_selection(unicode_name)

            assert result is None  # Should not raise

    def test_get_cached_with_special_chars_variable_name(self) -> None:
        """[P2] get_cached_model_selection handles special characters in variable name."""
        from raglite.external_data.storage import get_cached_model_selection

        with patch("raglite.external_data.storage.model_selection.get_session") as mock_get_session:
            mock_session = MagicMock()
            mock_query = MagicMock()
            mock_query.filter.return_value.first.return_value = None
            mock_session.query.return_value = mock_query
            mock_get_session.return_value = mock_session

            special_name = "var_name-with.special@chars#123"
            result = get_cached_model_selection(special_name)

            assert result is None  # Should not raise

    def test_cached_model_selection_with_none_best_mase(self) -> None:
        """[P1] M3: CachedModelSelection allows None for best_mase."""
        from raglite.external_data.storage import CachedModelSelection

        now = datetime.utcnow()

        cached = CachedModelSelection(
            variable_name="test_var",
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

        assert cached.best_mase is None
        assert cached.is_expired is False

    def test_is_expired_boundary_1_second_before_expiry(self) -> None:
        """[P2] is_expired boundary: 1 second before expiry returns False."""
        from raglite.external_data.storage import CachedModelSelection

        now = datetime.utcnow()
        future_expires = now + timedelta(seconds=1)  # Expires in 1 second

        cached = CachedModelSelection(
            variable_name="test_var",
            best_model="prophet",
            best_mape=5.0,
            best_mase=0.8,
            use_regressors=False,
            regressor_list=[],
            candidate_results={},
            data_characteristics=None,
            selected_at=now - timedelta(days=7),
            expires_at=future_expires,
        )

        # Should still be valid (not expired)
        assert cached.is_expired is False


# -----------------------------------------------------------------------------
# Concurrent Operations Tests (Integration-like but mocked)
# -----------------------------------------------------------------------------


class TestConcurrentScenarios:
    """[P2] Tests for concurrent cache operations (mocked)."""

    def test_concurrent_cache_same_variable(self) -> None:
        """[P2] cache_model_selection handles concurrent writes to same variable."""
        from raglite.external_data.storage import cache_model_selection
        from raglite.forecasting.model_selection import ModelSelectionResult

        result = ModelSelectionResult(
            variable_name="ebitda",
            best_model="prophet",
            best_mape=5.0,
            best_mase=0.8,
            best_with_regressors=True,
            best_regressor_set=["gas_price"],
            candidate_results={},
            data_characteristics=None,
            cv_folds=5,
            runtime_seconds=30.0,
        )

        with patch("raglite.external_data.storage.model_selection.get_session") as mock_get_session:
            mock_session = MagicMock()

            # Simulate IntegrityError on first commit (concurrent insert)
            mock_session.commit.side_effect = [
                IntegrityError("duplicate key", None, None),
                None,  # Second commit succeeds
            ]

            # Mock existing record for update path
            existing_record = MagicMock()
            existing_record.variable_name = "ebitda"
            mock_query = MagicMock()
            mock_query.filter.return_value.first.return_value = existing_record
            mock_session.query.return_value = mock_query

            mock_get_session.return_value = mock_session

            # Should handle IntegrityError and update existing record
            cache_model_selection(result)

            # Verify rollback was called after IntegrityError
            assert mock_session.rollback.called
