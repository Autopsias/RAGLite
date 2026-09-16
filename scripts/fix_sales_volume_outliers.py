#!/usr/bin/env python3
"""Fix Sales Volume outliers in SECIL BRITAS data.

Fix 2026-02-02: SECIL BRITAS has catastrophic outliers (143K kton vs normal 28-109 kton).
These impossible values cause 548% MAPE for Sales Volume forecasting.

This script identifies and removes outlier Volume IM values from SECIL BRITAS
that are physically impossible (>10,000 kton would be larger than all of Portugal's
annual cement production).

Usage:
    # Dry run (show what would be deleted):
    python scripts/fix_sales_volume_outliers.py --dry-run

    # Execute deletion:
    python scripts/fix_sales_volume_outliers.py --execute
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from raglite.shared.logging import get_logger

logger = get_logger(__name__)


async def find_outliers(threshold: float = 10000.0):
    """Find Volume IM outliers above threshold.

    Args:
        threshold: Maximum reasonable value in kton (default 10,000)

    Returns:
        List of outlier records
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
            query = f"""
                SELECT id, metric, entity_normalized, period, value, unit, document_id
                FROM financial_tables
                WHERE metric ILIKE '%%Volume IM%%'
                  AND value > {threshold}
                ORDER BY value DESC
            """
            cur.execute(query)
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


async def delete_outliers(threshold: float = 10000.0):
    """Delete Volume IM outliers above threshold.

    Args:
        threshold: Maximum reasonable value in kton (default 10,000)

    Returns:
        Number of deleted rows
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
            query = f"""
                DELETE FROM financial_tables
                WHERE metric ILIKE '%%Volume IM%%'
                  AND value > {threshold}
            """
            cur.execute(query)
            count = cur.rowcount
            conn.commit()
            return count
    finally:
        conn.close()


async def main():
    parser = argparse.ArgumentParser(description="Fix Sales Volume outliers in SECIL BRITAS data")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without making changes",
    )
    group.add_argument(
        "--execute",
        action="store_true",
        help="Execute the deletion",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=10000.0,
        help="Maximum reasonable value in kton (default: 10000)",
    )

    args = parser.parse_args()

    print(f"\n{'=' * 60}")
    print("Sales Volume Outlier Fix")
    print(f"{'=' * 60}")
    print(f"Threshold: {args.threshold:,.0f} kton")
    print()

    # Find outliers
    outliers = await find_outliers(args.threshold)

    if not outliers:
        print("No outliers found above threshold.")
        return 0

    print(f"Found {len(outliers)} outlier(s):")
    print("-" * 60)
    for row in outliers:
        print(f"  ID: {row['id']}")
        print(f"  Metric: {row['metric']}")
        print(f"  Entity: {row['entity_normalized']}")
        print(f"  Period: {row['period']}")
        print(f"  Value: {row['value']:,.2f} {row['unit'] or 'kton'}")
        print(f"  Source: {row['document_id']}")
        print("-" * 60)

    if args.dry_run:
        print("\nDRY RUN - No changes made.")
        print(f"Would delete {len(outliers)} row(s).")
        return 0

    if args.execute:
        print("\nExecuting deletion...")
        count = await delete_outliers(args.threshold)
        print(f"Deleted {count} row(s).")
        return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
