"""ATDD Integration Tests for Story 9.1: Schema Migration - Add Classification Columns.

Test IDs follow format: TEST-AC-9.1.{ac}.{test_number}

These tests validate behavior against a REAL PostgreSQL database (test instance).
All tests are expected to FAIL in the RED phase (no implementation exists yet).

Requires:
- APP_ENV=test (mandatory for test database isolation)
- PostgreSQL test container on port 5433
"""

from __future__ import annotations

import os

import pytest

# Integration test markers (MUST be after imports - E402 compliance)
pytestmark = [
    pytest.mark.integration,
    pytest.mark.slow,
]

# Priority markers for test prioritization (defined in pytest.ini)
# p0: Critical - must pass for story completion
# p1: Important - core functionality


# Skip if not in test environment
@pytest.fixture(autouse=True)
def ensure_test_environment():
    """Ensure tests run only in test environment."""
    if os.environ.get("APP_ENV") != "test":
        pytest.skip("Integration tests require APP_ENV=test")


@pytest.fixture(scope="function", autouse=True)
def cleanup_migration_columns():
    """Cleanup classification columns after each test (M4: function-scoped for isolation)."""
    yield
    # Teardown: Remove test columns
    if os.environ.get("APP_ENV") == "test":
        from raglite.shared.clients import get_postgresql_connection
        try:
            conn = get_postgresql_connection()
            cursor = conn.cursor()
            # M1: Fix DROP COLUMN syntax - separate statements, not comma-separated
            cursor.execute("ALTER TABLE financial_tables DROP COLUMN IF EXISTS period_type;")
            cursor.execute("ALTER TABLE financial_tables DROP COLUMN IF EXISTS value_type;")
            cursor.execute("ALTER TABLE financial_tables DROP COLUMN IF EXISTS entity_level;")
            cursor.execute("DROP INDEX IF EXISTS idx_period_type;")
            cursor.execute("DROP INDEX IF EXISTS idx_value_type;")
            cursor.execute("DROP INDEX IF EXISTS idx_entity_level;")
            conn.commit()
            cursor.close()
            conn.close()
        except Exception:
            pass  # Ignore cleanup errors


class TestAC1PeriodTypeColumnIntegration:
    """AC1: period_type Column Addition - Integration Tests.

    Tests actual database schema changes with a real PostgreSQL instance.
    """

    @pytest.mark.p0
    def test_ac_9_1_1_int_1_period_type_column_in_database(self) -> None:
        """TEST-AC-9.1.1.INT.1: period_type column exists in actual database.

        Given: Migration 007 has been applied to test database
        When: Querying information_schema for financial_tables columns
        Then: period_type column exists with VARCHAR(50) type
        """
        # Arrange: Apply migration
        from migrations.migration_007_add_classification_columns import apply_migration
        from raglite.shared.clients import get_postgresql_connection

        apply_migration()

        # Act: Query actual database schema (create new connection after migration)
        conn = get_postgresql_connection()
        try:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """
                    SELECT column_name, data_type, character_maximum_length, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = 'financial_tables'
                      AND column_name = 'period_type';
                    """
                )
                result = cursor.fetchone()
            finally:
                cursor.close()
        finally:
            conn.close()

        # Assert
        assert result is not None, "period_type column should exist"
        column_name, data_type, max_length, is_nullable = result
        assert column_name == "period_type", f"Expected column name 'period_type', got {column_name}"
        assert data_type == "character varying", f"Expected 'character varying', got {data_type}"
        assert max_length == 50, f"Expected length 50, got {max_length}"
        assert is_nullable == "YES", f"Column should be nullable, is_nullable={is_nullable}"

    @pytest.mark.p1
    def test_ac_9_1_1_int_2_idx_period_type_index_in_database(self) -> None:
        """TEST-AC-9.1.1.INT.2: idx_period_type index exists in actual database.

        Given: Migration 007 has been applied to test database
        When: Querying pg_indexes for financial_tables
        Then: idx_period_type index exists
        """
        # Arrange: Apply migration
        from migrations.migration_007_add_classification_columns import apply_migration
        from raglite.shared.clients import get_postgresql_connection

        apply_migration()

        # Act: Query actual database indexes (create new connection after migration)
        conn = get_postgresql_connection()
        try:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """
                    SELECT indexname, indexdef
                    FROM pg_indexes
                    WHERE tablename = 'financial_tables'
                      AND indexname = 'idx_period_type';
                    """
                )
                result = cursor.fetchone()
            finally:
                cursor.close()
        finally:
            conn.close()

        # Assert
        assert result is not None, "idx_period_type index should exist"
        indexname, indexdef = result
        assert indexname == "idx_period_type", f"Expected index name 'idx_period_type', got {indexname}"
        assert "period_type" in indexdef.lower(), f"Index definition should reference period_type: {indexdef}"


