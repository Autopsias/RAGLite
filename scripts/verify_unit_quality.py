#!/usr/bin/env python3
"""Verify unit quality after data remediation.

Validates the quality of unit data after running the fix scripts:
- Phase D: fix_unit_audit_columns.py
- Phase A: fix_unit_standardization.py
- Phase B: fix_unit_magnitude_inference.py
- Phase C: fix_unit_context_inference.py

Usage:
    POSTGRES_USER=raglite POSTGRES_PASSWORD=raglite POSTGRES_DB=raglite POSTGRES_PORT=5432 \
        uv run python scripts/verify_unit_quality.py
"""

from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass

# Suppress verbose logging unless DEBUG is set
if not os.getenv("DEBUG"):
    logging.getLogger("raglite").setLevel(logging.WARNING)


@dataclass
class QualityTarget:
    """Quality target definition."""

    name: str
    target: str
    current: float | int
    passed: bool
    details: str = ""


def verify_unit_quality() -> list[QualityTarget]:
    """Run all unit quality verification checks.

    Returns:
        List of QualityTarget results
    """
    from raglite.shared.clients import get_postgresql_connection

    conn = get_postgresql_connection()
    cursor = conn.cursor()
    results: list[QualityTarget] = []

    print("\n" + "=" * 70)
    print("Unit Quality Verification Report")
    print("=" * 70)

    # Check 1: NULL unit percentage
    print("\n1. NULL Unit Percentage")
    cursor.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN unit IS NULL THEN 1 ELSE 0 END) as null_count
        FROM financial_tables
    """)
    row = cursor.fetchone()
    total, null_count = row
    null_pct = 100.0 * null_count / total if total > 0 else 0

    passed = null_pct < 10.0
    results.append(
        QualityTarget(
            name="NULL units",
            target="<10%",
            current=null_pct,
            passed=passed,
            details=f"{null_count:,} of {total:,} rows",
        )
    )
    status = "✓ PASS" if passed else "✗ FAIL"
    print(f"   {status}: {null_pct:.1f}% NULL units (target: <10%)")
    print(f"   Details: {null_count:,} of {total:,} rows")

    # Check 2: Contaminated units (entity names in unit column)
    print("\n2. Contaminated Units")
    contaminated_patterns = [
        "GROUP",
        "ANGOLA",
        "TUNISIA",
        "LEBANON",
        "PORTUGAL",
        "BRAZIL",
        "EGYPT",
        "SPAIN",
        "MOROCCO",
        "N/A",
        "Intercompany",
    ]
    pattern_list = ", ".join(f"'{p}'" for p in contaminated_patterns)

    cursor.execute(f"""
        SELECT COUNT(*) FROM financial_tables
        WHERE unit IN ({pattern_list})
    """)
    contaminated_count = cursor.fetchone()[0]

    passed = contaminated_count == 0
    results.append(
        QualityTarget(
            name="Contaminated units",
            target="0",
            current=contaminated_count,
            passed=passed,
            details="Entity names in unit column",
        )
    )
    status = "✓ PASS" if passed else "✗ FAIL"
    print(f"   {status}: {contaminated_count:,} contaminated units (target: 0)")

    # Check 3: Unit variant count (should have canonical forms)
    print("\n3. Unit Variant Count")
    cursor.execute("""
        SELECT COUNT(DISTINCT unit)
        FROM financial_tables
        WHERE unit IS NOT NULL AND unit != ''
    """)
    unique_units = cursor.fetchone()[0]

    passed = unique_units < 30
    results.append(
        QualityTarget(
            name="Unique unit variants",
            target="<30",
            current=unique_units,
            passed=passed,
            details="Canonical forms expected",
        )
    )
    status = "✓ PASS" if passed else "✗ FAIL"
    print(f"   {status}: {unique_units} unique units (target: <30 canonical)")

    # Show top units
    cursor.execute("""
        SELECT unit, COUNT(*) as cnt
        FROM financial_tables
        WHERE unit IS NOT NULL AND unit != ''
        GROUP BY unit
        ORDER BY cnt DESC
        LIMIT 15
    """)
    top_units = cursor.fetchall()
    print("   Top units:")
    for unit_val, cnt in top_units:
        print(f"     {unit_val}: {cnt:,}")

    # Check 4: EBITDA swing ratio (should be reduced after unit standardization)
    # NOTE: Filter by M EUR unit and consolidated EBITDA IFRS (main metric) to get consistent scale
    # Exclude PRECAST and other sub-segments, and focus on full-year (YTD Dec) figures
    print("\n4. EBITDA Swing Ratio (M EUR, EBITDA IFRS YTD only)")
    cursor.execute("""
        SELECT
            MAX(value) / NULLIF(MIN(value), 0) as swing_ratio,
            MIN(value) as min_val,
            MAX(value) as max_val,
            COUNT(*) as cnt
        FROM financial_tables
        WHERE metric = 'EBITDA IFRS'
          AND entity_normalized = 'Group'
          AND value > 0
          AND unit = 'M EUR'
          AND period LIKE 'YTD Dec%'
    """)
    row = cursor.fetchone()
    swing_ratio = row[0] if row[0] else 0
    min_val = row[1] if row[1] else 0
    max_val = row[2] if row[2] else 0
    cnt = row[3]

    # For comparable YTD full-year figures, swing should be much lower
    passed = swing_ratio < 5.0
    results.append(
        QualityTarget(
            name="EBITDA IFRS swing (YTD)",
            target="<5x",
            current=swing_ratio,
            passed=passed,
            details=f"Range: {min_val:.2f} to {max_val:.2f} ({cnt} full-year points)",
        )
    )
    status = "✓ PASS" if passed else "✗ FAIL"
    print(f"   {status}: {swing_ratio:.1f}x swing ratio (target: <5x)")
    print(f"   Details: Range {min_val:.2f} to {max_val:.2f} ({cnt} data points)")

    # Check 5: Inference coverage
    print("\n5. Inference Coverage")
    cursor.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN unit_inferred = TRUE THEN 1 ELSE 0 END) as inferred_count
        FROM financial_tables
    """)
    row = cursor.fetchone()
    total, inferred_count = row
    inferred_pct = 100.0 * inferred_count / total if total > 0 else 0

    # This is informational, not pass/fail
    print(f"   INFO: {inferred_pct:.1f}% of units were inferred ({inferred_count:,} rows)")

    # Show inference methods breakdown
    cursor.execute("""
        SELECT unit_inference_method, COUNT(*) as cnt
        FROM financial_tables
        WHERE unit_inferred = TRUE
        GROUP BY unit_inference_method
        ORDER BY cnt DESC
    """)
    methods = cursor.fetchall()
    if methods:
        print("   Inference methods used:")
        for method, cnt in methods:
            print(f"     {method or 'NULL'}: {cnt:,}")

    # Check 6: Confidence levels
    print("\n6. Inference Confidence Distribution")
    cursor.execute("""
        SELECT
            COALESCE(unit_confidence, 'original') as confidence,
            COUNT(*) as cnt
        FROM financial_tables
        GROUP BY COALESCE(unit_confidence, 'original')
        ORDER BY cnt DESC
    """)
    confidence_dist = cursor.fetchall()
    print("   Distribution:")
    for conf, cnt in confidence_dist:
        pct = 100.0 * cnt / total
        print(f"     {conf}: {cnt:,} ({pct:.1f}%)")

    # Check 7: Low confidence review queue
    print("\n7. Low Confidence Review Queue")
    cursor.execute("""
        SELECT COUNT(*)
        FROM financial_tables
        WHERE unit_confidence = 'low'
    """)
    low_conf_count = cursor.fetchone()[0]
    print(f"   Rows flagged for review: {low_conf_count:,}")

    if low_conf_count > 0:
        cursor.execute("""
            SELECT metric, unit, COUNT(*) as cnt
            FROM financial_tables
            WHERE unit_confidence = 'low'
            GROUP BY metric, unit
            ORDER BY cnt DESC
            LIMIT 10
        """)
        low_conf = cursor.fetchall()
        print("   Top low-confidence inferences:")
        for metric, unit, cnt in low_conf:
            print(f"     '{metric}' → '{unit}': {cnt:,}")

    # Check 8: Verify original units preserved
    # NOTE: Only count rows that originally HAD units (non-null)
    print("\n8. Original Unit Preservation")
    cursor.execute("""
        SELECT
            SUM(CASE WHEN unit_original IS NOT NULL THEN 1 ELSE 0 END) as had_original,
            SUM(CASE WHEN unit_original IS NOT NULL AND unit_original != '' THEN 1 ELSE 0 END) as preserved_non_empty
        FROM financial_tables
    """)
    row = cursor.fetchone()
    had_original, preserved_non_empty = row
    # For preservation check: we only care if original non-null units were preserved
    # Rows that originally had NULL units don't need preservation
    preservation_pct = 100.0 * preserved_non_empty / had_original if had_original > 0 else 100.0

    # This should always be 100% if we ran Phase D correctly
    passed = preservation_pct > 90.0
    results.append(
        QualityTarget(
            name="Original units preserved",
            target=">90%",
            current=preservation_pct,
            passed=passed,
            details=f"{preserved_non_empty:,} of {had_original:,} original non-null units",
        )
    )
    status = "✓ PASS" if passed else "✗ FAIL"
    print(f"   {status}: {preservation_pct:.1f}% preserved (target: >90%)")
    print(f"   Details: {preserved_non_empty:,} of {had_original:,} original non-null units")

    # Check 9: Rollback capability
    print("\n9. Rollback Capability Check")
    cursor.execute("""
        SELECT COUNT(*)
        FROM financial_tables
        WHERE unit_inferred = TRUE
          AND unit != unit_original
    """)
    rollback_candidates = cursor.fetchone()[0]
    print(f"   Rows that could be rolled back: {rollback_candidates:,}")
    print("   Rollback command: UPDATE SET unit = unit_original WHERE unit_inferred = TRUE")

    cursor.close()

    return results


