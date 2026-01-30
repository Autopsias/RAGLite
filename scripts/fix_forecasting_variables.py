#!/usr/bin/env python3
"""Phase 4E: Forecasting Variable Preparation.

Ensures all forecasting variables have clean, validated data ready for model training.

Key forecasting variables:
- SECIL Internal: ebitda, revenue/turnover, variable_cost, sales_volume,
                  electricity_cost, thermal_cost, capacity_utilization
- External API: ttf_gas_price, petcoke_price, co2_eua_price, euribor_3m

This script:
1. Validates data quality for each variable
2. Fixes sign conventions (costs should be negative or clearly marked)
3. Removes invalid year values from capacity_utilization
4. Generates a readiness report

Prerequisites:
    - Run Phase 4A-4D first

Usage:
    POSTGRES_USER=raglite POSTGRES_PASSWORD=raglite POSTGRES_DB=raglite POSTGRES_PORT=5432 \
        uv run python scripts/fix_forecasting_variables.py

    # Dry run (show SQL without executing):
    POSTGRES_USER=raglite POSTGRES_PASSWORD=raglite POSTGRES_DB=raglite POSTGRES_PORT=5432 \
        uv run python scripts/fix_forecasting_variables.py --dry-run
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from dataclasses import dataclass, field

# Suppress verbose logging unless DEBUG is set
if not os.getenv("DEBUG"):
    logging.getLogger("raglite").setLevel(logging.WARNING)


@dataclass
class VariableQuality:
    """Quality assessment for a forecasting variable."""

    name: str
    metric_pattern: str
    data_points: int = 0
    unique_periods: int = 0
    unique_entities: int = 0
    null_units: int = 0
    negative_values: int = 0
    min_value: float = 0.0
    max_value: float = 0.0
    unique_units: int = 0
    status: str = "UNKNOWN"
    issues: list[str] = field(default_factory=list)


# Forecasting variable definitions
FORECASTING_VARIABLES = [
    # SECIL Internal Variables
    {
        "name": "EBITDA",
        "metric_pattern": "%ebitda%",
        "expected_unit": "M EUR",
        "sign": "positive",  # Profits are positive
        "min_points": 100,
    },
    {
        "name": "Revenue/Turnover",
        "metric_pattern": "%turnover%",
        "alt_patterns": ["%revenue%"],
        "expected_unit": "M EUR",
        "sign": "positive",
        "min_points": 100,
    },
    {
        "name": "Variable Cost",
        "metric_pattern": "%variable%cost%",
        "expected_unit": "M EUR",
        "sign": "cost_negative",  # Costs may be represented as negative
        "min_points": 50,
    },
    {
        "name": "Sales Volume",
        "metric_pattern": "%sales%volume%",
        "alt_patterns": ["%cement%", "%clinker%"],
        "expected_unit": "kton",
        "sign": "positive",
        "min_points": 100,
    },
    {
        "name": "Electricity Cost",
        "metric_pattern": "%electric%cost%",
        "alt_patterns": ["%electricity%"],
        "expected_unit": "M EUR",
        "sign": "cost_negative",
        "min_points": 30,
    },
    {
        "name": "Thermal Cost",
        "metric_pattern": "%thermal%cost%",
        "alt_patterns": ["%thermal%energy%"],
        "expected_unit": "M EUR",
        "sign": "cost_negative",
        "min_points": 30,
    },
    {
        "name": "Capacity Utilization",
        "metric_pattern": "%capacity%utilization%",
        "expected_unit": "%",
        "sign": "positive",
        "min_points": 50,
        "max_valid_value": 100,  # Percentage should be 0-100
    },
    {
        "name": "Average Selling Price",
        "metric_pattern": "%selling%price%",
        "alt_patterns": ["%avg%price%", "%average%price%"],
        "expected_unit": "EUR/ton",
        "sign": "positive",
        "min_points": 50,
    },
]


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Phase 4E: Prepare forecasting variables")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show SQL statements without executing them",
    )
    parser.add_argument(
        "--fix-all",
        action="store_true",
        help="Apply all automatic fixes (use with caution)",
    )
    return parser.parse_args()


def ensure_sign_convention_column(cursor, conn, dry_run: bool = False) -> bool:
    """Ensure sign_convention column exists for marking cost metrics."""
    cursor.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'financial_tables' AND column_name = 'sign_convention'
    """)
    if cursor.fetchone():
        print("  sign_convention column already exists")
        return True

    if dry_run:
        print("  [DRY RUN] Would create sign_convention column")
        return True

    print("  Creating sign_convention column...")
    cursor.execute("""
        ALTER TABLE financial_tables
        ADD COLUMN IF NOT EXISTS sign_convention VARCHAR(20)
    """)
    conn.commit()
    print("  sign_convention column created")
    return True


