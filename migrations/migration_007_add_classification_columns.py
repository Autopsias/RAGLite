#!/usr/bin/env python3
"""Apply Migration 007: Add Classification Columns.

This script implements Migration 007: Add Classification Columns to financial_tables
- Adds period_type column (VARCHAR 50, nullable)
- Adds value_type column (VARCHAR 50, nullable)
- Adds entity_level column (VARCHAR 100, nullable)
- Creates indexes on all three columns for query performance
- Uses IF NOT EXISTS guards for idempotency

Foundation for Epic 9: Data Quality at Ingestion

ROLLBACK INSTRUCTIONS:
If migration needs to be reverted, run the following SQL:

    DROP INDEX IF EXISTS idx_entity_level;
    DROP INDEX IF EXISTS idx_value_type;
    DROP INDEX IF EXISTS idx_period_type;
    ALTER TABLE financial_tables DROP COLUMN IF EXISTS entity_level;
    ALTER TABLE financial_tables DROP COLUMN IF EXISTS value_type;
    ALTER TABLE financial_tables DROP COLUMN IF EXISTS period_type;
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from raglite.shared.clients import get_postgresql_connection
from raglite.shared.logging import get_logger
from raglite.shared.safety import SafetyGuard

logger = get_logger(__name__)


def apply_migration() -> None:
    """Apply Migration 007: Add classification columns to financial_tables."""
    logger.info("=" * 80)
    logger.info("MIGRATION 007: Add Classification Columns")
    logger.info("=" * 80)

    # H1: Add SafetyGuard validation before database operations
    guard = SafetyGuard()
    guard.block_destructive_on_production("migration_007")

    conn = get_postgresql_connection()
    cursor = conn.cursor()

    try:
        # Step 1: Add period_type column
        logger.info("Step 1/6: Adding period_type column to financial_tables...")
        cursor.execute(
            """
            ALTER TABLE financial_tables
            ADD COLUMN IF NOT EXISTS period_type VARCHAR(50);
        """
        )
        conn.commit()
        logger.info("✅ period_type column added")

        # Step 2: Add value_type column
        logger.info("Step 2/6: Adding value_type column to financial_tables...")
        cursor.execute(
            """
            ALTER TABLE financial_tables
            ADD COLUMN IF NOT EXISTS value_type VARCHAR(50);
        """
        )
        conn.commit()
        logger.info("✅ value_type column added")

        # Step 3: Add entity_level column
        logger.info("Step 3/6: Adding entity_level column to financial_tables...")
        cursor.execute(
            """
            ALTER TABLE financial_tables
            ADD COLUMN IF NOT EXISTS entity_level VARCHAR(100);
        """
        )
        conn.commit()
        logger.info("✅ entity_level column added")

        # Step 4: Create index on period_type
        logger.info("Step 4/6: Creating index idx_period_type...")
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_period_type
            ON financial_tables(period_type);
        """
        )
        conn.commit()
        logger.info("✅ idx_period_type index created")

        # Step 5: Create index on value_type
        logger.info("Step 5/6: Creating index idx_value_type...")
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_value_type
            ON financial_tables(value_type);
        """
        )
        conn.commit()
        logger.info("✅ idx_value_type index created")

        # Step 6: Create index on entity_level
        logger.info("Step 6/6: Creating index idx_entity_level...")
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_entity_level
            ON financial_tables(entity_level);
        """
        )
        conn.commit()
        logger.info("✅ idx_entity_level index created")

        # Verify migration
        logger.info("=" * 80)
        logger.info("VERIFICATION")
        logger.info("=" * 80)

        # Check period_type column exists
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.columns
            WHERE table_name = 'financial_tables'
              AND column_name = 'period_type';
        """
        )
        period_type_exists = cursor.fetchone()[0] == 1
        logger.info(f"period_type column: {'✅ EXISTS' if period_type_exists else '❌ MISSING'}")

        # Check value_type column exists
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.columns
            WHERE table_name = 'financial_tables'
              AND column_name = 'value_type';
        """
        )
        value_type_exists = cursor.fetchone()[0] == 1
        logger.info(f"value_type column: {'✅ EXISTS' if value_type_exists else '❌ MISSING'}")

        # Check entity_level column exists
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.columns
            WHERE table_name = 'financial_tables'
              AND column_name = 'entity_level';
        """
        )
        entity_level_exists = cursor.fetchone()[0] == 1
        logger.info(f"entity_level column: {'✅ EXISTS' if entity_level_exists else '❌ MISSING'}")

        # Count indexes
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM pg_indexes
            WHERE tablename = 'financial_tables'
              AND indexname IN ('idx_period_type', 'idx_value_type', 'idx_entity_level');
        """
        )
        index_count = cursor.fetchone()[0]
        logger.info(f"Indexes created: {index_count}/3 {'✅' if index_count == 3 else '❌'}")

        # Final status
        logger.info("=" * 80)
        logger.info("MIGRATION STATUS")
        logger.info("=" * 80)

        if period_type_exists and value_type_exists and entity_level_exists and index_count == 3:
            logger.info("✅ Migration 007 completed successfully!")
            logger.info("Next steps:")
            logger.info("  1. Story 9.2: Implement period_type classification")
            logger.info("  2. Story 9.3: Implement value_type classification")
            logger.info("  3. Story 9.4: Implement entity_level classification")
        else:
            logger.error("❌ Migration 007 incomplete - see verification above")

    except Exception as e:
        logger.exception(
            "❌ Migration failed", extra={"error": str(e), "error_type": type(e).__name__}
        )
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def verify_migration() -> dict:
    """Verify Migration 007 was applied correctly.

    Returns:
        dict: Verification result with status and counts
    """
    # H2: Wrap entire function in try-except to catch connection errors
    try:
        conn = get_postgresql_connection()
        cursor = conn.cursor()

        try:
            # Check all three columns exist
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM information_schema.columns
                WHERE table_name = 'financial_tables'
                  AND column_name = 'period_type';
            """
            )
            period_type_exists = cursor.fetchone()[0] == 1

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM information_schema.columns
                WHERE table_name = 'financial_tables'
                  AND column_name = 'value_type';
            """
            )
            value_type_exists = cursor.fetchone()[0] == 1

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM information_schema.columns
                WHERE table_name = 'financial_tables'
                  AND column_name = 'entity_level';
            """
            )
            entity_level_exists = cursor.fetchone()[0] == 1

            # Check all three indexes exist
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM pg_indexes
                WHERE tablename = 'financial_tables'
                  AND indexname IN ('idx_period_type', 'idx_value_type', 'idx_entity_level');
            """
            )
            index_count = cursor.fetchone()[0]

            columns_verified = sum([period_type_exists, value_type_exists, entity_level_exists])
            all_present = columns_verified == 3 and index_count == 3

            return {
                "status": "SUCCESS" if all_present else "FAILED",
                "columns_verified": columns_verified,
                "indexes_verified": index_count,
            }

        except Exception as e:
            logger.exception(f"❌ Verification query failed: {e}")
            return {
                "status": "FAILED",
                "columns_verified": 0,
                "indexes_verified": 0,
            }
        finally:
            cursor.close()
            conn.close()

    except Exception as e:
        # H2: Catch connection errors and return FAILED status
        logger.exception(f"❌ Connection failed: {e}")
        return {
            "status": "FAILED",
            "columns_verified": 0,
            "indexes_verified": 0,
        }


if __name__ == "__main__":
    apply_migration()
