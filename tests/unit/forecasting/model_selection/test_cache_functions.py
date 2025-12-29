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

# Mark all tests in this module as unit tests
pytestmark = [pytest.mark.unit]

if TYPE_CHECKING:
    pass


class TestGetCachedModelSelectionMocked:
    """[P0] AC-7b.4.3: Mocked tests for get_cached_model_selection function."""

    def test_ac_7b_4_3_4_get_cached_model_selection_function_exists(self) -> None:
        """TEST-AC-7b.4.3.4: get_cached_model_selection function exists."""
        from raglite.external_data.storage import get_cached_model_selection

        assert callable(get_cached_model_selection)

    def test_ac_7b_4_3_5_get_cached_model_selection_returns_none_for_missing(
        self,
    ) -> None:
        """TEST-AC-7b.4.3.5: get_cached_model_selection returns None for missing variable."""
        from raglite.external_data.storage import get_cached_model_selection

        with patch("raglite.external_data.storage.model_selection.get_session") as mock_get_session:
            mock_session = MagicMock()
            mock_query = MagicMock()
            mock_query.filter.return_value.first.return_value = None
            mock_session.query.return_value = mock_query
            mock_get_session.return_value = mock_session

            result = get_cached_model_selection("nonexistent_variable")

            assert result is None

    def test_ac_7b_4_3_6_get_cached_model_selection_returns_cached_data(
        self,
    ) -> None:
        """TEST-AC-7b.4.3.6: get_cached_model_selection returns CachedModelSelection."""
        from raglite.external_data.storage import (
            CachedModelSelection,
            get_cached_model_selection,
        )

        # Create mock ORM object
        now = datetime.utcnow()
        mock_orm = MagicMock()
        mock_orm.variable_name = "ebitda"
        mock_orm.best_model = "prophet"
        mock_orm.best_mape = 5.5
        mock_orm.best_mase = 0.8
        mock_orm.use_regressors = True
        mock_orm.regressor_list = ["gas_price"]
        mock_orm.candidate_results = {}
        mock_orm.data_characteristics = {}
        mock_orm.selected_at = now
        mock_orm.expires_at = now + timedelta(days=7)

        with patch("raglite.external_data.storage.model_selection.get_session") as mock_get_session:
            mock_session = MagicMock()
            mock_query = MagicMock()
            mock_query.filter.return_value.first.return_value = mock_orm
            mock_session.query.return_value = mock_query
            mock_get_session.return_value = mock_session

            result = get_cached_model_selection("ebitda")

            assert result is not None
            assert isinstance(result, CachedModelSelection)
            assert result.variable_name == "ebitda"
            assert result.best_model == "prophet"


# -----------------------------------------------------------------------------
# TEST-AC-7b.4.4: invalidate_model_selection Tests (Mocked)
# -----------------------------------------------------------------------------


class TestInvalidateModelSelectionMocked:
    """[P0] AC-7b.4.4: Mocked tests for invalidate_model_selection function."""

    def test_ac_7b_4_4_1_invalidate_model_selection_function_exists(self) -> None:
        """TEST-AC-7b.4.4.1: invalidate_model_selection function exists."""
        from raglite.external_data.storage import invalidate_model_selection

        assert callable(invalidate_model_selection)

    def test_ac_7b_4_4_2_invalidate_single_variable(self) -> None:
        """TEST-AC-7b.4.4.2: invalidate_model_selection deletes single variable."""
        from raglite.external_data.storage import invalidate_model_selection

        with patch("raglite.external_data.storage.model_selection.get_session") as mock_get_session:
            mock_session = MagicMock()
            mock_query = MagicMock()
            mock_query.filter.return_value.delete.return_value = 1
            mock_session.query.return_value = mock_query
            mock_get_session.return_value = mock_session

            count = invalidate_model_selection("ebitda")

            assert count == 1
            mock_session.commit.assert_called_once()

    def test_ac_7b_4_4_3_invalidate_all_variables(self) -> None:
        """TEST-AC-7b.4.4.3: invalidate_model_selection(None) deletes all."""
        from raglite.external_data.storage import invalidate_model_selection

        with patch("raglite.external_data.storage.model_selection.get_session") as mock_get_session:
            mock_session = MagicMock()
            mock_query = MagicMock()
            mock_query.delete.return_value = 5
            mock_session.query.return_value = mock_query
            mock_get_session.return_value = mock_session

            count = invalidate_model_selection(None)

            assert count == 5
            mock_session.commit.assert_called_once()

    def test_ac_7b_4_4_4_invalidate_returns_zero_for_missing(self) -> None:
        """TEST-AC-7b.4.4.4: invalidate_model_selection returns 0 for missing variable."""
        from raglite.external_data.storage import invalidate_model_selection

        with patch("raglite.external_data.storage.model_selection.get_session") as mock_get_session:
            mock_session = MagicMock()
            mock_query = MagicMock()
            mock_query.filter.return_value.delete.return_value = 0
            mock_session.query.return_value = mock_query
            mock_get_session.return_value = mock_session

            count = invalidate_model_selection("nonexistent")

            assert count == 0


# -----------------------------------------------------------------------------
# TEST-AC-7b.4.5: cleanup_expired_model_selections Tests (Mocked)
# -----------------------------------------------------------------------------


class TestCleanupExpiredModelSelectionsMocked:
    """[P0] AC-7b.4.5: Mocked tests for cleanup_expired_model_selections function."""

    def test_ac_7b_4_5_7_cleanup_function_exists(self) -> None:
        """TEST-AC-7b.4.5.7: cleanup_expired_model_selections function exists."""
        from raglite.external_data.storage import cleanup_expired_model_selections

        assert callable(cleanup_expired_model_selections)

    def test_ac_7b_4_5_8_cleanup_deletes_expired_entries(self) -> None:
        """TEST-AC-7b.4.5.8: cleanup_expired_model_selections removes expired entries."""
        from raglite.external_data.storage import cleanup_expired_model_selections

        with patch("raglite.external_data.storage.model_selection.get_session") as mock_get_session:
            mock_session = MagicMock()
            mock_query = MagicMock()
            mock_query.filter.return_value.delete.return_value = 3
            mock_session.query.return_value = mock_query
            mock_get_session.return_value = mock_session

            count = cleanup_expired_model_selections()

            assert count == 3
            mock_session.commit.assert_called_once()

    def test_ac_7b_4_5_9_cleanup_returns_zero_when_none_expired(self) -> None:
        """TEST-AC-7b.4.5.9: cleanup_expired_model_selections returns 0 when none expired."""
        from raglite.external_data.storage import cleanup_expired_model_selections

        with patch("raglite.external_data.storage.model_selection.get_session") as mock_get_session:
            mock_session = MagicMock()
            mock_query = MagicMock()
            mock_query.filter.return_value.delete.return_value = 0
            mock_session.query.return_value = mock_query
            mock_get_session.return_value = mock_session

            count = cleanup_expired_model_selections()

            assert count == 0


# -----------------------------------------------------------------------------
# TEST-AC-7b.4.1: ModelSelectionORM Tests
# -----------------------------------------------------------------------------