def assess_variable_quality(cursor, var_def: dict) -> VariableQuality:
    """Assess the data quality for a single forecasting variable."""
    name = var_def["name"]
    pattern = var_def["metric_pattern"]
    alt_patterns = var_def.get("alt_patterns", [])

    # Build pattern match
    patterns = [pattern] + alt_patterns
    pattern_sql = " OR ".join([f"LOWER(metric) LIKE '{p}'" for p in patterns])

    quality = VariableQuality(name=name, metric_pattern=pattern)

    # Get basic stats
    cursor.execute(f"""
        SELECT
            COUNT(*) as data_points,
            COUNT(DISTINCT period) as unique_periods,
            COUNT(DISTINCT entity_normalized) as unique_entities,
            SUM(CASE WHEN unit IS NULL THEN 1 ELSE 0 END) as null_units,
            SUM(CASE WHEN value < 0 THEN 1 ELSE 0 END) as negative_values,
            MIN(value) as min_val,
            MAX(value) as max_val,
            COUNT(DISTINCT unit) as unique_units
        FROM financial_tables
        WHERE {pattern_sql}
    """)
    row = cursor.fetchone()

    quality.data_points = row[0] or 0
    quality.unique_periods = row[1] or 0
    quality.unique_entities = row[2] or 0
    quality.null_units = row[3] or 0
    quality.negative_values = row[4] or 0
    quality.min_value = row[5] or 0.0
    quality.max_value = row[6] or 0.0
    quality.unique_units = row[7] or 0

    # Assess status
    issues = []

    # Check minimum data points
    min_points = var_def.get("min_points", 50)
    if quality.data_points < min_points:
        issues.append(f"Insufficient data ({quality.data_points} < {min_points})")

    # Check NULL units
    if quality.data_points > 0:
        null_pct = 100.0 * quality.null_units / quality.data_points
        if null_pct > 20:
            issues.append(f"High NULL units ({null_pct:.1f}%)")

    # Check unit variants
    if quality.unique_units > 5:
        issues.append(f"Too many unit variants ({quality.unique_units})")

    # Check sign convention
    expected_sign = var_def.get("sign", "positive")
    if expected_sign == "positive" and quality.negative_values > 0:
        neg_pct = (
            100.0 * quality.negative_values / quality.data_points if quality.data_points > 0 else 0
        )
        if neg_pct > 10:
            issues.append(f"Unexpected negative values ({neg_pct:.1f}%)")

    # Check max valid value (for percentages)
    max_valid = var_def.get("max_valid_value")
    if max_valid and quality.max_value > max_valid:
        issues.append(f"Invalid values > {max_valid} (max: {quality.max_value:.0f})")

    # Determine status
    if not issues:
        quality.status = "READY"
    elif len(issues) == 1 and "Insufficient data" in issues[0]:
        quality.status = "MARGINAL"
    elif quality.data_points == 0:
        quality.status = "MISSING"
    else:
        quality.status = "CRITICAL"

    quality.issues = issues
    return quality


def print_variable_assessment(quality: VariableQuality) -> None:
    """Print assessment for a single variable."""
    status_colors = {
        "READY": "",
        "MARGINAL": "",
        "CRITICAL": "",
        "MISSING": "",
        "UNKNOWN": "",
    }

    print(f"\n  {quality.name}:")
    print(f"    Status: {quality.status}")
    print(f"    Data points: {quality.data_points:,}")
    print(f"    Unique periods: {quality.unique_periods}")
    print(f"    Unique entities: {quality.unique_entities}")
    print(
        f"    NULL units: {quality.null_units:,} ({100.0 * quality.null_units / max(quality.data_points, 1):.1f}%)"
    )
    print(f"    Negative values: {quality.negative_values:,}")
    print(f"    Value range: {quality.min_value:,.2f} to {quality.max_value:,.2f}")
    print(f"    Unit variants: {quality.unique_units}")

    if quality.issues:
        print("    Issues:")
        for issue in quality.issues:
            print(f"      - {issue}")


