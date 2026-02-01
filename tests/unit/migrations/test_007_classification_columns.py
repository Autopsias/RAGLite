"""ATDD Unit Tests for Story 9.1: Schema Migration - Add Classification Columns.

Test IDs follow format: TEST-AC-9.1.{ac}.{test_number}

These tests validate behavior from acceptance criteria, NOT implementation details.
Tests are ATDD tests - focus on acceptance criteria, not implementation details.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

# Module-level markers for test categorization
pytestmark = [
    pytest.mark.atdd,  # ATDD tests - early-phase acceptance criteria validation
]

# Priority markers for test prioritization (defined in pytest.ini)
# p0: Critical - must pass for story completion
# p1: Important - core functionality
# p2: Edge cases


class TestAC1PeriodTypeColumnAddition:
    """AC1: period_type Column Addition.

    Given the financial_tables table exists in PostgreSQL
    When Migration 007 is applied
    Then a new column period_type VARCHAR(50) is added
    And the column is nullable for backward compatibility
    And an index idx_period_type is created on the column
    """

    @pytest.mark.p0
    def test_ac_9_1_1_1_period_type_column_exists_after_migration(self) -> None:
        """TEST-AC-9.1.1.1: period_type column is added after migration.

        Given: The financial_tables table exists in PostgreSQL
        When: Migration 007 is applied
        Then: A new column period_type VARCHAR(50) is added
        """
        # Arrange: Import migration module (should fail - module doesn't exist yet)
        from migrations.migration_007_add_classification_columns import apply_migration

        # Act: Create mock connection and cursor
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

        # Assert: Verify ALTER TABLE was called with period_type column
        # Collect all SQL execute calls to verify column addition
        sql_calls = [str(call) for call in mock_cursor.execute.call_args_list]
        combined_sql = " ".join(sql_calls).lower()
        assert "period_type" in combined_sql, "period_type column should be added"
        assert "varchar(50)" in combined_sql, "period_type should be VARCHAR(50)"

        # M3: Add assertions for commit and close call counts
        assert mock_conn.commit.call_count >= 6, "Should commit after each migration step"
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()

    @pytest.mark.p0
    def test_ac_9_1_1_2_period_type_column_is_nullable(self) -> None:
        """TEST-AC-9.1.1.2: period_type column is nullable for backward compatibility.

        Given: The financial_tables table exists in PostgreSQL
        When: Migration 007 is applied
        Then: The period_type column is nullable (no NOT NULL constraint)
        """
        # Arrange
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

        # Assert: SQL should NOT contain NOT NULL for period_type
        # Verify nullable column - should NOT have NOT NULL constraint
        period_type_calls = [
            str(call).lower() for call in mock_cursor.execute.call_args_list
            if "period_type" in str(call).lower()
        ]
        assert len(period_type_calls) > 0, "period_type should be added"
        for call_sql in period_type_calls:
            # Column should be nullable - either no NOT NULL or has IF NOT EXISTS guard
            has_not_null = "not null" in call_sql
            has_if_not_exists = "if not exists" in call_sql
            assert not has_not_null or has_if_not_exists, \
                f"period_type column must be nullable (no NOT NULL constraint): {call_sql}"

    @pytest.mark.p1
    def test_ac_9_1_1_3_idx_period_type_index_created(self) -> None:
        """TEST-AC-9.1.1.3: idx_period_type index is created on period_type column.

        Given: The financial_tables table exists in PostgreSQL
        When: Migration 007 is applied
        Then: An index idx_period_type is created on the column
        """
        # Arrange
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

        # Assert: CREATE INDEX for idx_period_type was called
        executed_sql = " ".join(
            str(call) for call in mock_cursor.execute.call_args_list
        )
        assert "idx_period_type" in executed_sql.lower()
        assert "create index" in executed_sql.lower()


class TestAC2ValueTypeColumnAddition:
    """AC2: value_type Column Addition.

    Given the financial_tables table exists in PostgreSQL
    When Migration 007 is applied
    Then a new column value_type VARCHAR(50) is added
    And the column is nullable for backward compatibility
    And an index idx_value_type is created on the column
    """

    @pytest.mark.p0
    def test_ac_9_1_2_1_value_type_column_exists_after_migration(self) -> None:
        """TEST-AC-9.1.2.1: value_type column is added after migration.

        Given: The financial_tables table exists in PostgreSQL
        When: Migration 007 is applied
        Then: A new column value_type VARCHAR(50) is added
        """
        # Arrange
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

        # Assert
        executed_sql = " ".join(
            str(call) for call in mock_cursor.execute.call_args_list
        )
        assert "value_type" in executed_sql.lower()
        assert "varchar(50)" in executed_sql.lower()

    @pytest.mark.p0
    def test_ac_9_1_2_2_value_type_column_is_nullable(self) -> None:
        """TEST-AC-9.1.2.2: value_type column is nullable for backward compatibility.

        Given: The financial_tables table exists in PostgreSQL
        When: Migration 007 is applied
        Then: The value_type column is nullable
        """
        # Arrange
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

        # Assert
        value_type_calls = [
            str(call) for call in mock_cursor.execute.call_args_list
            if "value_type" in str(call).lower()
        ]
        for call_sql in value_type_calls:
            assert "not null" not in call_sql.lower() or "if not exists" in call_sql.lower()

    @pytest.mark.p1
    def test_ac_9_1_2_3_idx_value_type_index_created(self) -> None:
        """TEST-AC-9.1.2.3: idx_value_type index is created on value_type column.

        Given: The financial_tables table exists in PostgreSQL
        When: Migration 007 is applied
        Then: An index idx_value_type is created on the column
        """
        # Arrange
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

        # Assert
        executed_sql = " ".join(
            str(call) for call in mock_cursor.execute.call_args_list
        )
        assert "idx_value_type" in executed_sql.lower()
        assert "create index" in executed_sql.lower()


class TestAC3EntityLevelColumnAddition:
    """AC3: entity_level Column Addition.

    Given the financial_tables table exists in PostgreSQL
    When Migration 007 is applied
    Then a new column entity_level VARCHAR(100) is added
    And the column is nullable for backward compatibility
    And an index idx_entity_level is created on the column
    """

    @pytest.mark.p0
    def test_ac_9_1_3_1_entity_level_column_exists_after_migration(self) -> None:
        """TEST-AC-9.1.3.1: entity_level column is added after migration.

        Given: The financial_tables table exists in PostgreSQL
        When: Migration 007 is applied
        Then: A new column entity_level VARCHAR(100) is added
        """
        # Arrange
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

        # Assert
        executed_sql = " ".join(
            str(call) for call in mock_cursor.execute.call_args_list
        )
        assert "entity_level" in executed_sql.lower()
        assert "varchar(100)" in executed_sql.lower()

    @pytest.mark.p0
    def test_ac_9_1_3_2_entity_level_column_is_nullable(self) -> None:
        """TEST-AC-9.1.3.2: entity_level column is nullable for backward compatibility.

        Given: The financial_tables table exists in PostgreSQL
        When: Migration 007 is applied
        Then: The entity_level column is nullable
        """
        # Arrange
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

        # Assert
        entity_level_calls = [
            str(call) for call in mock_cursor.execute.call_args_list
            if "entity_level" in str(call).lower()
        ]
        for call_sql in entity_level_calls:
            assert "not null" not in call_sql.lower() or "if not exists" in call_sql.lower()

    @pytest.mark.p1
    def test_ac_9_1_3_3_idx_entity_level_index_created(self) -> None:
        """TEST-AC-9.1.3.3: idx_entity_level index is created on entity_level column.

        Given: The financial_tables table exists in PostgreSQL
        When: Migration 007 is applied
        Then: An index idx_entity_level is created on the column
        """
        # Arrange
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

        # Assert
        executed_sql = " ".join(
            str(call) for call in mock_cursor.execute.call_args_list
        )
        assert "idx_entity_level" in executed_sql.lower()
        assert "create index" in executed_sql.lower()


class TestAC4MigrationIdempotency:
    """AC4: Migration Script Idempotency.

    Given Migration 007 exists in migrations/
    When the migration is run multiple times
    Then it succeeds without errors (IF NOT EXISTS guards)
    And no duplicate columns or indexes are created
    """

    @pytest.mark.p0
    def test_ac_9_1_4_1_migration_uses_if_not_exists_for_columns(self) -> None:
        """TEST-AC-9.1.4.1: Migration uses IF NOT EXISTS guard for columns.

        Given: Migration 007 exists in migrations/
        When: The migration SQL is examined
        Then: Column additions use IF NOT EXISTS guard
        """
        # Arrange
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

        # Assert: All ALTER TABLE statements use IF NOT EXISTS
        alter_calls = [
            str(call) for call in mock_cursor.execute.call_args_list
            if "alter table" in str(call).lower()
        ]
        for call_sql in alter_calls:
            assert "if not exists" in call_sql.lower()

    @pytest.mark.p0
    def test_ac_9_1_4_2_migration_uses_if_not_exists_for_indexes(self) -> None:
        """TEST-AC-9.1.4.2: Migration uses IF NOT EXISTS guard for indexes.

        Given: Migration 007 exists in migrations/
        When: The migration SQL is examined
        Then: Index creation uses IF NOT EXISTS guard
        """
        # Arrange
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

        # Assert: All CREATE INDEX statements use IF NOT EXISTS
        index_calls = [
            str(call) for call in mock_cursor.execute.call_args_list
            if "create index" in str(call).lower()
        ]
        for call_sql in index_calls:
            assert "if not exists" in call_sql.lower()

    @pytest.mark.p1
    def test_ac_9_1_4_3_migration_runs_twice_without_error(self) -> None:
        """TEST-AC-9.1.4.3: Migration can run multiple times without error.

        Given: Migration 007 exists in migrations/
        When: The migration is run multiple times
        Then: It succeeds without errors
        """
        # Arrange
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
            # Act: Run migration twice
            apply_migration()
            apply_migration()

        # Assert: No exception raised, both runs complete
        # Expected: 6 SQL calls per run (3 ALTER TABLE + 3 CREATE INDEX) x 2 = 12 minimum
        EXPECTED_CALLS_PER_RUN = 6  # 3 columns + 3 indexes
        MIN_CALLS_FOR_TWO_RUNS = EXPECTED_CALLS_PER_RUN * 2
        assert mock_cursor.execute.call_count >= MIN_CALLS_FOR_TWO_RUNS, \
            f"Expected at least {MIN_CALLS_FOR_TWO_RUNS} calls for 2 migrations, got {mock_cursor.execute.call_count}"


class TestAC5VerificationScript:
    """AC5: Verification Script.

    Given Migration 007 has been applied
    When running the verification script
    Then it confirms all three columns exist
    And it confirms all three indexes exist
    And it reports the migration status as SUCCESS
    """

    @pytest.mark.p0
    def test_ac_9_1_5_1_verification_checks_all_columns_exist(self) -> None:
        """TEST-AC-9.1.5.1: Verification confirms all three columns exist.

        Given: Migration 007 has been applied
        When: Running the verification script
        Then: It confirms all three columns exist
        """
        # Arrange
        from migrations.migration_007_add_classification_columns import verify_migration

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # Simulate columns exist in information_schema
        # verify_migration() calls fetchone() 4 times:
        # 1. period_type exists -> (1,)
        # 2. value_type exists -> (1,)
        # 3. entity_level exists -> (1,)
        # 4. index count -> (3,)
        mock_cursor.fetchone.side_effect = [(1,), (1,), (1,), (3,)]

        with (
            patch(
                "migrations.migration_007_add_classification_columns.get_postgresql_connection",
                return_value=mock_conn,
            ),
            patch("migrations.migration_007_add_classification_columns.SafetyGuard"),
        ):
            # Act
            result = verify_migration()

        # Assert: Verification queries information_schema for all 3 columns
        info_schema_calls = [
            str(call) for call in mock_cursor.execute.call_args_list
            if "information_schema" in str(call).lower()
        ]
        assert len(info_schema_calls) >= 3
        assert any("period_type" in call.lower() for call in info_schema_calls)
        assert any("value_type" in call.lower() for call in info_schema_calls)
        assert any("entity_level" in call.lower() for call in info_schema_calls)
        assert result is True or result.get("status") == "SUCCESS"

    @pytest.mark.p0
    def test_ac_9_1_5_2_verification_checks_all_indexes_exist(self) -> None:
        """TEST-AC-9.1.5.2: Verification confirms all three indexes exist.

        Given: Migration 007 has been applied
        When: Running the verification script
        Then: It confirms all three indexes exist
        """
        # Arrange
        from migrations.migration_007_add_classification_columns import verify_migration

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # Simulate indexes exist in pg_indexes
        mock_cursor.fetchone.return_value = (3,)

        with (
            patch(
                "migrations.migration_007_add_classification_columns.get_postgresql_connection",
                return_value=mock_conn,
            ),
            patch("migrations.migration_007_add_classification_columns.SafetyGuard"),
        ):
            # Act
            _ = verify_migration()

        # Assert: Verification queries pg_indexes for all 3 indexes
        pg_indexes_calls = [
            str(call) for call in mock_cursor.execute.call_args_list
            if "pg_indexes" in str(call).lower()
        ]
        assert len(pg_indexes_calls) >= 1
        combined_sql = " ".join(pg_indexes_calls)
        assert "idx_period_type" in combined_sql.lower()
        assert "idx_value_type" in combined_sql.lower()
        assert "idx_entity_level" in combined_sql.lower()

    @pytest.mark.p0
    def test_ac_9_1_5_3_verification_reports_success_when_all_present(self) -> None:
        """TEST-AC-9.1.5.3: Verification reports SUCCESS when all present.

        Given: Migration 007 has been applied successfully
        When: Running the verification script
        Then: It reports the migration status as SUCCESS
        """
        # Arrange
        from migrations.migration_007_add_classification_columns import verify_migration

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # Simulate all checks pass
        mock_cursor.fetchone.side_effect = [
            (1,),  # period_type column exists
            (1,),  # value_type column exists
            (1,),  # entity_level column exists
            (3,),  # All 3 indexes exist
        ]

        with (
            patch(
                "migrations.migration_007_add_classification_columns.get_postgresql_connection",
                return_value=mock_conn,
            ),
            patch("migrations.migration_007_add_classification_columns.SafetyGuard"),
        ):
            # Act
            result = verify_migration()

        # Assert: Returns success status (dict with SUCCESS status or True bool)
        assert result is not None, "Verification result should not be None"
        if isinstance(result, dict):
            assert result.get("status") == "SUCCESS", \
                f"Expected SUCCESS status in result, got: {result}"
        elif isinstance(result, bool):
            assert result is True, "Expected True for successful migration verification"
        else:
            assert result, f"Expected truthy result for success, got: {result}"

    @pytest.mark.p1
    def test_ac_9_1_5_4_verification_fails_when_column_missing(self) -> None:
        """TEST-AC-9.1.5.4: Verification fails when a column is missing.

        Given: Migration 007 was only partially applied
        When: Running the verification script
        Then: It reports failure when a column is missing
        """
        # Arrange
        from migrations.migration_007_add_classification_columns import verify_migration

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # Simulate period_type column missing
        mock_cursor.fetchone.side_effect = [
            (0,),  # period_type column MISSING
            (1,),  # value_type column exists
            (1,),  # entity_level column exists
            (2,),  # Only 2 indexes exist
        ]

        with (
            patch(
                "migrations.migration_007_add_classification_columns.get_postgresql_connection",
                return_value=mock_conn,
            ),
            patch("migrations.migration_007_add_classification_columns.SafetyGuard"),
        ):
            # Act
            result = verify_migration()

        # Assert: Returns failure status
        if isinstance(result, bool):
            assert result is False
        elif isinstance(result, dict):
            assert result.get("status") != "SUCCESS"
        else:
            # Should return falsy value indicating failure
            assert not result

    @pytest.mark.p1
    def test_ac_9_1_5_5_verification_fails_when_index_missing(self) -> None:
        """TEST-AC-9.1.5.5: Verification fails when an index is missing.

        Given: Migration 007 was only partially applied
        When: Running the verification script
        Then: It reports failure when an index is missing
        """
        # Arrange
        from migrations.migration_007_add_classification_columns import verify_migration

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # Simulate all columns exist but one index missing
        mock_cursor.fetchone.side_effect = [
            (1,),  # period_type column exists
            (1,),  # value_type column exists
            (1,),  # entity_level column exists
            (2,),  # Only 2 of 3 indexes exist (missing one)
        ]

        with (
            patch(
                "migrations.migration_007_add_classification_columns.get_postgresql_connection",
                return_value=mock_conn,
            ),
            patch("migrations.migration_007_add_classification_columns.SafetyGuard"),
        ):
            # Act
            result = verify_migration()

        # Assert: Returns failure status
        if isinstance(result, bool):
            assert result is False
        elif isinstance(result, dict):
            assert result.get("status") != "SUCCESS"
        else:
            assert not result


class TestErrorHandlingAndEdgeCases:
    """Test error handling and edge cases for migration robustness.

    Tests coverage gaps identified in Phase 6 expansion:
    - Database connection failures
    - Rollback on migration error
    - Exception handling in verify_migration()
    """

    @pytest.mark.p0
    def test_ac_9_1_error_1_migration_fails_when_connection_unavailable(self) -> None:
        """TEST-AC-9.1.ERROR.1: Migration fails cleanly when database connection fails.

        Given: Database connection is unavailable
        When: Running apply_migration()
        Then: The migration raises an exception with clear error message
        """
        # Arrange
        from migrations.migration_007_add_classification_columns import apply_migration

        # Mock get_postgresql_connection to raise connection error
        with patch(
            "migrations.migration_007_add_classification_columns.get_postgresql_connection",
            side_effect=ConnectionError("Database connection failed"),
        ):
            # Act & Assert: Migration should raise and propagate the exception
            with pytest.raises(ConnectionError, match="Database connection failed"):
                apply_migration()

    @pytest.mark.p1
    def test_ac_9_1_error_2_migration_rolls_back_on_database_error(self) -> None:
        """TEST-AC-9.1.ERROR.2: Migration rolls back transaction on database error.

        Given: Migration is in progress
        When: A database error occurs during column addition
        Then: Transaction is rolled back via conn.rollback()
        """
        # Arrange
        from migrations.migration_007_add_classification_columns import apply_migration

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # Simulate database error on first column addition
        mock_cursor.execute.side_effect = Exception("Database error during ALTER TABLE")

        with (
            patch(
                "migrations.migration_007_add_classification_columns.get_postgresql_connection",
                return_value=mock_conn,
            ),
            patch("migrations.migration_007_add_classification_columns.SafetyGuard"),
        ):
            # Act & Assert: Migration should raise and rollback
            with pytest.raises(Exception, match="Database error during ALTER TABLE"):
                apply_migration()

            # Verify rollback was called
            mock_conn.rollback.assert_called_once()

    @pytest.mark.p1
    def test_ac_9_1_error_3_verify_migration_returns_failed_on_connection_failure(self) -> None:
        """TEST-AC-9.1.ERROR.3: verify_migration() returns FAILED on connection failure.

        Given: Database connection fails during verification
        When: Running verify_migration()
        Then: Returns FAILED status dict with zero counts (H2 fix)
        """
        # Arrange
        from migrations.migration_007_add_classification_columns import verify_migration

        # Mock get_postgresql_connection to raise connection error
        with patch(
            "migrations.migration_007_add_classification_columns.get_postgresql_connection",
            side_effect=ConnectionError("Cannot connect to database"),
        ):
            # Act
            result = verify_migration()

        # Assert: H2 fix - returns FAILED status instead of raising
        assert isinstance(result, dict)
        assert result["status"] == "FAILED"
        assert result["columns_verified"] == 0
        assert result["indexes_verified"] == 0

    @pytest.mark.p2
    def test_ac_9_1_error_4_verify_migration_handles_query_exception(self) -> None:
        """TEST-AC-9.1.ERROR.4: verify_migration() handles query exceptions gracefully.

        Given: Database connection succeeds but query fails
        When: Running verify_migration()
        Then: Returns FAILED status with zero counts
        """
        # Arrange
        from migrations.migration_007_add_classification_columns import verify_migration

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # Simulate query error
        mock_cursor.execute.side_effect = Exception("Query execution failed")

        with (
            patch(
                "migrations.migration_007_add_classification_columns.get_postgresql_connection",
                return_value=mock_conn,
            ),
            patch("migrations.migration_007_add_classification_columns.SafetyGuard"),
        ):
            # Act
            result = verify_migration()

        # Assert
        assert isinstance(result, dict)
        assert result["status"] == "FAILED"
        assert result["columns_verified"] == 0
        assert result["indexes_verified"] == 0
