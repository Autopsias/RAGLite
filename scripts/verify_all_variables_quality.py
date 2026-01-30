#!/usr/bin/env python3
"""Comprehensive Data Quality Verification for All Variables.

Validates the quality of ALL 982 metrics after Phase 4 remediation.
This is the final verification script to run after all fix scripts.

Checks:
1. Overall dataset health
2. Structural integrity (no empty metrics, no entity contamination)
3. Unit quality (standardization, NULL percentage)
4. Forecasting variable readiness
5. Critical issue detection

Usage:
    POSTGRES_USER=raglite POSTGRES_PASSWORD=raglite POSTGRES_DB=raglite POSTGRES_PORT=5432 \
        uv run python scripts/verify_all_variables_quality.py

    # With verbose output:
    POSTGRES_USER=raglite POSTGRES_PASSWORD=raglite POSTGRES_DB=raglite POSTGRES_PORT=5432 \
        uv run python scripts/verify_all_variables_quality.py --verbose
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from dataclasses import dataclass

# Suppress verbose logging unless DEBUG is set
if not os.getenv("DEBUG"):
    logging.getLogger("raglite").setLevel(logging.WARNING)


@dataclass
class QualityCheck:
    """Quality check result."""

    name: str
    target: str
    current: float | int | str
    passed: bool
    details: str = ""
    severity: str = "normal"  # normal, warning, critical


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Comprehensive data quality verification")
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed breakdown for each check",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )
    return parser.parse_args()


def check_dataset_overview(cursor, verbose: bool = False) -> list[QualityCheck]:
    """Check overall dataset health metrics."""
    checks: list[QualityCheck] = []

    print("\n" + "=" * 70)
    print("1. Dataset Overview")
    print("=" * 70)

    # Total rows
    cursor.execute("SELECT COUNT(*) FROM financial_tables")
    total_rows = cursor.fetchone()[0]
    print(f"\n  Total rows: {total_rows:,}")

    # Unique metrics
    cursor.execute("SELECT COUNT(DISTINCT metric) FROM financial_tables WHERE metric IS NOT NULL")
    unique_metrics = cursor.fetchone()[0]
    print(f"  Unique metrics: {unique_metrics:,}")

    # Unique entities
    cursor.execute("SELECT COUNT(DISTINCT entity_normalized) FROM financial_tables")
    unique_entities = cursor.fetchone()[0]
    print(f"  Unique entities: {unique_entities:,}")

    # Date range
    cursor.execute("""
        SELECT MIN(fiscal_year), MAX(fiscal_year)
        FROM financial_tables
        WHERE fiscal_year IS NOT NULL AND fiscal_year > 1900 AND fiscal_year < 2100
    """)
    min_year, max_year = cursor.fetchone()
    print(f"  Year range: {min_year} - {max_year}")

    return checks


def check_structural_integrity(cursor, verbose: bool = False) -> list[QualityCheck]:
    """Check structural integrity - no empty metrics, no entity contamination."""
    checks: list[QualityCheck] = []

    print("\n" + "=" * 70)
    print("2. Structural Integrity")
    print("=" * 70)

    # Empty metric rows
    cursor.execute("""
        SELECT COUNT(*) FROM financial_tables
        WHERE metric IS NULL OR metric = ''
    """)
    empty_metrics = cursor.fetchone()[0]
    passed = empty_metrics == 0
    checks.append(
        QualityCheck(
            name="Empty metric rows",
            target="0",
            current=empty_metrics,
            passed=passed,
            details="Headers/dividers should be removed",
            severity="critical"
            if empty_metrics > 1000
            else "warning"
            if empty_metrics > 0
            else "normal",
        )
    )
    status = "PASS" if passed else "FAIL"
    print(f"\n  [{status}] Empty metric rows: {empty_metrics:,} (target: 0)")

    # Entity contamination
    contamination_patterns = [
        "CF from Operations",
        "De(in)crease Trade Working Capital",
        "CF from Operating Activities",
        "Net interest expenses",
    ]
    pattern_list = ", ".join(f"'{p}'" for p in contamination_patterns)
    cursor.execute(f"""
        SELECT COUNT(*) FROM financial_tables
        WHERE entity_normalized IN ({pattern_list})
    """)
    entity_contamination = cursor.fetchone()[0]
    passed = entity_contamination == 0
    checks.append(
        QualityCheck(
            name="Entity contamination",
            target="0",
            current=entity_contamination,
            passed=passed,
            details="Metrics in entity field",
            severity="critical"
            if entity_contamination > 100
            else "warning"
            if entity_contamination > 0
            else "normal",
        )
    )
    status = "PASS" if passed else "FAIL"
    print(f"  [{status}] Entity contamination: {entity_contamination:,} (target: 0)")

    # Future year errors
    cursor.execute("""
        SELECT COUNT(*) FROM financial_tables
        WHERE fiscal_year > 2026
    """)
    future_years = cursor.fetchone()[0]
    passed = future_years == 0
    checks.append(
        QualityCheck(
            name="Future year errors",
            target="0",
            current=future_years,
            passed=passed,
            details="Invalid year values",
        )
    )
    status = "PASS" if passed else "FAIL"
    print(f"  [{status}] Future year errors: {future_years:,} (target: 0)")

    return checks


def check_unit_quality(cursor, verbose: bool = False) -> list[QualityCheck]:
    """Check unit standardization and NULL percentage."""
    checks: list[QualityCheck] = []

    print("\n" + "=" * 70)
    print("3. Unit Quality")
    print("=" * 70)

    # NULL unit percentage
    cursor.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN unit IS NULL THEN 1 ELSE 0 END) as null_count
        FROM financial_tables
    """)
    total, null_count = cursor.fetchone()
    null_pct = 100.0 * null_count / total if total > 0 else 0

    passed = null_pct < 5.0
    checks.append(
        QualityCheck(
            name="NULL units",
            target="<5%",
            current=f"{null_pct:.1f}%",
            passed=passed,
            details=f"{null_count:,} of {total:,} rows",
            severity="critical" if null_pct > 20 else "warning" if null_pct > 5 else "normal",
        )
    )
    status = "PASS" if passed else "FAIL"
    print(f"\n  [{status}] NULL units: {null_pct:.1f}% (target: <5%)")
    print(f"          {null_count:,} of {total:,} rows")

    # Unique unit variants
    cursor.execute("""
        SELECT COUNT(DISTINCT unit)
        FROM financial_tables
        WHERE unit IS NOT NULL AND unit != ''
    """)
    unique_units = cursor.fetchone()[0]
    passed = unique_units < 30
    checks.append(
        QualityCheck(
            name="Unique unit variants",
            target="<30",
            current=unique_units,
            passed=passed,
            details="Canonical forms expected",
        )
    )
    status = "PASS" if passed else "FAIL"
    print(f"  [{status}] Unique unit variants: {unique_units} (target: <30)")

    if verbose:
        print("\n  Top 15 units:")
        cursor.execute("""
            SELECT unit, COUNT(*) as cnt
            FROM financial_tables
            WHERE unit IS NOT NULL AND unit != ''
            GROUP BY unit
            ORDER BY cnt DESC
            LIMIT 15
        """)
        for unit, cnt in cursor.fetchall():
            print(f"    {unit}: {cnt:,}")

    # Contaminated units (entity names in unit field)
    contaminated_patterns = ["GROUP", "ANGOLA", "TUNISIA", "LEBANON", "N/A"]
    pattern_list = ", ".join(f"'{p}'" for p in contaminated_patterns)
    cursor.execute(f"""
        SELECT COUNT(*) FROM financial_tables
        WHERE unit IN ({pattern_list})
    """)
    contaminated_units = cursor.fetchone()[0]
    passed = contaminated_units == 0
    checks.append(
        QualityCheck(
            name="Contaminated units",
            target="0",
            current=contaminated_units,
            passed=passed,
            details="Entity names in unit field",
        )
    )
    status = "PASS" if passed else "FAIL"
    print(f"  [{status}] Contaminated units: {contaminated_units:,} (target: 0)")

    # Inference coverage
    cursor.execute("""
        SELECT
            SUM(CASE WHEN unit_inferred = TRUE THEN 1 ELSE 0 END) as inferred
        FROM financial_tables
    """)
    inferred = cursor.fetchone()[0] or 0
    inferred_pct = 100.0 * inferred / total if total > 0 else 0
    print(f"\n  INFO: Inferred units: {inferred_pct:.1f}% ({inferred:,} rows)")

    return checks


