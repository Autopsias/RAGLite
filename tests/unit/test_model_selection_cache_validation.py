"""Unit tests for input validation (M4 requirements).

Story 7b-4: Model Selection Cache in PostgreSQL

Test IDs map to Acceptance Criteria:
- M4: Input validation tests for get_cached_model_selection and invalidate_model_selection
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

# Mark all tests in this module as unit tests
pytestmark = [pytest.mark.unit]


class TestInputValidation:
    """[P0] M4 input validation tests for get_cached_model_selection and invalidate_model_selection."""

    def test_m4_get_cached_empty_variable_name(self) -> None:
        """[P0] M4: get_cached_model_selection rejects empty variable_name."""
        from raglite.external_data.storage import get_cached_model_selection

        with pytest.raises(ValueError, match="variable_name cannot be empty"):
            get_cached_model_selection("")

    def test_m4_get_cached_whitespace_only_variable_name(self) -> None:
        """[P0] M4: get_cached_model_selection rejects whitespace-only variable_name."""
        from raglite.external_data.storage import get_cached_model_selection

        with pytest.raises(ValueError, match="variable_name cannot be empty"):
            get_cached_model_selection("   ")

    def test_m4_get_cached_exceeds_100_chars(self) -> None:
        """[P0] M4: get_cached_model_selection rejects variable_name exceeding 100 chars."""
        from raglite.external_data.storage import get_cached_model_selection

        long_name = "a" * 101
        with pytest.raises(ValueError, match="variable_name cannot exceed 100 characters"):
            get_cached_model_selection(long_name)

    def test_m4_get_cached_exactly_100_chars(self) -> None:
        """[P1] M4: get_cached_model_selection accepts variable_name at 100 char limit."""
        from raglite.external_data.storage import get_cached_model_selection

        with patch("raglite.external_data.storage.model_selection.get_session") as mock_get_session:
            mock_session = MagicMock()
            mock_query = MagicMock()
            mock_query.filter.return_value.first.return_value = None
            mock_session.query.return_value = mock_query
            mock_get_session.return_value = mock_session

            exactly_100 = "a" * 100
            result = get_cached_model_selection(exactly_100)

            assert result is None  # Should not raise

    def test_m4_invalidate_empty_variable_name(self) -> None:
        """[P0] M4: invalidate_model_selection rejects empty variable_name."""
        from raglite.external_data.storage import invalidate_model_selection

        with pytest.raises(ValueError, match="variable_name cannot be empty"):
            invalidate_model_selection("")

    def test_m4_invalidate_whitespace_only_variable_name(self) -> None:
        """[P0] M4: invalidate_model_selection rejects whitespace-only variable_name."""
        from raglite.external_data.storage import invalidate_model_selection

        with pytest.raises(ValueError, match="variable_name cannot be empty"):
            invalidate_model_selection("   ")

    def test_m4_invalidate_exceeds_100_chars(self) -> None:
        """[P0] M4: invalidate_model_selection rejects variable_name exceeding 100 chars."""
        from raglite.external_data.storage import invalidate_model_selection

        long_name = "a" * 101
        with pytest.raises(ValueError, match="variable_name cannot exceed 100 characters"):
            invalidate_model_selection(long_name)

    def test_m4_invalidate_exactly_100_chars(self) -> None:
        """[P1] M4: invalidate_model_selection accepts variable_name at 100 char limit."""
        from raglite.external_data.storage import invalidate_model_selection

        with patch("raglite.external_data.storage.model_selection.get_session") as mock_get_session:
            mock_session = MagicMock()
            mock_query = MagicMock()
            mock_query.filter.return_value.delete.return_value = 0
            mock_session.query.return_value = mock_query
            mock_get_session.return_value = mock_session

            exactly_100 = "a" * 100
            count = invalidate_model_selection(exactly_100)

            assert count == 0  # Should not raise

    def test_m4_invalidate_none_allows_all(self) -> None:
        """[P0] M4: invalidate_model_selection(None) allows invalidating all entries."""
        from raglite.external_data.storage import invalidate_model_selection

        with patch("raglite.external_data.storage.model_selection.get_session") as mock_get_session:
            mock_session = MagicMock()
            mock_query = MagicMock()
            mock_query.delete.return_value = 5
            mock_session.query.return_value = mock_query
            mock_get_session.return_value = mock_session

            count = invalidate_model_selection(None)

            assert count == 5  # Should not raise
