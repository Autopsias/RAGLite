#!/usr/bin/env python3
"""Populate entity_normalized column based on entity_mappings.

This script implements Phase 3 of Migration 001: Hybrid Entity Model.
- Updates entity_normalized column for all rows matching entity_mappings
- Verifies coverage matches expectations (~74.2%)
- Prepares data for hybrid entity search in text-to-SQL
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from raglite.shared.clients import get_postgresql_connection
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


def main() -> None:
    """Populate entity_normalized column using entity_mappings."""
    logger.info("=" * 80)
    logger.info("POPULATE ENTITY_NORMALIZED COLUMN")
    logger.info("=" * 80)
    logger.info("")

    conn = get_postgresql_connection()
    cursor = conn.cursor()

    try:
        # Step 1: Update entity_normalized for mapped entities
        logger.info("Step 1/2: Updating entity_normalized for mapped entities...")
        logger.info("")

        # Get all mappings
        cursor.execute(
            """
            SELECT canonical_name, raw_mentions
            FROM entity_mappings
            ORDER BY canonical_name;
        """
        )
        mappings = cursor.fetchall()

        if not mappings:
            logger.warning("⚠️ No entity mappings found in entity_mappings table")
            logger.info("")
            logger.info("Run this first: uv run python scripts/analyze-and-normalize-entities.py")
            sys.exit(1)

        total_updated = 0
        for canonical_name, raw_mentions in mappings:
            # Update all rows where entity matches any alias
            cursor.execute(
                """
                UPDATE financial_tables
                SET entity_normalized = %s
                WHERE entity = ANY(%s)
                  AND entity_normalized IS NULL;
            """,
                (canonical_name, raw_mentions),
            )

            rows_updated = cursor.rowcount
            total_updated += rows_updated

            logger.info(f"  {canonical_name:30} → {rows_updated:6,} rows updated")

        conn.commit()
        logger.info("")
        logger.info(f"✅ Total rows updated: {total_updated:,}")
        logger.info("")

        # Step 2: Verify coverage
        logger.info("Step 2/2: Verifying coverage...")
        logger.info("")

        cursor.execute("SELECT COUNT(*) FROM financial_tables")
        total_rows = cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM financial_tables
            WHERE entity_normalized IS NOT NULL
        """
        )
        normalized_rows = cursor.fetchone()[0]

        coverage_pct = (normalized_rows / total_rows * 100) if total_rows > 0 else 0

        logger.info(f"Total rows: {total_rows:,}")
        logger.info(f"Normalized rows: {normalized_rows:,}")
        logger.info(f"Coverage: {coverage_pct:.1f}%")
        logger.info("")

        # Expected coverage check
        expected_coverage = 74.2
        if coverage_pct >= expected_coverage - 5:
            logger.info(f"✅ Coverage within expected range (~{expected_coverage}%)")
        else:
            logger.warning(f"⚠️ Coverage lower than expected ({expected_coverage}%)")

        logger.info("")

        # Show entity distribution
        logger.info("Entity distribution:")
        cursor.execute(
            """
            SELECT entity_normalized, COUNT(*) as count
            FROM financial_tables
            WHERE entity_normalized IS NOT NULL
            GROUP BY entity_normalized
            ORDER BY COUNT(*) DESC;
        """
        )
        distribution = cursor.fetchall()

        for entity, count in distribution:
            logger.info(f"  {entity:30} {count:6,} rows")

        logger.info("")
        logger.info("=" * 80)
        logger.info("SUCCESS")
        logger.info("=" * 80)
        logger.info("✅ Entity normalization complete!")
        logger.info("")
        logger.info("Next step:")
        logger.info("  Update text-to-SQL in raglite/retrieval/sql_table_search.py")
        logger.info("  Add hybrid entity matching with fuzzy search")

    except Exception as e:
        logger.error(f"❌ Population failed: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()
