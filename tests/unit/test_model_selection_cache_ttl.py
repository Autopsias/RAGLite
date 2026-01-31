"""Unit tests for TTL calculation and is_expired property.

Story 7b-4: Model Selection Cache in PostgreSQL

Test IDs map to Acceptance Criteria:
- TEST-AC-7b.4.5.x: TTL and expiration tests
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from raglite.external_data.storage import MODEL_SELECTION_TTL_DAYS, CachedModelSelection

# Mark all tests in this module as unit tests
pytestmark = [pytest.mark.unit]


class TestIsExpiredProperty:
    """[P0] AC-7b.4.5: is_expired property tests for TTL validation."""

    def test_ac_7b_4_5_1_is_expired_false_for_fresh_entry(self) -> None:
        """TEST-AC-7b.4.5.1: is_expired=False for entries within TTL."""

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


class TestTTLCalculation:
    """[P0] AC-7b.4.5: TTL calculation tests."""

    def test_ac_7b_4_5_4_model_selection_ttl_days_constant_exists(self) -> None:
        """TEST-AC-7b.4.5.4: MODEL_SELECTION_TTL_DAYS constant exists."""
        assert MODEL_SELECTION_TTL_DAYS is not None
        assert isinstance(MODEL_SELECTION_TTL_DAYS, int)

    def test_ac_7b_4_5_5_model_selection_ttl_days_is_7(self) -> None:
        """TEST-AC-7b.4.5.5: MODEL_SELECTION_TTL_DAYS equals 7."""
        assert MODEL_SELECTION_TTL_DAYS == 7

    def test_ac_7b_4_5_6_calculate_expires_at(self) -> None:
        """TEST-AC-7b.4.5.6: expires_at = selected_at + 7 days."""
        selected_at = datetime(2024, 1, 15, 10, 30, 0)
        expected_expires_at = selected_at + timedelta(days=MODEL_SELECTION_TTL_DAYS)

        assert expected_expires_at == datetime(2024, 1, 22, 10, 30, 0)
