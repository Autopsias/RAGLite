"""Migration script tests for model_selection table.

Story 7b-4: Model Selection Cache in PostgreSQL
TEST-AC-7b.4.6.x: Migration tests
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

# Mark all tests as integration and PostgreSQL-only
pytestmark = [
    pytest.mark.integration,
    pytest.mark.postgresql_only,
    pytest.mark.preserve_collection,
    pytest.mark.slow,
]


class TestMigrationScript:
    """[P0] AC-7b.4.6: Migration script tests."""

    @pytest.mark.preserve_collection
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

    @pytest.mark.preserve_collection
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

    @pytest.mark.preserve_collection
    def test_ac_7b_4_6_3_variable_name_index_exists(self, db_session: Session) -> None:
        """TEST-AC-7b.4.6.3: variable_name index exists.

        Note: The migration uses explicit index naming (idx_model_selection_variable)
        while Alembic/SQLAlchemy auto-generates (ix_model_selection_variable_name).
        """
        from sqlalchemy import inspect

        inspector = inspect(db_session.bind)
        indexes = inspector.get_indexes("model_selection")
        index_names = {idx["name"] for idx in indexes}

        # Accept either raw SQL migration name or Alembic/SQLAlchemy auto-generated name
        variable_index_exists = (
            "idx_model_selection_variable" in index_names
            or "ix_model_selection_variable_name" in index_names
        )
        assert variable_index_exists, (
            f"Neither idx_model_selection_variable nor ix_model_selection_variable_name "
            f"found in indexes: {index_names}"
        )

    @pytest.mark.preserve_collection
    def test_ac_7b_4_6_4_expires_at_index_exists(self, db_session: Session) -> None:
        """TEST-AC-7b.4.6.4: idx_model_selection_expires index exists."""
        from sqlalchemy import inspect

        inspector = inspect(db_session.bind)
        indexes = inspector.get_indexes("model_selection")
        index_names = {idx["name"] for idx in indexes}

        assert "idx_model_selection_expires" in index_names

    @pytest.mark.manages_collection_state
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
