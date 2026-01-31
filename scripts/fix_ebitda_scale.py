#!/usr/bin/env python3
"""Phase 4D: EBITDA Scale Reconciliation.

Resolves the kEUR vs M EUR mixing in EBITDA metrics where:
- 828 rows with kEUR have values 1000x off compared to M EUR
- Some kEUR values are actually M EUR (small values like 150)
- Some kEUR values are genuinely large (100K+)

Strategy:
1. Analyze value distributions for each unit
2. For values that look like M EUR (small absolute value), convert to M EUR
3. Flag suspicious large values for review
4. Create a review queue for manual verification

Prerequisites:
    - Run Phase 4A, 4B, 4C first

Usage:
    POSTGRES_USER=raglite POSTGRES_PASSWORD=raglite POSTGRES_DB=raglite POSTGRES_PORT=5432 \
        uv run python scripts/fix_ebitda_scale.py

    # Dry run (show SQL without executing):
    POSTGRES_USER=raglite POSTGRES_PASSWORD=raglite POSTGRES_DB=raglite POSTGRES_PORT=5432 \
        uv run python scripts/fix_ebitda_scale.py --dry-run
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
        description="Phase 4D: Resolve EBITDA kEUR vs M EUR scale mixing"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show SQL statements without executing them",
    )
    parser.add_argument(
        "--create-review-table",
        action="store_true",
        help="Create a review table for suspicious values",
    )
    return parser.parse_args()


def analyze_ebitda_scale_issues(cursor) -> dict[str, int]:
    """Analyze the current state of EBITDA scale issues."""
    results: dict[str, int] = {}

    print("\nAnalyzing EBITDA scale issues...")

    # Get EBITDA metrics distribution
    cursor.execute("""
        SELECT unit, COUNT(*) as cnt,
               MIN(value) as min_val,
               MAX(value) as max_val,
               AVG(value) as avg_val
        FROM financial_tables
        WHERE LOWER(metric) LIKE '%ebitda%'
        GROUP BY unit
        ORDER BY cnt DESC
    """)
    unit_dist = cursor.fetchall()

    print("\n  EBITDA unit distribution:")
    print(f"  {'Unit':<15} {'Count':>10} {'Min':>15} {'Max':>15} {'Avg':>15}")
    print("  " + "-" * 70)
    for unit, cnt, min_val, max_val, avg_val in unit_dist:
        unit_display = unit or "(null)"
        min_str = f"{min_val:,.2f}" if min_val else "N/A"
        max_str = f"{max_val:,.2f}" if max_val else "N/A"
        avg_str = f"{avg_val:,.2f}" if avg_val else "N/A"
        print(f"  {unit_display:<15} {cnt:>10,} {min_str:>15} {max_str:>15} {avg_str:>15}")
        results[f"ebitda_{unit or 'null'}_count"] = cnt

    # Check for potential scale issues
    # kEUR values that are suspiciously small (likely should be M EUR)
    cursor.execute("""
        SELECT COUNT(*) FROM financial_tables
        WHERE LOWER(metric) LIKE '%ebitda%'
          AND unit = 'kEUR'
          AND ABS(value) < 1000
    """)
    small_keur = cursor.fetchone()[0]
    results["small_keur_values"] = small_keur
    print("\n  Potential scale issues:")
    print(f"    kEUR values with |value| < 1000: {small_keur:,} (likely M EUR)")

    # kEUR values that are very large (could be correct or 1000x off)
    cursor.execute("""
        SELECT COUNT(*) FROM financial_tables
        WHERE LOWER(metric) LIKE '%ebitda%'
          AND unit = 'kEUR'
          AND ABS(value) > 100000
    """)
    large_keur = cursor.fetchone()[0]
    results["large_keur_values"] = large_keur
    print(f"    kEUR values with |value| > 100K: {large_keur:,} (needs review)")

    # Check entity-specific patterns
    print("\n  Entity distribution for EBITDA kEUR:")
    cursor.execute("""
        SELECT entity_normalized, COUNT(*) as cnt,
               MIN(value) as min_val, MAX(value) as max_val
        FROM financial_tables
        WHERE LOWER(metric) LIKE '%ebitda%'
          AND unit = 'kEUR'
        GROUP BY entity_normalized
        ORDER BY cnt DESC
        LIMIT 10
    """)
    entities = cursor.fetchall()
    for entity, cnt, min_val, max_val in entities:
        print(f"    {entity}: {cnt:,} rows (range: {min_val:,.0f} to {max_val:,.0f})")

    return results


def create_review_table(cursor, conn, dry_run: bool = False) -> int:
    """Create a review table for suspicious EBITDA scale values."""
    print("\nCreating EBITDA scale review table...")

    if dry_run:
        cursor.execute("""
            SELECT COUNT(*) FROM financial_tables
            WHERE LOWER(metric) LIKE '%ebitda%'
              AND (
                  (unit = 'kEUR' AND ABS(value) > 50000)
                  OR (unit = 'M EUR' AND ABS(value) > 1000)
              )
        """)
        count = cursor.fetchone()[0]
        print(f"  [DRY RUN] Would create review table with {count:,} suspicious rows")
        return count

    # Drop if exists
    cursor.execute("DROP TABLE IF EXISTS ebitda_scale_review")

    # Create review table
    cursor.execute("""
        CREATE TABLE ebitda_scale_review AS
        SELECT id, document_id, source_document, entity, entity_normalized,
               metric, period, fiscal_year, value, unit, unit_original,
               'needs_review' as review_status,
               NULL::text as review_notes
        FROM financial_tables
        WHERE LOWER(metric) LIKE '%ebitda%'
          AND (
              (unit = 'kEUR' AND ABS(value) > 50000)
              OR (unit = 'M EUR' AND ABS(value) > 1000)
          )
    """)
    cursor.execute("SELECT COUNT(*) FROM ebitda_scale_review")
    count = cursor.fetchone()[0]
    conn.commit()
    print(f"  Created ebitda_scale_review table with {count:,} rows")
    return count


def fix_small_keur_to_meur(cursor, conn, dry_run: bool = False) -> int:
    """Convert small kEUR values to M EUR (they're likely mislabeled).

    Logic: If a kEUR value is < 1000, it's almost certainly a M EUR value
    that was incorrectly labeled. E.g., "150 kEUR" is likely "150 M EUR"
    """
    print("\nStep 1: Converting small kEUR values to M EUR...")

    if dry_run:
        cursor.execute("""
            SELECT entity_normalized, metric, period, value, unit
            FROM financial_tables
            WHERE LOWER(metric) LIKE '%ebitda%'
              AND unit = 'kEUR'
              AND ABS(value) < 1000
            ORDER BY entity_normalized, period
            LIMIT 20
        """)
        samples = cursor.fetchall()
        print(f"  [DRY RUN] Would convert {len(samples):,}+ rows from kEUR to M EUR")
        print("  Sample conversions:")
        for entity, metric, period, value, unit in samples:
            print(f"    {entity} | {period} | {value:.2f} kEUR -> {value:.2f} M EUR")

        cursor.execute("""
            SELECT COUNT(*) FROM financial_tables
            WHERE LOWER(metric) LIKE '%ebitda%'
              AND unit = 'kEUR'
              AND ABS(value) < 1000
        """)
        count = cursor.fetchone()[0]
        return count

    cursor.execute("""
        UPDATE financial_tables
        SET unit = 'M EUR',
            unit_inferred = TRUE,
            unit_inference_method = 'ebitda_scale_correction',
            unit_confidence = 'medium'
        WHERE LOWER(metric) LIKE '%ebitda%'
          AND unit = 'kEUR'
          AND ABS(value) < 1000
    """)
    count = cursor.rowcount
    conn.commit()
    print(f"  Converted {count:,} small kEUR values to M EUR")
    return count


def flag_suspicious_large_values(cursor, conn, dry_run: bool = False) -> int:
    """Flag suspiciously large kEUR values for review.

    Logic: kEUR values > 100K could be:
    - Correct (100K kEUR = 100M EUR - plausible for large entities)
    - Wrong (should be M EUR - value would be 1000x too high)

    We flag these with low confidence for manual review.
    """
    print("\nStep 2: Flagging suspicious large kEUR values...")

    if dry_run:
        cursor.execute("""
            SELECT entity_normalized, metric, period, value
            FROM financial_tables
            WHERE LOWER(metric) LIKE '%ebitda%'
              AND unit = 'kEUR'
              AND ABS(value) > 100000
            ORDER BY ABS(value) DESC
            LIMIT 10
        """)
        samples = cursor.fetchall()
        count = len(samples)
        print(f"  [DRY RUN] Would flag {count:,}+ rows as low confidence")
        print("  Suspicious values (kEUR > 100K):")
        for entity, metric, period, value in samples:
            equivalent_meur = value / 1000
            print(
                f"    {entity} | {period} | {value:,.0f} kEUR = {equivalent_meur:,.0f} M EUR (if mislabeled)"
            )

        cursor.execute("""
            SELECT COUNT(*) FROM financial_tables
            WHERE LOWER(metric) LIKE '%ebitda%'
              AND unit = 'kEUR'
              AND ABS(value) > 100000
        """)
        total = cursor.fetchone()[0]
        return total

    cursor.execute("""
        UPDATE financial_tables
        SET unit_confidence = 'low',
            unit_inference_method = COALESCE(unit_inference_method, 'flagged_for_review')
        WHERE LOWER(metric) LIKE '%ebitda%'
          AND unit = 'kEUR'
          AND ABS(value) > 100000
    """)
    count = cursor.rowcount
    conn.commit()
    print(f"  Flagged {count:,} large kEUR values as low confidence")
    return count


def fix_percentage_ebitda(cursor, conn, dry_run: bool = False) -> int:
    """Fix EBITDA rows with % unit - these are EBITDA margins, not EBITDA."""
    print("\nStep 3: Reclassifying EBITDA rows with '%' unit to EBITDA Margin...")

    if dry_run:
        cursor.execute("""
            SELECT metric, COUNT(*) as cnt
            FROM financial_tables
            WHERE LOWER(metric) LIKE '%ebitda%'
              AND unit = '%'
            GROUP BY metric
            ORDER BY cnt DESC
        """)
        findings = cursor.fetchall()
        total = sum(cnt for _, cnt in findings)
        print(f"  [DRY RUN] Would reclassify {total:,} rows:")
        for metric, cnt in findings:
            print(f"    {metric} -> {metric} Margin: {cnt:,} rows")
        return total

    # Add "Margin" suffix if not already present
    cursor.execute("""
        UPDATE financial_tables
        SET metric = CASE
                WHEN metric LIKE '%Margin%' THEN metric
                ELSE metric || ' Margin'
            END,
            unit_inferred = TRUE,
            unit_inference_method = 'ebitda_margin_reclassification'
        WHERE LOWER(metric) LIKE '%ebitda%'
          AND unit = '%'
          AND metric NOT LIKE '%Margin%'
    """)
    count = cursor.rowcount
    conn.commit()
    print(f"  Reclassified {count:,} rows to EBITDA Margin")
    return count


def standardize_null_units(cursor, conn, dry_run: bool = False) -> int:
    """Set NULL units on EBITDA metrics to M EUR (default for consolidated reporting)."""
    print("\nStep 4: Setting NULL units to 'M EUR' for EBITDA metrics...")

    if dry_run:
        cursor.execute("""
            SELECT entity_normalized, COUNT(*) as cnt
            FROM financial_tables
            WHERE LOWER(metric) LIKE '%ebitda%'
              AND metric NOT LIKE '%Margin%'
              AND unit IS NULL
            GROUP BY entity_normalized
            ORDER BY cnt DESC
        """)
        findings = cursor.fetchall()
        total = sum(cnt for _, cnt in findings)
        print(f"  [DRY RUN] Would set {total:,} NULL units to 'M EUR':")
        for entity, cnt in findings[:5]:
            print(f"    {entity}: {cnt:,} rows")
        return total

    cursor.execute("""
        UPDATE financial_tables
        SET unit = 'M EUR',
            unit_inferred = TRUE,
            unit_inference_method = 'ebitda_default_meur',
            unit_confidence = 'medium'
        WHERE LOWER(metric) LIKE '%ebitda%'
          AND metric NOT LIKE '%Margin%'
          AND unit IS NULL
    """)
    count = cursor.rowcount
    conn.commit()
    print(f"  Set {count:,} NULL units to 'M EUR'")
    return count


def verify_ebitda_cleanup(cursor) -> dict[str, int]:
    """Verify the EBITDA metrics after cleanup."""
    print("\n" + "=" * 70)
    print("Verification: EBITDA After Scale Reconciliation")
    print("=" * 70)

    results: dict[str, int] = {}

    # Get EBITDA metrics distribution
    cursor.execute("""
        SELECT unit, COUNT(*) as cnt,
               MIN(value) as min_val,
               MAX(value) as max_val,
               AVG(value) as avg_val
        FROM financial_tables
        WHERE LOWER(metric) LIKE '%ebitda%'
          AND metric NOT LIKE '%Margin%'
        GROUP BY unit
        ORDER BY cnt DESC
    """)
    unit_dist = cursor.fetchall()

    print("\n  EBITDA (non-margin) unit distribution after cleanup:")
    print(f"  {'Unit':<15} {'Count':>10} {'Min':>15} {'Max':>15} {'Avg':>15}")
    print("  " + "-" * 70)
    for unit, cnt, min_val, max_val, avg_val in unit_dist:
        unit_display = unit or "(null)"
        min_str = f"{min_val:,.2f}" if min_val else "N/A"
        max_str = f"{max_val:,.2f}" if max_val else "N/A"
        avg_str = f"{avg_val:,.2f}" if avg_val else "N/A"
        print(f"  {unit_display:<15} {cnt:>10,} {min_str:>15} {max_str:>15} {avg_str:>15}")
        results[f"final_ebitda_{unit or 'null'}_count"] = cnt

    # Check M EUR swing ratio (should be reasonable after cleanup)
    cursor.execute("""
        SELECT
            MAX(value) / NULLIF(MIN(value), 0) as swing,
            MIN(value) as min_val,
            MAX(value) as max_val
        FROM financial_tables
        WHERE metric = 'EBITDA IFRS'
          AND entity_normalized = 'Group'
          AND unit = 'M EUR'
          AND value > 0
          AND period LIKE 'YTD Dec%'
    """)
    row = cursor.fetchone()
    if row and row[0]:
        swing, min_val, max_val = row
        results["meur_swing_ratio"] = swing
        print(
            f"\n  M EUR swing ratio (Group, YTD Dec): {swing:.2f}x ({min_val:.0f} to {max_val:.0f})"
        )

    # Check confidence distribution
    cursor.execute("""
        SELECT COALESCE(unit_confidence, 'original') as conf, COUNT(*) as cnt
        FROM financial_tables
        WHERE LOWER(metric) LIKE '%ebitda%'
        GROUP BY COALESCE(unit_confidence, 'original')
        ORDER BY cnt DESC
    """)
    conf_dist = cursor.fetchall()
    print("\n  Confidence distribution for EBITDA metrics:")
    for conf, cnt in conf_dist:
        print(f"    {conf}: {cnt:,}")
        results[f"confidence_{conf}"] = cnt

    return results


def ebitda_scale_reconciliation(
    dry_run: bool = False, create_review: bool = False
) -> dict[str, int]:
    """Run all EBITDA scale reconciliation operations.

    Args:
        dry_run: If True, only print SQL without executing
        create_review: If True, create a review table for suspicious values

    Returns:
        Dict with counts of rows affected by each operation
    """
    from raglite.shared.clients import get_postgresql_connection

    conn = get_postgresql_connection()
    cursor = conn.cursor()
    results: dict[str, int] = {}

    print("\n" + "=" * 70)
    print("Phase 4D: EBITDA Scale Reconciliation")
    print("=" * 70)

    # Analyze initial state
    initial_analysis = analyze_ebitda_scale_issues(cursor)
    results.update({f"initial_{k}": v for k, v in initial_analysis.items()})

    # Create review table if requested
    if create_review:
        results["review_table_rows"] = create_review_table(cursor, conn, dry_run)

    # Execute reconciliation operations
    results["small_keur_converted"] = fix_small_keur_to_meur(cursor, conn, dry_run)
    results["large_keur_flagged"] = flag_suspicious_large_values(cursor, conn, dry_run)
    results["pct_reclassified"] = fix_percentage_ebitda(cursor, conn, dry_run)
    results["null_units_set"] = standardize_null_units(cursor, conn, dry_run)

    # Verify cleanup
    if not dry_run:
        verification = verify_ebitda_cleanup(cursor)
        results.update(verification)

    cursor.close()
    return results


def print_summary(results: dict[str, int], dry_run: bool) -> None:
    """Print summary of all operations."""
    print("\n" + "=" * 70)
    print("PHASE 4D SUMMARY")
    print("=" * 70)

    print(f"\n{'Operation':<40} {'Rows':>15}")
    print("-" * 55)

    # Filter to show only operation results
    ops = [
        "small_keur_converted",
        "large_keur_flagged",
        "pct_reclassified",
        "null_units_set",
        "review_table_rows",
    ]
    for key in ops:
        if key in results:
            print(f"{key:<40} {results[key]:>15,}")

    print("-" * 55)
    total = sum(results.get(k, 0) for k in ops)
    print(f"{'Total rows processed':<40} {total:>15,}")

    # Show swing ratio improvement
    if "meur_swing_ratio" in results:
        print(f"\nM EUR swing ratio after cleanup: {results['meur_swing_ratio']:.2f}x")

    if dry_run:
        print("\n[DRY RUN] No changes were made to the database.")
        print("Run without --dry-run to apply changes.")


def main() -> int:
    """Main entry point."""
    args = parse_args()

    try:
        results = ebitda_scale_reconciliation(
            dry_run=args.dry_run, create_review=args.create_review_table
        )

        print_summary(results, args.dry_run)

        print("\n" + "=" * 70)
        if args.dry_run:
            print("Phase 4D complete (DRY RUN)")
        else:
            print("Phase 4D complete")
        print("=" * 70)
        print("\nNext step: Run scripts/fix_forecasting_variables.py (Phase 4E)")

        return 0

    except Exception as e:
        print(f"\n ERROR: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
