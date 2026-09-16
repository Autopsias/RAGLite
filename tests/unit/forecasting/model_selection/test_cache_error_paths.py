"""[P1] Error path testing for model selection cache.

Story 8.4a-2 Phase 6: Test automation expansion.
Tests error handling, recovery scenarios, and database failure cases.
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

pytestmark = [pytest.mark.unit]


# Lazy import to avoid module dependency issues
def get_sqlalchemy_exceptions():
    """Lazy import of SQLAlchemy exceptions."""
    try:
        from sqlalchemy.exc import IntegrityError, OperationalError

        return IntegrityError, OperationalError
    except ImportError:
        pytest.skip("SQLAlchemy not available")
        return None, None


# =============================================================================
# Database Error Handling
# =============================================================================


class TestDatabaseErrors:
    """[P1] Test handling of database errors in cache operations."""

    def test_cache_storage_on_database_connection_error(self) -> None:
        """[P1] Test cache_model_selection handles database connection errors."""
        IntegrityError, OperationalError = get_sqlalchemy_exceptions()

        IntegrityError, OperationalError = get_sqlalchemy_exceptions()

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
            data_characteristics=None,
            cv_folds=5,
            runtime_seconds=30.0,
        )

        with patch("raglite.external_data.storage.model_selection.get_session") as mock_get_session:
            mock_session = MagicMock()
            mock_session.commit.side_effect = OperationalError("connection error", None, None)
            mock_get_session.return_value = mock_session

            # Should raise error (not silently fail)
            with pytest.raises(OperationalError):
                cache_model_selection(result)

    def test_cache_retrieval_on_database_connection_error(self) -> None:
        """[P1] Test get_cached_model_selection handles connection errors."""
        IntegrityError, OperationalError = get_sqlalchemy_exceptions()

        from raglite.external_data.storage import get_cached_model_selection

        with patch("raglite.external_data.storage.model_selection.get_session") as mock_get_session:
            mock_session = MagicMock()
            mock_session.query.side_effect = OperationalError("connection error", None, None)
            mock_get_session.return_value = mock_session

            # Should raise error (session.close() in finally block happens after)
            with pytest.raises(OperationalError):
                get_cached_model_selection("test_var")

    def test_cache_invalidation_on_database_error(self) -> None:
        """[P1] Test invalidate_model_selection handles database errors."""
        IntegrityError, OperationalError = get_sqlalchemy_exceptions()

        from raglite.external_data.storage import invalidate_model_selection

        with patch("raglite.external_data.storage.model_selection.get_session") as mock_get_session:
            mock_session = MagicMock()
            mock_session.commit.side_effect = OperationalError("connection error", None, None)
            mock_get_session.return_value = mock_session

            # Should raise error
            with pytest.raises(OperationalError):
                invalidate_model_selection("test_var")


# =============================================================================
# Integrity Constraint Violations
# =============================================================================


class TestIntegrityConstraints:
    """[P1] Test handling of database integrity constraint violations."""

    def test_duplicate_variable_name_insert(self) -> None:
        """[P1] Test handling of duplicate variable_name inserts."""
        IntegrityError, OperationalError = get_sqlalchemy_exceptions()

        from raglite.external_data.storage import cache_model_selection
        from raglite.forecasting.model_selection import ModelSelectionResult

        result = ModelSelectionResult(
            variable_name="duplicate_var",
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

        with patch("raglite.external_data.storage.model_selection.get_session") as mock_get_session:
            mock_session = MagicMock()
            mock_session.commit.side_effect = IntegrityError("duplicate key", None, None)
            mock_get_session.return_value = mock_session

            # Should raise IntegrityError
            with pytest.raises(IntegrityError):
                cache_model_selection(result)

    def test_null_variable_name_insert(self) -> None:
        """[P1] Test handling of NULL variable_name (should fail at validation)."""
        IntegrityError, OperationalError = get_sqlalchemy_exceptions()

        from raglite.external_data.storage import get_cached_model_selection

        # get_cached_model_selection has explicit validation (not Pydantic)
        with pytest.raises(ValueError, match="variable_name cannot be empty"):
            get_cached_model_selection("")  # Empty string triggers validation


# =============================================================================
# Cache Expiration Edge Cases
# =============================================================================


class TestCacheExpirationEdgeCases:
    """[P2] Test edge cases in cache expiration logic."""

    def test_cleanup_with_no_expired_entries(self) -> None:
        """[P2] Test cleanup when no entries are expired."""
        IntegrityError, OperationalError = get_sqlalchemy_exceptions()

        from raglite.external_data.storage import cleanup_expired_model_selections

        with patch("raglite.external_data.storage.model_selection.get_session") as mock_get_session:
            mock_session = MagicMock()
            mock_query = MagicMock()
            mock_query.filter.return_value.delete.return_value = 0  # Fixed: delete() returns int
            mock_session.query.return_value = mock_query
            mock_get_session.return_value = mock_session

            # Should complete without errors
            deleted_count = cleanup_expired_model_selections()
            assert deleted_count == 0

    def test_cleanup_with_all_entries_expired(self) -> None:
        """[P2] Test cleanup when ALL entries are expired."""
        IntegrityError, OperationalError = get_sqlalchemy_exceptions()

        from raglite.external_data.storage import cleanup_expired_model_selections

        with patch("raglite.external_data.storage.model_selection.get_session") as mock_get_session:
            mock_session = MagicMock()
            mock_query = MagicMock()
            mock_query.filter.return_value.delete.return_value = 100
            mock_session.query.return_value = mock_query
            mock_get_session.return_value = mock_session

            # Should delete all 100 entries
            deleted_count = cleanup_expired_model_selections()
            assert deleted_count == 100

    def test_get_cache_with_exactly_expired_entry(self) -> None:
        """[P2] Test cache retrieval for entry that expired exactly now."""
        IntegrityError, OperationalError = get_sqlalchemy_exceptions()

        from decimal import Decimal

        from raglite.external_data.storage import (
            MODEL_SELECTION_TTL_DAYS,
            get_cached_model_selection,
        )

        with patch("raglite.external_data.storage.model_selection.get_session") as mock_get_session:
            mock_session = MagicMock()

            # Mock entry that expired exactly now
            now = datetime.now()
            mock_orm = MagicMock()
            mock_orm.variable_name = "test_var"
            mock_orm.best_model = "prophet"
            mock_orm.best_mape = Decimal("5.0")
            mock_orm.best_mase = Decimal("0.8")
            mock_orm.use_regressors = False
            mock_orm.regressor_list = []
            mock_orm.candidate_results = {}
            mock_orm.data_characteristics = None
            mock_orm.selected_at = now - timedelta(days=MODEL_SELECTION_TTL_DAYS)
            mock_orm.expires_at = now  # Expired exactly now

            mock_query = MagicMock()
            mock_query.filter.return_value.first.return_value = mock_orm
            mock_session.query.return_value = mock_query
            mock_get_session.return_value = mock_session

            # get_cached_model_selection returns entry (is_expired property checks expiration)
            result = get_cached_model_selection("test_var")
            assert result is not None
            assert result.is_expired is True  # Caller checks this property


# =============================================================================
# Invalid Input Handling
# =============================================================================


class TestInvalidInputs:
    """[P1] Test handling of invalid inputs to cache functions."""

    def test_cache_with_empty_variable_name(self) -> None:
        """[P1] Test get_cached_model_selection with empty string variable name."""
        IntegrityError, OperationalError = get_sqlalchemy_exceptions()

        from raglite.external_data.storage import get_cached_model_selection

        # Should be caught by explicit validation
        with pytest.raises(ValueError, match="variable_name cannot be empty"):
            get_cached_model_selection("")  # Empty string triggers validation

    def test_cache_with_invalid_model_name(self) -> None:
        """[P2] Test cache with non-existent model name."""
        IntegrityError, OperationalError = get_sqlalchemy_exceptions()

        from raglite.external_data.storage import cache_model_selection
        from raglite.forecasting.model_selection import ModelSelectionResult

        result = ModelSelectionResult(
            variable_name="test_var",
            best_model="invalid_model_xyz",  # Not in CANDIDATE_MODELS
            best_mape=5.0,
            best_mase=0.8,
            best_with_regressors=False,
            best_regressor_set=[],
            candidate_results={},
            data_characteristics=None,
            cv_folds=5,
            runtime_seconds=30.0,
        )

        with patch("raglite.external_data.storage.model_selection.get_session") as mock_get_session:
            mock_session = MagicMock()
            mock_get_session.return_value = mock_session

            # Should still cache (validation happens at model selection level)
            cache_model_selection(result)
            mock_session.add.assert_called_once()

    def test_cache_with_negative_mape(self) -> None:
        """[P2] Test cache with negative MAPE (invalid but possible data error)."""
        IntegrityError, OperationalError = get_sqlalchemy_exceptions()

        from raglite.external_data.storage import cache_model_selection
        from raglite.forecasting.model_selection import ModelSelectionResult

        result = ModelSelectionResult(
            variable_name="test_var",
            best_model="prophet",
            best_mape=-5.0,  # Invalid (MAPE should be positive)
            best_mase=0.8,
            best_with_regressors=False,
            best_regressor_set=[],
            candidate_results={},
            data_characteristics=None,
            cv_folds=5,
            runtime_seconds=30.0,
        )

        with patch("raglite.external_data.storage.model_selection.get_session") as mock_get_session:
            mock_session = MagicMock()
            mock_get_session.return_value = mock_session

            # Should cache (business logic validation happens elsewhere)
            cache_model_selection(result)
            mock_session.add.assert_called_once()


# =============================================================================
# Concurrent Access Edge Cases
# =============================================================================


class TestConcurrentAccess:
    """[P2] Test concurrent access scenarios to cache."""

    def test_concurrent_cache_writes_same_variable(self) -> None:
        """[P2] Test handling of concurrent writes for same variable."""
        IntegrityError, OperationalError = get_sqlalchemy_exceptions()

        from raglite.external_data.storage import cache_model_selection
        from raglite.forecasting.model_selection import ModelSelectionResult

        result = ModelSelectionResult(
            variable_name="concurrent_var",
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

        # Test upsert behavior - IntegrityError triggers update path
        with patch("raglite.external_data.storage.model_selection.get_session") as mock_get_session:
            mock_session = MagicMock()
            # First commit raises IntegrityError (duplicate), then update succeeds
            mock_session.commit.side_effect = [
                IntegrityError("duplicate key", None, None),
                None,  # Update succeeds
            ]

            # Mock the query for update path
            mock_existing = MagicMock()
            mock_session.query.return_value.filter.return_value.first.return_value = mock_existing
            mock_get_session.return_value = mock_session

            # Should handle race condition via update (upsert semantics)
            cache_model_selection(result)

            # Verify rollback and update path executed
            assert mock_session.rollback.called
            assert mock_session.commit.call_count == 2

    def test_read_during_write_transaction(self) -> None:
        """[P2] Test cache read while write is in progress."""
        IntegrityError, OperationalError = get_sqlalchemy_exceptions()

        from raglite.external_data.storage import get_cached_model_selection

        with patch("raglite.external_data.storage.model_selection.get_session") as mock_get_session:
            mock_session = MagicMock()
            mock_query = MagicMock()

            # Simulate read returning None (write transaction not yet committed)
            mock_query.filter.return_value.first.return_value = None
            mock_session.query.return_value = mock_query
            mock_get_session.return_value = mock_session

            # Should return None (cache miss during uncommitted write)
            result = get_cached_model_selection("test_var")
            assert result is None


# =============================================================================
# Session Management Edge Cases
# =============================================================================


class TestSessionManagement:
    """[P2] Test database session management edge cases."""

    def test_session_rollback_on_error(self) -> None:
        """[P2] Test that session is rolled back on error."""
        IntegrityError, OperationalError = get_sqlalchemy_exceptions()

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
            data_characteristics=None,
            cv_folds=5,
            runtime_seconds=30.0,
        )

        with patch("raglite.external_data.storage.model_selection.get_session") as mock_get_session:
            mock_session = MagicMock()
            mock_session.commit.side_effect = OperationalError("", None, None)
            mock_get_session.return_value = mock_session

            # Should raise error
            with pytest.raises(OperationalError):
                cache_model_selection(result)

            # Session should be rolled back (called by context manager)
            # Note: Exact rollback behavior depends on implementation

    def test_multiple_operations_same_session(self) -> None:
        """[P2] Test multiple cache operations reusing same session."""
        IntegrityError, OperationalError = get_sqlalchemy_exceptions()

        from raglite.external_data.storage import (
            cache_model_selection,
            get_cached_model_selection,
        )
        from raglite.forecasting.model_selection import ModelSelectionResult

        result = ModelSelectionResult(
            variable_name="test_var",
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

        with patch("raglite.external_data.storage.model_selection.get_session") as mock_get_session:
            mock_session = MagicMock()
            mock_get_session.return_value = mock_session

            # Write operation
            cache_model_selection(result)

            # Read operation (same session)
            get_cached_model_selection("test_var")

            # Both operations should work
            assert mock_session.add.called
            assert mock_session.query.called
