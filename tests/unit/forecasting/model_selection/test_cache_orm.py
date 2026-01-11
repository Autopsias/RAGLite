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


class TestModelSelectionORM:
    """[P0] AC-7b.4.1: Tests for ModelSelectionORM model."""

    def test_ac_7b_4_1_1_model_selection_orm_exists(self) -> None:
        """TEST-AC-7b.4.1.1: ModelSelectionORM class exists."""
        from raglite.external_data.orm_models import ModelSelectionORM

        assert ModelSelectionORM is not None

    def test_ac_7b_4_1_2_model_selection_orm_has_table_name(self) -> None:
        """TEST-AC-7b.4.1.2: ModelSelectionORM has correct table name."""
        from raglite.external_data.orm_models import ModelSelectionORM

        assert ModelSelectionORM.__tablename__ == "model_selection"

    def test_ac_7b_4_1_3_model_selection_orm_has_required_columns(self) -> None:
        """TEST-AC-7b.4.1.3: ModelSelectionORM has all required columns."""
        from raglite.external_data.orm_models import ModelSelectionORM

        required_columns = [
            "id",
            "variable_name",
            "best_model",
            "best_mape",
            "best_mase",
            "use_regressors",
            "regressor_list",
            "candidate_results",
            "data_characteristics",
            "selected_at",
            "expires_at",
        ]

        mapper = ModelSelectionORM.__mapper__
        column_names = [c.key for c in mapper.columns]

        for col in required_columns:
            assert col in column_names, f"Missing required column: {col}"

    def test_ac_7b_4_1_4_variable_name_is_unique(self) -> None:
        """TEST-AC-7b.4.1.4: variable_name column is unique."""
        from raglite.external_data.orm_models import ModelSelectionORM

        mapper = ModelSelectionORM.__mapper__
        variable_name_col = mapper.columns["variable_name"]

        assert variable_name_col.unique is True

    def test_ac_7b_4_1_5_expires_at_is_not_nullable(self) -> None:
        """TEST-AC-7b.4.1.5: expires_at column is not nullable."""
        from raglite.external_data.orm_models import ModelSelectionORM

        mapper = ModelSelectionORM.__mapper__
        expires_at_col = mapper.columns["expires_at"]

        assert expires_at_col.nullable is False


# -----------------------------------------------------------------------------
# JSON Serialization Tests
# -----------------------------------------------------------------------------


class TestJSONSerialization:
    """[P1] Tests for JSON serialization of cache data."""

    def test_candidate_results_serialization(self) -> None:
        """Candidate results dict can be serialized to JSON."""
        import json

        from raglite.external_data.storage import CachedModelSelection

        now = datetime.utcnow()
        cached = CachedModelSelection(
            variable_name="test",
            best_model="prophet",
            best_mape=5.0,
            best_mase=0.8,
            use_regressors=False,
            regressor_list=[],
            candidate_results={
                "prophet_False": {"mape": 5.0, "mase": 0.8},
                "xgboost_False": {"mape": 6.0, "mase": 0.9},
            },
            data_characteristics={"trend": "linear"},
            selected_at=now,
            expires_at=now + timedelta(days=7),
        )

        # Should not raise
        json_str = json.dumps(cached.candidate_results)
        assert isinstance(json_str, str)

    def test_data_characteristics_serialization(self) -> None:
        """Data characteristics dict can be serialized to JSON."""
        import json

        from raglite.external_data.storage import CachedModelSelection

        now = datetime.utcnow()
        cached = CachedModelSelection(
            variable_name="test",
            best_model="prophet",
            best_mape=5.0,
            best_mase=0.8,
            use_regressors=False,
            regressor_list=[],
            candidate_results={},
            data_characteristics={
                "trend": "linear",
                "seasonality_type": "yearly",
                "volatility_level": "medium",
                "sample_size": 48,
            },
            selected_at=now,
            expires_at=now + timedelta(days=7),
        )

        # Should not raise
        json_str = json.dumps(cached.data_characteristics)
        assert isinstance(json_str, str)

    def test_regressor_list_serialization(self) -> None:
        """Regressor list can be serialized to JSON."""
        import json

        from raglite.external_data.storage import CachedModelSelection

        now = datetime.utcnow()
        cached = CachedModelSelection(
            variable_name="test",
            best_model="prophet",
            best_mape=5.0,
            best_mase=0.8,
            use_regressors=True,
            regressor_list=["gas_price", "euribor", "electricity_price"],
            candidate_results={},
            data_characteristics=None,
            selected_at=now,
            expires_at=now + timedelta(days=7),
        )

        # Should not raise
        json_str = json.dumps(cached.regressor_list)
        assert isinstance(json_str, str)
        assert "gas_price" in json_str


# -----------------------------------------------------------------------------
# M4 Input Validation Tests (Code Review Fix)
# -----------------------------------------------------------------------------


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


# -----------------------------------------------------------------------------
# Edge Case Tests (Additional Coverage)
# -----------------------------------------------------------------------------