def fix_capacity_utilization_years(cursor, conn, dry_run: bool = False) -> int:
    """Remove year values incorrectly stored in capacity_utilization.

    Pattern: Values like 2020, 2021, 2022 that are clearly year numbers,
    not utilization percentages.
    """
    print("\nStep 2: Fixing capacity utilization year values...")

    if dry_run:
        cursor.execute("""
            SELECT value, COUNT(*) as cnt
            FROM financial_tables
            WHERE LOWER(metric) LIKE '%capacity%utilization%'
              AND value > 100
              AND value >= 1900 AND value < 2100
            GROUP BY value
            ORDER BY value
        """)
        findings = cursor.fetchall()
        total = sum(cnt for _, cnt in findings)
        print(f"  [DRY RUN] Would delete {total:,} rows with year values:")
        for value, cnt in findings:
            print(f"    {int(value)}: {cnt:,} rows")
        return total

    cursor.execute("""
        DELETE FROM financial_tables
        WHERE LOWER(metric) LIKE '%capacity%utilization%'
          AND value > 100
          AND value >= 1900 AND value < 2100
    """)
    count = cursor.rowcount
    conn.commit()
    print(f"  Deleted {count:,} rows with year values in capacity_utilization")
    return count


def mark_cost_sign_convention(cursor, conn, dry_run: bool = False) -> int:
    """Mark cost metrics with sign convention for correct interpretation."""
    print("\nStep 3: Marking cost metrics with sign convention...")

    cost_patterns = [
        ("%variable%cost%", "cost_negative"),
        ("%electric%cost%", "cost_negative"),
        ("%thermal%cost%", "cost_negative"),
        ("%electricity%cost%", "cost_negative"),
        ("%fuel%cost%", "cost_negative"),
        ("%energy%cost%", "cost_negative"),
    ]

    total = 0
    for pattern, convention in cost_patterns:
        if dry_run:
            cursor.execute(f"""
                SELECT COUNT(*) FROM financial_tables
                WHERE LOWER(metric) LIKE '{pattern}'
                  AND (sign_convention IS NULL OR sign_convention = '')
            """)
            count = cursor.fetchone()[0]
            if count > 0:
                print(f"  [DRY RUN] Would mark {count:,} rows with '{pattern}' as {convention}")
            total += count
        else:
            cursor.execute(f"""
                UPDATE financial_tables
                SET sign_convention = '{convention}'
                WHERE LOWER(metric) LIKE '{pattern}'
                  AND (sign_convention IS NULL OR sign_convention = '')
            """)
            count = cursor.rowcount
            if count > 0:
                print(f"  Marked {count:,} '{pattern}' rows as {convention}")
            total += count

    if not dry_run:
        conn.commit()

    return total


def fix_invalid_percentage_values(cursor, conn, dry_run: bool = False) -> int:
    """Fix percentage metrics with values > 100 (data corruption)."""
    print("\nStep 4: Fixing invalid percentage values (>100%)...")

    # Metrics that should be percentages
    pct_patterns = [
        "%margin%",
        "%utilization%",
        "%rate%",
        "%share%",
        "%ratio%",
    ]

    pattern_sql = " OR ".join([f"LOWER(metric) LIKE '{p}'" for p in pct_patterns])

    if dry_run:
        cursor.execute(f"""
            SELECT metric, COUNT(*) as cnt, MAX(value) as max_val
            FROM financial_tables
            WHERE ({pattern_sql})
              AND unit = '%'
              AND value > 100
              AND value < 1900  -- Exclude year values
            GROUP BY metric
            ORDER BY cnt DESC
            LIMIT 10
        """)
        findings = cursor.fetchall()
        total = sum(cnt for _, cnt, _ in findings)
        print(f"  [DRY RUN] Found {total:,} suspicious percentage values > 100:")
        for metric, cnt, max_val in findings:
            print(f"    {metric}: {cnt:,} rows (max: {max_val:.0f})")
        return total

    # Flag these for review rather than delete
    cursor.execute(f"""
        UPDATE financial_tables
        SET unit_confidence = 'low',
            unit_inference_method = COALESCE(unit_inference_method, 'flagged_invalid_pct')
        WHERE ({pattern_sql})
          AND unit = '%'
          AND value > 100
          AND value < 1900
    """)
    count = cursor.rowcount
    conn.commit()
    print(f"  Flagged {count:,} suspicious percentage values for review")
    return count