def check_ratio_metric(cursor, verbose: bool = False) -> list[QualityCheck]:
    """Check Ratio metric cleanup status."""
    checks: list[QualityCheck] = []

    print("\n" + "=" * 70)
    print("4. Ratio Metric Status")
    print("=" * 70)

    # Total Ratio rows
    cursor.execute("SELECT COUNT(*) FROM financial_tables WHERE metric = 'Ratio'")
    total = cursor.fetchone()[0]
    print(f"\n  Total 'Ratio' rows: {total:,}")

    if total == 0:
        print("  (Ratio metric not present or fully reclassified)")
        return checks

    # Unique units in Ratio
    cursor.execute("""
        SELECT COUNT(DISTINCT unit) FROM financial_tables WHERE metric = 'Ratio'
    """)
    unique_units = cursor.fetchone()[0]
    passed = unique_units < 20
    checks.append(
        QualityCheck(
            name="Ratio unique units",
            target="<20",
            current=unique_units,
            passed=passed,
            details="Was 1,604 before Phase 4B",
            severity="critical"
            if unique_units > 100
            else "warning"
            if unique_units > 20
            else "normal",
        )
    )
    status = "PASS" if passed else "FAIL"
    print(f"  [{status}] Unique units in Ratio: {unique_units} (target: <20)")

    if verbose:
        print("\n  Unit distribution:")
        cursor.execute("""
            SELECT COALESCE(unit, '(null)'), COUNT(*)
            FROM financial_tables
            WHERE metric = 'Ratio'
            GROUP BY unit
            ORDER BY COUNT(*) DESC
            LIMIT 10
        """)
        for unit, cnt in cursor.fetchall():
            print(f"    {unit}: {cnt:,}")

    return checks


