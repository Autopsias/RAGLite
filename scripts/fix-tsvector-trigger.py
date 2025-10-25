"""Fix missing content_tsv trigger and backfill existing data.

ROOT CAUSE: init-postgresql.py created the content_tsv column but never created
the trigger to populate it with to_tsvector('english', content). Both the migration
script and ingestion pipeline assumed the trigger existed (comments: "will be generated
by trigger"), but it was never created.

This script:
1. Creates the missing trigger function for automatic tsvector population
2. Creates the trigger for INSERT and UPDATE operations
3. Backfills all existing NULL content_tsv values

Usage:
    python scripts/fix-tsvector-trigger.py
"""

import logging
import sys

import psycopg2

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def fix_tsvector_trigger(
    host: str = "localhost",
    port: int = 5432,
    dbname: str = "raglite",
    user: str = "raglite",
    password: str = "raglite",
) -> None:
    """Create missing tsvector trigger and backfill existing data.

    Args:
        host: PostgreSQL host
        port: PostgreSQL port
        dbname: Database name
        user: Database user
        password: Database password

    Raises:
        psycopg2.Error: If database connection or trigger creation fails
    """
    conn = None
    cursor = None

    try:
        # Connect to PostgreSQL
        logger.info(f"Connecting to PostgreSQL at {host}:{port}/{dbname}")
        conn = psycopg2.connect(host=host, port=port, dbname=dbname, user=user, password=password)
        cursor = conn.cursor()

        # Step 1: Create trigger function
        logger.info("Creating trigger function for content_tsv auto-population...")
        cursor.execute("""
            CREATE OR REPLACE FUNCTION update_content_tsv()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.content_tsv := to_tsvector('english', COALESCE(NEW.content, ''));
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """)
        conn.commit()
        logger.info("✓ Trigger function created: update_content_tsv()")

        # Step 2: Create trigger for INSERT and UPDATE
        logger.info("Creating trigger on financial_chunks table...")
        cursor.execute("""
            DROP TRIGGER IF EXISTS trg_update_content_tsv ON financial_chunks;

            CREATE TRIGGER trg_update_content_tsv
            BEFORE INSERT OR UPDATE ON financial_chunks
            FOR EACH ROW
            EXECUTE FUNCTION update_content_tsv();
        """)
        conn.commit()
        logger.info("✓ Trigger created: trg_update_content_tsv")

        # Step 3: Check how many rows need backfilling
        logger.info("Checking existing NULL content_tsv rows...")
        cursor.execute("""
            SELECT COUNT(*) FROM financial_chunks WHERE content_tsv IS NULL;
        """)
        null_count = cursor.fetchone()[0]
        logger.info(f"Found {null_count} rows with NULL content_tsv")

        if null_count > 0:
            # Step 4: Backfill existing NULL content_tsv values
            logger.info(f"Backfilling {null_count} existing rows...")
            cursor.execute("""
                UPDATE financial_chunks
                SET content_tsv = to_tsvector('english', content)
                WHERE content_tsv IS NULL;
            """)
            conn.commit()
            logger.info(f"✓ Backfilled {null_count} rows with tsvector values")

            # Step 5: Verify backfill
            logger.info("Verifying backfill...")
            cursor.execute("""
                SELECT
                    COUNT(*) as total,
                    COUNT(content_tsv) as populated,
                    COUNT(*) - COUNT(content_tsv) as still_null
                FROM financial_chunks;
            """)
            result = cursor.fetchone()
            total, populated, still_null = result

            logger.info("=" * 60)
            logger.info("VERIFICATION RESULTS")
            logger.info("=" * 60)
            logger.info(f"Total rows: {total}")
            logger.info(f"Populated: {populated}")
            logger.info(f"Still NULL: {still_null}")

            if still_null == 0:
                logger.info("✅ SUCCESS: All content_tsv values populated!")
            else:
                logger.warning(f"⚠️  WARNING: {still_null} rows still have NULL content_tsv")

            # Step 6: Test full-text search
            logger.info("\nTesting full-text search...")
            test_queries = ["variable cost", "EBITDA", "thermal energy"]

            for query in test_queries:
                cursor.execute(
                    """
                    SELECT COUNT(*) as matches
                    FROM financial_chunks
                    WHERE content_tsv @@ plainto_tsquery('english', %s);
                """,
                    (query,),
                )
                matches = cursor.fetchone()[0]
                logger.info(f"  '{query}': {matches} matches")

        else:
            logger.info("✅ All content_tsv values already populated (nothing to backfill)")

        logger.info("=" * 60)
        logger.info("✅ TSVECTOR TRIGGER FIX COMPLETE!")
        logger.info("=" * 60)
        logger.info("")
        logger.info("Next steps:")
        logger.info("1. Re-run accuracy tests to measure improvement")
        logger.info("2. If still <70%, investigate query classification logic")
        logger.info("3. Consider testing with table-only restriction")

    except psycopg2.Error as e:
        logger.error(f"❌ Database error: {e}")
        if conn:
            conn.rollback()
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        if conn:
            conn.rollback()
        sys.exit(1)
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
            logger.info("Database connection closed")


if __name__ == "__main__":
    fix_tsvector_trigger()
