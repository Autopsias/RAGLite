#!/usr/bin/env python3
"""Fix GROUP Turnover unit mixing (kEUR vs M EUR).

Fix 2026-02-02: GROUP Turnover has unit mixing where some values are in kEUR
and others in M EUR. This causes 63% MAPE from scale inconsistency.

This script normalizes all kEUR values to M EUR for consistency.

Usage:
    # Dry run (show what would be updated):
    python scripts/fix_group_turnover_units.py --dry-run

    # Execute normalization:
    python scripts/fix_group_turnover_units.py --execute
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from raglite.shared.logging import get_logger

logger = get_logger(__name__)


async def find_keur_rows():
    """Find Turnover rows with kEUR units that need conversion.

    Returns:
        List of rows needing conversion
    """
    import psycopg2
    from psycopg2.extras import RealDictCursor

    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        user="raglite",
        password="raglite",
        database="raglite",
    )

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            query = """
                SELECT id, metric, entity_normalized, period, value, unit, document_id
                FROM financial_tables
                WHERE metric ILIKE '%Turnover%'
                  AND entity_normalized = 'Group'
                  AND (LOWER(unit) LIKE '%keur%' OR LOWER(unit) LIKE '%1000 eur%' OR LOWER(unit) LIKE '%k eur%')
                ORDER BY period DESC
            """
            cur.execute(query)
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


async def convert_to_meur():
    """Convert kEUR values to M EUR.

    Returns:
        Number of updated rows
    """
    import psycopg2

    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        user="raglite",
        password="raglite",
        database="raglite",
    )

    try:
        with conn.cursor() as cur:
            query = """
                UPDATE financial_tables
                SET value = value / 1000,
                    unit = 'M EUR'
                WHERE metric ILIKE '%Turnover%'
                  AND entity_normalized = 'Group'
                  AND (LOWER(unit) LIKE '%keur%' OR LOWER(unit) LIKE '%1000 eur%' OR LOWER(unit) LIKE '%k eur%')
            """
            cur.execute(query)
            count = cur.rowcount
            conn.commit()
            return count
    finally:
        conn.close()


async def show_turnover_summary():
    """Show summary of GROUP Turnover data by unit."""
    import psycopg2
    from psycopg2.extras import RealDictCursor

    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        user="raglite",
        password="raglite",
        database="raglite",
    )

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            query = """
                SELECT unit, COUNT(*) as cnt, MIN(value) as min_val, MAX(value) as max_val, AVG(value) as avg_val
                FROM financial_tables
                WHERE metric ILIKE '%Turnover%'
                  AND entity_normalized = 'Group'
                GROUP BY unit
                ORDER BY cnt DESC
            """
            cur.execute(query)
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


async def main():
    parser = argparse.ArgumentParser(description="Fix GROUP Turnover unit mixing (kEUR vs M EUR)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be updated without making changes",
    )
    group.add_argument(
        "--execute",
        action="store_true",
        help="Execute the unit conversion",
    )
    group.add_argument(
        "--summary",
        action="store_true",
        help="Show summary of current data by unit",
    )

    args = parser.parse_args()

    print(f"\n{'=' * 60}")
    print("GROUP Turnover Unit Fix")
    print(f"{'=' * 60}")
    print()

    if args.summary:
        summary = await show_turnover_summary()
        print("Current GROUP Turnover data by unit:")
        print("-" * 60)
        for row in summary:
            print(f"  Unit: {row['unit'] or 'NULL'}")
            print(f"  Count: {row['cnt']}")
            print(f"  Range: {row['min_val']:,.2f} - {row['max_val']:,.2f}")
            print(f"  Average: {row['avg_val']:,.2f}")
            print("-" * 60)
        return 0

    # Find rows needing conversion
    keur_rows = await find_keur_rows()

    if not keur_rows:
        print("No kEUR rows found needing conversion.")
        return 0

    print(f"Found {len(keur_rows)} row(s) with kEUR units:")
    print("-" * 60)
    for row in keur_rows[:10]:  # Show first 10
        print(f"  ID: {row['id']}")
        print(f"  Metric: {row['metric']}")
        print(f"  Period: {row['period']}")
        print(f"  Value: {row['value']:,.2f} {row['unit']}")
        print(f"  After: {row['value'] / 1000:,.2f} M EUR")
        print("-" * 60)

    if len(keur_rows) > 10:
        print(f"  ... and {len(keur_rows) - 10} more rows")

    if args.dry_run:
        print("\nDRY RUN - No changes made.")
        print(f"Would convert {len(keur_rows)} row(s) from kEUR to M EUR.")
        return 0

    if args.execute:
        print("\nExecuting conversion...")
        count = await convert_to_meur()
        print(f"Converted {count} row(s) from kEUR to M EUR.")
        return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