def print_summary(results: list[QualityTarget]) -> int:
    """Print summary and return exit code."""
    print("\n" + "=" * 70)
    print("QUALITY SUMMARY")
    print("=" * 70)

    passed_count = sum(1 for r in results if r.passed)
    total_checks = len(results)

    print(f"\n{'Check':<30} {'Target':>10} {'Current':>10} {'Status':>10}")
    print("-" * 70)

    for r in results:
        current_str = f"{r.current:.1f}" if isinstance(r.current, float) else str(r.current)
        status = "✓ PASS" if r.passed else "✗ FAIL"
        print(f"{r.name:<30} {r.target:>10} {current_str:>10} {status:>10}")

    print("-" * 70)
    print(f"Passed: {passed_count}/{total_checks}")

    # Success criteria
    if passed_count == total_checks:
        print("\n✓ All quality checks passed!")
        return 0
    else:
        print(f"\n✗ {total_checks - passed_count} check(s) failed")
        return 1


def print_remediation_status() -> None:
    """Print current remediation status vs targets."""
    print("\n" + "=" * 70)
    print("REMEDIATION STATUS vs TARGETS")
    print("=" * 70)

    # Get current metrics from database
    from raglite.shared.clients import get_postgresql_connection

    conn = get_postgresql_connection()
    cursor = conn.cursor()

    # Get current NULL percentage
    cursor.execute("""
        SELECT
            ROUND(100.0 * SUM(CASE WHEN unit IS NULL THEN 1 ELSE 0 END) / COUNT(*)::numeric, 1)
        FROM financial_tables
    """)
    current_null_pct = cursor.fetchone()[0]

    # Get EBITDA swing ratio (for M EUR only, comparable scale)
    cursor.execute("""
        SELECT ROUND((MAX(value) / NULLIF(MIN(value), 0))::numeric, 1)
        FROM financial_tables
        WHERE metric = 'EBITDA IFRS'
          AND entity_normalized = 'Group'
          AND value > 0
          AND unit = 'M EUR'
          AND period LIKE 'YTD Dec%'
    """)
    current_swing = cursor.fetchone()[0] or 0

    # Get contaminated count
    cursor.execute("""
        SELECT COUNT(*) FROM financial_tables
        WHERE unit IN ('GROUP', 'ANGOLA', 'TUNISIA', 'LEBANON', 'N/A')
    """)
    current_contaminated = cursor.fetchone()[0]

    cursor.close()

    print(f"""
    | Metric              | Before   | Current  | Target   |
    |---------------------|----------|----------|----------|
    | NULL units          | 59.6%    | {current_null_pct}%     | <10%     |
    | Contaminated units  | ~7,200   | {current_contaminated}       | 0        |
    | EBITDA swing ratio  | 12.4x    | {current_swing}x      | <5x      |
    """)


def main() -> int:
    """Main entry point."""
    try:
        results = verify_unit_quality()
        exit_code = print_summary(results)
        print_remediation_status()
        return exit_code

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
