#!/usr/bin/env python3
"""Phase A: Standardize unit variants and clean contaminated units.

This script:
1. Standardizes unit variants to canonical forms (K EUR → kEUR, MEUR → M EUR)
2. Cleans entity name contamination (GROUP, ANGOLA, etc. → NULL)
3. Fixes malformed percentage units ("% -" → "%")
4. NULLs out invalid decimal fragments (.1, .5, etc.)

Prerequisites:
    - Run fix_unit_audit_columns.py first to preserve original units

Usage:
    POSTGRES_USER=raglite POSTGRES_PASSWORD=raglite POSTGRES_DB=raglite POSTGRES_PORT=5432 \
        uv run python scripts/fix_unit_standardization.py

    # Dry run (show SQL without executing):
    POSTGRES_USER=raglite POSTGRES_PASSWORD=raglite POSTGRES_DB=raglite POSTGRES_PORT=5432 \
        uv run python scripts/fix_unit_standardization.py --dry-run
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

# Suppress verbose logging unless DEBUG is set
if not os.getenv("DEBUG"):
    logging.getLogger("raglite").setLevel(logging.WARNING)


# Standardization mappings: variant → canonical form
UNIT_STANDARDIZATION: dict[str, str] = {
    # kEUR variants → canonical kEUR
    "K EUR": "kEUR",
    "KEUR": "kEUR",
    "Keur": "kEUR",
    "k EUR": "kEUR",
    "keur": "kEUR",
    "1000 EUR": "kEUR",
    "1,000 EUR": "kEUR",
    "thousand EUR": "kEUR",
    "K€": "kEUR",
    "k€": "kEUR",
    # MEUR variants → canonical M EUR
    "MEUR": "M EUR",
    "Meur": "M EUR",
    "meur": "M EUR",
    "M€": "M EUR",
    "m€": "M EUR",
    "m EUR": "M EUR",
    "Million EUR": "M EUR",
    "million EUR": "M EUR",
    "Millions EUR": "M EUR",
    "EUR M": "M EUR",
    "EUR m": "M EUR",
    "EUR millions": "M EUR",
    # EUR variants → canonical EUR
    "Eur": "EUR",
    "eur": "EUR",
    "€": "EUR",
    "Euro": "EUR",
    "euro": "EUR",
    "EURO": "EUR",
    # Percentage variants → canonical %
    "percent": "%",
    "Percent": "%",
    "pct": "%",
    "Pct": "%",
    "PCT": "%",
    "percentage": "%",
    "pp": "pp",  # Percentage points (keep as is)
    # Production units - standardize
    "Kton": "kton",
    "KTON": "kton",
    "kt": "kton",
    "KT": "kton",
    "Mton": "Mton",
    "MTON": "Mton",
    "Mt": "Mton",
    "MT": "Mton",
    "ton": "ton",
    "Ton": "ton",
    "TON": "ton",
    "tonnes": "ton",
    "Tonnes": "ton",
    # Energy units - standardize
    "GWH": "GWh",
    "gwh": "GWh",
    "Gwh": "GWh",
    "MWH": "MWh",
    "mwh": "MWh",
    "Mwh": "MWh",
    "KWH": "kWh",
    "kwh": "kWh",
    "Kwh": "kWh",
    "GJ": "GJ",
    "gj": "GJ",
    "Gj": "GJ",
}

# Entity names that contaminate the unit column (should be NULL)
CONTAMINATED_UNITS: set[str] = {
    # Geographic entities
    "GROUP",
    "Group",
    "group",
    "ANGOLA",
    "Angola",
    "TUNISIA",
    "Tunisia",
    "LEBANON",
    "Lebanon",
    "PORTUGAL",
    "Portugal",
    "BRAZIL",
    "Brazil",
    "EGYPT",
    "Egypt",
    "SPAIN",
    "Spain",
    "MOROCCO",
    "Morocco",
    "ALGERIA",
    "Algeria",
    # Business segment contamination
    "Intercompany/Forex/Adj.",
    "Intercompany",
    "Forex",
    "Adj.",
    "Adjustment",
    "Adjustments",
    "Eliminations",
    "Consolidation",
    "Corporate",
    # Invalid/placeholder values
    "N/A",
    "n/a",
    "NA",
    "na",
    "N.A.",
    "-",
    "--",
    "---",
    "x",
    "X",
    "xx",
    "XX",
    "xxx",
    "XXX",
    "TBD",
    "tbd",
    "TBC",
    "Unknown",
    "unknown",
    "UNKNOWN",
    "null",
    "NULL",
    "None",
    "none",
    "NONE",
    "",
    " ",
    "  ",
}

# Malformed percentage patterns to fix
MALFORMED_PERCENTAGE_PATTERNS: list[tuple[str, str]] = [
    # Pattern: units containing "%" with extra characters
    ("% -", "%"),
    ("%  0%", "%"),
    ("% B", "%"),
    ("% LY", "%"),
    ("% vs", "%"),
    ("% vs.", "%"),
    ("% YoY", "%"),
    ("% yoy", "%"),
    ("% vs LY", "%"),
    ("% vs PY", "%"),
    ("% var", "%"),
    ("% Var", "%"),
    ("%  ", "%"),
    ("% ", "%"),
]


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Standardize unit variants and clean contaminated units"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show SQL statements without executing them",
    )
    return parser.parse_args()


def check_prerequisites(cursor) -> bool:
    """Check that audit columns exist before proceeding."""
    cursor.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'financial_tables'
          AND column_name = 'unit_original'
    """)
    return cursor.fetchone() is not None


