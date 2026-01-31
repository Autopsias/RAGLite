#!/usr/bin/env python3
"""Phase 4B: Ratio Metric Decomposition.

The "Ratio" metric has 1,604 unique unit variants - extreme contamination.
This script splits it into proper categories with correct units.

Key patterns:
- Percentage ratios (157K rows with %)
- YoY changes stored in unit field (e.g., "% -100%")
- Malformed units with carriage returns

Prerequisites:
    - Run Phase 4A (fix_structural_cleanup.py) first

Usage:
    POSTGRES_USER=raglite POSTGRES_PASSWORD=raglite POSTGRES_DB=raglite POSTGRES_PORT=5432 \
        uv run python scripts/fix_ratio_decomposition.py

    # Dry run (show SQL without executing):
    POSTGRES_USER=raglite POSTGRES_PASSWORD=raglite POSTGRES_DB=raglite POSTGRES_PORT=5432 \
        uv run python scripts/fix_ratio_decomposition.py --dry-run
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
        description="Phase 4B: Decompose Ratio metric into proper categories"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show SQL statements without executing them",
    )
    return parser.parse_args()


def analyze_ratio_contamination(cursor) -> dict[str, int]:
    """Analyze the current state of Ratio metric contamination.

    Returns:
        Dict with analysis results
    """
    results: dict[str, int] = {}

    print("\nAnalyzing 'Ratio' metric contamination...")

    # Total Ratio rows
    cursor.execute("""
        SELECT COUNT(*) FROM financial_tables WHERE metric = 'Ratio'
    """)
    total = cursor.fetchone()[0]
    results["total_ratio_rows"] = total
    print(f"  Total 'Ratio' rows: {total:,}")

    # Unique units
    cursor.execute("""
        SELECT COUNT(DISTINCT unit) FROM financial_tables WHERE metric = 'Ratio'
    """)
    unique_units = cursor.fetchone()[0]
    results["unique_units"] = unique_units
    print(f"  Unique unit variants: {unique_units:,}")

    # Top units distribution
    print("\n  Top 20 unit variants in 'Ratio' metric:")
    cursor.execute("""
        SELECT COALESCE(unit, '(null)') as unit, COUNT(*) as cnt
        FROM financial_tables
        WHERE metric = 'Ratio'
        GROUP BY unit
        ORDER BY cnt DESC
        LIMIT 20
    """)
    top_units = cursor.fetchall()
    for unit, cnt in top_units:
        # Escape any special characters for display
        display_unit = repr(unit) if unit and ("\r" in unit or "\n" in unit) else unit
        print(f"    {display_unit}: {cnt:,}")

    # Count pattern types
    cursor.execute("""
        SELECT
            SUM(CASE WHEN unit = '%' THEN 1 ELSE 0 END) as pct_only,
            SUM(CASE WHEN unit ~ '^%\\s+-?\\d' THEN 1 ELSE 0 END) as yoy_in_unit,
            SUM(CASE WHEN unit ~ E'[\\r\\n]' THEN 1 ELSE 0 END) as cr_lf,
            SUM(CASE WHEN unit = 'pp' THEN 1 ELSE 0 END) as pp,
            SUM(CASE WHEN unit IS NULL THEN 1 ELSE 0 END) as null_unit
        FROM financial_tables
        WHERE metric = 'Ratio'
    """)
    row = cursor.fetchone()
    results["pct_only"] = row[0] or 0
    results["yoy_in_unit"] = row[1] or 0
    results["cr_lf"] = row[2] or 0
    results["pp"] = row[3] or 0
    results["null_unit"] = row[4] or 0

    print("\n  Pattern breakdown:")
    print(f"    Pure '%': {results['pct_only']:,}")
    print(f"    YoY in unit field: {results['yoy_in_unit']:,}")
    print(f"    CR/LF contaminated: {results['cr_lf']:,}")
    print(f"    'pp' (percentage points): {results['pp']:,}")
    print(f"    NULL unit: {results['null_unit']:,}")

    return results


def ensure_yoy_column(cursor, conn, dry_run: bool = False) -> bool:
    """Ensure yoy_change column exists for extracting YoY values from unit field."""
    cursor.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'financial_tables' AND column_name = 'yoy_change'
    """)
    if cursor.fetchone():
        print("  yoy_change column already exists")
        return True

    if dry_run:
        print("  [DRY RUN] Would create yoy_change column")
        return True

    print("  Creating yoy_change column...")
    cursor.execute("""
        ALTER TABLE financial_tables
        ADD COLUMN IF NOT EXISTS yoy_change VARCHAR(50)
    """)
    conn.commit()
    print("  yoy_change column created")
    return True


