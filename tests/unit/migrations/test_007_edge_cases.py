"""Phase 6 Coverage Expansion: Edge Cases for Story 9.1 Migration.

Tests coverage gaps identified in Phase 6 expansion:
- Partial migration failures
- Concurrent connection handling
- Schema validation edge cases
- Index creation with existing data
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

pytestmark = [
    pytest.mark.atdd,
]


class TestPartialMigrationFailures:
    """Edge case tests for partial migration failures.

    Tests behavior when migration partially succeeds then fails.
    """

    @pytest.mark.p1
    def test_partial_column_addition_then_failure(self) -> None:
        """[P1] Partial migration: column added, then error on index creation.

        Given: Migration starts successfully
        When: Column addition succeeds but index creation fails
        Then: Transaction rolls back all changes
        """
        from migrations.migration_007_add_classification_columns import apply_migration

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # Simulate: columns succeed, first index fails
        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            # Succeed for first 3 calls (columns), fail on 4th (index)
            if call_count[0] == 4:
                raise Exception("Index creation failed")

        mock_cursor.execute.side_effect = side_effect

        with (
            patch(
                "migrations.migration_007_add_classification_columns.get_postgresql_connection",
                return_value=mock_conn,
            ),
            patch("migrations.migration_007_add_classification_columns.SafetyGuard"),
        ):
            with pytest.raises(Exception, match="Index creation failed"):
                apply_migration()

        # Verify rollback was called
        mock_conn.rollback.assert_called_once()

    @pytest.mark.p2
    def test_migration_with_invalid_column_type(self) -> None:
        """[P2] Migration fails if database rejects column type.

        Given: Migration script attempts to add column
        When: Database rejects column type (hypothetical scenario)
        Then: Error is propagated and transaction rolls back
        """
        from migrations.migration_007_add_classification_columns import apply_migration

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # Simulate invalid column type error on first ALTER
        mock_cursor.execute.side_effect = Exception("type VARCHAR does not exist")

        with (
            patch(
                "migrations.migration_007_add_classification_columns.get_postgresql_connection",
                return_value=mock_conn,
            ),
            patch("migrations.migration_007_add_classification_columns.SafetyGuard"),
        ):
            with pytest.raises(Exception, match="type VARCHAR does not exist"):
                apply_migration()

        mock_conn.rollback.assert_called_once()


class TestSchemaValidationEdgeCases:
    """Edge cases for schema validation logic."""

    @pytest.mark.p1
    def test_verify_migration_with_partial_columns(self) -> None:
        """[P1] Verification detects when only some columns exist.

        Given: Migration partially applied (only 2 of 3 columns)
        When: Running verify_migration()
        Then: Returns FAILED status with correct count
        """
        from migrations.migration_007_add_classification_columns import verify_migration

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # Simulate: period_type and value_type exist, entity_level missing
        mock_cursor.fetchone.side_effect = [
            (1,),  # period_type exists
            (1,),  # value_type exists
            (0,),  # entity_level MISSING
            (2,),  # Only 2 indexes exist
        ]

        with (
            patch(
                "migrations.migration_007_add_classification_columns.get_postgresql_connection",
                return_value=mock_conn,
            ),
            patch("migrations.migration_007_add_classification_columns.SafetyGuard"),
        ):
            result = verify_migration()

        assert isinstance(result, dict)
        assert result["status"] == "FAILED"
        assert result["columns_verified"] == 2
        assert result["indexes_verified"] == 2

    @pytest.mark.p2
    def test_verify_migration_with_no_columns(self) -> None:
        """[P2] Verification handles case where no columns exist.

        Given: Migration never run
        When: Running verify_migration()
        Then: Returns FAILED with zero counts
        """
        from migrations.migration_007_add_classification_columns import verify_migration

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # Simulate: no columns or indexes exist
        mock_cursor.fetchone.side_effect = [
            (0,),  # period_type missing
            (0,),  # value_type missing
            (0,),  # entity_level missing
            (0,),  # No indexes
        ]

        with (
            patch(
                "migrations.migration_007_add_classification_columns.get_postgresql_connection",
                return_value=mock_conn,
            ),
            patch("migrations.migration_007_add_classification_columns.SafetyGuard"),
        ):
            result = verify_migration()

        assert isinstance(result, dict)
        assert result["status"] == "FAILED"
        assert result["columns_verified"] == 0
        assert result["indexes_verified"] == 0


class TestSafetyGuardIntegration:
    """Edge cases for SafetyGuard integration."""

    @pytest.mark.p0
    def test_migration_blocked_on_production(self) -> None:
        """[P0] Migration blocked when SafetyGuard detects production.

        Given: SafetyGuard detects production environment
        When: Running apply_migration()
        Then: Raises ProductionProtectionError before database operations
        """
        from migrations.migration_007_add_classification_columns import apply_migration

        mock_conn = MagicMock()
        mock_guard = MagicMock()
        mock_guard.block_destructive_on_production.side_effect = Exception(
            "SAFETY: Production database detected"
        )

        with (
            patch(
                "migrations.migration_007_add_classification_columns.get_postgresql_connection",
                return_value=mock_conn,
            ),
            patch(
                "migrations.migration_007_add_classification_columns.SafetyGuard",
                return_value=mock_guard,
            ),
        ):
            with pytest.raises(Exception, match="Production database detected"):
                apply_migration()

        # Verify NO database operations were attempted
        mock_conn.cursor.assert_not_called()

    @pytest.mark.p1
    def test_verify_migration_bypasses_safety_guard(self) -> None:
        """[P1] verify_migration() does not trigger SafetyGuard.

        Given: verify_migration() is read-only
        When: Running verification
        Then: SafetyGuard is not invoked (no destructive operations)
        """
        from migrations.migration_007_add_classification_columns import verify_migration

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # Simulate successful verification
        mock_cursor.fetchone.side_effect = [(1,), (1,), (1,), (3,)]

        with (
            patch(
                "migrations.migration_007_add_classification_columns.get_postgresql_connection",
                return_value=mock_conn,
            ),
            patch(
                "migrations.migration_007_add_classification_columns.SafetyGuard"
            ) as mock_guard,
        ):
            result = verify_migration()

        # SafetyGuard should NOT be instantiated for read-only verification
        mock_guard.assert_not_called()
        assert result["status"] == "SUCCESS"


class TestConnectionResourceManagement:
    """Edge cases for connection and resource management."""

    @pytest.mark.p1
    def test_connection_closed_on_success(self) -> None:
        """[P1] Database connection properly closed on successful migration.

        Given: Migration completes successfully
        When: apply_migration() returns
        Then: Connection and cursor are closed
        """
        from migrations.migration_007_add_classification_columns import apply_migration

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with (
            patch(
                "migrations.migration_007_add_classification_columns.get_postgresql_connection",
                return_value=mock_conn,
            ),
            patch("migrations.migration_007_add_classification_columns.SafetyGuard"),
        ):
            apply_migration()

        # Verify cleanup
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()

    @pytest.mark.p1
    def test_connection_closed_on_failure(self) -> None:
        """[P1] Database connection closed even when migration fails.

        Given: Migration fails during execution
        When: Exception is raised
        Then: Connection and cursor still closed via finally block
        """
        from migrations.migration_007_add_classification_columns import apply_migration

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.execute.side_effect = Exception("Database error")

        with (
            patch(
                "migrations.migration_007_add_classification_columns.get_postgresql_connection",
                return_value=mock_conn,
            ),
            patch("migrations.migration_007_add_classification_columns.SafetyGuard"),
        ):
            with pytest.raises(Exception, match="Database error"):
                apply_migration()

        # Verify cleanup happened despite error
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()

    @pytest.mark.p2
    def test_verify_connection_closed_after_check(self) -> None:
        """[P2] verify_migration() closes connection after verification.

        Given: Verification completes
        When: verify_migration() returns
        Then: Connection and cursor are closed
        """
        from migrations.migration_007_add_classification_columns import verify_migration

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchone.side_effect = [(1,), (1,), (1,), (3,)]

        with (
            patch(
                "migrations.migration_007_add_classification_columns.get_postgresql_connection",
                return_value=mock_conn,
            ),
            patch("migrations.migration_007_add_classification_columns.SafetyGuard"),
        ):
            _ = verify_migration()

        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()


class TestIdempotencyEdgeCases:
    """Edge cases for idempotency behavior."""

    @pytest.mark.p1
    def test_migration_with_columns_already_exist(self) -> None:
        """[P1] Migration succeeds when columns already exist.

        Given: All columns already exist from previous migration
        When: Running apply_migration() again
        Then: IF NOT EXISTS prevents errors, migration succeeds
        """
        from migrations.migration_007_add_classification_columns import apply_migration

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # Simulate all statements succeed (IF NOT EXISTS prevents duplicates)
        mock_cursor.execute.return_value = None

        with (
            patch(
                "migrations.migration_007_add_classification_columns.get_postgresql_connection",
                return_value=mock_conn,
            ),
            patch("migrations.migration_007_add_classification_columns.SafetyGuard"),
        ):
            # Should NOT raise
            apply_migration()

        # Verify commit was called (successful completion)
        assert mock_conn.commit.call_count >= 6

    @pytest.mark.p2
    def test_migration_with_indexes_already_exist(self) -> None:
        """[P2] Migration succeeds when indexes already exist.

        Given: All indexes already exist from previous migration
        When: Running apply_migration() again
        Then: IF NOT EXISTS prevents errors on index creation
        """
        from migrations.migration_007_add_classification_columns import apply_migration

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with (
            patch(
                "migrations.migration_007_add_classification_columns.get_postgresql_connection",
                return_value=mock_conn,
            ),
            patch("migrations.migration_007_add_classification_columns.SafetyGuard"),
        ):
            apply_migration()

        # Collect all CREATE INDEX calls
        create_index_calls = [
            str(call)
            for call in mock_cursor.execute.call_args_list
            if "create index" in str(call).lower()
        ]

        # All CREATE INDEX should have IF NOT EXISTS
        assert len(create_index_calls) == 3
        for call_sql in create_index_calls:
            assert "if not exists" in call_sql.lower()
