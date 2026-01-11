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
        with patch("raglite.external_data.storage.model_selection.get_session") as mock_get_session:
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

        with patch("raglite.external_data.storage.model_selection.get_session") as mock_get_session:
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