def check_currency_metric(cursor, verbose: bool = False) -> list[QualityCheck]:
    """Check Currency metric cleanup status."""
    checks: list[QualityCheck] = []

    print("\n" + "=" * 70)
    print("5. Currency Metric Status")
    print("=" * 70)

    # Total Currency rows
    cursor.execute("SELECT COUNT(*) FROM financial_tables WHERE metric = 'Currency (1000 EUR)'")
    total = cursor.fetchone()[0]
    print(f"\n  Total 'Currency (1000 EUR)' rows: {total:,}")

    if total == 0:
        print("  (Currency metric not present)")
        return checks

    # Unique units in Currency
    cursor.execute("""
        SELECT COUNT(DISTINCT unit) FROM financial_tables
        WHERE metric = 'Currency (1000 EUR)'
    """)
    unique_units = cursor.fetchone()[0]
    passed = unique_units < 10
    checks.append(
        QualityCheck(
            name="Currency unique units",
            target="<10",
            current=unique_units,
            passed=passed,
            details="Was 317 before Phase 4C",
        )
    )
    status = "PASS" if passed else "FAIL"
    print(f"  [{status}] Unique units in Currency: {unique_units} (target: <10)")

    if verbose:
        print("\n  Unit distribution:")
        cursor.execute("""
            SELECT COALESCE(unit, '(null)'), COUNT(*)
            FROM financial_tables
            WHERE metric = 'Currency (1000 EUR)'
            GROUP BY unit
            ORDER BY COUNT(*) DESC
            LIMIT 10
        """)
        for unit, cnt in cursor.fetchall():
            print(f"    {unit}: {cnt:,}")

    return checks


def check_ebitda_scale(cursor, verbose: bool = False) -> list[QualityCheck]:
    """Check EBITDA scale reconciliation status."""
    checks: list[QualityCheck] = []

    print("\n" + "=" * 70)
    print("6. EBITDA Scale Status")
    print("=" * 70)

    # EBITDA unit distribution
    cursor.execute("""
        SELECT unit, COUNT(*) as cnt
        FROM financial_tables
        WHERE LOWER(metric) LIKE '%ebitda%'
          AND metric NOT LIKE '%Margin%'
        GROUP BY unit
        ORDER BY cnt DESC
    """)
    unit_dist = cursor.fetchall()
    print("\n  EBITDA unit distribution:")
    for unit, cnt in unit_dist:
        print(f"    {unit or '(null)'}: {cnt:,}")

    # Check kEUR count (should be minimal after Phase 4D)
    cursor.execute("""
        SELECT COUNT(*) FROM financial_tables
        WHERE LOWER(metric) LIKE '%ebitda%'
          AND metric NOT LIKE '%Margin%'
          AND unit = 'kEUR'
    """)
    keur_count = cursor.fetchone()[0]
    passed = keur_count < 100
    checks.append(
        QualityCheck(
            name="EBITDA kEUR rows",
            target="<100",
            current=keur_count,
            passed=passed,
            details="Should be mostly M EUR",
        )
    )
    status = "PASS" if passed else "FAIL"
    print(f"\n  [{status}] EBITDA kEUR rows: {keur_count:,} (target: <100)")

    # Check swing ratio (comparable M EUR only)
    cursor.execute("""
        SELECT
            MAX(value) / NULLIF(MIN(value), 0) as swing,
            MIN(value), MAX(value)
        FROM financial_tables
        WHERE metric = 'EBITDA IFRS'
          AND entity_normalized = 'Group'
          AND unit = 'M EUR'
          AND value > 0
          AND period LIKE 'YTD Dec%'
    """)
    row = cursor.fetchone()
    if row and row[0]:
        swing = row[0]
        passed = swing < 5.0
        checks.append(
            QualityCheck(
                name="EBITDA swing ratio",
                target="<5x",
                current=f"{swing:.2f}x",
                passed=passed,
                details=f"Range: {row[1]:.0f} to {row[2]:.0f} M EUR",
            )
        )
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] EBITDA swing ratio: {swing:.2f}x (target: <5x)")

    return checks