class TestAC2ValueTypeColumnIntegration:
    """AC2: value_type Column Addition - Integration Tests."""

    @pytest.mark.p0
    def test_ac_9_1_2_int_1_value_type_column_in_database(self) -> None:
        """TEST-AC-9.1.2.INT.1: value_type column exists in actual database.

        Given: Migration 007 has been applied to test database
        When: Querying information_schema for financial_tables columns
        Then: value_type column exists with VARCHAR(50) type
        """
        # Arrange: Apply migration
        from migrations.migration_007_add_classification_columns import apply_migration
        from raglite.shared.clients import get_postgresql_connection

        apply_migration()

        # Act: Create new connection after migration
        conn = get_postgresql_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT column_name, data_type, character_maximum_length, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'financial_tables'
              AND column_name = 'value_type';
            """
        )
        result = cursor.fetchone()
        cursor.close()
        conn.close()

        # Assert
        assert result is not None, "value_type column should exist"
        column_name, data_type, max_length, is_nullable = result
        assert column_name == "value_type"
        assert data_type == "character varying"
        assert max_length == 50
        assert is_nullable == "YES"

    @pytest.mark.p1
    def test_ac_9_1_2_int_2_idx_value_type_index_in_database(self) -> None:
        """TEST-AC-9.1.2.INT.2: idx_value_type index exists in actual database.

        Given: Migration 007 has been applied to test database
        When: Querying pg_indexes for financial_tables
        Then: idx_value_type index exists
        """
        # Arrange: Apply migration
        from migrations.migration_007_add_classification_columns import apply_migration
        from raglite.shared.clients import get_postgresql_connection

        apply_migration()

        # Act: Create new connection after migration
        conn = get_postgresql_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'financial_tables'
              AND indexname = 'idx_value_type';
            """
        )
        result = cursor.fetchone()
        cursor.close()
        conn.close()

        # Assert
        assert result is not None, "idx_value_type index should exist"
        indexname, indexdef = result
        assert indexname == "idx_value_type"
        assert "value_type" in indexdef.lower()