def extract_yoy_from_units(cursor, conn, dry_run: bool = False) -> int:
    """Extract YoY change values stored in unit field.

    Pattern: "% -100%", "% +50%", "% -1%" etc.
    These are YoY changes stored in the unit field.
    """
    print("\nStep 2: Extracting YoY changes from unit field...")

    if dry_run:
        cursor.execute("""
            SELECT COUNT(*) FROM financial_tables
            WHERE metric = 'Ratio'
              AND unit ~ '^%\\s+-?\\d+%?$'
        """)
        count = cursor.fetchone()[0]
        print(f"  [DRY RUN] Would extract YoY from {count:,} rows")

        # Show samples
        cursor.execute("""
            SELECT unit, COUNT(*) as cnt
            FROM financial_tables
            WHERE metric = 'Ratio'
              AND unit ~ '^%\\s+-?\\d+%?$'
            GROUP BY unit
            ORDER BY cnt DESC
            LIMIT 10
        """)
        samples = cursor.fetchall()
        if samples:
            print("  Sample unit values with YoY:")
            for unit, cnt in samples:
                print(f"    '{unit}': {cnt:,}")
        return count

    # Extract YoY change to separate column
    cursor.execute("""
        UPDATE financial_tables
        SET yoy_change = REGEXP_REPLACE(unit, '^%\\s*', ''),
            unit = '%',
            unit_inferred = TRUE,
            unit_inference_method = 'yoy_extraction'
        WHERE metric = 'Ratio'
          AND unit ~ '^%\\s+-?\\d+%?$'
    """)
    count = cursor.rowcount
    conn.commit()
    print(f"  Extracted YoY from {count:,} rows")
    return count


def clean_cr_lf_units(cursor, conn, dry_run: bool = False) -> int:
    """Clean units with carriage returns/line feeds."""
    print("\nStep 3: Cleaning CR/LF contaminated units...")

    if dry_run:
        cursor.execute("""
            SELECT COUNT(*) FROM financial_tables
            WHERE metric = 'Ratio'
              AND unit ~ E'[\\r\\n]'
        """)
        count = cursor.fetchone()[0]
        print(f"  [DRY RUN] Would clean {count:,} rows with CR/LF")
        return count

    cursor.execute("""
        UPDATE financial_tables
        SET unit = '%',
            unit_inferred = TRUE,
            unit_inference_method = 'cr_lf_cleanup'
        WHERE metric = 'Ratio'
          AND unit ~ E'[\\r\\n]'
    """)
    count = cursor.rowcount
    conn.commit()
    print(f"  Cleaned {count:,} rows with CR/LF")
    return count


def standardize_percentage_units(cursor, conn, dry_run: bool = False) -> int:
    """Standardize various percentage unit representations.

    Consolidates: "percent", "Percent", "PERCENT", "pct", etc. to "%"
    """
    print("\nStep 4: Standardizing percentage unit representations...")

    percentage_variants = [
        "percent",
        "Percent",
        "PERCENT",
        "pct",
        "Pct",
        "PCT",
        "percentage",
        "Percentage",
    ]
    variant_list = ", ".join(f"'{v}'" for v in percentage_variants)

    if dry_run:
        cursor.execute(f"""
            SELECT unit, COUNT(*) as cnt
            FROM financial_tables
            WHERE metric = 'Ratio'
              AND LOWER(unit) IN ({", ".join(f"'{v.lower()}'" for v in percentage_variants)})
            GROUP BY unit
        """)
        variants = cursor.fetchall()
        total = sum(cnt for _, cnt in variants)
        print(f"  [DRY RUN] Would standardize {total:,} rows")
        for unit, cnt in variants:
            print(f"    '{unit}': {cnt:,}")
        return total

    cursor.execute(f"""
        UPDATE financial_tables
        SET unit = '%',
            unit_inferred = TRUE,
            unit_inference_method = 'pct_standardization'
        WHERE metric = 'Ratio'
          AND LOWER(unit) IN ({", ".join(f"'{v.lower()}'" for v in percentage_variants)})
    """)
    count = cursor.rowcount
    conn.commit()
    print(f"  Standardized {count:,} rows to '%'")
    return count


