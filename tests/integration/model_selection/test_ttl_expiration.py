"""TTL and expiration tests for model selection cache.

Story 7b-4: Model Selection Cache in PostgreSQL
TEST-AC-7b.4.5.x: TTL/expiration tests
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

import pytest

from raglite.external_data.orm_models import ModelSelectionORM
from raglite.external_data.storage import (
    MODEL_SELECTION_TTL_DAYS,
    cache_model_selection,
    cleanup_expired_model_selections,
    get_cached_model_selection,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

# Mark all tests as integration and PostgreSQL-only
pytestmark = [
    pytest.mark.integration,
    pytest.mark.postgresql_only,
    pytest.mark.slow,
    pytest.mark.xdist_group(name="model_selection_cache"),  # Prevent race conditions
]


class TestTTLExpirationIntegration:
    """[P0] AC-7b.4.5: Integration tests for TTL and expiration."""

    @pytest.mark.manages_collection_state
    def test_ac_7b_4_5_10_expires_at_set_correctly(
        self,
        db_session: Session,
        sample_model_selection_result,
        cleanup_model_selection,
    ) -> None:
        """TEST-AC-7b.4.5.10: expires_at is set to selected_at + 7 days."""
        before = datetime.utcnow()
        cache_model_selection(sample_model_selection_result)
        after = datetime.utcnow()

        record = (
            db_session.query(ModelSelectionORM)
            .filter(ModelSelectionORM.variable_name == "ebitda")
            .first()
        )

        # selected_at should be between before and after
        assert before <= record.selected_at <= after

        # expires_at should be selected_at + 7 days
        expected_expires = record.selected_at + timedelta(days=MODEL_SELECTION_TTL_DAYS)
        assert record.expires_at == expected_expires

    @pytest.mark.manages_collection_state
    def test_ac_7b_4_5_11_cleanup_removes_expired_entries(
        self,
        db_session: Session,
        cleanup_model_selection,
    ) -> None:
        """TEST-AC-7b.4.5.11: cleanup_expired_model_selections removes expired entries."""
        now = datetime.utcnow()

        # Insert one fresh and one expired entry
        fresh_entry = ModelSelectionORM(
            variable_name="fresh_var",
            best_model="prophet",
            best_mape=5.0,
            best_mase=0.8,
            use_regressors=False,
            regressor_list=[],
            candidate_results={},
            data_characteristics=None,
            selected_at=now,
            expires_at=now + timedelta(days=7),
        )
        expired_entry = ModelSelectionORM(
            variable_name="expired_var",
            best_model="xgboost",
            best_mape=6.0,
            best_mase=0.9,
            use_regressors=False,
            regressor_list=[],
            candidate_results={},
            data_characteristics=None,
            selected_at=now - timedelta(days=8),
            expires_at=now - timedelta(days=1),
        )
        db_session.add(fresh_entry)
        db_session.add(expired_entry)
        db_session.commit()

        # Cleanup
        count = cleanup_expired_model_selections()
        assert count == 1

        # Verify fresh still exists
        fresh = get_cached_model_selection("fresh_var")
        assert fresh is not None

        # Verify expired is gone
        expired = get_cached_model_selection("expired_var")
        assert expired is None

    @pytest.mark.manages_collection_state
    def test_ac_7b_4_5_12_cleanup_returns_zero_when_none_expired(
        self,
        db_session: Session,
        sample_model_selection_result,
        cleanup_model_selection,
    ) -> None:
        """TEST-AC-7b.4.5.12: cleanup_expired_model_selections returns 0 when none expired."""
        # Cache fresh entry
        cache_model_selection(sample_model_selection_result)

        # Cleanup should find nothing
        count = cleanup_expired_model_selections()
        assert count == 0

    @pytest.mark.manages_collection_state
    def test_cleanup_with_mixed_fresh_and_expired(
        self,
        db_session: Session,
        cleanup_model_selection,
    ) -> None:
        """[P1] cleanup_expired_model_selections only removes expired entries."""
        now = datetime.utcnow()

        # Insert 3 fresh and 2 expired entries
        for i in range(5):
            if i < 3:
                # Fresh entries
                expires_at = now + timedelta(days=7)
            else:
                # Expired entries
                expires_at = now - timedelta(days=1)

            entry = ModelSelectionORM(
                variable_name=f"var_{i}",
                best_model="prophet",
                best_mape=5.0,
                best_mase=0.8,
                use_regressors=False,
                regressor_list=[],
                candidate_results={},
                data_characteristics=None,
                selected_at=now - timedelta(days=8 if i >= 3 else 0),
                expires_at=expires_at,
            )
            db_session.add(entry)
        db_session.commit()

        # Cleanup
        count = cleanup_expired_model_selections()
        assert count == 2

        # Verify fresh entries still exist
        for i in range(3):
            cached = get_cached_model_selection(f"var_{i}")
            assert cached is not None

        # Verify expired entries are gone
        for i in range(3, 5):
            cached = get_cached_model_selection(f"var_{i}")
            assert cached is None