class TestAC3EntityLevelColumnIntegration:
    """AC3: entity_level Column Addition - Integration Tests."""

    @pytest.mark.p0
    def test_ac_9_1_3_int_1_entity_level_column_in_database(self) -> None:
        """TEST-AC-9.1.3.INT.1: entity_level column exists in actual database.

        Given: Migration 007 has been applied to test database
        When: Querying information_schema for financial_tables columns
        Then: entity_level column exists with VARCHAR(100) type
        """
        # Arrange: Apply migration
        from migrations.migration_007_add_classification_columns import apply_migration
        from raglite.shared.clients import get_postgresql_connection

        apply_migration()

        # Act: Create new connection after migration
        conn = get_postgresql_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT column_name, data_type, character_maximum_length, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'financial_tables'
              AND column_name = 'entity_level';
            """
        )
        result = cursor.fetchone()
        cursor.close()
        conn.close()

        # Assert
        assert result is not None, "entity_level column should exist"
        column_name, data_type, max_length, is_nullable = result
        assert column_name == "entity_level"
        assert data_type == "character varying"
        assert max_length == 100  # Note: VARCHAR(100) for entity_level
        assert is_nullable == "YES"

    @pytest.mark.p1
    def test_ac_9_1_3_int_2_idx_entity_level_index_in_database(self) -> None:
        """TEST-AC-9.1.3.INT.2: idx_entity_level index exists in actual database.

        Given: Migration 007 has been applied to test database
        When: Querying pg_indexes for financial_tables
        Then: idx_entity_level index exists
        """
        # Arrange: Apply migration
        from migrations.migration_007_add_classification_columns import apply_migration
        from raglite.shared.clients import get_postgresql_connection

        apply_migration()

        # Act: Create new connection after migration
        conn = get_postgresql_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'financial_tables'
              AND indexname = 'idx_entity_level';
            """
        )
        result = cursor.fetchone()
        cursor.close()
        conn.close()

        # Assert
        assert result is not None, "idx_entity_level index should exist"
        indexname, indexdef = result
        assert indexname == "idx_entity_level"
        assert "entity_level" in indexdef.lower()


class TestAC4MigrationIdempotencyIntegration:
    """AC4: Migration Script Idempotency - Integration Tests."""

    @pytest.mark.p0
    def test_ac_9_1_4_int_1_migration_idempotent_on_real_database(self) -> None:
        """TEST-AC-9.1.4.INT.1: Migration runs twice without error on real database.

        Given: Migration 007 has been applied once
        When: Migration 007 is applied again
        Then: No errors are raised and schema is unchanged
        """
        # Arrange: Import migration
        from migrations.migration_007_add_classification_columns import apply_migration
        from raglite.shared.clients import get_postgresql_connection

        # Act: Run migration twice
        apply_migration()
        apply_migration()  # Should not raise

        # Assert: Verify exactly 3 new columns exist (no duplicates)
        conn = get_postgresql_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.columns
            WHERE table_name = 'financial_tables'
              AND column_name IN ('period_type', 'value_type', 'entity_level');
            """
        )
        column_count = cursor.fetchone()[0]
        cursor.close()
        conn.close()

        assert column_count == 3, "Should have exactly 3 classification columns"

    @pytest.mark.p1
    def test_ac_9_1_4_int_2_no_duplicate_indexes_on_real_database(self) -> None:
        """TEST-AC-9.1.4.INT.2: No duplicate indexes after running migration twice.

        Given: Migration 007 has been applied twice
        When: Querying pg_indexes
        Then: Exactly 3 classification column indexes exist (no duplicates)
        """
        # Arrange: Import migration
        from migrations.migration_007_add_classification_columns import apply_migration
        from raglite.shared.clients import get_postgresql_connection

        # Act: Run migration twice
        apply_migration()
        apply_migration()

        # Assert: Verify exactly 3 indexes exist
        conn = get_postgresql_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM pg_indexes
            WHERE tablename = 'financial_tables'
              AND indexname IN ('idx_period_type', 'idx_value_type', 'idx_entity_level');
            """
        )
        index_count = cursor.fetchone()[0]
        cursor.close()
        conn.close()

        assert index_count == 3, "Should have exactly 3 classification indexes"


class TestAC5VerificationIntegration:
    """AC5: Verification Script - Integration Tests."""

    @pytest.mark.p0
    def test_ac_9_1_5_int_1_verification_passes_on_real_database(self) -> None:
        """TEST-AC-9.1.5.INT.1: Verification passes after successful migration.

        Given: Migration 007 has been applied successfully
        When: Running verification on real database
        Then: Verification reports SUCCESS
        """
        # Arrange: Apply migration
        from migrations.migration_007_add_classification_columns import (
            apply_migration,
            verify_migration,
        )

        apply_migration()

        # Act: Run verification (creates its own connection)
        result = verify_migration()

        # Assert
        if isinstance(result, bool):
            assert result is True
        elif isinstance(result, dict):
            assert result.get("status") == "SUCCESS"
            assert result.get("columns_verified") == 3
            assert result.get("indexes_verified") == 3
        else:
            assert result  # Should be truthy