def handle_percentage_points(cursor, conn, dry_run: bool = False) -> int:
    """Keep 'pp' (percentage points) as distinct unit - it's valid."""
    print("\nStep 5: Verifying 'pp' (percentage points) rows...")

    cursor.execute("""
        SELECT COUNT(*) FROM financial_tables
        WHERE metric = 'Ratio' AND unit = 'pp'
    """)
    count = cursor.fetchone()[0]
    print(f"  Found {count:,} rows with 'pp' unit (keeping as-is)")
    return 0  # No changes needed


def set_null_units_to_percent(cursor, conn, dry_run: bool = False) -> int:
    """Set NULL units on Ratio metric to '%'."""
    print("\nStep 6: Setting NULL units to '%' for Ratio metric...")

    if dry_run:
        cursor.execute("""
            SELECT COUNT(*) FROM financial_tables
            WHERE metric = 'Ratio'
              AND unit IS NULL
        """)
        count = cursor.fetchone()[0]
        print(f"  [DRY RUN] Would set {count:,} NULL units to '%'")
        return count

    cursor.execute("""
        UPDATE financial_tables
        SET unit = '%',
            unit_inferred = TRUE,
            unit_inference_method = 'ratio_default'
        WHERE metric = 'Ratio'
          AND unit IS NULL
    """)
    count = cursor.rowcount
    conn.commit()
    print(f"  Set {count:,} NULL units to '%'")
    return count


def clean_remaining_anomalies(cursor, conn, dry_run: bool = False) -> int:
    """Clean remaining anomalous unit values in Ratio metric.

    After the main cleanup, any remaining non-standard units should be
    examined and cleaned.
    """
    print("\nStep 7: Cleaning remaining anomalous units...")

    # Valid units for Ratio metric
    valid_units = ["%", "pp", "x", "times", "ratio"]

    if dry_run:
        cursor.execute("""
            SELECT unit, COUNT(*) as cnt
            FROM financial_tables
            WHERE metric = 'Ratio'
              AND unit IS NOT NULL
              AND unit NOT IN ('%', 'pp', 'x', 'times', 'ratio')
            GROUP BY unit
            ORDER BY cnt DESC
            LIMIT 20
        """)
        anomalies = cursor.fetchall()
        total = sum(cnt for _, cnt in anomalies)
        print(f"  [DRY RUN] Found {total:,} rows with anomalous units:")
        for unit, cnt in anomalies:
            display = repr(unit) if len(str(unit)) > 20 else unit
            print(f"    '{display}': {cnt:,}")
        return total

    # For anomalies that look like numbers (e.g., "0", "1"), set to %
    cursor.execute("""
        UPDATE financial_tables
        SET unit = '%',
            unit_inferred = TRUE,
            unit_inference_method = 'anomaly_cleanup'
        WHERE metric = 'Ratio'
          AND unit IS NOT NULL
          AND unit NOT IN ('%', 'pp', 'x', 'times', 'ratio')
          AND unit ~ '^-?[0-9]'
    """)
    numeric_cleaned = cursor.rowcount

    # For very long anomalies (likely data corruption), set to %
    cursor.execute("""
        UPDATE financial_tables
        SET unit = '%',
            unit_inferred = TRUE,
            unit_inference_method = 'anomaly_cleanup'
        WHERE metric = 'Ratio'
          AND unit IS NOT NULL
          AND unit NOT IN ('%', 'pp', 'x', 'times', 'ratio')
          AND LENGTH(unit) > 10
    """)
    long_cleaned = cursor.rowcount

    conn.commit()
    total = numeric_cleaned + long_cleaned
    print(
        f"  Cleaned {total:,} anomalous units (numeric: {numeric_cleaned}, long strings: {long_cleaned})"
    )
    return total


