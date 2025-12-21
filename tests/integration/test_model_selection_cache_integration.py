"""Integration tests for model selection cache in PostgreSQL.

Story 7b-4: Model Selection Cache in PostgreSQL

TDD Phase: RED - These tests are expected to FAIL until implementation complete.

The following do NOT exist yet:
- CachedModelSelection dataclass in storage.py
- cache_model_selection() function in storage.py
- get_cached_model_selection() function in storage.py
- invalidate_model_selection() function in storage.py
- cleanup_expired_model_selections() function in storage.py
- ModelSelectionORM in orm_models.py
- Migration 006_add_model_selection.sql

Test IDs map to Acceptance Criteria:
- TEST-AC-7b.4.1.x: Table/schema tests
- TEST-AC-7b.4.2.x: cache_model_selection tests
- TEST-AC-7b.4.3.x: get_cached_model_selection tests (incl. <100ms performance)
- TEST-AC-7b.4.4.x: invalidate_model_selection tests
- TEST-AC-7b.4.5.x: TTL/expiration tests
- TEST-AC-7b.4.6.x: Migration tests

Integration tests use PostgreSQL on test port 5433.
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

import pytest

# Mark all tests in this module as integration tests (PostgreSQL only, no Qdrant needed)
pytestmark = [
    pytest.mark.integration,
    pytest.mark.postgresql_only,  # Skip Qdrant fixtures - this module only uses PostgreSQL
]

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


# -----------------------------------------------------------------------------
# Test Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
def db_session():
    """Provide a database session for tests.

    Uses test database (port 5433) per conftest.py configuration.
    """
    from raglite.shared.database import get_session

    session = get_session()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def sample_model_selection_result():
    """Create a sample ModelSelectionResult for testing."""
    from raglite.forecasting.model_selection import ModelSelectionResult

    return ModelSelectionResult(
        variable_name="ebitda",
        best_model="prophet",
        best_mape=5.5,
        best_mase=0.8,
        best_with_regressors=True,
        best_regressor_set=["gas_price", "euribor"],
        candidate_results={
            "prophet_True": {"mape": 5.5, "mase": 0.8},
            "prophet_False": {"mape": 6.2, "mase": 0.9},
            "xgboost_True": {"mape": 5.8, "mase": 0.85},
            "xgboost_False": {"mape": 6.5, "mase": 0.95},
        },
        data_characteristics=None,
        cv_folds=5,
        runtime_seconds=45.0,
    )


@pytest.fixture
def cleanup_model_selection(db_session: Session):
    """Clean up model_selection table after tests."""
    yield
    # Cleanup after test
    try:
        from raglite.external_data.orm_models import ModelSelectionORM

        db_session.query(ModelSelectionORM).delete()
        db_session.commit()
    except Exception:
        db_session.rollback()


# -----------------------------------------------------------------------------
# TEST-AC-7b.4.6: Migration Script Tests
# -----------------------------------------------------------------------------


class TestMigrationScript:
    """[P0] AC-7b.4.6: Migration script tests."""

    def test_ac_7b_4_6_1_model_selection_table_exists(self, db_session: Session) -> None:
        """TEST-AC-7b.4.6.1: model_selection table exists after migration."""
        from sqlalchemy import inspect

        inspector = inspect(db_session.bind)
        tables = inspector.get_table_names()

        assert "model_selection" in tables, (
            "model_selection table not found. "
            "Run: docker exec raglite-postgresql-test psql -U raglite_ci -d raglite_ci "
            "-f migrations/006_add_model_selection.sql"
        )

    def test_ac_7b_4_6_2_table_has_correct_columns(self, db_session: Session) -> None:
        """TEST-AC-7b.4.6.2: model_selection table has correct columns."""
        from sqlalchemy import inspect

        inspector = inspect(db_session.bind)
        columns = {c["name"] for c in inspector.get_columns("model_selection")}

        required_columns = {
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
        }

        for col in required_columns:
            assert col in columns, f"Missing column: {col}"

    def test_ac_7b_4_6_3_variable_name_index_exists(self, db_session: Session) -> None:
        """TEST-AC-7b.4.6.3: variable_name index exists.

        Note: SQLAlchemy auto-generates index name as ix_model_selection_variable_name
        when using index=True on the column definition.
        """
        from sqlalchemy import inspect

        inspector = inspect(db_session.bind)
        indexes = inspector.get_indexes("model_selection")
        index_names = {idx["name"] for idx in indexes}

        # SQLAlchemy names the index ix_<table>_<column> when using index=True
        assert "ix_model_selection_variable_name" in index_names

    def test_ac_7b_4_6_4_expires_at_index_exists(self, db_session: Session) -> None:
        """TEST-AC-7b.4.6.4: idx_model_selection_expires index exists."""
        from sqlalchemy import inspect

        inspector = inspect(db_session.bind)
        indexes = inspector.get_indexes("model_selection")
        index_names = {idx["name"] for idx in indexes}

        assert "idx_model_selection_expires" in index_names

    def test_ac_7b_4_6_5_migration_is_idempotent(self, db_session: Session) -> None:
        """TEST-AC-7b.4.6.5: Migration can run multiple times without error."""
        import subprocess

        # Run migration again - should not fail
        result = subprocess.run(
            [
                "docker",
                "exec",
                "raglite-postgresql-test",
                "psql",
                "-U",
                "raglite_ci",
                "-d",
                "raglite_ci",
                "-f",
                "/migrations/006_add_model_selection.sql",
            ],
            capture_output=True,
            text=True,
        )

        # Should succeed (return code 0) or at least not fail catastrophically
        # Note: This test assumes migration file is mounted in container
        # If not mounted, test should be skipped
        if "No such file or directory" in result.stderr:
            pytest.skip("Migration file not mounted in test container")

        assert result.returncode == 0, f"Migration failed: {result.stderr}"


# -----------------------------------------------------------------------------
# TEST-AC-7b.4.2: cache_model_selection Integration Tests
# -----------------------------------------------------------------------------


class TestCacheModelSelectionIntegration:
    """[P0] AC-7b.4.2: Integration tests for cache_model_selection."""

    @pytest.mark.asyncio
    @pytest.mark.manages_collection_state
    async def test_ac_7b_4_2_4_cache_stores_result_in_database(
        self,
        db_session: Session,
        sample_model_selection_result,
        cleanup_model_selection,
    ) -> None:
        """TEST-AC-7b.4.2.4: cache_model_selection stores result in database."""
        from raglite.external_data.orm_models import ModelSelectionORM
        from raglite.external_data.storage import cache_model_selection

        await cache_model_selection(sample_model_selection_result)

        # Verify record exists
        record = (
            db_session.query(ModelSelectionORM)
            .filter(ModelSelectionORM.variable_name == "ebitda")
            .first()
        )

        assert record is not None
        assert record.variable_name == "ebitda"
        assert record.best_model == "prophet"
        assert float(record.best_mape) == pytest.approx(5.5, rel=0.01)
        assert float(record.best_mase) == pytest.approx(0.8, rel=0.01)
        assert record.use_regressors is True

    @pytest.mark.asyncio
    @pytest.mark.manages_collection_state
    async def test_ac_7b_4_2_5_cache_upsert_updates_existing(
        self,
        db_session: Session,
        sample_model_selection_result,
        cleanup_model_selection,
    ) -> None:
        """TEST-AC-7b.4.2.5: cache_model_selection upserts (updates existing)."""
        from raglite.external_data.orm_models import ModelSelectionORM
        from raglite.external_data.storage import cache_model_selection
        from raglite.forecasting.model_selection import ModelSelectionResult

        # First cache
        await cache_model_selection(sample_model_selection_result)

        # Modify and cache again
        updated_result = ModelSelectionResult(
            variable_name="ebitda",  # Same variable
            best_model="xgboost",  # Different model
            best_mape=4.5,  # Better MAPE
            best_mase=0.7,
            best_with_regressors=False,
            best_regressor_set=[],
            candidate_results={},
            data_characteristics=None,
            cv_folds=5,
            runtime_seconds=30.0,
        )
        await cache_model_selection(updated_result)

        # Verify only one record exists
        count = (
            db_session.query(ModelSelectionORM)
            .filter(ModelSelectionORM.variable_name == "ebitda")
            .count()
        )
        assert count == 1

        # Verify it's the updated one
        record = (
            db_session.query(ModelSelectionORM)
            .filter(ModelSelectionORM.variable_name == "ebitda")
            .first()
        )
        assert record.best_model == "xgboost"
        assert float(record.best_mape) == pytest.approx(4.5, rel=0.01)

    @pytest.mark.asyncio
    @pytest.mark.manages_collection_state
    async def test_ac_7b_4_2_6_cache_stores_regressor_list_as_json(
        self,
        db_session: Session,
        sample_model_selection_result,
        cleanup_model_selection,
    ) -> None:
        """TEST-AC-7b.4.2.6: regressor_list is stored as JSONB array."""
        from raglite.external_data.orm_models import ModelSelectionORM
        from raglite.external_data.storage import cache_model_selection

        await cache_model_selection(sample_model_selection_result)

        record = (
            db_session.query(ModelSelectionORM)
            .filter(ModelSelectionORM.variable_name == "ebitda")
            .first()
        )

        assert record.regressor_list == ["gas_price", "euribor"]

    @pytest.mark.asyncio
    @pytest.mark.manages_collection_state
    async def test_ac_7b_4_2_7_cache_stores_candidate_results_as_json(
        self,
        db_session: Session,
        sample_model_selection_result,
        cleanup_model_selection,
    ) -> None:
        """TEST-AC-7b.4.2.7: candidate_results is stored as JSONB."""
        from raglite.external_data.orm_models import ModelSelectionORM
        from raglite.external_data.storage import cache_model_selection

        await cache_model_selection(sample_model_selection_result)

        record = (
            db_session.query(ModelSelectionORM)
            .filter(ModelSelectionORM.variable_name == "ebitda")
            .first()
        )

        assert "prophet_True" in record.candidate_results
        assert record.candidate_results["prophet_True"]["mape"] == 5.5


# -----------------------------------------------------------------------------
# TEST-AC-7b.4.3: get_cached_model_selection Integration Tests
# -----------------------------------------------------------------------------


class TestGetCachedModelSelectionIntegration:
    """[P0] AC-7b.4.3: Integration tests for get_cached_model_selection."""

    @pytest.mark.asyncio
    @pytest.mark.manages_collection_state
    async def test_ac_7b_4_3_7_get_returns_cached_model_selection(
        self,
        db_session: Session,
        sample_model_selection_result,
        cleanup_model_selection,
    ) -> None:
        """TEST-AC-7b.4.3.7: get_cached_model_selection returns CachedModelSelection."""
        from raglite.external_data.storage import (
            CachedModelSelection,
            cache_model_selection,
            get_cached_model_selection,
        )

        await cache_model_selection(sample_model_selection_result)
        result = await get_cached_model_selection("ebitda")

        assert result is not None
        assert isinstance(result, CachedModelSelection)
        assert result.variable_name == "ebitda"
        assert result.best_model == "prophet"
        assert result.best_mape == pytest.approx(5.5, rel=0.01)
        assert result.use_regressors is True
        assert result.regressor_list == ["gas_price", "euribor"]

    @pytest.mark.asyncio
    async def test_ac_7b_4_3_8_get_returns_none_for_missing(
        self,
        cleanup_model_selection,
    ) -> None:
        """TEST-AC-7b.4.3.8: get_cached_model_selection returns None for missing."""
        from raglite.external_data.storage import get_cached_model_selection

        result = await get_cached_model_selection("nonexistent_variable")
        assert result is None

    @pytest.mark.asyncio
    @pytest.mark.manages_collection_state
    async def test_ac_7b_4_3_9_get_performance_under_100ms(
        self,
        db_session: Session,
        sample_model_selection_result,
        cleanup_model_selection,
    ) -> None:
        """TEST-AC-7b.4.3.9: get_cached_model_selection completes in <100ms."""
        from raglite.external_data.storage import (
            cache_model_selection,
            get_cached_model_selection,
        )

        # First cache the result
        await cache_model_selection(sample_model_selection_result)

        # Measure lookup time
        start = time.time()
        result = await get_cached_model_selection("ebitda")
        elapsed_ms = (time.time() - start) * 1000

        assert result is not None
        assert elapsed_ms < 100, f"Lookup took {elapsed_ms:.1f}ms, exceeds 100ms target"

    @pytest.mark.asyncio
    @pytest.mark.manages_collection_state
    async def test_ac_7b_4_3_10_get_returns_expired_with_flag(
        self,
        db_session: Session,
        cleanup_model_selection,
    ) -> None:
        """TEST-AC-7b.4.3.10: get_cached_model_selection returns expired entry with is_expired=True."""
        from raglite.external_data.orm_models import ModelSelectionORM
        from raglite.external_data.storage import get_cached_model_selection

        # Insert expired entry directly
        now = datetime.utcnow()
        expired_entry = ModelSelectionORM(
            variable_name="expired_var",
            best_model="prophet",
            best_mape=5.0,
            best_mase=0.8,
            use_regressors=False,
            regressor_list=[],
            candidate_results={},
            data_characteristics=None,
            selected_at=now - timedelta(days=8),
            expires_at=now - timedelta(days=1),  # Expired yesterday
        )
        db_session.add(expired_entry)
        db_session.commit()

        result = await get_cached_model_selection("expired_var")

        assert result is not None
        assert result.is_expired is True


# -----------------------------------------------------------------------------
# TEST-AC-7b.4.4: invalidate_model_selection Integration Tests
# -----------------------------------------------------------------------------


class TestInvalidateModelSelectionIntegration:
    """[P0] AC-7b.4.4: Integration tests for invalidate_model_selection."""

    @pytest.mark.asyncio
    @pytest.mark.manages_collection_state
    async def test_ac_7b_4_4_5_invalidate_deletes_single_variable(
        self,
        db_session: Session,
        sample_model_selection_result,
        cleanup_model_selection,
    ) -> None:
        """TEST-AC-7b.4.4.5: invalidate_model_selection deletes single variable."""
        from raglite.external_data.storage import (
            cache_model_selection,
            get_cached_model_selection,
            invalidate_model_selection,
        )

        # Cache the result
        await cache_model_selection(sample_model_selection_result)

        # Verify it exists
        result = await get_cached_model_selection("ebitda")
        assert result is not None

        # Invalidate
        count = await invalidate_model_selection("ebitda")
        assert count == 1

        # Verify it's gone
        result = await get_cached_model_selection("ebitda")
        assert result is None

    @pytest.mark.asyncio
    @pytest.mark.manages_collection_state
    async def test_ac_7b_4_4_6_invalidate_all_deletes_all_entries(
        self,
        db_session: Session,
        cleanup_model_selection,
    ) -> None:
        """TEST-AC-7b.4.4.6: invalidate_model_selection(None) deletes all entries."""
        from raglite.external_data.storage import (
            cache_model_selection,
            get_cached_model_selection,
            invalidate_model_selection,
        )
        from raglite.forecasting.model_selection import ModelSelectionResult

        # Cache multiple results
        for i, var in enumerate(["var1", "var2", "var3"]):
            result = ModelSelectionResult(
                variable_name=var,
                best_model="prophet",
                best_mape=5.0 + i,
                best_mase=0.8,
                best_with_regressors=False,
                best_regressor_set=[],
                candidate_results={},
                data_characteristics=None,
                cv_folds=5,
                runtime_seconds=30.0,
            )
            await cache_model_selection(result)

        # Invalidate all
        count = await invalidate_model_selection(None)
        assert count == 3

        # Verify all are gone
        for var in ["var1", "var2", "var3"]:
            result = await get_cached_model_selection(var)
            assert result is None

    @pytest.mark.asyncio
    async def test_ac_7b_4_4_7_invalidate_returns_zero_for_nonexistent(
        self,
        cleanup_model_selection,
    ) -> None:
        """TEST-AC-7b.4.4.7: invalidate_model_selection returns 0 for nonexistent variable."""
        from raglite.external_data.storage import invalidate_model_selection

        count = await invalidate_model_selection("nonexistent")
        assert count == 0


# -----------------------------------------------------------------------------
# TEST-AC-7b.4.5: TTL and Expiration Integration Tests
# -----------------------------------------------------------------------------


class TestTTLExpirationIntegration:
    """[P0] AC-7b.4.5: Integration tests for TTL and expiration."""

    @pytest.mark.asyncio
    @pytest.mark.manages_collection_state
    async def test_ac_7b_4_5_10_expires_at_set_correctly(
        self,
        db_session: Session,
        sample_model_selection_result,
        cleanup_model_selection,
    ) -> None:
        """TEST-AC-7b.4.5.10: expires_at is set to selected_at + 7 days."""
        from raglite.external_data.orm_models import ModelSelectionORM
        from raglite.external_data.storage import (
            MODEL_SELECTION_TTL_DAYS,
            cache_model_selection,
        )

        before = datetime.utcnow()
        await cache_model_selection(sample_model_selection_result)
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

    @pytest.mark.asyncio
    @pytest.mark.manages_collection_state
    async def test_ac_7b_4_5_11_cleanup_removes_expired_entries(
        self,
        db_session: Session,
        cleanup_model_selection,
    ) -> None:
        """TEST-AC-7b.4.5.11: cleanup_expired_model_selections removes expired entries."""
        from raglite.external_data.orm_models import ModelSelectionORM
        from raglite.external_data.storage import (
            cleanup_expired_model_selections,
            get_cached_model_selection,
        )

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
        count = await cleanup_expired_model_selections()
        assert count == 1

        # Verify fresh still exists
        fresh = await get_cached_model_selection("fresh_var")
        assert fresh is not None

        # Verify expired is gone
        expired = await get_cached_model_selection("expired_var")
        assert expired is None

    @pytest.mark.asyncio
    @pytest.mark.manages_collection_state
    async def test_ac_7b_4_5_12_cleanup_returns_zero_when_none_expired(
        self,
        db_session: Session,
        sample_model_selection_result,
        cleanup_model_selection,
    ) -> None:
        """TEST-AC-7b.4.5.12: cleanup_expired_model_selections returns 0 when none expired."""
        from raglite.external_data.storage import (
            cache_model_selection,
            cleanup_expired_model_selections,
        )

        # Cache fresh entry
        await cache_model_selection(sample_model_selection_result)

        # Cleanup should find nothing
        count = await cleanup_expired_model_selections()
        assert count == 0


# -----------------------------------------------------------------------------
# M4 Input Validation Integration Tests
# -----------------------------------------------------------------------------


class TestInputValidationIntegration:
    """[P0] M4 input validation integration tests with real database."""

    @pytest.mark.asyncio
    async def test_m4_get_cached_empty_variable_name_integration(
        self,
        cleanup_model_selection,
    ) -> None:
        """[P0] M4: get_cached_model_selection rejects empty variable_name (real DB)."""
        from raglite.external_data.storage import get_cached_model_selection

        with pytest.raises(ValueError, match="variable_name cannot be empty"):
            await get_cached_model_selection("")

    @pytest.mark.asyncio
    async def test_m4_get_cached_whitespace_only_integration(
        self,
        cleanup_model_selection,
    ) -> None:
        """[P0] M4: get_cached_model_selection rejects whitespace-only variable_name (real DB)."""
        from raglite.external_data.storage import get_cached_model_selection

        with pytest.raises(ValueError, match="variable_name cannot be empty"):
            await get_cached_model_selection("   \t\n  ")

    @pytest.mark.asyncio
    async def test_m4_get_cached_exceeds_100_chars_integration(
        self,
        cleanup_model_selection,
    ) -> None:
        """[P0] M4: get_cached_model_selection rejects >100 char variable_name (real DB)."""
        from raglite.external_data.storage import get_cached_model_selection

        long_name = "a" * 101
        with pytest.raises(ValueError, match="variable_name cannot exceed 100 characters"):
            await get_cached_model_selection(long_name)

    @pytest.mark.asyncio
    async def test_m4_invalidate_empty_variable_name_integration(
        self,
        cleanup_model_selection,
    ) -> None:
        """[P0] M4: invalidate_model_selection rejects empty variable_name (real DB)."""
        from raglite.external_data.storage import invalidate_model_selection

        with pytest.raises(ValueError, match="variable_name cannot be empty"):
            await invalidate_model_selection("")

    @pytest.mark.asyncio
    async def test_m4_invalidate_whitespace_only_integration(
        self,
        cleanup_model_selection,
    ) -> None:
        """[P0] M4: invalidate_model_selection rejects whitespace-only variable_name (real DB)."""
        from raglite.external_data.storage import invalidate_model_selection

        with pytest.raises(ValueError, match="variable_name cannot be empty"):
            await invalidate_model_selection("   \t\n  ")

    @pytest.mark.asyncio
    async def test_m4_invalidate_exceeds_100_chars_integration(
        self,
        cleanup_model_selection,
    ) -> None:
        """[P0] M4: invalidate_model_selection rejects >100 char variable_name (real DB)."""
        from raglite.external_data.storage import invalidate_model_selection

        long_name = "a" * 101
        with pytest.raises(ValueError, match="variable_name cannot exceed 100 characters"):
            await invalidate_model_selection(long_name)


# -----------------------------------------------------------------------------
# Edge Case Integration Tests
# -----------------------------------------------------------------------------


class TestEdgeCasesIntegration:
    """[P1] Edge case integration tests with real database."""

    @pytest.mark.asyncio
    @pytest.mark.manages_collection_state
    async def test_cache_and_retrieve_with_none_data_characteristics(
        self,
        db_session: Session,
        cleanup_model_selection,
    ) -> None:
        """[P1] cache_model_selection stores None data_characteristics correctly."""
        from raglite.external_data.storage import (
            cache_model_selection,
            get_cached_model_selection,
        )
        from raglite.forecasting.model_selection import ModelSelectionResult

        result = ModelSelectionResult(
            variable_name="test_none_chars",
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

        await cache_model_selection(result)

        cached = await get_cached_model_selection("test_none_chars")
        assert cached is not None
        assert cached.data_characteristics is None

    @pytest.mark.asyncio
    @pytest.mark.manages_collection_state
    async def test_cache_and_retrieve_with_empty_regressor_list(
        self,
        db_session: Session,
        cleanup_model_selection,
    ) -> None:
        """[P1] cache_model_selection stores empty regressor_list correctly."""
        from raglite.external_data.storage import (
            cache_model_selection,
            get_cached_model_selection,
        )
        from raglite.forecasting.model_selection import ModelSelectionResult

        result = ModelSelectionResult(
            variable_name="test_empty_regressors",
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

        await cache_model_selection(result)

        cached = await get_cached_model_selection("test_empty_regressors")
        assert cached is not None
        assert cached.regressor_list == []

    @pytest.mark.asyncio
    @pytest.mark.manages_collection_state
    async def test_cache_and_retrieve_with_large_candidate_results(
        self,
        db_session: Session,
        cleanup_model_selection,
    ) -> None:
        """[P2] cache_model_selection handles large candidate_results JSON."""
        from raglite.external_data.storage import (
            cache_model_selection,
            get_cached_model_selection,
        )
        from raglite.forecasting.model_selection import ModelSelectionResult

        # Simulate large candidate_results (50+ entries)
        large_results = {
            f"model_{i}_regressors_{i % 2}": {"mape": 5.0 + i * 0.1, "mase": 0.8 + i * 0.01}
            for i in range(50)
        }

        result = ModelSelectionResult(
            variable_name="test_large_results",
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

        await cache_model_selection(result)

        cached = await get_cached_model_selection("test_large_results")
        assert cached is not None
        assert len(cached.candidate_results) == 50

    @pytest.mark.asyncio
    @pytest.mark.manages_collection_state
    async def test_cache_and_retrieve_with_very_long_regressor_list(
        self,
        db_session: Session,
        cleanup_model_selection,
    ) -> None:
        """[P2] cache_model_selection handles very long regressor list."""
        from raglite.external_data.storage import (
            cache_model_selection,
            get_cached_model_selection,
        )
        from raglite.forecasting.model_selection import ModelSelectionResult

        # Edge case: 20+ regressors
        long_regressors = [f"regressor_{i}" for i in range(20)]

        result = ModelSelectionResult(
            variable_name="test_long_regressors",
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

        await cache_model_selection(result)

        cached = await get_cached_model_selection("test_long_regressors")
        assert cached is not None
        assert len(cached.regressor_list) == 20

    @pytest.mark.asyncio
    @pytest.mark.manages_collection_state
    async def test_cache_and_retrieve_with_unicode_variable_name(
        self,
        db_session: Session,
        cleanup_model_selection,
    ) -> None:
        """[P2] cache_model_selection handles Unicode variable names."""
        from raglite.external_data.storage import (
            cache_model_selection,
            get_cached_model_selection,
        )
        from raglite.forecasting.model_selection import ModelSelectionResult

        unicode_name = "变量名称"  # Chinese characters

        result = ModelSelectionResult(
            variable_name=unicode_name,
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

        await cache_model_selection(result)

        cached = await get_cached_model_selection(unicode_name)
        assert cached is not None
        assert cached.variable_name == unicode_name

    @pytest.mark.asyncio
    @pytest.mark.manages_collection_state
    async def test_cache_and_retrieve_with_special_chars_variable_name(
        self,
        db_session: Session,
        cleanup_model_selection,
    ) -> None:
        """[P2] cache_model_selection handles special characters in variable name."""
        from raglite.external_data.storage import (
            cache_model_selection,
            get_cached_model_selection,
        )
        from raglite.forecasting.model_selection import ModelSelectionResult

        special_name = "var_name-with.special@chars#123"

        result = ModelSelectionResult(
            variable_name=special_name,
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

        await cache_model_selection(result)

        cached = await get_cached_model_selection(special_name)
        assert cached is not None
        assert cached.variable_name == special_name

    @pytest.mark.asyncio
    @pytest.mark.manages_collection_state
    async def test_cache_and_retrieve_with_none_best_mase(
        self,
        db_session: Session,
        cleanup_model_selection,
    ) -> None:
        """[P1] M3: CachedModelSelection preserves None for best_mase."""
        from raglite.external_data.orm_models import ModelSelectionORM
        from raglite.external_data.storage import get_cached_model_selection

        now = datetime.utcnow()

        # Insert directly with None best_mase
        entry = ModelSelectionORM(
            variable_name="test_none_mase",
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
        db_session.add(entry)
        db_session.commit()

        cached = await get_cached_model_selection("test_none_mase")
        assert cached is not None
        assert cached.best_mase is None

    @pytest.mark.asyncio
    @pytest.mark.manages_collection_state
    async def test_variable_name_exactly_100_chars(
        self,
        db_session: Session,
        cleanup_model_selection,
    ) -> None:
        """[P1] M4: Cache and retrieve variable_name at 100 char boundary."""
        from raglite.external_data.storage import (
            cache_model_selection,
            get_cached_model_selection,
        )
        from raglite.forecasting.model_selection import ModelSelectionResult

        exactly_100 = "a" * 100

        result = ModelSelectionResult(
            variable_name=exactly_100,
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

        await cache_model_selection(result)

        cached = await get_cached_model_selection(exactly_100)
        assert cached is not None
        assert cached.variable_name == exactly_100
        assert len(cached.variable_name) == 100


# -----------------------------------------------------------------------------
# Error Handling Integration Tests
# -----------------------------------------------------------------------------


class TestErrorHandlingIntegration:
    """[P1] Error handling integration tests with real database."""

    @pytest.mark.asyncio
    @pytest.mark.manages_collection_state
    async def test_get_cached_returns_none_after_invalidation(
        self,
        db_session: Session,
        sample_model_selection_result,
        cleanup_model_selection,
    ) -> None:
        """[P1] get_cached_model_selection returns None after invalidation."""
        from raglite.external_data.storage import (
            cache_model_selection,
            get_cached_model_selection,
            invalidate_model_selection,
        )

        await cache_model_selection(sample_model_selection_result)

        # Verify it exists
        cached = await get_cached_model_selection("ebitda")
        assert cached is not None

        # Invalidate
        await invalidate_model_selection("ebitda")

        # Verify it's gone
        cached_after = await get_cached_model_selection("ebitda")
        assert cached_after is None

    @pytest.mark.asyncio
    async def test_invalidate_nonexistent_variable_returns_zero(
        self,
        cleanup_model_selection,
    ) -> None:
        """[P1] invalidate_model_selection returns 0 for nonexistent variable."""
        from raglite.external_data.storage import invalidate_model_selection

        count = await invalidate_model_selection("nonexistent_variable_xyz")
        assert count == 0

    @pytest.mark.asyncio
    @pytest.mark.manages_collection_state
    async def test_cleanup_with_mixed_fresh_and_expired(
        self,
        db_session: Session,
        cleanup_model_selection,
    ) -> None:
        """[P1] cleanup_expired_model_selections only removes expired entries."""
        from raglite.external_data.orm_models import ModelSelectionORM
        from raglite.external_data.storage import (
            cleanup_expired_model_selections,
            get_cached_model_selection,
        )

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
        count = await cleanup_expired_model_selections()
        assert count == 2

        # Verify fresh entries still exist
        for i in range(3):
            cached = await get_cached_model_selection(f"var_{i}")
            assert cached is not None

        # Verify expired entries are gone
        for i in range(3, 5):
            cached = await get_cached_model_selection(f"var_{i}")
            assert cached is None


# -----------------------------------------------------------------------------
# Performance Tests
# -----------------------------------------------------------------------------


class TestPerformance:
    """[P0] Performance tests for cache operations."""

    @pytest.mark.asyncio
    @pytest.mark.manages_collection_state
    async def test_cache_performance_under_500ms(
        self,
        sample_model_selection_result,
        cleanup_model_selection,
    ) -> None:
        """cache_model_selection completes in <500ms."""
        from raglite.external_data.storage import cache_model_selection

        start = time.time()
        await cache_model_selection(sample_model_selection_result)
        elapsed_ms = (time.time() - start) * 1000

        assert elapsed_ms < 500, f"Cache took {elapsed_ms:.1f}ms, exceeds 500ms target"

    @pytest.mark.asyncio
    @pytest.mark.manages_collection_state
    async def test_invalidate_performance_under_200ms(
        self,
        sample_model_selection_result,
        cleanup_model_selection,
    ) -> None:
        """invalidate_model_selection completes in <200ms."""
        from raglite.external_data.storage import (
            cache_model_selection,
            invalidate_model_selection,
        )

        await cache_model_selection(sample_model_selection_result)

        start = time.time()
        await invalidate_model_selection("ebitda")
        elapsed_ms = (time.time() - start) * 1000

        assert elapsed_ms < 200, f"Invalidate took {elapsed_ms:.1f}ms, exceeds 200ms target"

    @pytest.mark.asyncio
    @pytest.mark.manages_collection_state
    async def test_cleanup_performance_under_1s(
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
        count = await cleanup_expired_model_selections()
        elapsed_ms = (time.time() - start) * 1000

        assert count == 50
        assert elapsed_ms < 1000, f"Cleanup took {elapsed_ms:.1f}ms, exceeds 1s target"