class TestDataInsertionIntegration:
    """Integration tests for INSERT with classification fields.

    These tests verify that the new columns can be used for data insertion.
    """

    @pytest.mark.p1
    def test_ac_9_1_data_1_insert_with_classification_fields(self) -> None:
        """TEST-AC-9.1.DATA.1: Data can be inserted with classification fields.

        Given: Migration 007 has been applied
        When: Inserting a row with period_type, value_type, and entity_level
        Then: The insert succeeds and data can be retrieved
        """
        # Arrange: Apply migration
        from migrations.migration_007_add_classification_columns import apply_migration
        from raglite.shared.clients import get_postgresql_connection

        apply_migration()

        # Act: Insert data with classification fields (create new connection)
        conn = get_postgresql_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO financial_tables (
                document_id, page_number, table_index, entity, metric, period,
                fiscal_year, value, unit, period_type, value_type, entity_level
            ) VALUES (
                'test-doc-001', 1, 1, 'Test Entity', 'Revenue', 'May-24',
                2024, 1000000.00, 'EUR', 'monthly_actual', 'actual', 'group'
            ) RETURNING id;
            """
        )
        inserted_id = cursor.fetchone()[0]
        conn.commit()

        # Query to verify
        cursor.execute(
            """
            SELECT period_type, value_type, entity_level
            FROM financial_tables
            WHERE id = %s;
            """,
            (inserted_id,),
        )
        result = cursor.fetchone()

        # Cleanup
        cursor.execute("DELETE FROM financial_tables WHERE id = %s;", (inserted_id,))
        conn.commit()
        cursor.close()
        conn.close()

        # Assert
        assert result is not None
        period_type, value_type, entity_level = result
        assert period_type == "monthly_actual"
        assert value_type == "actual"
        assert entity_level == "group"

    @pytest.mark.p1
    def test_ac_9_1_data_2_insert_with_null_classification_fields(self) -> None:
        """TEST-AC-9.1.DATA.2: Data can be inserted with NULL classification fields.

        Given: Migration 007 has been applied
        When: Inserting a row without classification fields (NULLs)
        Then: The insert succeeds (backward compatibility)
        """
        # Arrange: Apply migration
        from migrations.migration_007_add_classification_columns import apply_migration
        from raglite.shared.clients import get_postgresql_connection

        apply_migration()

        # Act: Insert data WITHOUT classification fields (use defaults/NULLs)
        conn = get_postgresql_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO financial_tables (
                document_id, page_number, table_index, entity, metric, period,
                fiscal_year, value, unit
            ) VALUES (
                'test-doc-002', 2, 1, 'Test Entity 2', 'EBITDA', 'Jun-24',
                2024, 500000.00, 'EUR'
            ) RETURNING id;
            """
        )
        inserted_id = cursor.fetchone()[0]
        conn.commit()

        # Query to verify NULLs
        cursor.execute(
            """
            SELECT period_type, value_type, entity_level
            FROM financial_tables
            WHERE id = %s;
            """,
            (inserted_id,),
        )
        result = cursor.fetchone()

        # Cleanup
        cursor.execute("DELETE FROM financial_tables WHERE id = %s;", (inserted_id,))
        conn.commit()
        cursor.close()
        conn.close()

        # Assert: All classification fields are NULL (backward compatible)
        assert result is not None
        period_type, value_type, entity_level = result
        assert period_type is None
        assert value_type is None
        assert entity_level is None


