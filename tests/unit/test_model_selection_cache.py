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


# -----------------------------------------------------------------------------
# TEST-AC-7b.4.3: CachedModelSelection Dataclass Tests
# -----------------------------------------------------------------------------


class TestCachedModelSelectionDataclass:
    """[P0] AC-7b.4.3: CachedModelSelection dataclass tests."""

    def test_ac_7b_4_3_1_cached_model_selection_exists(self) -> None:
        """TEST-AC-7b.4.3.1: CachedModelSelection dataclass exists."""
        from raglite.external_data.storage import CachedModelSelection

        assert CachedModelSelection is not None

    def test_ac_7b_4_3_2_cached_model_selection_has_required_fields(self) -> None:
        """TEST-AC-7b.4.3.2: CachedModelSelection has all required fields."""
        from dataclasses import fields

        from raglite.external_data.storage import CachedModelSelection

        field_names = {f.name for f in fields(CachedModelSelection)}
        required_fields = {
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
        }

        for field in required_fields:
            assert field in field_names, f"Missing required field: {field}"

    def test_ac_7b_4_3_3_cached_model_selection_instantiation(self) -> None:
        """TEST-AC-7b.4.3.3: CachedModelSelection can be instantiated."""
        from raglite.external_data.storage import CachedModelSelection

        now = datetime.utcnow()
        expires = now + timedelta(days=7)

        cached = CachedModelSelection(
            variable_name="ebitda",
            best_model="prophet",
            best_mape=5.5,
            best_mase=0.8,
            use_regressors=True,
            regressor_list=["gas_price", "euribor"],
            candidate_results={"prophet_True": {"mape": 5.5, "mase": 0.8}},
            data_characteristics={"trend": "linear", "seasonality": "yearly"},
            selected_at=now,
            expires_at=expires,
        )

        assert cached.variable_name == "ebitda"
        assert cached.best_model == "prophet"
        assert cached.best_mape == 5.5
        assert cached.best_mase == 0.8
        assert cached.use_regressors is True
        assert cached.regressor_list == ["gas_price", "euribor"]


# -----------------------------------------------------------------------------
# TEST-AC-7b.4.5: is_expired Property Tests
# -----------------------------------------------------------------------------


class TestIsExpiredProperty:
    """[P0] AC-7b.4.5: is_expired property tests for TTL validation."""

    def test_ac_7b_4_5_1_is_expired_false_for_fresh_entry(self) -> None:
        """TEST-AC-7b.4.5.1: is_expired=False for entries within TTL."""
        from raglite.external_data.storage import CachedModelSelection

        now = datetime.utcnow()
        expires = now + timedelta(days=7)

        cached = CachedModelSelection(
            variable_name="revenue",
            best_model="xgboost",
            best_mape=4.2,
            best_mase=0.7,
            use_regressors=False,
            regressor_list=[],
            candidate_results={},
            data_characteristics=None,
            selected_at=now,
            expires_at=expires,
        )

        assert cached.is_expired is False

    def test_ac_7b_4_5_2_is_expired_true_for_expired_entry(self) -> None:
        """TEST-AC-7b.4.5.2: is_expired=True for entries past TTL."""
        from raglite.external_data.storage import CachedModelSelection

        now = datetime.utcnow()
        past_expires = now - timedelta(hours=1)  # Expired 1 hour ago

        cached = CachedModelSelection(
            variable_name="revenue",
            best_model="xgboost",
            best_mape=4.2,
            best_mase=0.7,
            use_regressors=False,
            regressor_list=[],
            candidate_results={},
            data_characteristics=None,
            selected_at=now - timedelta(days=8),
            expires_at=past_expires,
        )

        assert cached.is_expired is True

    def test_ac_7b_4_5_3_is_expired_boundary_exactly_at_expiry(self) -> None:
        """TEST-AC-7b.4.5.3: is_expired boundary condition at exact expiry time."""
        from raglite.external_data.storage import CachedModelSelection

        now = datetime.utcnow()
        # Set expires_at to 1 second in the past to ensure it's expired
        past_expires = now - timedelta(seconds=1)

        cached = CachedModelSelection(
            variable_name="revenue",
            best_model="xgboost",
            best_mape=4.2,
            best_mase=0.7,
            use_regressors=False,
            regressor_list=[],
            candidate_results={},
            data_characteristics=None,
            selected_at=now - timedelta(days=7),
            expires_at=past_expires,
        )

        # At or past expiry time should be expired
        assert cached.is_expired is True


# -----------------------------------------------------------------------------
# TEST-AC-7b.4.5: TTL Calculation Tests
# -----------------------------------------------------------------------------