def get_forecasting_variable_patterns() -> list[tuple[str, list[str], str, int]]:
    """Get forecasting variable patterns from variable_configs.

    Returns:
        List of (name, db_patterns, expected_unit, min_points) tuples
    """
    try:
        from raglite.forecasting.data_quality.variable_configs import VARIABLE_QUALITY_CONFIGS

        # Map variable config names to display names and expected units
        # Phase 1: Original 5 variables
        # Phase 2: +3 already-configured variables (electricity_cost, thermal_cost, avg_selling_price)
        # Phase 3: +4 new variables (capex, fixed_costs, headcount, other_costs)
        variable_map = {
            # Original 5 variables
            "ebitda": ("EBITDA", "M EUR", 100),
            "revenue": ("Revenue/Turnover", "M EUR", 100),
            "variable_cost": ("Variable Cost", "EUR/ton", 50),
            "sales_volume": ("Sales Volume", "kton", 100),
            "capacity_utilization": ("Capacity Utilization", "%", 50),
            # Phase 1: Enable already-configured variables
            "electricity_cost": ("Electricity Cost", "EUR/ton", 50),
            "thermal_cost": ("Thermal Cost", "EUR/ton", 50),
            "avg_selling_price": ("Avg Selling Price", "EUR/ton", 50),
            # Phase 2: New high-value variables
            "capex": ("CAPEX", "M EUR", 50),
            "fixed_costs": ("Fixed Costs", "EUR/ton", 50),
            "headcount": ("Headcount", "count", 50),
            "other_costs": ("Other Costs/Income", "EUR/ton", 50),
        }

        result = []
        for config_name, (display_name, unit, min_points) in variable_map.items():
            if config_name in VARIABLE_QUALITY_CONFIGS:
                config = VARIABLE_QUALITY_CONFIGS[config_name]
                # Convert aliases to SQL LIKE patterns
                patterns = []
                for alias in config.db_metric_aliases:
                    # Escape special chars and create LIKE pattern
                    pattern = f"%{alias.lower()}%"
                    patterns.append(pattern)
                result.append((display_name, patterns, unit, min_points))
            else:
                # Fallback to simple pattern if config not found
                result.append((display_name, [f"%{config_name}%"], unit, min_points))

        return result
    except ImportError:
        # Fallback patterns if config import fails
        return [
            ("EBITDA", ["%ebitda%"], "M EUR", 100),
            ("Revenue/Turnover", ["%turnover%"], "M EUR", 100),
            ("Variable Cost", ["%variable%cost%"], "M EUR", 50),
            ("Sales Volume", ["%sales%volume%"], "kton", 100),
            ("Capacity Utilization", ["%frequency%ratio%", "%capacity%utilization%"], "%", 50),
        ]


