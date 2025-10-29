#!/usr/bin/env python3
"""Apply hybrid entity model schema migration.

This script implements Migration 001: Hybrid Entity Model
- Adds entity_normalized column to financial_tables
- Creates entity_mappings dimension table
- Installs pg_trgm extension for fuzzy matching
- Creates all necessary indexes

Based on production patterns from FinRAG, Bloomberg NLP, and TableRAG.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from raglite.shared.clients import get_postgresql_connection
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


def apply_migration() -> None:
    """Apply Migration 001: Hybrid Entity Model schema changes."""
    logger.info("=" * 80)
    logger.info("MIGRATION 001: Hybrid Entity Model")
    logger.info("=" * 80)
    logger.info("")

    conn = get_postgresql_connection()
    cursor = conn.cursor()

    try:
        # Step 1: Install pg_trgm extension
        logger.info("Step 1/5: Installing pg_trgm extension...")
        cursor.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
        conn.commit()
        logger.info("✅ pg_trgm extension installed")
        logger.info("")

        # Step 2: Add entity_normalized column
        logger.info("Step 2/5: Adding entity_normalized column to financial_tables...")
        cursor.execute("""
            ALTER TABLE financial_tables
            ADD COLUMN IF NOT EXISTS entity_normalized VARCHAR(255);
        """)
        conn.commit()
        logger.info("✅ entity_normalized column added")
        logger.info("")

        # Step 3: Create entity_mappings dimension table
        logger.info("Step 3/5: Creating entity_mappings dimension table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entity_mappings (
                entity_id SERIAL PRIMARY KEY,
                canonical_name VARCHAR(255) NOT NULL,
                raw_mentions TEXT[],
                entity_type VARCHAR(50),
                section_context VARCHAR(500),
                created_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(canonical_name)
            );
        """)
        conn.commit()
        logger.info("✅ entity_mappings table created")
        logger.info("")

        # Step 4: Create indexes for exact matching
        logger.info("Step 4/5: Creating indexes for exact matching...")

        # Index on entity_normalized
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_entity_normalized
            ON financial_tables(entity_normalized)
            WHERE entity_normalized IS NOT NULL;
        """)

        # Index on entity_mappings.raw_mentions (GIN array index)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_entity_mappings_raw
            ON entity_mappings USING GIN(raw_mentions);
        """)

        conn.commit()
        logger.info("✅ Exact match indexes created")
        logger.info("")

        # Step 5: Create GIN indexes for fuzzy matching
        logger.info("Step 5/5: Creating GIN indexes for fuzzy text search...")

        # GIN trigram index on entity (raw)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_entity_trgm
            ON financial_tables USING GIN (entity gin_trgm_ops)
            WHERE entity IS NOT NULL;
        """)

        # GIN trigram index on entity_normalized
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_entity_normalized_trgm
            ON financial_tables USING GIN (entity_normalized gin_trgm_ops)
            WHERE entity_normalized IS NOT NULL;
        """)

        conn.commit()
        logger.info("✅ Fuzzy match indexes created (pg_trgm)")
        logger.info("")

        # Verify migration
        logger.info("=" * 80)
        logger.info("VERIFICATION")
        logger.info("=" * 80)

        # Check entity_normalized column exists
        cursor.execute("""
            SELECT COUNT(*)
            FROM information_schema.columns
            WHERE table_name = 'financial_tables'
              AND column_name = 'entity_normalized';
        """)
        column_exists = cursor.fetchone()[0] == 1
        logger.info(f"entity_normalized column: {'✅ EXISTS' if column_exists else '❌ MISSING'}")

        # Check entity_mappings table exists
        cursor.execute("""
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_name = 'entity_mappings';
        """)
        table_exists = cursor.fetchone()[0] == 1
        logger.info(f"entity_mappings table: {'✅ EXISTS' if table_exists else '❌ MISSING'}")

        # Check pg_trgm extension
        cursor.execute("""
            SELECT COUNT(*)
            FROM pg_extension
            WHERE extname = 'pg_trgm';
        """)
        extension_exists = cursor.fetchone()[0] == 1
        logger.info(f"pg_trgm extension: {'✅ INSTALLED' if extension_exists else '❌ MISSING'}")

        # Count indexes
        cursor.execute("""
            SELECT COUNT(*)
            FROM pg_indexes
            WHERE tablename IN ('financial_tables', 'entity_mappings')
              AND indexname IN (
                  'idx_entity_normalized',
                  'idx_entity_trgm',
                  'idx_entity_normalized_trgm',
                  'idx_entity_mappings_raw'
              );
        """)
        index_count = cursor.fetchone()[0]
        logger.info(f"Indexes created: {index_count}/4 {'✅' if index_count == 4 else '❌'}")
        logger.info("")

        # Test fuzzy matching functionality
        logger.info("=" * 80)
        logger.info("FUZZY MATCHING TEST")
        logger.info("=" * 80)

        # Test similarity function
        cursor.execute("""
            SELECT similarity('Portugal Cement', 'Portugal') as score;
        """)
        similarity_score = cursor.fetchone()[0]
        logger.info(
            f"Similarity test: similarity('Portugal Cement', 'Portugal') = {similarity_score:.3f}"
        )
        logger.info(f"Fuzzy matching: {'✅ WORKING' if similarity_score > 0 else '❌ FAILED'}")
        logger.info("")

        # Final status
        logger.info("=" * 80)
        logger.info("MIGRATION STATUS")
        logger.info("=" * 80)

        if column_exists and table_exists and extension_exists and index_count == 4:
            logger.info("✅ Migration 001 completed successfully!")
            logger.info("")
            logger.info("Next steps:")
            logger.info("  1. Run: python scripts/analyze-and-normalize-entities.py")
            logger.info("  2. Run: python scripts/populate-entity-normalized.py")
            logger.info("  3. Update text-to-SQL in raglite/retrieval/sql_table_search.py")
            logger.info("  4. Run: python scripts/validate-story-2.13-hybrid.py")
        else:
            logger.error("❌ Migration 001 incomplete - see verification above")
            sys.exit(1)

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    apply_migration()
