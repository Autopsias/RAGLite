#!/usr/bin/env python3
"""Phase 4C: Currency Metric Cleanup.

The "Currency (1000 EUR)" metric has 317 unique unit variants - severe contamination.
This script fixes:
- Rows with % unit (wrong metric type - should be Currency Ratio)
- Metric names stored in unit field
- Severely corrupted strings in unit field
- Standardizes to kEUR

Prerequisites:
    - Run Phase 4A and 4B first

Usage:
    POSTGRES_USER=raglite POSTGRES_PASSWORD=raglite POSTGRES_DB=raglite POSTGRES_PORT=5432 \
        uv run python scripts/fix_currency_cleanup.py

    # Dry run (show SQL without executing):
    POSTGRES_USER=raglite POSTGRES_PASSWORD=raglite POSTGRES_DB=raglite POSTGRES_PORT=5432 \
        uv run python scripts/fix_currency_cleanup.py --dry-run
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
        description="Phase 4C: Clean Currency (1000 EUR) metric contamination"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show SQL statements without executing them",
    )
    return parser.parse_args()


def analyze_currency_contamination(cursor) -> dict[str, int]:
    """Analyze the current state of Currency metric contamination."""
    results: dict[str, int] = {}

    print("\nAnalyzing 'Currency (1000 EUR)' metric contamination...")

    # Total Currency rows
    cursor.execute("""
        SELECT COUNT(*) FROM financial_tables
        WHERE metric = 'Currency (1000 EUR)'
    """)
    total = cursor.fetchone()[0]
    results["total_currency_rows"] = total
    print(f"  Total 'Currency (1000 EUR)' rows: {total:,}")

    # Unique units
    cursor.execute("""
        SELECT COUNT(DISTINCT unit) FROM financial_tables
        WHERE metric = 'Currency (1000 EUR)'
    """)
    unique_units = cursor.fetchone()[0]
    results["unique_units"] = unique_units
    print(f"  Unique unit variants: {unique_units:,}")

    # Top units distribution
    print("\n  Top 20 unit variants:")
    cursor.execute("""
        SELECT COALESCE(unit, '(null)') as unit, COUNT(*) as cnt
        FROM financial_tables
        WHERE metric = 'Currency (1000 EUR)'
        GROUP BY unit
        ORDER BY cnt DESC
        LIMIT 20
    """)
    top_units = cursor.fetchall()
    for unit, cnt in top_units:
        # Escape special characters
        display_unit = (
            repr(unit) if unit and ("\r" in unit or "\n" in unit or len(str(unit)) > 30) else unit
        )
        print(f"    {display_unit}: {cnt:,}")

    # Count problem types
    cursor.execute("""
        SELECT
            SUM(CASE WHEN unit = '%' THEN 1 ELSE 0 END) as pct_unit,
            SUM(CASE WHEN unit LIKE '%EBITDA%' OR unit LIKE '%Sales%' OR unit LIKE '%Revenue%' THEN 1 ELSE 0 END) as metric_in_unit,
            SUM(CASE WHEN unit ~ '%.*%.*%' THEN 1 ELSE 0 END) as triple_pct,
            SUM(CASE WHEN unit ~ E'[\\r\\n]' THEN 1 ELSE 0 END) as cr_lf,
            SUM(CASE WHEN unit IS NULL OR unit = '' THEN 1 ELSE 0 END) as null_empty
        FROM financial_tables
        WHERE metric = 'Currency (1000 EUR)'
    """)
    row = cursor.fetchone()
    results["pct_unit"] = row[0] or 0
    results["metric_in_unit"] = row[1] or 0
    results["triple_pct"] = row[2] or 0
    results["cr_lf"] = row[3] or 0
    results["null_empty"] = row[4] or 0

    print("\n  Problem breakdown:")
    print(f"    '%' unit (wrong type): {results['pct_unit']:,}")
    print(f"    Metric name in unit field: {results['metric_in_unit']:,}")
    print(f"    Triple %%% contamination: {results['triple_pct']:,}")
    print(f"    CR/LF contamination: {results['cr_lf']:,}")
    print(f"    NULL/empty: {results['null_empty']:,}")

    return results


def fix_percentage_units(cursor, conn, dry_run: bool = False) -> int:
    """Fix rows with % unit - these are actually Currency Ratio metrics."""
    print("\nStep 1: Fixing rows with '%' unit (reclassifying as Currency Ratio)...")

    if dry_run:
        cursor.execute("""
            SELECT COUNT(*) FROM financial_tables
            WHERE metric = 'Currency (1000 EUR)'
              AND unit = '%'
        """)
        count = cursor.fetchone()[0]
        print(
            f"  [DRY RUN] Would reclassify {count:,} rows from 'Currency (1000 EUR)' to 'Currency Ratio'"
        )
        return count

    cursor.execute("""
        UPDATE financial_tables
        SET metric = 'Currency Ratio',
            unit_inferred = TRUE,
            unit_inference_method = 'metric_reclassification'
        WHERE metric = 'Currency (1000 EUR)'
          AND unit = '%'
    """)
    count = cursor.rowcount
    conn.commit()
    print(f"  Reclassified {count:,} rows to 'Currency Ratio'")
    return count


def fix_metric_in_unit_field(cursor, conn, dry_run: bool = False) -> int:
    """Fix rows where metric names are stored in the unit field."""
    print("\nStep 2: Fixing metric names in unit field...")

    # Patterns that indicate a metric name in the unit field
    metric_patterns = [
        "EBITDA",
        "Sales",
        "Revenue",
        "Turnover",
        "Cost",
        "Margin",
        "Profit",
    ]

    if dry_run:
        cursor.execute("""
            SELECT unit, COUNT(*) as cnt
            FROM financial_tables
            WHERE metric = 'Currency (1000 EUR)'
              AND (unit LIKE '%EBITDA%'
                   OR unit LIKE '%Sales%'
                   OR unit LIKE '%Revenue%'
                   OR unit LIKE '%Turnover%'
                   OR unit LIKE '%Cost%'
                   OR unit LIKE '%Margin%'
                   OR unit LIKE '%Profit%')
            GROUP BY unit
            ORDER BY cnt DESC
        """)
        findings = cursor.fetchall()
        total = sum(cnt for _, cnt in findings)
        print(f"  [DRY RUN] Would clean {total:,} rows with metric names in unit:")
        for unit, cnt in findings[:10]:
            print(f"    '{unit}': {cnt:,}")
        return total

    cursor.execute("""
        UPDATE financial_tables
        SET unit = 'kEUR',
            unit_inferred = TRUE,
            unit_inference_method = 'metric_in_unit_cleanup'
        WHERE metric = 'Currency (1000 EUR)'
          AND (unit LIKE '%EBITDA%'
               OR unit LIKE '%Sales%'
               OR unit LIKE '%Revenue%'
               OR unit LIKE '%Turnover%'
               OR unit LIKE '%Cost%'
               OR unit LIKE '%Margin%'
               OR unit LIKE '%Profit%')
    """)
    count = cursor.rowcount
    conn.commit()
    print(f"  Cleaned {count:,} rows with metric names in unit")
    return count


def fix_triple_percentage(cursor, conn, dry_run: bool = False) -> int:
    """Fix severely corrupted strings like '%0%0%'."""
    print("\nStep 3: Fixing triple %%% contamination...")

    if dry_run:
        cursor.execute("""
            SELECT unit, COUNT(*) as cnt
            FROM financial_tables
            WHERE metric = 'Currency (1000 EUR)'
              AND unit ~ '%.*%.*%'
            GROUP BY unit
            ORDER BY cnt DESC
        """)
        findings = cursor.fetchall()
        total = sum(cnt for _, cnt in findings)
        print(f"  [DRY RUN] Would clean {total:,} rows with triple %%%:")
        for unit, cnt in findings[:10]:
            print(f"    '{unit}': {cnt:,}")
        return total

    cursor.execute("""
        UPDATE financial_tables
        SET unit = 'kEUR',
            unit_inferred = TRUE,
            unit_inference_method = 'corrupted_string_cleanup'
        WHERE metric = 'Currency (1000 EUR)'
          AND unit ~ '%.*%.*%'
    """)
    count = cursor.rowcount
    conn.commit()
    print(f"  Cleaned {count:,} rows with triple %%% contamination")
    return count


def fix_cr_lf_contamination(cursor, conn, dry_run: bool = False) -> int:
    """Fix units with carriage returns/line feeds."""
    print("\nStep 4: Fixing CR/LF contamination...")

    if dry_run:
        cursor.execute("""
            SELECT COUNT(*) FROM financial_tables
            WHERE metric = 'Currency (1000 EUR)'
              AND unit ~ E'[\\r\\n]'
        """)
        count = cursor.fetchone()[0]
        print(f"  [DRY RUN] Would clean {count:,} rows with CR/LF")
        return count

    cursor.execute("""
        UPDATE financial_tables
        SET unit = 'kEUR',
            unit_inferred = TRUE,
            unit_inference_method = 'cr_lf_cleanup'
        WHERE metric = 'Currency (1000 EUR)'
          AND unit ~ E'[\\r\\n]'
    """)
    count = cursor.rowcount
    conn.commit()
    print(f"  Cleaned {count:,} rows with CR/LF")
    return count


def standardize_null_empty(cursor, conn, dry_run: bool = False) -> int:
    """Standardize NULL/empty units to kEUR."""
    print("\nStep 5: Standardizing NULL/empty units to 'kEUR'...")

    if dry_run:
        cursor.execute("""
            SELECT COUNT(*) FROM financial_tables
            WHERE metric = 'Currency (1000 EUR)'
              AND (unit IS NULL OR unit = '')
        """)
        count = cursor.fetchone()[0]
        print(f"  [DRY RUN] Would set {count:,} NULL/empty units to 'kEUR'")
        return count

    cursor.execute("""
        UPDATE financial_tables
        SET unit = 'kEUR',
            unit_inferred = TRUE,
            unit_inference_method = 'currency_standardization'
        WHERE metric = 'Currency (1000 EUR)'
          AND (unit IS NULL OR unit = '')
    """)
    count = cursor.rowcount
    conn.commit()
    print(f"  Set {count:,} NULL/empty units to 'kEUR'")
    return count


def standardize_currency_variants(cursor, conn, dry_run: bool = False) -> int:
    """Standardize various EUR representations to 'kEUR'."""
    print("\nStep 6: Standardizing EUR variants...")

    # Various representations of 1000 EUR
    variants = [
        "1000 EUR",
        "kEUR",
        "K EUR",
        "1,000 EUR",
        "EUR (1000)",
        "EUR",
        "eur",
        "Eur",
        "€",
        "euros",
        "Euros",
    ]

    if dry_run:
        cursor.execute("""
            SELECT unit, COUNT(*) as cnt
            FROM financial_tables
            WHERE metric = 'Currency (1000 EUR)'
              AND unit IS NOT NULL
              AND unit != ''
              AND unit != 'kEUR'
              AND unit NOT LIKE '%EBITDA%'
              AND unit NOT LIKE '%Sales%'
              AND unit NOT ~ '%.*%.*%'
              AND unit NOT ~ E'[\\r\\n]'
            GROUP BY unit
            ORDER BY cnt DESC
            LIMIT 20
        """)
        findings = cursor.fetchall()
        total = sum(cnt for _, cnt in findings)
        print(f"  [DRY RUN] Would standardize {total:,} rows with various EUR representations:")
        for unit, cnt in findings[:10]:
            print(f"    '{unit}': {cnt:,}")
        return total

    # Standardize common variants
    cursor.execute("""
        UPDATE financial_tables
        SET unit = 'kEUR',
            unit_inferred = TRUE,
            unit_inference_method = 'eur_variant_standardization'
        WHERE metric = 'Currency (1000 EUR)'
          AND unit IN ('1000 EUR', 'K EUR', '1,000 EUR', 'EUR (1000)', 'EUR', 'eur', 'Eur', 'euros', 'Euros')
    """)
    count = cursor.rowcount
    conn.commit()
    print(f"  Standardized {count:,} EUR variant rows to 'kEUR'")
    return count


def clean_remaining_anomalies(cursor, conn, dry_run: bool = False) -> int:
    """Clean any remaining anomalous unit values."""
    print("\nStep 7: Cleaning remaining anomalies...")

    # Valid units for Currency metric
    valid_units = ["kEUR", "M EUR", "EUR", "USD", "BRL", "TND", "EGP", "LBP", "MAD"]

    if dry_run:
        cursor.execute("""
            SELECT unit, COUNT(*) as cnt
            FROM financial_tables
            WHERE metric = 'Currency (1000 EUR)'
              AND unit IS NOT NULL
              AND unit != ''
              AND unit NOT IN ('kEUR', 'M EUR', 'EUR', 'USD', 'BRL', 'TND', 'EGP', 'LBP', 'MAD')
            GROUP BY unit
            ORDER BY cnt DESC
            LIMIT 20
        """)
        findings = cursor.fetchall()
        total = sum(cnt for _, cnt in findings)
        print(f"  [DRY RUN] Found {total:,} rows with remaining anomalies:")
        for unit, cnt in findings[:10]:
            display = repr(unit) if len(str(unit)) > 20 else unit
            print(f"    '{display}': {cnt:,}")
        return total

    # Set remaining anomalies to kEUR
    cursor.execute("""
        UPDATE financial_tables
        SET unit = 'kEUR',
            unit_inferred = TRUE,
            unit_inference_method = 'anomaly_cleanup'
        WHERE metric = 'Currency (1000 EUR)'
          AND unit IS NOT NULL
          AND unit != ''
          AND unit NOT IN ('kEUR', 'M EUR', 'EUR', 'USD', 'BRL', 'TND', 'EGP', 'LBP', 'MAD')
    """)
    count = cursor.rowcount
    conn.commit()
    print(f"  Cleaned {count:,} remaining anomalies")
    return count


def verify_currency_cleanup(cursor) -> dict[str, int]:
    """Verify the Currency metric after cleanup."""
    print("\n" + "=" * 70)
    print("Verification: Currency (1000 EUR) After Cleanup")
    print("=" * 70)

    results: dict[str, int] = {}

    # Total Currency rows
    cursor.execute("""
        SELECT COUNT(*) FROM financial_tables
        WHERE metric = 'Currency (1000 EUR)'
    """)
    total = cursor.fetchone()[0]
    results["total_currency_rows"] = total
    print(f"\n  Total 'Currency (1000 EUR)' rows: {total:,}")

    # Unique units
    cursor.execute("""
        SELECT COUNT(DISTINCT unit) FROM financial_tables
        WHERE metric = 'Currency (1000 EUR)'
    """)
    unique_units = cursor.fetchone()[0]
    results["unique_units_after"] = unique_units
    print(f"  Unique unit variants: {unique_units}")

    # Unit distribution
    print("\n  Unit distribution after cleanup:")
    cursor.execute("""
        SELECT COALESCE(unit, '(null)') as unit, COUNT(*) as cnt
        FROM financial_tables
        WHERE metric = 'Currency (1000 EUR)'
        GROUP BY unit
        ORDER BY cnt DESC
        LIMIT 10
    """)
    units = cursor.fetchall()
    for unit, cnt in units:
        pct = 100.0 * cnt / total if total > 0 else 0
        print(f"    {unit}: {cnt:,} ({pct:.1f}%)")

    # Check Currency Ratio (reclassified)
    cursor.execute("""
        SELECT COUNT(*) FROM financial_tables
        WHERE metric = 'Currency Ratio'
    """)
    ratio_count = cursor.fetchone()[0]
    results["currency_ratio_rows"] = ratio_count
    print(f"\n  New 'Currency Ratio' metric rows: {ratio_count:,}")

    return results


def currency_cleanup(dry_run: bool = False) -> dict[str, int]:
    """Run all currency cleanup operations.

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
    print("Phase 4C: Currency Metric Cleanup")
    print("=" * 70)

    # Analyze initial state
    initial_analysis = analyze_currency_contamination(cursor)
    results.update({f"initial_{k}": v for k, v in initial_analysis.items()})

    # Execute cleanup operations
    results["pct_reclassified"] = fix_percentage_units(cursor, conn, dry_run)
    results["metric_in_unit_fixed"] = fix_metric_in_unit_field(cursor, conn, dry_run)
    results["triple_pct_fixed"] = fix_triple_percentage(cursor, conn, dry_run)
    results["cr_lf_fixed"] = fix_cr_lf_contamination(cursor, conn, dry_run)
    results["null_empty_standardized"] = standardize_null_empty(cursor, conn, dry_run)
    results["eur_variants_standardized"] = standardize_currency_variants(cursor, conn, dry_run)
    results["anomalies_cleaned"] = clean_remaining_anomalies(cursor, conn, dry_run)

    # Verify cleanup
    if not dry_run:
        verification = verify_currency_cleanup(cursor)
        results.update({f"final_{k}": v for k, v in verification.items()})

    cursor.close()
    return results


def print_summary(results: dict[str, int], dry_run: bool) -> None:
    """Print summary of all operations."""
    print("\n" + "=" * 70)
    print("PHASE 4C SUMMARY")
    print("=" * 70)

    print(f"\n{'Operation':<40} {'Rows':>15}")
    print("-" * 55)

    # Filter to show only operation results
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
        results = currency_cleanup(dry_run=args.dry_run)

        print_summary(results, args.dry_run)

        print("\n" + "=" * 70)
        if args.dry_run:
            print("Phase 4C complete (DRY RUN)")
        else:
            print("Phase 4C complete")
        print("=" * 70)
        print("\nNext step: Run scripts/fix_ebitda_scale.py (Phase 4D)")

        return 0

    except Exception as e:
        print(f"\n ERROR: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
