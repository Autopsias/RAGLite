#!/usr/bin/env python3
"""Fix GROUP EBITDA misclassified values causing incorrect forecasts.

Root cause analysis (2026-02-02):
Phase 1 - Fixed YTD outlier:
- YTD Nov-23 value of 6651 M EUR was 42x higher than any other YTD value
- Deleted as data corruption

Phase 2 - Fix monthly_actual misclassifications:
- Monthly EBITDA range should be 10-30 M EUR (annual ~160M / 12 months)
- Values like 75.96, 87.91, 89.00 M EUR are IMPOSSIBLE for single months
- Root cause: PDF extraction captured YTD values without "YTD" prefix
- Period classifier saw "Jun-24" and classified as monthly_actual

Fix Strategy:
1. RECLASSIFY: Records with no existing YTD (preserve as ytd_actual)
2. DELETE: Duplicates (monthly ≈ existing YTD within 2%)
3. DELETE: Impossible values (monthly > YTD for same period)

Usage:
    # Dry run (shows what would be changed):
    source .env && unset APP_ENV && uv run python scripts/fix_group_ebitda_outlier.py --dry-run

    # Apply fix:
    source .env && unset APP_ENV && uv run python scripts/fix_group_ebitda_outlier.py
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
        description="Fix GROUP EBITDA outlier value causing UnitMixingError"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without making changes",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed analysis",
    )
    return parser.parse_args()


def find_records_to_reclassify(cursor) -> list:
    """Find monthly_actual records that should be reclassified as ytd_actual.

    These are YTD values that were captured without the "YTD" prefix during
    PDF extraction. We identify them by:
    1. Value > 50 M EUR (too high for monthly when annual is ~160M)
    2. No existing YTD record for that period (not a duplicate)
    """
    print("\n" + "=" * 70)
    print("Phase 1: Finding records to RECLASSIFY (preserve data)")
    print("=" * 70)

    # Find monthly values > 50M that have NO corresponding YTD value
    # These are likely misclassified YTD values we should preserve
    cursor.execute("""
        SELECT m.id, m.period, m.value, m.unit, m.entity, m.document_id
        FROM financial_tables m
        WHERE m.metric = 'EBITDA IFRS'
          AND m.entity_normalized = 'Group'
          AND m.period_type = 'monthly_actual'
          AND m.value_type = 'actual'
          AND m.value > 50
          AND NOT EXISTS (
              SELECT 1 FROM financial_tables y
              WHERE y.metric = 'EBITDA IFRS'
                AND y.entity_normalized = 'Group'
                AND y.period_type = 'ytd_actual'
                AND y.value_type = 'actual'
                AND REPLACE(y.period, 'YTD ', '') = m.period
          )
        ORDER BY m.value DESC
    """)

    reclassify = cursor.fetchall()

    if reclassify:
        print(f"\nRecords to reclassify: {len(reclassify)}")
        for id_, period, value, unit, entity, doc_id in reclassify:
            print(f"  ID {id_}: {period} = {value:.2f} {unit}")
            print(f"      → Will become: YTD {period}")
            print(f"      Document: {doc_id}")
    else:
        print("\nNo records need reclassification.")

    return reclassify


def find_duplicates_and_impossible(cursor) -> list:
    """Find records that are duplicates or have impossible values.

    Duplicates: monthly_actual value ≈ ytd_actual value for same period
    Impossible: monthly value > YTD value (cumulative can't be less than single month)
    """
    print("\n" + "=" * 70)
    print("Phase 2: Finding DUPLICATES and IMPOSSIBLE values (to delete)")
    print("=" * 70)

    # Find monthly values that are duplicates of existing YTD values
    # (within 1% tolerance for floating point comparison)
    cursor.execute("""
        SELECT m.id, m.period, m.value, m.unit, m.entity, m.document_id,
               y.value as ytd_value, y.period as ytd_period
        FROM financial_tables m
        JOIN financial_tables y ON (
            y.metric = 'EBITDA IFRS'
            AND y.entity_normalized = 'Group'
            AND y.period_type = 'ytd_actual'
            AND y.value_type = 'actual'
            AND REPLACE(y.period, 'YTD ', '') = m.period
        )
        WHERE m.metric = 'EBITDA IFRS'
          AND m.entity_normalized = 'Group'
          AND m.period_type = 'monthly_actual'
          AND m.value_type = 'actual'
          AND m.value > 50
          AND ABS(m.value - y.value) / GREATEST(y.value, 0.01) < 0.02
        ORDER BY m.value DESC
    """)

    duplicates = cursor.fetchall()

    if duplicates:
        print(f"\nDuplicate records found: {len(duplicates)}")
        for id_, period, value, unit, entity, doc_id, ytd_val, ytd_period in duplicates:
            print(f"  ID {id_}: {period} = {value:.2f} {unit}")
            print(f"      Duplicate of: {ytd_period} = {ytd_val:.2f} {unit}")
            print("      Reason: Values within 2% (same data point)")

    # Find monthly values that are impossible (higher than YTD for that month)
    cursor.execute("""
        SELECT m.id, m.period, m.value, m.unit, m.entity, m.document_id,
               y.value as ytd_value, y.period as ytd_period
        FROM financial_tables m
        JOIN financial_tables y ON (
            y.metric = 'EBITDA IFRS'
            AND y.entity_normalized = 'Group'
            AND y.period_type = 'ytd_actual'
            AND y.value_type = 'actual'
            AND REPLACE(y.period, 'YTD ', '') = m.period
        )
        WHERE m.metric = 'EBITDA IFRS'
          AND m.entity_normalized = 'Group'
          AND m.period_type = 'monthly_actual'
          AND m.value_type = 'actual'
          AND m.value > 30
          AND m.value > y.value * 1.5
        ORDER BY m.value DESC
    """)

    impossible = cursor.fetchall()

    if impossible:
        print(f"\nImpossible records found: {len(impossible)}")
        for id_, period, value, unit, entity, doc_id, ytd_val, ytd_period in impossible:
            ratio = value / ytd_val if ytd_val > 0 else float("inf")
            print(f"  ID {id_}: {period} = {value:.2f} {unit}")
            print(f"      YTD for same month: {ytd_period} = {ytd_val:.2f} {unit}")
            print(f"      Reason: Monthly is {ratio:.1f}x higher than YTD (impossible)")

    # Combine for deletion (extract just the IDs and basic info)
    # Use dict to deduplicate by ID (same record may appear in both lists)
    to_delete_map = {}
    for row in duplicates:
        to_delete_map[row[0]] = (row[0], row[1], row[2], row[3], row[4], row[5], "duplicate")
    for row in impossible:
        if row[0] not in to_delete_map:  # Don't overwrite if already marked as duplicate
            to_delete_map[row[0]] = (row[0], row[1], row[2], row[3], row[4], row[5], "impossible")

    return list(to_delete_map.values())


def analyze_monthly_outliers(cursor) -> list:
    """Analyze monthly_actual values to identify misclassified annual values.

    Monthly EBITDA for GROUP should be ~10-30 M EUR. Values > 100 M EUR
    are likely misclassified YTD or annual values.
    """
    print("\n" + "=" * 70)
    print("Analyzing Monthly EBITDA values for GROUP entity")
    print("=" * 70)

    # Get statistics for monthly values
    cursor.execute("""
        SELECT
            COUNT(*) as total,
            AVG(value) as avg_val,
            STDDEV(value) as std_dev,
            MIN(value) as min_val,
            MAX(value) as max_val,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY value) as median
        FROM financial_tables
        WHERE metric = 'EBITDA IFRS'
          AND entity_normalized = 'Group'
          AND period_type = 'monthly_actual'
          AND value_type = 'actual'
          AND value > 0
    """)
    row = cursor.fetchone()
    total, avg_val, std_dev, min_val, max_val, median = row

    print("\nMonthly Statistics:")
    print(f"  Total rows: {total}")
    print(f"  Average: {avg_val:.2f} M EUR")
    print(f"  Median: {median:.2f} M EUR")
    print(f"  Range: {min_val:.2f} to {max_val:.2f} M EUR")

    # Use domain knowledge: Monthly EBITDA > 100M is suspicious
    # Normal monthly EBITDA is ~10-30M based on YTD ~160M/year pattern
    monthly_threshold = 100.0

    print(f"\nMonthly outlier threshold (domain knowledge): {monthly_threshold:.2f} M EUR")
    print("  (Normal monthly EBITDA is ~10-30M based on ~160M annual)")

    cursor.execute(
        """
        SELECT id, period, value, unit, entity, document_id
        FROM financial_tables
        WHERE metric = 'EBITDA IFRS'
          AND entity_normalized = 'Group'
          AND period_type = 'monthly_actual'
          AND value_type = 'actual'
          AND value > %s
    """,
        (monthly_threshold,),
    )

    outliers = cursor.fetchall()

    if outliers:
        print(f"\nMonthly outliers found: {len(outliers)}")
        for id_, period, value, unit, entity, doc_id in outliers:
            print(f"  ID {id_}: {period} = {value:.2f} {unit}")
            print(f"      Document: {doc_id}")
    else:
        print("\nNo monthly outliers found.")

    return outliers


def analyze_ytd_values(cursor) -> dict:
    """Analyze YTD values to identify outliers."""
    print("\n" + "=" * 70)
    print("Analyzing YTD EBITDA values for GROUP entity")
    print("=" * 70)

    # Get statistics
    cursor.execute("""
        SELECT
            COUNT(*) as total,
            AVG(value) as avg_val,
            STDDEV(value) as std_dev,
            MIN(value) as min_val,
            MAX(value) as max_val,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY value) as median
        FROM financial_tables
        WHERE metric = 'EBITDA IFRS'
          AND entity_normalized = 'Group'
          AND period_type = 'ytd_actual'
          AND value_type = 'actual'
          AND value > 0
    """)
    row = cursor.fetchone()
    total, avg_val, std_dev, min_val, max_val, median = row

    print("\nYTD Statistics (with outlier):")
    print(f"  Total rows: {total}")
    print(f"  Average: {avg_val:.2f} M EUR")
    print(f"  Std Dev: {std_dev:.2f} M EUR")
    print(f"  Median: {median:.2f} M EUR")
    print(f"  Range: {min_val:.2f} to {max_val:.2f} M EUR")

    # Identify outliers (> 3 std deviations from mean)
    outlier_threshold = avg_val + 3 * std_dev
    print(f"\nOutlier threshold (mean + 3σ): {outlier_threshold:.2f} M EUR")

    cursor.execute(
        """
        SELECT id, period, value, unit, entity, document_id
        FROM financial_tables
        WHERE metric = 'EBITDA IFRS'
          AND entity_normalized = 'Group'
          AND period_type = 'ytd_actual'
          AND value_type = 'actual'
          AND value > %s
    """,
        (outlier_threshold,),
    )

    outliers = cursor.fetchall()

    if outliers:
        print(f"\nOutliers found: {len(outliers)}")
        for id_, period, value, unit, entity, doc_id in outliers:
            print(f"  ID {id_}: {period} = {value:.2f} {unit}")
            print(f"      Entity: {entity}")
            print(f"      Document: {doc_id}")
    else:
        print("\nNo outliers found.")

    # Calculate statistics without outliers
    cursor.execute(
        """
        SELECT
            COUNT(*) as total,
            AVG(value) as avg_val,
            STDDEV(value) as std_dev,
            MIN(value) as min_val,
            MAX(value) as max_val
        FROM financial_tables
        WHERE metric = 'EBITDA IFRS'
          AND entity_normalized = 'Group'
          AND period_type = 'ytd_actual'
          AND value_type = 'actual'
          AND value > 0
          AND value <= %s
    """,
        (outlier_threshold,),
    )
    row = cursor.fetchone()
    clean_total, clean_avg, clean_std, clean_min, clean_max = row

    print("\nYTD Statistics (without outliers):")
    print(f"  Total rows: {clean_total}")
    print(f"  Average: {clean_avg:.2f} M EUR")
    print(f"  Std Dev: {clean_std:.2f} M EUR")
    print(f"  Range: {clean_min:.2f} to {clean_max:.2f} M EUR")
    print(f"  Expected swing: {clean_max / clean_min:.1f}x")

    return {
        "outlier_threshold": outlier_threshold,
        "outliers": outliers,
        "clean_stats": {
            "total": clean_total,
            "avg": clean_avg,
            "max": clean_max,
            "min": clean_min,
        },
    }


def reclassify_records(cursor, conn, records, dry_run: bool) -> int:
    """Reclassify monthly_actual records as ytd_actual.

    These are YTD values that were captured without the "YTD" prefix.
    """
    if not records:
        print("\nNo records to reclassify.")
        return 0

    print("\n" + "=" * 70)
    print("Phase 3: Reclassifying records (monthly_actual → ytd_actual)")
    print("=" * 70)

    reclassified = 0
    for id_, period, value, unit, entity, doc_id in records:
        new_period = f"YTD {period}"
        if dry_run:
            print(f"\n[DRY RUN] Would reclassify ID {id_}:")
            print(f"    {period} → {new_period}")
            print("    period_type: monthly_actual → ytd_actual")
        else:
            cursor.execute(
                """
                UPDATE financial_tables
                SET period = %s,
                    period_type = 'ytd_actual'
                WHERE id = %s
            """,
                (new_period, id_),
            )
            conn.commit()
            print(f"\nReclassified ID {id_}: {period} → {new_period}")
            reclassified += 1

    return len(records)


def delete_records(cursor, conn, records, dry_run: bool) -> int:
    """Delete duplicate or impossible records."""
    if not records:
        print("\nNo records to delete.")
        return 0

    print("\n" + "=" * 70)
    print("Phase 4: Deleting duplicates and impossible values")
    print("=" * 70)

    for id_, period, value, unit, entity, doc_id, reason in records:
        if dry_run:
            print(f"\n[DRY RUN] Would delete ID {id_}: {period} = {value:.2f} {unit}")
            print(f"    Reason: {reason}")
        else:
            cursor.execute("DELETE FROM financial_tables WHERE id = %s", (id_,))
            conn.commit()
            print(f"\nDeleted ID {id_}: {period} = {value:.2f} {unit} ({reason})")

    return len(records)


def find_duplicate_sep24_records(cursor) -> list:
    """Find duplicate Sep-24 records to remove (keep only one)."""
    print("\n" + "=" * 70)
    print("Phase 2b: Finding duplicate Sep-24 records")
    print("=" * 70)

    cursor.execute("""
        SELECT id, period, value, unit, entity, document_id
        FROM financial_tables
        WHERE metric = 'EBITDA IFRS'
          AND entity_normalized = 'Group'
          AND period_type = 'monthly_actual'
          AND period = 'Sep-24'
          AND value = 39.35
        ORDER BY id
    """)

    duplicates = cursor.fetchall()

    if len(duplicates) > 1:
        # Keep the first one, delete the rest
        to_delete = []
        print(f"\nFound {len(duplicates)} Sep-24 records with value 39.35:")
        for i, (id_, period, value, unit, entity, doc_id) in enumerate(duplicates):
            if i == 0:
                print(f"  ID {id_}: {period} = {value:.2f} {unit} → KEEP")
            else:
                print(f"  ID {id_}: {period} = {value:.2f} {unit} → DELETE")
                to_delete.append((id_, period, value, unit, entity, doc_id, "duplicate"))
        return to_delete

    print("\nNo duplicate Sep-24 records found.")
    return []


def find_impossible_ytd_progression(cursor) -> list:
    """Find YTD values that break cumulative progression.

    YTD values must increase monotonically within a year. If Jan YTD > Feb YTD,
    or if Jan YTD is > 50% of full year, it's clearly wrong.
    """
    print("\n" + "=" * 70)
    print("Phase 2c: Finding YTD values that break cumulative progression")
    print("=" * 70)

    to_delete = []

    # Check for Jan YTD values that are impossibly high
    # Jan YTD should be ~8-10% of full year (1 month / 12 months)
    # Flag if Jan YTD > 30% of Dec YTD for same year
    cursor.execute("""
        SELECT j.id, j.period, j.value, j.unit, j.entity, j.document_id,
               d.value as dec_value, d.period as dec_period
        FROM financial_tables j
        JOIN financial_tables d ON (
            d.metric = 'EBITDA IFRS'
            AND d.entity_normalized = 'Group'
            AND d.period_type = 'ytd_actual'
            AND d.period LIKE 'YTD Dec-' || SUBSTRING(j.period FROM 9 FOR 2)
        )
        WHERE j.metric = 'EBITDA IFRS'
          AND j.entity_normalized = 'Group'
          AND j.period_type = 'ytd_actual'
          AND j.period LIKE 'YTD Jan-%'
          AND j.value > d.value * 0.30
    """)

    impossible = cursor.fetchall()

    if impossible:
        print(f"\nImpossible Jan YTD values found: {len(impossible)}")
        for id_, period, value, unit, entity, doc_id, dec_val, dec_period in impossible:
            pct = (value / dec_val * 100) if dec_val > 0 else float("inf")
            print(f"  ID {id_}: {period} = {value:.2f} {unit}")
            print(f"      Full year ({dec_period}): {dec_val:.2f} {unit}")
            print(f"      Reason: Jan is {pct:.0f}% of full year (expected ~8%)")
            to_delete.append((id_, period, value, unit, entity, doc_id, "impossible_ytd"))
    else:
        print("\nNo impossible Jan YTD values found.")

    # Check for Feb YTD values that are > 50% of full year (impossible)
    cursor.execute("""
        SELECT f.id, f.period, f.value, f.unit, f.entity, f.document_id,
               d.value as dec_value, d.period as dec_period
        FROM financial_tables f
        JOIN financial_tables d ON (
            d.metric = 'EBITDA IFRS'
            AND d.entity_normalized = 'Group'
            AND d.period_type = 'ytd_actual'
            AND d.period LIKE 'YTD Dec-' || SUBSTRING(f.period FROM 9 FOR 2)
        )
        WHERE f.metric = 'EBITDA IFRS'
          AND f.entity_normalized = 'Group'
          AND f.period_type = 'ytd_actual'
          AND f.period LIKE 'YTD Feb-%'
          AND f.value > d.value * 0.50
    """)

    feb_impossible = cursor.fetchall()

    if feb_impossible:
        print(f"\nImpossible Feb YTD values found: {len(feb_impossible)}")
        for id_, period, value, unit, entity, doc_id, dec_val, dec_period in feb_impossible:
            pct = (value / dec_val * 100) if dec_val > 0 else float("inf")
            print(f"  ID {id_}: {period} = {value:.2f} {unit}")
            print(f"      Full year ({dec_period}): {dec_val:.2f} {unit}")
            print(f"      Reason: Feb is {pct:.0f}% of full year (expected ~16%)")
            to_delete.append((id_, period, value, unit, entity, doc_id, "impossible_ytd"))

    # Check for YTD values that break cumulative progression
    # (a later month should never be less than an earlier month)
    # Look for May values less than Apr, Jun less than May, etc.
    cursor.execute("""
        WITH month_order AS (
            SELECT id, period, value, unit, entity, document_id,
                   CASE
                       WHEN period LIKE 'YTD Jan%' THEN 1
                       WHEN period LIKE 'YTD Feb%' THEN 2
                       WHEN period LIKE 'YTD Mar%' THEN 3
                       WHEN period LIKE 'YTD Apr%' THEN 4
                       WHEN period LIKE 'YTD May%' THEN 5
                       WHEN period LIKE 'YTD Jun%' THEN 6
                       WHEN period LIKE 'YTD Jul%' THEN 7
                       WHEN period LIKE 'YTD Aug%' THEN 8
                       WHEN period LIKE 'YTD Sep%' THEN 9
                       WHEN period LIKE 'YTD Oct%' THEN 10
                       WHEN period LIKE 'YTD Nov%' THEN 11
                       WHEN period LIKE 'YTD Dec%' THEN 12
                   END as month_num,
                   SUBSTRING(period FROM 9 FOR 2) as year
            FROM financial_tables
            WHERE metric = 'EBITDA IFRS'
              AND entity_normalized = 'Group'
              AND period_type = 'ytd_actual'
              AND unit = 'M EUR'
              AND value > 0
        )
        SELECT m.id, m.period, m.value, m.unit, m.entity, m.document_id,
               p.value as prior_value, p.period as prior_period
        FROM month_order m
        JOIN month_order p ON (
            p.year = m.year
            AND p.month_num = m.month_num - 1
        )
        WHERE m.value < p.value * 0.5
          AND m.month_num > 1  -- Skip January
    """)

    progression_breaks = cursor.fetchall()

    if progression_breaks:
        # Deduplicate by ID (same record may match multiple prior month values)
        seen_ids = set()
        unique_breaks = []
        for row in progression_breaks:
            if row[0] not in seen_ids:
                seen_ids.add(row[0])
                unique_breaks.append(row)

        print(f"\nYTD progression breaks found: {len(unique_breaks)}")
        for id_, period, value, unit, entity, doc_id, prior_val, prior_period in unique_breaks:
            print(f"  ID {id_}: {period} = {value:.2f} {unit}")
            print(f"      Prior month ({prior_period}): {prior_val:.2f} {unit}")
            print("      Reason: Value dropped (cumulative should only increase)")
            to_delete.append((id_, period, value, unit, entity, doc_id, "progression_break"))

    return to_delete


def fix_outliers(cursor, conn, outliers, dry_run: bool) -> int:
    """Delete outlier records (legacy function for YTD outliers)."""
    if not outliers:
        print("\nNo outliers to fix.")
        return 0

    print("\n" + "=" * 70)
    print("Fixing YTD outliers")
    print("=" * 70)

    for id_, period, value, unit, entity, doc_id in outliers:
        if dry_run:
            print(f"\n[DRY RUN] Would delete ID {id_}: {period} = {value:.2f} {unit}")
        else:
            cursor.execute("DELETE FROM financial_tables WHERE id = %s", (id_,))
            conn.commit()
            print(f"\nDeleted ID {id_}: {period} = {value:.2f} {unit}")

    return len(outliers)


def verify_fix(cursor, metric: str = "EBITDA") -> None:
    """Verify the fix by simulating extraction."""
    print("\n" + "=" * 70)
    print("Verifying fix - Simulating GROUP EBITDA extraction")
    print("=" * 70)

    # Check remaining YTD values
    cursor.execute("""
        SELECT
            MAX(value) / MIN(value) as swing,
            MIN(value) as min_val,
            MAX(value) as max_val,
            COUNT(*) as total
        FROM financial_tables
        WHERE metric = 'EBITDA IFRS'
          AND entity_normalized = 'Group'
          AND period_type IN ('ytd_actual', 'monthly_actual')
          AND value_type = 'actual'
          AND value > 0
    """)
    row = cursor.fetchone()
    swing, min_val, max_val, total = row

    print("\nPost-fix statistics:")
    print(f"  Total rows: {total}")
    print(f"  Range: {min_val:.2f} to {max_val:.2f} M EUR")
    print(f"  Raw swing: {swing:.1f}x")

    # Check if swing is below threshold
    EBITDA_SWING_THRESHOLD = 300.0
    if swing <= EBITDA_SWING_THRESHOLD:
        print(f"\n✓ SUCCESS: Swing {swing:.1f}x is below threshold {EBITDA_SWING_THRESHOLD}x")
    else:
        print(f"\n✗ WARNING: Swing {swing:.1f}x still exceeds threshold {EBITDA_SWING_THRESHOLD}x")
        print("  Additional investigation may be needed.")


def main() -> int:
    """Main entry point."""
    args = parse_args()

    from raglite.shared.clients import get_postgresql_connection

    conn = get_postgresql_connection()
    cursor = conn.cursor()

    try:
        reclassified_count = 0
        deleted_count = 0

        # Phase 1: Find records to RECLASSIFY (no existing YTD)
        to_reclassify = find_records_to_reclassify(cursor)
        if to_reclassify:
            reclassified_count = reclassify_records(cursor, conn, to_reclassify, args.dry_run)

        # Phase 2: Find duplicates and impossible values to DELETE
        to_delete = find_duplicates_and_impossible(cursor)

        # Phase 2b: Find duplicate Sep-24 records
        sep24_duplicates = find_duplicate_sep24_records(cursor)
        to_delete.extend(sep24_duplicates)

        # Phase 2c: Find YTD values that break cumulative progression
        impossible_ytd = find_impossible_ytd_progression(cursor)
        to_delete.extend(impossible_ytd)

        if to_delete:
            deleted_count = delete_records(cursor, conn, to_delete, args.dry_run)

        # Legacy: Analyze and fix YTD outliers (e.g., 6651 M EUR)
        analysis = analyze_ytd_values(cursor)
        if analysis["outliers"]:
            fixed_count = fix_outliers(cursor, conn, analysis["outliers"], args.dry_run)
            deleted_count += fixed_count

        # Verify fix
        if not args.dry_run:
            verify_fix(cursor)

        # Summary
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        if args.dry_run:
            print(f"[DRY RUN] Would reclassify: {reclassified_count} record(s)")
            print(f"[DRY RUN] Would delete: {deleted_count} record(s)")
            print("\nRun without --dry-run to apply changes.")
        else:
            print(f"Reclassified: {reclassified_count} record(s)")
            print(f"Deleted: {deleted_count} record(s)")
            print(f"Total data preserved: {reclassified_count}")
            print(f"Total records removed: {deleted_count}")
        print("=" * 70)

        return 0

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback

        traceback.print_exc()
        return 1
    finally:
        cursor.close()


if __name__ == "__main__":
    sys.exit(main())
