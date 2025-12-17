#!/usr/bin/env python3
"""Backfill entity_normalized column in financial_tables.

Story 6.28: Populates entity_normalized column using entity_mappings table
and Python fuzzy matching for unmapped entities.

Usage:
    uv run python scripts/backfill_entity_normalized.py [--dry-run]
"""

import argparse
import logging
import sys
from typing import Any

import psycopg2

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def get_connection() -> Any:
    """Get PostgreSQL connection."""
    return psycopg2.connect(
        host="localhost",
        port=5432,
        database="raglite",
        user="raglite",
        password="raglite",
    )


def backfill_from_mappings(cursor: Any, dry_run: bool = False) -> int:
    """Backfill entity_normalized using entity_mappings table.

    Args:
        cursor: Database cursor
        dry_run: If True, don't commit changes

    Returns:
        Number of rows updated
    """
    # Update using exact case-insensitive match
    update_sql = """
    UPDATE financial_tables ft
    SET entity_normalized = em.canonical_entity
    FROM entity_mappings em
    WHERE LOWER(TRIM(ft.entity)) = LOWER(TRIM(em.raw_entity))
      AND ft.entity_normalized IS NULL
    """

    if dry_run:
        # Count how many would be updated
        count_sql = """
        SELECT COUNT(*)
        FROM financial_tables ft
        JOIN entity_mappings em ON LOWER(TRIM(ft.entity)) = LOWER(TRIM(em.raw_entity))
        WHERE ft.entity_normalized IS NULL
        """
        cursor.execute(count_sql)
        count = cursor.fetchone()[0]
        logger.info(f"[DRY RUN] Would update {count} rows from entity_mappings")
        return count

    cursor.execute(update_sql)
    updated = cursor.rowcount
    logger.info(f"Updated {updated} rows using entity_mappings table")
    return updated


def backfill_unmapped_entities(cursor: Any, dry_run: bool = False) -> int:
    """Set entity_normalized to original entity for unmapped rows.

    For entities not in the mappings table, we set entity_normalized
    to the original entity value (preserving case), truncated to 100 chars.

    Args:
        cursor: Database cursor
        dry_run: If True, don't commit changes

    Returns:
        Number of rows updated
    """
    # Set unmapped entities to their original value (truncated to 100 chars)
    update_sql = """
    UPDATE financial_tables
    SET entity_normalized = LEFT(TRIM(entity), 100)
    WHERE entity_normalized IS NULL
      AND entity IS NOT NULL
      AND TRIM(entity) != ''
    """

    if dry_run:
        count_sql = """
        SELECT COUNT(*)
        FROM financial_tables
        WHERE entity_normalized IS NULL
          AND entity IS NOT NULL
          AND TRIM(entity) != ''
        """
        cursor.execute(count_sql)
        count = cursor.fetchone()[0]
        logger.info(f"[DRY RUN] Would set {count} unmapped rows to original entity")
        return count

    cursor.execute(update_sql)
    updated = cursor.rowcount
    logger.info(f"Set {updated} unmapped rows to original entity value")
    return updated


def get_stats(cursor: Any) -> dict[str, Any]:
    """Get statistics about entity normalization."""
    stats = {}

    # Total rows
    cursor.execute("SELECT COUNT(*) FROM financial_tables")
    stats["total_rows"] = cursor.fetchone()[0]

    # Rows with entity_normalized set
    cursor.execute("SELECT COUNT(*) FROM financial_tables WHERE entity_normalized IS NOT NULL")
    stats["normalized_rows"] = cursor.fetchone()[0]

    # Unique canonical entities
    cursor.execute(
        "SELECT COUNT(DISTINCT entity_normalized) FROM financial_tables WHERE entity_normalized IS NOT NULL"
    )
    stats["unique_canonical"] = cursor.fetchone()[0]

    # Top 10 canonical entities
    cursor.execute("""
        SELECT entity_normalized, COUNT(*) as cnt
        FROM financial_tables
        WHERE entity_normalized IS NOT NULL
        GROUP BY entity_normalized
        ORDER BY cnt DESC
        LIMIT 10
    """)
    stats["top_entities"] = cursor.fetchall()

    return stats


def main():
    parser = argparse.ArgumentParser(description="Backfill entity_normalized column")
    parser.add_argument("--dry-run", action="store_true", help="Don't commit changes")
    args = parser.parse_args()

    logger.info("Starting entity_normalized backfill")
    if args.dry_run:
        logger.info("DRY RUN MODE - no changes will be committed")

    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Check if entity_normalized column exists
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'financial_tables'
            AND column_name = 'entity_normalized'
        """)
        if not cursor.fetchone():
            logger.error("entity_normalized column does not exist. Run migration 005 first.")
            sys.exit(1)

        # Get initial stats
        initial_stats = get_stats(cursor)
        logger.info(
            f"Initial state: {initial_stats['normalized_rows']}/{initial_stats['total_rows']} rows normalized"
        )

        # Step 1: Backfill from entity_mappings table
        mapped_count = backfill_from_mappings(cursor, args.dry_run)

        # Step 2: Handle unmapped entities
        unmapped_count = backfill_unmapped_entities(cursor, args.dry_run)

        if not args.dry_run:
            conn.commit()
            logger.info("Changes committed")

            # Get final stats
            final_stats = get_stats(cursor)
            logger.info(
                f"Final state: {final_stats['normalized_rows']}/{final_stats['total_rows']} rows normalized"
            )
            logger.info(f"Unique canonical entities: {final_stats['unique_canonical']}")
            logger.info("Top 10 canonical entities:")
            for entity, count in final_stats["top_entities"]:
                logger.info(f"  {entity}: {count} rows")

        total_updated = mapped_count + unmapped_count
        logger.info(
            f"Backfill complete: {total_updated} total rows {'would be ' if args.dry_run else ''}updated"
        )

    except Exception as e:
        logger.error(f"Error during backfill: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()