def standardize_units(dry_run: bool = False) -> dict[str, int]:
    """Standardize unit variants and clean contaminated values.

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
    print("Phase A: Unit Standardization")
    print("=" * 70)

    # Check prerequisites
    if not check_prerequisites(cursor):
        print("\n✗ ERROR: Audit columns not found!")
        print("  Run fix_unit_audit_columns.py first to preserve original units.")
        return {"error": 1}

    # Step 1: Show current unit distribution
    print("\nStep 1: Current unit distribution (top 30)...")
    cursor.execute("""
        SELECT unit, COUNT(*) as cnt
        FROM financial_tables
        WHERE unit IS NOT NULL AND unit != ''
        GROUP BY unit
        ORDER BY cnt DESC
        LIMIT 30
    """)
    units = cursor.fetchall()
    print(f"  {'Unit':<30} {'Count':>10}")
    print("  " + "-" * 42)
    for unit_val, cnt in units:
        # Highlight units that will be modified
        marker = ""
        if unit_val in UNIT_STANDARDIZATION:
            marker = " → " + UNIT_STANDARDIZATION[unit_val]
        elif unit_val in CONTAMINATED_UNITS:
            marker = " → NULL (contaminated)"
        print(f"  {unit_val:<30} {cnt:>10}{marker}")

    # Step 2: Apply unit standardization
    print("\nStep 2: Applying unit standardization mappings...")
    total_standardized = 0

    for variant, canonical in UNIT_STANDARDIZATION.items():
        # Build SQL for this mapping
        update_sql = """
            UPDATE financial_tables
            SET unit = %s,
                unit_inferred = TRUE,
                unit_inference_method = 'standardization',
                unit_confidence = 'high'
            WHERE unit = %s
              AND (unit_inferred IS NULL OR unit_inferred = FALSE)
        """

        if dry_run:
            # Count how many would be affected
            cursor.execute(
                """
                SELECT COUNT(*) FROM financial_tables
                WHERE unit = %s AND (unit_inferred IS NULL OR unit_inferred = FALSE)
            """,
                (variant,),
            )
            count = cursor.fetchone()[0]
            if count > 0:
                print(f"  [DRY RUN] '{variant}' → '{canonical}': {count:,} rows")
                total_standardized += count
        else:
            cursor.execute(update_sql, (canonical, variant))
            if cursor.rowcount > 0:
                print(f"  '{variant}' → '{canonical}': {cursor.rowcount:,} rows")
                total_standardized += cursor.rowcount

    if not dry_run:
        conn.commit()
    results["standardized_variants"] = total_standardized
    print(f"  Total standardized: {total_standardized:,} rows")

    # Step 3: Clean contaminated units (set to NULL)
    print("\nStep 3: Cleaning contaminated units (entity names → NULL)...")
    total_cleaned = 0

    # Build a single UPDATE for all contaminated values
    placeholders = ", ".join(["%s"] * len(CONTAMINATED_UNITS))
    clean_sql = f"""
        UPDATE financial_tables
        SET unit = NULL,
            unit_inferred = TRUE,
            unit_inference_method = 'contamination_cleanup',
            unit_confidence = 'high'
        WHERE unit IN ({placeholders})
          AND (unit_inferred IS NULL OR unit_inferred = FALSE)
    """

    if dry_run:
        cursor.execute(
            f"""
            SELECT unit, COUNT(*) as cnt FROM financial_tables
            WHERE unit IN ({placeholders})
              AND (unit_inferred IS NULL OR unit_inferred = FALSE)
            GROUP BY unit
            ORDER BY cnt DESC
        """,
            tuple(CONTAMINATED_UNITS),
        )
        contaminated = cursor.fetchall()
        for unit_val, cnt in contaminated:
            if cnt > 0:
                print(f"  [DRY RUN] '{unit_val}' → NULL: {cnt:,} rows")
                total_cleaned += cnt
    else:
        cursor.execute(clean_sql, tuple(CONTAMINATED_UNITS))
        total_cleaned = cursor.rowcount
        conn.commit()

    results["cleaned_contamination"] = total_cleaned
    print(f"  Total cleaned: {total_cleaned:,} rows")

    # Step 4: Fix malformed percentage patterns
    print("\nStep 4: Fixing malformed percentage patterns...")
    total_percentage_fixed = 0

    for pattern, replacement in MALFORMED_PERCENTAGE_PATTERNS:
        fix_sql = """
            UPDATE financial_tables
            SET unit = %s,
                unit_inferred = TRUE,
                unit_inference_method = 'percentage_fix',
                unit_confidence = 'high'
            WHERE unit = %s
              AND (unit_inferred IS NULL OR unit_inferred = FALSE)
        """

        if dry_run:
            cursor.execute(
                """
                SELECT COUNT(*) FROM financial_tables
                WHERE unit = %s AND (unit_inferred IS NULL OR unit_inferred = FALSE)
            """,
                (pattern,),
            )
            count = cursor.fetchone()[0]
            if count > 0:
                print(f"  [DRY RUN] '{pattern}' → '{replacement}': {count:,} rows")
                total_percentage_fixed += count
        else:
            cursor.execute(fix_sql, (replacement, pattern))
            if cursor.rowcount > 0:
                print(f"  '{pattern}' → '{replacement}': {cursor.rowcount:,} rows")
                total_percentage_fixed += cursor.rowcount

    # Also fix any unit that starts/ends with "%" but has extra characters
    pattern_sql = """
        UPDATE financial_tables
        SET unit = '%',
            unit_inferred = TRUE,
            unit_inference_method = 'percentage_pattern_fix',
            unit_confidence = 'high'
        WHERE unit ~ '^%.*[^%]$|^[^%].*%$'
          AND LENGTH(unit) > 1
          AND LENGTH(unit) < 10
          AND (unit_inferred IS NULL OR unit_inferred = FALSE)
    """

    if dry_run:
        cursor.execute("""
            SELECT unit, COUNT(*) FROM financial_tables
            WHERE unit ~ '^%.*[^%]$|^[^%].*%$'
              AND LENGTH(unit) > 1
              AND LENGTH(unit) < 10
              AND (unit_inferred IS NULL OR unit_inferred = FALSE)
            GROUP BY unit
        """)
        patterns = cursor.fetchall()
        for unit_val, cnt in patterns:
            print(f"  [DRY RUN] pattern '{unit_val}' → '%': {cnt:,} rows")
            total_percentage_fixed += cnt
    else:
        cursor.execute(pattern_sql)
        total_percentage_fixed += cursor.rowcount
        conn.commit()

    results["percentage_fixed"] = total_percentage_fixed
    print(f"  Total percentage patterns fixed: {total_percentage_fixed:,} rows")

    # Step 5: NULL out invalid decimal fragments
    print("\nStep 5: Cleaning invalid decimal fragments...")
    decimal_sql = """
        UPDATE financial_tables
        SET unit = NULL,
            unit_inferred = TRUE,
            unit_inference_method = 'decimal_cleanup',
            unit_confidence = 'high'
        WHERE unit ~ '^\\.[0-9]+$'
          AND (unit_inferred IS NULL OR unit_inferred = FALSE)
    """

    if dry_run:
        cursor.execute("""
            SELECT unit, COUNT(*) FROM financial_tables
            WHERE unit ~ '^\\.[0-9]+$'
              AND (unit_inferred IS NULL OR unit_inferred = FALSE)
            GROUP BY unit
            ORDER BY COUNT(*) DESC
            LIMIT 20
        """)
        decimals = cursor.fetchall()
        total_decimals = 0
        for unit_val, cnt in decimals:
            print(f"  [DRY RUN] '{unit_val}' → NULL: {cnt:,} rows")
            total_decimals += cnt
        results["decimal_cleaned"] = total_decimals
    else:
        cursor.execute(decimal_sql)
        results["decimal_cleaned"] = cursor.rowcount
        conn.commit()
        print(f"  Decimal fragments cleaned: {results['decimal_cleaned']:,} rows")

    # Step 6: Show updated unit distribution
    print("\nStep 6: Updated unit distribution (top 30)...")
    cursor.execute("""
        SELECT unit, COUNT(*) as cnt
        FROM financial_tables
        WHERE unit IS NOT NULL AND unit != ''
        GROUP BY unit
        ORDER BY cnt DESC
        LIMIT 30
    """)
    units = cursor.fetchall()
    print(f"  {'Unit':<30} {'Count':>10}")
    print("  " + "-" * 42)
    for unit_val, cnt in units:
        print(f"  {unit_val:<30} {cnt:>10}")

    # Show NULL/empty count
    cursor.execute("""
        SELECT
            SUM(CASE WHEN unit IS NULL THEN 1 ELSE 0 END) as null_count,
            SUM(CASE WHEN unit = '' THEN 1 ELSE 0 END) as empty_count,
            COUNT(*) as total
        FROM financial_tables
    """)
    row = cursor.fetchone()
    print(f"\n  NULL units: {row[0]:,} ({100.0 * row[0] / row[2]:.1f}%)")
    print(f"  Empty units: {row[1]:,} ({100.0 * row[1] / row[2]:.1f}%)")
    print(f"  Total rows: {row[2]:,}")

    cursor.close()

    return results


def main() -> int:
    """Main entry point."""
    args = parse_args()

    try:
        results = standardize_units(dry_run=args.dry_run)

        if "error" in results:
            return 1

        print("\n" + "=" * 70)
        print("RESULTS SUMMARY")
        print("=" * 70)
        for key, value in results.items():
            print(f"  {key}: {value:,}")

        total_modified = sum(v for k, v in results.items() if k != "error")
        print(f"\n  Total rows modified: {total_modified:,}")

        if args.dry_run:
            print("\n[DRY RUN] No changes were made to the database.")
            print("Run without --dry-run to apply changes.")

        print("\n✓ Phase A complete. Unit variants standardized.")
        print("  Next step: Run scripts/fix_unit_magnitude_inference.py (Phase B)")

        return 0

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
