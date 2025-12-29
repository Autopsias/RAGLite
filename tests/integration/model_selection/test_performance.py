"""Performance tests for model selection cache operations.

Story 7b-4: Model Selection Cache in PostgreSQL
Performance benchmarks
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

# Mark all tests as integration and PostgreSQL-only
pytestmark = [
    pytest.mark.integration,
    pytest.mark.postgresql_only,
    pytest.mark.slow,
]


class TestPerformance:
    """[P0] Performance tests for cache operations."""

    @pytest.mark.manages_collection_state
    def test_cache_performance_under_500ms(
        self,
        sample_model_selection_result,
        cleanup_model_selection,
    ) -> None:
        """cache_model_selection completes in <500ms."""
        from raglite.external_data.storage import cache_model_selection

        start = time.time()
        cache_model_selection(sample_model_selection_result)
        elapsed_ms = (time.time() - start) * 1000

        assert elapsed_ms < 500, f"Cache took {elapsed_ms:.1f}ms, exceeds 500ms target"

    @pytest.mark.manages_collection_state
    def test_invalidate_performance_under_200ms(
        self,
        sample_model_selection_result,
        cleanup_model_selection,
    ) -> None:
        """invalidate_model_selection completes in <200ms."""
        from raglite.external_data.storage import (
            cache_model_selection,
            invalidate_model_selection,
        )

        cache_model_selection(sample_model_selection_result)

        start = time.time()
        invalidate_model_selection("ebitda")
        elapsed_ms = (time.time() - start) * 1000

        assert elapsed_ms < 200, f"Invalidate took {elapsed_ms:.1f}ms, exceeds 200ms target"

    @pytest.mark.manages_collection_state
    def test_cleanup_performance_under_1s(
        self,
        db_session: Session,
        cleanup_model_selection,
    ) -> None:
        """cleanup_expired_model_selections completes in <1s."""
        from raglite.external_data.orm_models import ModelSelectionORM
        from raglite.external_data.storage import cleanup_expired_model_selections

        now = datetime.utcnow()

        # Insert 50 expired entries
        for i in range(50):
            entry = ModelSelectionORM(
                variable_name=f"expired_var_{i}",
                best_model="prophet",
                best_mape=5.0,
                best_mase=0.8,
                use_regressors=False,
                regressor_list=[],
                candidate_results={},
                data_characteristics=None,
                selected_at=now - timedelta(days=10),
                expires_at=now - timedelta(days=3),
            )
            db_session.add(entry)
        db_session.commit()

        start = time.time()
        count = cleanup_expired_model_selections()
        elapsed_ms = (time.time() - start) * 1000

        assert count == 50
        assert elapsed_ms < 1000, f"Cleanup took {elapsed_ms:.1f}ms, exceeds 1s target"