def validate_forecasting_readiness(cursor) -> dict[str, VariableQuality]:
    """Validate all forecasting variables and generate readiness report."""
    print("\n" + "=" * 70)
    print("Forecasting Variable Readiness Assessment")
    print("=" * 70)

    assessments: dict[str, VariableQuality] = {}

    for var_def in FORECASTING_VARIABLES:
        quality = assess_variable_quality(cursor, var_def)
        assessments[quality.name] = quality
        print_variable_assessment(quality)

    return assessments


def print_readiness_matrix(assessments: dict[str, VariableQuality]) -> None:
    """Print a summary readiness matrix."""
    print("\n" + "=" * 70)
    print("FORECASTING READINESS MATRIX")
    print("=" * 70)

    print(f"\n{'Variable':<25} {'Status':<12} {'Points':>10} {'NULL %':>10} {'Issues':>10}")
    print("-" * 70)

    ready_count = 0
    for name, quality in assessments.items():
        null_pct = f"{100.0 * quality.null_units / max(quality.data_points, 1):.1f}%"
        issue_count = len(quality.issues)
        print(
            f"{name:<25} {quality.status:<12} {quality.data_points:>10,} {null_pct:>10} {issue_count:>10}"
        )
        if quality.status == "READY":
            ready_count += 1

    print("-" * 70)
    total = len(assessments)
    print(f"Ready: {ready_count}/{total} ({100.0 * ready_count / total:.1f}%)")


def forecasting_preparation(dry_run: bool = False, fix_all: bool = False) -> dict[str, int]:
    """Run all forecasting preparation operations.

    Args:
        dry_run: If True, only print SQL without executing
        fix_all: If True, apply all automatic fixes

    Returns:
        Dict with counts of rows affected by each operation
    """
    from raglite.shared.clients import get_postgresql_connection

    conn = get_postgresql_connection()
    cursor = conn.cursor()
    results: dict[str, int] = {}

    print("\n" + "=" * 70)
    print("Phase 4E: Forecasting Variable Preparation")
    print("=" * 70)

    # Step 1: Ensure sign_convention column exists
    print("\nStep 1: Ensuring sign_convention column exists...")
    ensure_sign_convention_column(cursor, conn, dry_run)

    # Execute preparation operations
    results["capacity_years_fixed"] = fix_capacity_utilization_years(cursor, conn, dry_run)
    results["cost_conventions_marked"] = mark_cost_sign_convention(cursor, conn, dry_run)
    results["invalid_pct_flagged"] = fix_invalid_percentage_values(cursor, conn, dry_run)

    # Validate forecasting readiness
    assessments = validate_forecasting_readiness(cursor)
    print_readiness_matrix(assessments)

    # Store assessment results
    for name, quality in assessments.items():
        safe_name = name.lower().replace(" ", "_").replace("/", "_")
        results[f"var_{safe_name}_points"] = quality.data_points
        results[f"var_{safe_name}_status"] = 1 if quality.status == "READY" else 0

    cursor.close()
    return results


def print_summary(results: dict[str, int], dry_run: bool) -> None:
    """Print summary of all operations."""
    print("\n" + "=" * 70)
    print("PHASE 4E SUMMARY")
    print("=" * 70)

    print(f"\n{'Operation':<40} {'Rows':>15}")
    print("-" * 55)

    ops = ["capacity_years_fixed", "cost_conventions_marked", "invalid_pct_flagged"]
    for key in ops:
        if key in results:
            print(f"{key:<40} {results[key]:>15,}")

    print("-" * 55)
    total = sum(results.get(k, 0) for k in ops)
    print(f"{'Total rows processed':<40} {total:>15,}")

    # Count ready variables
    ready_count = sum(1 for k, v in results.items() if k.endswith("_status") and v == 1)
    total_vars = sum(1 for k in results.keys() if k.endswith("_status"))
    print(f"\nForecasting variables ready: {ready_count}/{total_vars}")

    if dry_run:
        print("\n[DRY RUN] No changes were made to the database.")
        print("Run without --dry-run to apply changes.")


def main() -> int:
    """Main entry point."""
    args = parse_args()

    try:
        results = forecasting_preparation(dry_run=args.dry_run, fix_all=args.fix_all)

        print_summary(results, args.dry_run)

        print("\n" + "=" * 70)
        if args.dry_run:
            print("Phase 4E complete (DRY RUN)")
        else:
            print("Phase 4E complete")
        print("=" * 70)
        print(
            "\nNext step: Run scripts/verify_all_variables_quality.py for comprehensive validation"
        )

        return 0

    except Exception as e:
        print(f"\n ERROR: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