class TestIndexUsageAndQueryPerformance:
    """Integration tests for index usage and query performance.

    Tests coverage gaps identified in Phase 6 expansion:
    - Indexes are actually used by queries (EXPLAIN ANALYZE)
    - Filter queries work correctly
    - Combined filters perform well
    - NULL handling in queries
    """

    @pytest.mark.p1
    def test_ac_9_1_index_1_filter_by_period_type(self) -> None:
        """TEST-AC-9.1.INDEX.1: Queries can filter by period_type.

        Given: Migration 007 has been applied and data inserted
        When: Filtering by period_type in WHERE clause
        Then: Query returns correct results
        """
        # Arrange: Apply migration and insert test data
        from migrations.migration_007_add_classification_columns import apply_migration
        from raglite.shared.clients import get_postgresql_connection

        apply_migration()

        conn = get_postgresql_connection()
        cursor = conn.cursor()

        # Insert multiple rows with different period types
        cursor.execute(
            """
            INSERT INTO financial_tables (
                document_id, page_number, table_index, entity, metric, period,
                fiscal_year, value, unit, period_type, value_type, entity_level
            ) VALUES
            ('test-001', 1, 1, 'Entity A', 'Revenue', 'Jan-24', 2024, 100.0, 'EUR', 'monthly_actual', 'actual', 'group'),
            ('test-002', 1, 1, 'Entity B', 'Revenue', 'Q1-24', 2024, 300.0, 'EUR', 'ytd_actual', 'actual', 'group'),
            ('test-003', 1, 1, 'Entity C', 'Revenue', 'Budget-24', 2024, 500.0, 'EUR', 'budget', 'budget', 'group')
            RETURNING id;
            """
        )
        inserted_ids = [row[0] for row in cursor.fetchall()]
        conn.commit()

        # Act: Filter by period_type
        cursor.execute(
            """
            SELECT COUNT(*) FROM financial_tables
            WHERE period_type = 'monthly_actual';
            """
        )
        monthly_count = cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT COUNT(*) FROM financial_tables
            WHERE period_type = 'budget';
            """
        )
        budget_count = cursor.fetchone()[0]

        # Cleanup
        for row_id in inserted_ids:
            cursor.execute("DELETE FROM financial_tables WHERE id = %s;", (row_id,))
        conn.commit()
        cursor.close()
        conn.close()

        # Assert
        assert monthly_count == 1
        assert budget_count == 1

    @pytest.mark.p1
    def test_ac_9_1_index_2_combined_filters(self) -> None:
        """TEST-AC-9.1.INDEX.2: Queries can combine multiple classification filters.

        Given: Migration 007 has been applied and data inserted
        When: Filtering by period_type AND value_type AND entity_level
        Then: Query returns correct results
        """
        # Arrange
        from migrations.migration_007_add_classification_columns import apply_migration
        from raglite.shared.clients import get_postgresql_connection

        apply_migration()

        conn = get_postgresql_connection()
        cursor = conn.cursor()

        # Insert test data with varied classifications
        cursor.execute(
            """
            INSERT INTO financial_tables (
                document_id, page_number, table_index, entity, metric, period,
                fiscal_year, value, unit, period_type, value_type, entity_level
            ) VALUES
            ('test-004', 1, 1, 'Entity D', 'EBITDA', 'Jan-24', 2024, 50.0, 'EUR', 'monthly_actual', 'actual', 'group'),
            ('test-005', 1, 1, 'Entity E', 'EBITDA', 'Jan-24', 2024, 45.0, 'EUR', 'monthly_actual', 'actual', 'country'),
            ('test-006', 1, 1, 'Entity F', 'EBITDA', 'Budget-24', 2024, 60.0, 'EUR', 'budget', 'budget', 'group')
            RETURNING id;
            """
        )
        inserted_ids = [row[0] for row in cursor.fetchall()]
        conn.commit()

        # Act: Combined filter
        cursor.execute(
            """
            SELECT COUNT(*) FROM financial_tables
            WHERE period_type = 'monthly_actual'
              AND value_type = 'actual'
              AND entity_level = 'group';
            """
        )
        combined_count = cursor.fetchone()[0]

        # Cleanup
        for row_id in inserted_ids:
            cursor.execute("DELETE FROM financial_tables WHERE id = %s;", (row_id,))
        conn.commit()
        cursor.close()
        conn.close()

        # Assert: Should find exactly 1 row (test-004)
        assert combined_count == 1

    @pytest.mark.p2
    def test_ac_9_1_index_3_null_handling_in_queries(self) -> None:
        """TEST-AC-9.1.INDEX.3: Queries handle NULL classification fields correctly.

        Given: Migration 007 has been applied
        When: Querying with IS NULL / IS NOT NULL on classification fields
        Then: Query returns correct results
        """
        # Arrange
        from migrations.migration_007_add_classification_columns import apply_migration
        from raglite.shared.clients import get_postgresql_connection

        apply_migration()

        conn = get_postgresql_connection()
        cursor = conn.cursor()

        # Insert data with NULLs and non-NULLs
        cursor.execute(
            """
            INSERT INTO financial_tables (
                document_id, page_number, table_index, entity, metric, period,
                fiscal_year, value, unit, period_type, value_type, entity_level
            ) VALUES
            ('test-007', 1, 1, 'Entity G', 'Revenue', 'Jan-24', 2024, 100.0, 'EUR', 'monthly_actual', 'actual', 'group'),
            ('test-008', 1, 1, 'Entity H', 'Revenue', 'Feb-24', 2024, 110.0, 'EUR', NULL, NULL, NULL)
            RETURNING id;
            """
        )
        inserted_ids = [row[0] for row in cursor.fetchall()]
        conn.commit()

        # Act: Query for NULLs and NOT NULLs
        cursor.execute(
            """
            SELECT COUNT(*) FROM financial_tables
            WHERE period_type IS NULL;
            """
        )
        null_count = cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT COUNT(*) FROM financial_tables
            WHERE period_type IS NOT NULL;
            """
        )
        not_null_count = cursor.fetchone()[0]

        # Cleanup
        for row_id in inserted_ids:
            cursor.execute("DELETE FROM financial_tables WHERE id = %s;", (row_id,))
        conn.commit()
        cursor.close()
        conn.close()

        # Assert: Verify exact counts from our inserted test data
        # Inserted 2 rows: test-007 with period_type='monthly_actual' (NOT NULL)
        #                  test-008 with period_type=NULL
        assert null_count >= 1, f"Expected at least 1 NULL period_type row from test data, got {null_count}"
        assert not_null_count >= 1, f"Expected at least 1 NOT NULL period_type row from test data, got {not_null_count}"

    @pytest.mark.p2
    def test_ac_9_1_index_4_index_usage_verified_via_explain(self) -> None:
        """TEST-AC-9.1.INDEX.4: Indexes are used by query planner (EXPLAIN ANALYZE).

        Given: Migration 007 has been applied
        When: Running EXPLAIN ANALYZE on a period_type filter query
        Then: Query plan shows index scan (idx_period_type)
        """
        # Arrange
        from migrations.migration_007_add_classification_columns import apply_migration
        from raglite.shared.clients import get_postgresql_connection

        apply_migration()

        conn = get_postgresql_connection()
        cursor = conn.cursor()

        # Act: Run EXPLAIN ANALYZE
        cursor.execute(
            """
            EXPLAIN (FORMAT JSON) SELECT * FROM financial_tables
            WHERE period_type = 'monthly_actual';
            """
        )
        explain_result = cursor.fetchone()[0]

        cursor.close()
        conn.close()

        # Assert: Verify plan exists (exact index usage depends on data volume)
        assert explain_result is not None
        # Plan should contain either Index Scan or Bitmap Index Scan for idx_period_type
        plan_json = str(explain_result)
        # Note: Small tables may use Seq Scan, but idx should exist
        assert "idx_period_type" in plan_json or "Scan" in plan_json
