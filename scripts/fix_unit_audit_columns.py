#!/usr/bin/env python3
"""Phase D: Add audit columns for unit tracking.

Adds tracking columns to preserve original units and track inference metadata.
This MUST be run first before any other unit repair scripts.

Usage:
    POSTGRES_USER=raglite POSTGRES_PASSWORD=raglite POSTGRES_DB=raglite POSTGRES_PORT=5432 \
        uv run python scripts/fix_unit_audit_columns.py

    # Dry run (show SQL without executing):
    POSTGRES_USER=raglite POSTGRES_PASSWORD=raglite POSTGRES_DB=raglite POSTGRES_PORT=5432 \
        uv run python scripts/fix_unit_audit_columns.py --dry-run
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

# Suppress verbose logging unless DEBUG is set
if not os.getenv("DEBUG"):
    logging.getLogger("raglite").setLevel(logging.WARNING)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Add audit columns for unit tracking to financial_tables"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show SQL statements without executing them",
    )
    return parser.parse_args()


def add_audit_columns(dry_run: bool = False) -> dict[str, int]:
    """Add audit columns to financial_tables.

    Columns added:
        - unit_original: VARCHAR(50) - Preserves the original unit value
        - unit_inferred: BOOLEAN - TRUE if unit was inferred, FALSE/NULL if original
        - unit_inference_method: VARCHAR(50) - Method used for inference
        - unit_confidence: VARCHAR(20) - Confidence level ('high', 'medium', 'low')

    Args:
        dry_run: If True, only print SQL without executing

    Returns:
        Dict with counts of rows affected by each operation
    """
    from raglite.shared.clients import get_postgresql_connection

    conn = get_postgresql_connection()
    cursor = conn.cursor()
    results: dict[str, int] = {}

    # SQL statements for adding columns
    add_column_statements = [
        (
            "unit_original",
            """
            ALTER TABLE financial_tables
            ADD COLUMN IF NOT EXISTS unit_original VARCHAR(50)
            """,
        ),
        (
            "unit_inferred",
            """
            ALTER TABLE financial_tables
            ADD COLUMN IF NOT EXISTS unit_inferred BOOLEAN DEFAULT FALSE
            """,
        ),
        (
            "unit_inference_method",
            """
            ALTER TABLE financial_tables
            ADD COLUMN IF NOT EXISTS unit_inference_method VARCHAR(50)
            """,
        ),
        (
            "unit_confidence",
            """
            ALTER TABLE financial_tables
            ADD COLUMN IF NOT EXISTS unit_confidence VARCHAR(20)
            """,
        ),
    ]

    print("\n" + "=" * 70)
    print("Phase D: Add Audit Columns for Unit Tracking")
    print("=" * 70)

    # Step 1: Add columns
    print("\nStep 1: Adding audit columns...")
    for col_name, sql in add_column_statements:
        print(f"  Adding column: {col_name}")
        if dry_run:
            print(f"    [DRY RUN] Would execute:\n    {sql.strip()}")
        else:
            try:
                cursor.execute(sql)
                conn.commit()
                print(f"    ✓ Column {col_name} added (or already exists)")
            except Exception as e:
                conn.rollback()
                print(f"    ✗ Error adding {col_name}: {e}")
                results[f"error_{col_name}"] = 1

    # Step 2: Preserve original units (only for rows where unit_original is NULL)
    print("\nStep 2: Preserving original unit values...")
    preserve_sql = """
        UPDATE financial_tables
        SET unit_original = unit
        WHERE unit_original IS NULL
          AND unit IS NOT NULL
    """

    if dry_run:
        # Count how many would be affected
        # In dry-run mode, columns may not exist yet, so count all non-null units
        try:
            cursor.execute("""
                SELECT COUNT(*)
                FROM financial_tables
                WHERE unit_original IS NULL AND unit IS NOT NULL
            """)
            count = cursor.fetchone()[0]
        except Exception:
            # Column doesn't exist yet, count all non-null units
            conn.rollback()
            cursor.execute("""
                SELECT COUNT(*)
                FROM financial_tables
                WHERE unit IS NOT NULL
            """)
            count = cursor.fetchone()[0]
        print(f"  [DRY RUN] Would preserve {count:,} original unit values")
        results["preserved_units"] = count
    else:
        cursor.execute(preserve_sql)
        results["preserved_units"] = cursor.rowcount
        conn.commit()
        print(f"  ✓ Preserved {results['preserved_units']:,} original unit values")

    # Step 3: Create index for faster inference queries
    print("\nStep 3: Creating indexes for efficient queries...")
    index_statements = [
        (
            "idx_financial_tables_unit_inferred",
            """
            CREATE INDEX IF NOT EXISTS idx_financial_tables_unit_inferred
            ON financial_tables(unit_inferred) WHERE unit_inferred = TRUE
            """,
        ),
        (
            "idx_financial_tables_unit_null",
            """
            CREATE INDEX IF NOT EXISTS idx_financial_tables_unit_null
            ON financial_tables(metric) WHERE unit IS NULL OR unit = ''
            """,
        ),
    ]

    for idx_name, sql in index_statements:
        print(f"  Creating index: {idx_name}")
        if dry_run:
            print(f"    [DRY RUN] Would execute:\n    {sql.strip()}")
        else:
            try:
                cursor.execute(sql)
                conn.commit()
                print(f"    ✓ Index {idx_name} created (or already exists)")
            except Exception as e:
                conn.rollback()
                print(f"    ✗ Error creating index {idx_name}: {e}")

    # Step 4: Verify schema changes
    print("\nStep 4: Verifying schema changes...")
    cursor.execute("""
        SELECT column_name, data_type, column_default
        FROM information_schema.columns
        WHERE table_name = 'financial_tables'
          AND column_name IN ('unit_original', 'unit_inferred', 'unit_inference_method', 'unit_confidence')
        ORDER BY column_name
    """)
    columns = cursor.fetchall()

    if columns:
        print("  Audit columns present:")
        for col_name, data_type, default in columns:
            default_str = f" (default: {default})" if default else ""
            print(f"    - {col_name}: {data_type}{default_str}")
        results["columns_verified"] = len(columns)
    elif dry_run:
        print("  [DRY RUN] Columns would be created by this script")
        results["columns_verified"] = 4  # Expected 4 columns
    else:
        print("  ✗ No audit columns found (schema change may have failed)")
        results["columns_verified"] = 0

    # Step 5: Show summary statistics
    print("\nStep 5: Summary statistics...")

    # In dry-run mode, columns may not exist yet
    try:
        cursor.execute("""
            SELECT
                COUNT(*) as total_rows,
                COUNT(unit_original) as with_original,
                SUM(CASE WHEN unit_inferred = TRUE THEN 1 ELSE 0 END) as inferred_count
            FROM financial_tables
        """)
        row = cursor.fetchone()
        print(f"  Total rows: {row[0]:,}")
        print(f"  With original unit preserved: {row[1]:,}")
        print(f"  Already marked as inferred: {row[2]:,}")
    except Exception:
        # Columns don't exist yet (dry-run mode)
        conn.rollback()
        cursor.execute("SELECT COUNT(*) FROM financial_tables")
        row = cursor.fetchone()
        print(f"  Total rows: {row[0]:,}")
        print("  [DRY RUN] Audit columns will be created by this script")

    cursor.close()

    return results


def main() -> int:
    """Main entry point."""
    args = parse_args()

    try:
        results = add_audit_columns(dry_run=args.dry_run)

        print("\n" + "=" * 70)
        print("RESULTS SUMMARY")
        print("=" * 70)
        for key, value in results.items():
            print(f"  {key}: {value:,}")

        if args.dry_run:
            print("\n[DRY RUN] No changes were made to the database.")
            print("Run without --dry-run to apply changes.")

        print("\n✓ Phase D complete. Audit columns are ready.")
        print("  Next step: Run scripts/fix_unit_standardization.py (Phase A)")

        return 0

    except Exception as e:
        print(f"\n✗ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