def check_forecasting_readiness(cursor, verbose: bool = False) -> list[QualityCheck]:
    """Check forecasting variable readiness.

    Uses db_metric_aliases from variable_configs.py for pattern matching,
    ensuring Capacity Utilization finds "Frequency Ratio" metric.
    """
    checks: list[QualityCheck] = []

    print("\n" + "=" * 70)
    print("7. Forecasting Variable Readiness")
    print("=" * 70)

    # Get patterns from variable configs (or fallback)
    variables = get_forecasting_variable_patterns()

    ready_count = 0
    total_vars = len(variables)

    print(f"\n  {'Variable':<25} {'Points':>10} {'NULL %':>10} {'Status':<12}")
    print("  " + "-" * 60)

    for name, patterns, expected_unit, min_points in variables:
        # Build OR query for multiple patterns
        pattern_conditions = " OR ".join(f"LOWER(metric) LIKE '{p}'" for p in patterns)

        cursor.execute(f"""
            SELECT
                COUNT(*) as points,
                SUM(CASE WHEN unit IS NULL THEN 1 ELSE 0 END) as null_units
            FROM financial_tables
            WHERE {pattern_conditions}
        """)
        row = cursor.fetchone()
        points = row[0] or 0
        null_units = row[1] or 0
        null_pct = 100.0 * null_units / points if points > 0 else 0

        # Determine status
        if points >= min_points and null_pct < 20:
            status = "READY"
            ready_count += 1
        elif points >= min_points * 0.5:
            status = "MARGINAL"
        elif points == 0:
            status = "MISSING"
        else:
            status = "CRITICAL"

        print(f"  {name:<25} {points:>10,} {null_pct:>9.1f}% {status:<12}")

        if verbose and points > 0:
            # Show which patterns matched
            for pattern in patterns:
                cursor.execute(f"""
                    SELECT COUNT(*) FROM financial_tables
                    WHERE LOWER(metric) LIKE '{pattern}'
                """)
                pattern_count = cursor.fetchone()[0]
                if pattern_count > 0:
                    print(f"      (pattern '{pattern}': {pattern_count:,})")

    print("  " + "-" * 60)
    print(f"  Ready: {ready_count}/{total_vars}")

    checks.append(
        QualityCheck(
            name="Forecasting vars ready",
            target=">=4",
            current=ready_count,
            passed=ready_count >= 4,
            details=f"{ready_count}/{total_vars} variables",
        )
    )

    return checks


def print_summary(all_checks: list[QualityCheck]) -> int:
    """Print final summary and return exit code."""
    print("\n" + "=" * 70)
    print("QUALITY SUMMARY")
    print("=" * 70)

    passed_count = sum(1 for c in all_checks if c.passed)
    total_count = len(all_checks)

    print(f"\n{'Check':<30} {'Target':>12} {'Current':>12} {'Status':>8}")
    print("-" * 70)

    for check in all_checks:
        current_str = str(check.current)[:12]
        status = "PASS" if check.passed else "FAIL"
        print(f"{check.name:<30} {check.target:>12} {current_str:>12} {status:>8}")

    print("-" * 70)
    print(f"Passed: {passed_count}/{total_count}")

    # Count critical issues
    critical_count = sum(1 for c in all_checks if not c.passed and c.severity == "critical")
    warning_count = sum(1 for c in all_checks if not c.passed and c.severity == "warning")

    if critical_count > 0:
        print(f"\nCRITICAL issues: {critical_count}")
    if warning_count > 0:
        print(f"Warnings: {warning_count}")

    if passed_count == total_count:
        print("\nALL QUALITY CHECKS PASSED!")
        return 0
    else:
        print(f"\n{total_count - passed_count} check(s) failed")
        return 1 if critical_count > 0 else 0  # Only fail on critical


def verify_all_quality(verbose: bool = False) -> int:
    """Run all quality verification checks.

    Args:
        verbose: If True, show detailed breakdown

    Returns:
        Exit code (0 = success, 1 = failures)
    """
    from raglite.shared.clients import get_postgresql_connection

    conn = get_postgresql_connection()
    cursor = conn.cursor()

    all_checks: list[QualityCheck] = []

    print("\n" + "=" * 70)
    print("COMPREHENSIVE DATA QUALITY VERIFICATION")
    print("Phase 4 Post-Remediation Assessment")
    print("=" * 70)

    # Run all checks
    check_dataset_overview(cursor, verbose)
    all_checks.extend(check_structural_integrity(cursor, verbose))
    all_checks.extend(check_unit_quality(cursor, verbose))
    all_checks.extend(check_ratio_metric(cursor, verbose))
    all_checks.extend(check_currency_metric(cursor, verbose))
    all_checks.extend(check_ebitda_scale(cursor, verbose))
    all_checks.extend(check_forecasting_readiness(cursor, verbose))

    cursor.close()

    # Print summary and return exit code
    return print_summary(all_checks)


def main() -> int:
    """Main entry point."""
    args = parse_args()

    try:
        return verify_all_quality(verbose=args.verbose)

    except Exception as e:
        print(f"\n ERROR: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