class TestTTLCalculation:
    """[P0] AC-7b.4.5: TTL calculation tests."""

    def test_ac_7b_4_5_4_model_selection_ttl_days_constant_exists(self) -> None:
        """TEST-AC-7b.4.5.4: MODEL_SELECTION_TTL_DAYS constant exists."""
        from raglite.external_data.storage import MODEL_SELECTION_TTL_DAYS

        assert MODEL_SELECTION_TTL_DAYS is not None
        assert isinstance(MODEL_SELECTION_TTL_DAYS, int)

    def test_ac_7b_4_5_5_model_selection_ttl_days_is_7(self) -> None:
        """TEST-AC-7b.4.5.5: MODEL_SELECTION_TTL_DAYS equals 7."""
        from raglite.external_data.storage import MODEL_SELECTION_TTL_DAYS

        assert MODEL_SELECTION_TTL_DAYS == 7

    def test_ac_7b_4_5_6_calculate_expires_at(self) -> None:
        """TEST-AC-7b.4.5.6: expires_at = selected_at + 7 days."""
        from raglite.external_data.storage import MODEL_SELECTION_TTL_DAYS

        selected_at = datetime(2024, 1, 15, 10, 30, 0)
        expected_expires_at = selected_at + timedelta(days=MODEL_SELECTION_TTL_DAYS)

        assert expected_expires_at == datetime(2024, 1, 22, 10, 30, 0)


# -----------------------------------------------------------------------------
# TEST-AC-7b.4.2: cache_model_selection Tests (Mocked)
# -----------------------------------------------------------------------------


class TestCacheModelSelectionMocked:
    """[P0] AC-7b.4.2: Mocked tests for cache_model_selection function."""

    def test_ac_7b_4_2_1_cache_model_selection_function_exists(self) -> None:
        """TEST-AC-7b.4.2.1: cache_model_selection function exists."""
        from raglite.external_data.storage import cache_model_selection

        assert callable(cache_model_selection)

    def test_ac_7b_4_2_2_cache_model_selection_accepts_model_selection_result(
        self,
    ) -> None:
        """TEST-AC-7b.4.2.2: cache_model_selection accepts ModelSelectionResult."""
        from raglite.external_data.storage import cache_model_selection
        from raglite.forecasting.model_selection import ModelSelectionResult

        # Create a mock result
        mock_result = ModelSelectionResult(
            variable_name="test_variable",
            best_model="prophet",
            best_mape=5.0,
            best_mase=0.9,
            best_with_regressors=True,
            best_regressor_set=["gas_price"],
            candidate_results={"prophet_True": {"mape": 5.0, "mase": 0.9}},
            data_characteristics=None,
            cv_folds=5,
            runtime_seconds=30.0,
        )

        # Mock the database session
        with patch("raglite.shared.database.get_session") as mock_get_session:
            mock_session = MagicMock()
            mock_get_session.return_value = mock_session

            # Function should not raise
            cache_model_selection(mock_result)

    def test_ac_7b_4_2_3_cache_model_selection_sets_expires_at(self) -> None:
        """TEST-AC-7b.4.2.3: cache_model_selection sets expires_at correctly."""
        from raglite.external_data.storage import (
            MODEL_SELECTION_TTL_DAYS,
            cache_model_selection,
        )
        from raglite.forecasting.model_selection import ModelSelectionResult

        mock_result = ModelSelectionResult(
            variable_name="test_variable",
            best_model="prophet",
            best_mape=5.0,
            best_mase=0.9,
            best_with_regressors=False,
            best_regressor_set=[],
            candidate_results={},
            data_characteristics=None,
            cv_folds=5,
            runtime_seconds=30.0,
        )

        with patch("raglite.shared.database.get_session") as mock_get_session:
            mock_session = MagicMock()
            mock_get_session.return_value = mock_session

            cache_model_selection(mock_result)

            # Verify session.add was called with correct expires_at
            call_args = mock_session.add.call_args
            assert call_args is not None
            orm_obj = call_args[0][0]

            # expires_at should be ~7 days from now
            now = datetime.utcnow()
            expected_min = now + timedelta(days=MODEL_SELECTION_TTL_DAYS - 1)
            expected_max = now + timedelta(days=MODEL_SELECTION_TTL_DAYS + 1)

            assert expected_min <= orm_obj.expires_at <= expected_max


# -----------------------------------------------------------------------------
# TEST-AC-7b.4.3: get_cached_model_selection Tests (Mocked)
# -----------------------------------------------------------------------------


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

        with patch("raglite.shared.database.get_session") as mock_get_session:
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

        with patch("raglite.shared.database.get_session") as mock_get_session:
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

        with patch("raglite.shared.database.get_session") as mock_get_session:
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

        with patch("raglite.shared.database.get_session") as mock_get_session:
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

        with patch("raglite.shared.database.get_session") as mock_get_session:
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

        with patch("raglite.shared.database.get_session") as mock_get_session:
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

        with patch("raglite.shared.database.get_session") as mock_get_session:
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

        with patch("raglite.shared.database.get_session") as mock_get_session:
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

        with patch("raglite.shared.database.get_session") as mock_get_session:
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

        with patch("raglite.shared.database.get_session") as mock_get_session:
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

        with patch("raglite.shared.database.get_session") as mock_get_session:
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

        with patch("raglite.shared.database.get_session") as mock_get_session:
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

        with patch("raglite.shared.database.get_session") as mock_get_session:
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

        with patch("raglite.shared.database.get_session") as mock_get_session:
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

        with patch("raglite.shared.database.get_session") as mock_get_session:
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

        with patch("raglite.shared.database.get_session") as mock_get_session:
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

        with patch("raglite.shared.database.get_session") as mock_get_session:
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