def verify_ratio_cleanup(cursor) -> dict[str, int]:
    """Verify the Ratio metric after cleanup."""
    print("\n" + "=" * 70)
    print("Verification: Ratio Metric After Cleanup")
    print("=" * 70)

    results: dict[str, int] = {}

    # Total Ratio rows
    cursor.execute("""
        SELECT COUNT(*) FROM financial_tables WHERE metric = 'Ratio'
    """)
    total = cursor.fetchone()[0]
    results["total_ratio_rows"] = total
    print(f"\n  Total 'Ratio' rows: {total:,}")

    # Unique units
    cursor.execute("""
        SELECT COUNT(DISTINCT unit) FROM financial_tables WHERE metric = 'Ratio'
    """)
    unique_units = cursor.fetchone()[0]
    results["unique_units_after"] = unique_units
    print(f"  Unique unit variants: {unique_units}")

    # Unit distribution
    print("\n  Unit distribution after cleanup:")
    cursor.execute("""
        SELECT COALESCE(unit, '(null)') as unit, COUNT(*) as cnt
        FROM financial_tables
        WHERE metric = 'Ratio'
        GROUP BY unit
        ORDER BY cnt DESC
        LIMIT 10
    """)
    units = cursor.fetchall()
    for unit, cnt in units:
        pct = 100.0 * cnt / total if total > 0 else 0
        print(f"    {unit}: {cnt:,} ({pct:.1f}%)")

    # Check for remaining issues
    cursor.execute("""
        SELECT COUNT(*) FROM financial_tables
        WHERE metric = 'Ratio'
          AND unit NOT IN ('%', 'pp', 'x', 'times', 'ratio')
          AND unit IS NOT NULL
    """)
    remaining_issues = cursor.fetchone()[0]
    results["remaining_issues"] = remaining_issues
    print(f"\n  Remaining non-standard units: {remaining_issues:,}")

    return results


def ratio_decomposition(dry_run: bool = False) -> dict[str, int]:
    """Run all ratio decomposition operations.

    Args:
        dry_run: If True, only print SQL without executing

    Returns:
        Dict with counts of rows affected by each operation
    """
    from raglite.shared.clients import get_postgresql_connection

    conn = get_postgresql_connection()
    cursor = conn.cursor()
    results: dict[str, int] = {}

    print("\n" + "=" * 70)
    print("Phase 4B: Ratio Metric Decomposition")
    print("=" * 70)

    # Analyze initial state
    initial_analysis = analyze_ratio_contamination(cursor)
    results.update({f"initial_{k}": v for k, v in initial_analysis.items()})

    # Step 1: Ensure yoy_change column exists
    print("\nStep 1: Ensuring yoy_change column exists...")
    ensure_yoy_column(cursor, conn, dry_run)

    # Execute decomposition operations
    results["yoy_extracted"] = extract_yoy_from_units(cursor, conn, dry_run)
    results["cr_lf_cleaned"] = clean_cr_lf_units(cursor, conn, dry_run)
    results["pct_standardized"] = standardize_percentage_units(cursor, conn, dry_run)
    results["null_units_set"] = set_null_units_to_percent(cursor, conn, dry_run)
    results["anomalies_cleaned"] = clean_remaining_anomalies(cursor, conn, dry_run)

    # Verify cleanup
    if not dry_run:
        verification = verify_ratio_cleanup(cursor)
        results.update({f"final_{k}": v for k, v in verification.items()})

    cursor.close()
    return results


def print_summary(results: dict[str, int], dry_run: bool) -> None:
    """Print summary of all operations."""
    print("\n" + "=" * 70)
    print("PHASE 4B SUMMARY")
    print("=" * 70)

    print(f"\n{'Operation':<40} {'Rows':>15}")
    print("-" * 55)

    # Filter to show only operation results, not analysis
    ops = {
        k: v
        for k, v in results.items()
        if not k.startswith("initial_") and not k.startswith("final_")
    }
    for key, value in ops.items():
        print(f"{key:<40} {value:>15,}")

    print("-" * 55)
    total = sum(ops.values())
    print(f"{'Total rows processed':<40} {total:>15,}")

    # Show before/after comparison
    if "initial_unique_units" in results and "final_unique_units_after" in results:
        print(
            f"\nUnique units: {results['initial_unique_units']:,} -> {results['final_unique_units_after']:,}"
        )
        reduction = results["initial_unique_units"] - results["final_unique_units_after"]
        print(f"Reduction: {reduction:,} unit variants eliminated")

    if dry_run:
        print("\n[DRY RUN] No changes were made to the database.")
        print("Run without --dry-run to apply changes.")


def main() -> int:
    """Main entry point."""
    args = parse_args()

    try:
        results = ratio_decomposition(dry_run=args.dry_run)

        print_summary(results, args.dry_run)

        print("\n" + "=" * 70)
        if args.dry_run:
            print("Phase 4B complete (DRY RUN)")
        else:
            print("Phase 4B complete")
        print("=" * 70)
        print("\nNext step: Run scripts/fix_currency_cleanup.py (Phase 4C)")

        return 0

    except Exception as e:
        print(f"\n ERROR: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
