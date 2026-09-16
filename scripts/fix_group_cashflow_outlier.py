#!/usr/bin/env python3
"""Fix GROUP Cash Flow misclassified values causing incorrect forecasts.

Root cause analysis (2026-02-02):
Same issues as EBITDA - YTD/monthly confusion and unit mixing:
- kEUR values misclassified as monthly when they're YTD
- Missing units that should be kEUR or M EUR
- Negative values misclassified
- Invalid unit values ("GROUP" instead of actual unit)

Issues Identified:
| Problem | Record IDs | Value | Issue |
|---------|-----------|-------|-------|
| kEUR misclassified as monthly | 3123 | 14,504 kEUR | Should be YTD Dec-18 |
| Missing unit, wrong period_type | 9549 | 14,467 (blank) | Should be kEUR, YTD Dec-21 |
| Negative kEUR misclassified | 13626 | -2,075 kEUR | Should be YTD Jan-23 |
| Invalid unit ("GROUP") | 1299300 | 16.27 | Unit should be M EUR |

Fix Strategy:
1. NORMALIZE: kEUR values → M EUR (divide by 1000)
2. FIX UNITS: Blank units → infer from magnitude
3. RECLASSIFY: Monthly values that are actually YTD
4. DELETE: Duplicates (monthly ≈ existing YTD within 2%)
5. DELETE: Impossible values (monthly > YTD for same period)
6. FIX: Invalid unit values ("GROUP" → "M EUR")

Usage:
    # Dry run (shows what would be changed):
    source .env && unset APP_ENV && uv run python scripts/fix_group_cashflow_outlier.py --dry-run

    # Apply fix:
    source .env && unset APP_ENV && uv run python scripts/fix_group_cashflow_outlier.py
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
        description="Fix GROUP Cash Flow outlier values causing UnitMixingError"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without making changes",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed analysis",
    )
    return parser.parse_args()


def analyze_cash_flow_data(cursor) -> dict:
    """Analyze Cash Flow data to understand current state."""
    print("\n" + "=" * 70)
    print("Analyzing Cash Flow data for GROUP entity")
    print("=" * 70)

    # Get unit distribution
    cursor.execute("""
        SELECT unit, COUNT(*) as cnt, MIN(value) as min_val, MAX(value) as max_val
        FROM financial_tables
        WHERE metric ILIKE '%cash flow%'
          AND entity_normalized = 'Group'
          AND value_type = 'actual'
        GROUP BY unit
        ORDER BY cnt DESC
    """)

    unit_dist = cursor.fetchall()
    print("\nUnit distribution:")
    for unit, cnt, min_val, max_val in unit_dist:
        unit_str = unit if unit else "(blank)"
        print(f"  {unit_str}: {cnt} rows, range {min_val:.2f} to {max_val:.2f}")

    # Get period_type distribution
    cursor.execute("""
        SELECT period_type, COUNT(*) as cnt
        FROM financial_tables
        WHERE metric ILIKE '%cash flow%'
          AND entity_normalized = 'Group'
          AND value_type = 'actual'
        GROUP BY period_type
        ORDER BY cnt DESC
    """)

    period_dist = cursor.fetchall()
    print("\nPeriod type distribution:")
    for period_type, cnt in period_dist:
        print(f"  {period_type}: {cnt} rows")

    # Calculate swing ratio
    cursor.execute("""
        SELECT
            MAX(value) / NULLIF(MIN(NULLIF(value, 0)), 0) as swing,
            MIN(value) as min_val,
            MAX(value) as max_val,
            COUNT(*) as total
        FROM financial_tables
        WHERE metric ILIKE '%cash flow%'
          AND entity_normalized = 'Group'
          AND value_type = 'actual'
          AND value != 0
    """)

    row = cursor.fetchone()
    swing, min_val, max_val, total = row

    print("\nOverall statistics:")
    print(f"  Total rows: {total}")
    print(f"  Range: {min_val:.2f} to {max_val:.2f}")
    print(f"  Raw swing: {swing:.1f}x" if swing else "  Raw swing: N/A")

    return {
        "unit_distribution": unit_dist,
        "period_distribution": period_dist,
        "swing": swing,
        "min_val": min_val,
        "max_val": max_val,
        "total": total,
    }


def find_keur_to_normalize(cursor) -> list:
    """Find kEUR values that need normalization to M EUR."""
    print("\n" + "=" * 70)
    print("Phase 1: Finding kEUR values to normalize")
    print("=" * 70)

    cursor.execute("""
        SELECT id, period, value, unit, entity, document_id, period_type
        FROM financial_tables
        WHERE metric ILIKE '%cash flow%'
          AND entity_normalized = 'Group'
          AND value_type = 'actual'
          AND LOWER(unit) LIKE '%keur%'
        ORDER BY ABS(value) DESC
        LIMIT 50
    """)

    records = cursor.fetchall()

    if records:
        print(f"\nkEUR records found: {len(records)}")
        for id_, period, value, unit, entity, doc_id, period_type in records[:10]:
            m_eur_value = value / 1000
            print(f"  ID {id_}: {period} = {value:.2f} {unit} → {m_eur_value:.2f} M EUR")
    else:
        print("\nNo kEUR records found.")

    return records


def find_blank_unit_records(cursor) -> list:
    """Find records with blank/missing units."""
    print("\n" + "=" * 70)
    print("Phase 2: Finding records with blank units")
    print("=" * 70)

    cursor.execute("""
        SELECT id, period, value, unit, entity, document_id, period_type
        FROM financial_tables
        WHERE metric ILIKE '%cash flow%'
          AND entity_normalized = 'Group'
          AND value_type = 'actual'
          AND (unit IS NULL OR unit = '' OR TRIM(unit) = '')
        ORDER BY ABS(value) DESC
        LIMIT 50
    """)

    records = cursor.fetchall()

    if records:
        print(f"\nBlank unit records found: {len(records)}")
        for id_, period, value, unit, entity, doc_id, period_type in records[:10]:
            # Infer unit from magnitude
            if abs(value) > 1000:
                inferred = "kEUR (convert to M EUR)"
            else:
                inferred = "M EUR"
            print(f"  ID {id_}: {period} = {value:.2f} → inferred: {inferred}")
    else:
        print("\nNo blank unit records found.")

    return records


def find_invalid_unit_records(cursor) -> list:
    """Find records with invalid unit values (e.g., 'GROUP')."""
    print("\n" + "=" * 70)
    print("Phase 3: Finding records with invalid units")
    print("=" * 70)

    cursor.execute("""
        SELECT id, period, value, unit, entity, document_id, period_type
        FROM financial_tables
        WHERE metric ILIKE '%cash flow%'
          AND entity_normalized = 'Group'
          AND value_type = 'actual'
          AND unit NOT IN ('M EUR', 'kEUR', 'EUR', '')
          AND unit IS NOT NULL
        ORDER BY id
        LIMIT 50
    """)

    records = cursor.fetchall()

    if records:
        print(f"\nInvalid unit records found: {len(records)}")
        for id_, period, value, unit, entity, doc_id, period_type in records[:10]:
            print(f"  ID {id_}: {period} = {value:.2f} '{unit}' → should be M EUR")
    else:
        print("\nNo invalid unit records found.")

    return records


def find_records_to_reclassify(cursor) -> list:
    """Find monthly_actual records that should be reclassified as ytd_actual.

    These are YTD values that were captured without the "YTD" prefix during
    PDF extraction. We identify them by:
    1. Value > 50 M EUR (too high for monthly when annual is similar magnitude)
    2. No existing YTD record for that period (not a duplicate)
    """
    print("\n" + "=" * 70)
    print("Phase 4: Finding records to RECLASSIFY (preserve data)")
    print("=" * 70)

    # Find monthly values > 50M that have NO corresponding YTD value
    cursor.execute("""
        SELECT m.id, m.period, m.value, m.unit, m.entity, m.document_id
        FROM financial_tables m
        WHERE m.metric ILIKE '%cash flow%'
          AND m.entity_normalized = 'Group'
          AND m.period_type = 'monthly_actual'
          AND m.value_type = 'actual'
          AND ABS(m.value) > 50
          AND NOT EXISTS (
              SELECT 1 FROM financial_tables y
              WHERE y.metric ILIKE '%cash flow%'
                AND y.entity_normalized = 'Group'
                AND y.period_type = 'ytd_actual'
                AND y.value_type = 'actual'
                AND REPLACE(y.period, 'YTD ', '') = m.period
          )
        ORDER BY ABS(m.value) DESC
    """)

    reclassify = cursor.fetchall()

    if reclassify:
        print(f"\nRecords to reclassify: {len(reclassify)}")
        for id_, period, value, unit, entity, doc_id in reclassify[:10]:
            print(f"  ID {id_}: {period} = {value:.2f} {unit}")
            print(f"      → Will become: YTD {period}")
    else:
        print("\nNo records need reclassification.")

    return reclassify


def find_duplicates_and_impossible(cursor) -> list:
    """Find records that are duplicates or have impossible values.

    Duplicates: monthly_actual value ≈ ytd_actual value for same period
    Impossible: monthly value > YTD value (cumulative can't be less than single month)
    """
    print("\n" + "=" * 70)
    print("Phase 5: Finding DUPLICATES and IMPOSSIBLE values (to delete)")
    print("=" * 70)

    # Find monthly values that are duplicates of existing YTD values
    cursor.execute("""
        SELECT m.id, m.period, m.value, m.unit, m.entity, m.document_id,
               y.value as ytd_value, y.period as ytd_period
        FROM financial_tables m
        JOIN financial_tables y ON (
            y.metric ILIKE '%cash flow%'
            AND y.entity_normalized = 'Group'
            AND y.period_type = 'ytd_actual'
            AND y.value_type = 'actual'
            AND REPLACE(y.period, 'YTD ', '') = m.period
        )
        WHERE m.metric ILIKE '%cash flow%'
          AND m.entity_normalized = 'Group'
          AND m.period_type = 'monthly_actual'
          AND m.value_type = 'actual'
          AND ABS(m.value) > 10
          AND ABS(m.value - y.value) / GREATEST(ABS(y.value), 0.01) < 0.02
        ORDER BY ABS(m.value) DESC
    """)

    duplicates = cursor.fetchall()

    if duplicates:
        print(f"\nDuplicate records found: {len(duplicates)}")
        for id_, period, value, unit, entity, doc_id, ytd_val, ytd_period in duplicates[:5]:
            print(f"  ID {id_}: {period} = {value:.2f} {unit}")
            print(f"      Duplicate of: {ytd_period} = {ytd_val:.2f}")

    # Find monthly values that are impossible (higher magnitude than YTD)
    cursor.execute("""
        SELECT m.id, m.period, m.value, m.unit, m.entity, m.document_id,
               y.value as ytd_value, y.period as ytd_period
        FROM financial_tables m
        JOIN financial_tables y ON (
            y.metric ILIKE '%cash flow%'
            AND y.entity_normalized = 'Group'
            AND y.period_type = 'ytd_actual'
            AND y.value_type = 'actual'
            AND REPLACE(y.period, 'YTD ', '') = m.period
        )
        WHERE m.metric ILIKE '%cash flow%'
          AND m.entity_normalized = 'Group'
          AND m.period_type = 'monthly_actual'
          AND m.value_type = 'actual'
          AND ABS(m.value) > 30
          AND ABS(m.value) > ABS(y.value) * 1.5
        ORDER BY ABS(m.value) DESC
    """)

    impossible = cursor.fetchall()

    if impossible:
        print(f"\nImpossible records found: {len(impossible)}")
        for id_, period, value, unit, entity, doc_id, ytd_val, ytd_period in impossible[:5]:
            ratio = abs(value / ytd_val) if ytd_val != 0 else float("inf")
            print(f"  ID {id_}: {period} = {value:.2f} {unit}")
            print(f"      YTD for same month: {ytd_period} = {ytd_val:.2f}")
            print(f"      Reason: Monthly is {ratio:.1f}x higher (impossible)")

    # Combine for deletion
    to_delete_map = {}
    for row in duplicates:
        to_delete_map[row[0]] = (row[0], row[1], row[2], row[3], row[4], row[5], "duplicate")
    for row in impossible:
        if row[0] not in to_delete_map:
            to_delete_map[row[0]] = (row[0], row[1], row[2], row[3], row[4], row[5], "impossible")

    return list(to_delete_map.values())


def normalize_keur_to_meur(cursor, conn, records, dry_run: bool) -> int:
    """Normalize kEUR values to M EUR (divide by 1000)."""
    if not records:
        print("\nNo kEUR records to normalize.")
        return 0

    print("\n" + "=" * 70)
    print("Normalizing kEUR values to M EUR")
    print("=" * 70)

    normalized = 0
    for id_, period, value, unit, entity, doc_id, period_type in records:
        new_value = value / 1000
        if dry_run:
            print(f"\n[DRY RUN] Would normalize ID {id_}:")
            print(f"    {value:.2f} {unit} → {new_value:.2f} M EUR")
        else:
            cursor.execute(
                """
                UPDATE financial_tables
                SET value = %s,
                    unit = 'M EUR'
                WHERE id = %s
            """,
                (new_value, id_),
            )
            conn.commit()
            print(f"\nNormalized ID {id_}: {value:.2f} kEUR → {new_value:.2f} M EUR")
            normalized += 1

    return len(records)


def fix_blank_units(cursor, conn, records, dry_run: bool) -> int:
    """Fix records with blank units by inferring from magnitude."""
    if not records:
        print("\nNo blank unit records to fix.")
        return 0

    print("\n" + "=" * 70)
    print("Fixing blank units")
    print("=" * 70)

    fixed = 0
    for id_, period, value, unit, entity, doc_id, period_type in records:
        # Infer unit from magnitude
        if abs(value) > 1000:
            # Large values are likely kEUR, normalize to M EUR
            new_value = value / 1000
            new_unit = "M EUR"
            action = f"{value:.2f} → {new_value:.2f} M EUR"
        else:
            # Smaller values are already in M EUR scale
            new_value = value
            new_unit = "M EUR"
            action = "set unit to M EUR"

        if dry_run:
            print(f"\n[DRY RUN] Would fix ID {id_}: {action}")
        else:
            cursor.execute(
                """
                UPDATE financial_tables
                SET value = %s,
                    unit = %s
                WHERE id = %s
            """,
                (new_value, new_unit, id_),
            )
            conn.commit()
            print(f"\nFixed ID {id_}: {action}")
            fixed += 1

    return len(records)


def fix_invalid_units(cursor, conn, records, dry_run: bool) -> int:
    """Fix records with invalid unit values."""
    if not records:
        print("\nNo invalid unit records to fix.")
        return 0

    print("\n" + "=" * 70)
    print("Fixing invalid units")
    print("=" * 70)

    fixed = 0
    for id_, period, value, unit, entity, doc_id, period_type in records:
        if dry_run:
            print(f"\n[DRY RUN] Would fix ID {id_}: '{unit}' → 'M EUR'")
        else:
            cursor.execute(
                """
                UPDATE financial_tables
                SET unit = 'M EUR'
                WHERE id = %s
            """,
                (id_,),
            )
            conn.commit()
            print(f"\nFixed ID {id_}: '{unit}' → 'M EUR'")
            fixed += 1

    return len(records)


def reclassify_records(cursor, conn, records, dry_run: bool) -> int:
    """Reclassify monthly_actual records as ytd_actual."""
    if not records:
        print("\nNo records to reclassify.")
        return 0

    print("\n" + "=" * 70)
    print("Reclassifying records (monthly_actual → ytd_actual)")
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
    print("Deleting duplicates and impossible values")
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


def verify_fix(cursor) -> None:
    """Verify the fix by checking data quality metrics."""
    print("\n" + "=" * 70)
    print("Verifying fix - Cash Flow data quality")
    print("=" * 70)

    # Check unit distribution after fix
    cursor.execute("""
        SELECT unit, COUNT(*) as cnt
        FROM financial_tables
        WHERE metric ILIKE '%cash flow%'
          AND entity_normalized = 'Group'
          AND value_type = 'actual'
        GROUP BY unit
        ORDER BY cnt DESC
    """)

    unit_dist = cursor.fetchall()
    print("\nPost-fix unit distribution:")
    for unit, cnt in unit_dist:
        unit_str = unit if unit else "(blank)"
        print(f"  {unit_str}: {cnt} rows")

    # Check swing ratio
    cursor.execute("""
        SELECT
            MAX(value) / NULLIF(MIN(NULLIF(value, 0)), 0) as swing,
            MIN(value) as min_val,
            MAX(value) as max_val,
            COUNT(*) as total
        FROM financial_tables
        WHERE metric ILIKE '%cash flow%'
          AND entity_normalized = 'Group'
          AND value_type = 'actual'
          AND value != 0
          AND unit = 'M EUR'
    """)
    row = cursor.fetchone()
    swing, min_val, max_val, total = row

    print("\nPost-fix statistics (M EUR only):")
    print(f"  Total rows: {total}")
    print(f"  Range: {min_val:.2f} to {max_val:.2f} M EUR")
    print(f"  Swing: {swing:.1f}x" if swing else "  Swing: N/A")

    # Check if swing is acceptable
    CASHFLOW_SWING_THRESHOLD = 300.0
    if swing and swing <= CASHFLOW_SWING_THRESHOLD:
        print(f"\n✓ SUCCESS: Swing {swing:.1f}x is below threshold {CASHFLOW_SWING_THRESHOLD}x")
    elif swing:
        print(
            f"\n✗ WARNING: Swing {swing:.1f}x still exceeds threshold {CASHFLOW_SWING_THRESHOLD}x"
        )
        print("  Additional investigation may be needed.")
    else:
        print("\n⚠ WARNING: Could not calculate swing ratio")


def main() -> int:
    """Main entry point."""
    args = parse_args()

    from raglite.shared.clients import get_postgresql_connection

    conn = get_postgresql_connection()
    cursor = conn.cursor()

    try:
        # Analyze current state
        analyze_cash_flow_data(cursor)

        # Track changes
        normalized_count = 0
        blank_fixed_count = 0
        invalid_fixed_count = 0
        reclassified_count = 0
        deleted_count = 0

        # Phase 1: Normalize kEUR to M EUR
        keur_records = find_keur_to_normalize(cursor)
        if keur_records:
            normalized_count = normalize_keur_to_meur(cursor, conn, keur_records, args.dry_run)

        # Phase 2: Fix blank units
        blank_records = find_blank_unit_records(cursor)
        if blank_records:
            blank_fixed_count = fix_blank_units(cursor, conn, blank_records, args.dry_run)

        # Phase 3: Fix invalid units
        invalid_records = find_invalid_unit_records(cursor)
        if invalid_records:
            invalid_fixed_count = fix_invalid_units(cursor, conn, invalid_records, args.dry_run)

        # Phase 4: Reclassify misclassified monthly values
        to_reclassify = find_records_to_reclassify(cursor)
        if to_reclassify:
            reclassified_count = reclassify_records(cursor, conn, to_reclassify, args.dry_run)

        # Phase 5: Delete duplicates and impossible values
        to_delete = find_duplicates_and_impossible(cursor)
        if to_delete:
            deleted_count = delete_records(cursor, conn, to_delete, args.dry_run)

        # Verify fix
        if not args.dry_run:
            verify_fix(cursor)

        # Summary
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        if args.dry_run:
            print(f"[DRY RUN] Would normalize: {normalized_count} kEUR record(s)")
            print(f"[DRY RUN] Would fix blank units: {blank_fixed_count} record(s)")
            print(f"[DRY RUN] Would fix invalid units: {invalid_fixed_count} record(s)")
            print(f"[DRY RUN] Would reclassify: {reclassified_count} record(s)")
            print(f"[DRY RUN] Would delete: {deleted_count} record(s)")
            print("\nRun without --dry-run to apply changes.")
        else:
            print(f"Normalized kEUR to M EUR: {normalized_count} record(s)")
            print(f"Fixed blank units: {blank_fixed_count} record(s)")
            print(f"Fixed invalid units: {invalid_fixed_count} record(s)")
            print(f"Reclassified: {reclassified_count} record(s)")
            print(f"Deleted: {deleted_count} record(s)")
            print(
                f"\nTotal modified: {normalized_count + blank_fixed_count + invalid_fixed_count + reclassified_count}"
            )
            print(f"Total removed: {deleted_count}")
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
