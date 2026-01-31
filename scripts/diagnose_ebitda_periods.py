#!/usr/bin/env python3
"""Diagnostic script for EBITDA period parsing issues.

Analyzes period formats in database using the new period classification module.
Run after implementing period parser fixes to validate improvements.

EBITDA Data Quality Fix (2026-01-30): Updated to use period_classification module.

Usage:
    python scripts/diagnose_ebitda_periods.py
"""

from collections import Counter

from raglite.forecasting.timeseries.parsing import parse_period_to_date
from raglite.forecasting.timeseries.period_classification import (
    ClassifiedPeriod,
    PeriodType,
    classify_period,
    generate_classification_report,
    validate_period_homogeneity,
)
from raglite.shared.clients import get_postgresql_connection
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


def is_parseable_after_normalization(classified: ClassifiedPeriod) -> bool:
    """Test if a classified period can be parsed after normalization."""
    if not classified.is_usable or not classified.normalized:
        return False
    try:
        parse_period_to_date(classified.normalized, 2024)  # fiscal_year from period
        return True
    except (ValueError, TypeError):
        return False


def main() -> None:
    """Analyze GROUP EBITDA period formats and parseability."""
    conn = get_postgresql_connection()
    cursor = conn.cursor()

    # Query all EBITDA periods with values
    # No entity filter to see all period patterns across data
    query = """
        SELECT period, value, document_id
        FROM financial_tables
        WHERE metric = 'EBITDA'
          AND period IS NOT NULL
          AND TRIM(period) <> ''
          AND value IS NOT NULL
        ORDER BY period;
    """

    cursor.execute(query)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    print("\n" + "=" * 80)
    print("EBITDA PERIOD PARSING DIAGNOSTIC REPORT")
    print("=" * 80)
    print(f"\nTotal EBITDA records with non-null period and value: {len(rows)}")

    if len(rows) == 0:
        print("\nNo records found. Check entity/metric filters in query.")
        print("=" * 80)
        return

    # Extract periods and classify them
    periods = [row[0] for row in rows]
    classified_periods = [classify_period(p) for p in periods]

    # Generate classification report
    report = generate_classification_report(periods)

    # Count parseable after normalization
    parseable_after_norm = sum(1 for c in classified_periods if is_parseable_after_normalization(c))

    # Validate homogeneity
    is_homogeneous, homogeneity_info = validate_period_homogeneity(classified_periods)

    # Print classification summary
    print(f"\n{'=' * 80}")
    print("PERIOD CLASSIFICATION SUMMARY (New Module)")
    print("=" * 80)
    print(f"{'Type':<25} {'Count':<10} {'%':<10}")
    print("-" * 80)
    print(
        f"{'MONTHLY_ACTUAL (usable)':<25} {report.monthly_actual_count:<10} {report.monthly_actual_count / len(rows) * 100:>6.1f}%"
    )
    print(
        f"{'YTD_ACTUAL (usable)':<25} {report.ytd_actual_count:<10} {report.ytd_actual_count / len(rows) * 100:>6.1f}%"
    )
    print(
        f"{'BUDGET (excluded)':<25} {report.budget_count:<10} {report.budget_count / len(rows) * 100:>6.1f}%"
    )
    print(
        f"{'YTD_BUDGET (excluded)':<25} {report.ytd_budget_count:<10} {report.ytd_budget_count / len(rows) * 100:>6.1f}%"
    )
    print(
        f"{'UNKNOWN (excluded)':<25} {report.unknown_count:<10} {report.unknown_count / len(rows) * 100:>6.1f}%"
    )
    print("-" * 80)
    print(f"{'TOTAL USABLE':<25} {report.usable_records:<10} {report.usability_rate:>6.1f}%")

    # Print parseability summary
    print(f"\n{'=' * 80}")
    print("PARSEABILITY SUMMARY")
    print("=" * 80)
    print(f"Records classified as usable: {report.usable_records}")
    print(f"Records parseable after normalization: {parseable_after_norm}")
    print(
        f"Parseability rate of usable: {parseable_after_norm / max(report.usable_records, 1) * 100:.1f}%"
    )

    # Print homogeneity check
    print(f"\n{'=' * 80}")
    print("HOMOGENEITY CHECK")
    print("=" * 80)
    print(f"Is homogeneous: {is_homogeneous}")
    print(f"Info: {homogeneity_info}")

    # Show examples by type
    print(f"\n{'=' * 80}")
    print("EXAMPLES BY CLASSIFICATION TYPE")
    print("=" * 80)

    examples_by_type: dict[PeriodType, list[tuple[str, str | None]]] = {pt: [] for pt in PeriodType}
    for classified in classified_periods:
        if len(examples_by_type[classified.period_type]) < 5:
            examples_by_type[classified.period_type].append(
                (classified.original, classified.normalized)
            )

    for period_type in PeriodType:
        examples = examples_by_type[period_type]
        if examples:
            print(f"\n{period_type.value.upper()}:")
            for orig, norm in examples:
                if norm:
                    print(f"  '{orig}' -> '{norm}'")
                else:
                    print(f"  '{orig}' -> (excluded)")

    # Show unparseable usable periods (should be empty after fix)
    unparseable_usable = [
        c for c in classified_periods if c.is_usable and not is_parseable_after_normalization(c)
    ]
    if unparseable_usable:
        print(f"\n{'=' * 80}")
        print("WARNING: USABLE PERIODS THAT FAILED TO PARSE")
        print("=" * 80)
        for c in unparseable_usable[:10]:
            print(f"  Original: '{c.original}' -> Normalized: '{c.normalized}'")
        if len(unparseable_usable) > 10:
            print(f"  ... and {len(unparseable_usable) - 10} more")

    # Print exclusion breakdown
    print(f"\n{'=' * 80}")
    print("EXCLUSION BREAKDOWN")
    print("=" * 80)
    excluded = [c for c in classified_periods if not c.is_usable]
    exclusion_counter: Counter[str] = Counter()
    for c in excluded:
        exclusion_counter[c.period_type.value] += 1

    print(f"Total excluded: {len(excluded)} records")
    for reason, count in exclusion_counter.most_common():
        examples = [c.original for c in excluded if c.period_type.value == reason][:3]
        print(f"  {reason}: {count} (e.g., {examples})")

    # Print recommendations
    print(f"\n{'=' * 80}")
    print("EXPECTED IMPROVEMENT")
    print("=" * 80)
    print("\n  BEFORE FIX:")
    print("    - Only strict Mon-YY format accepted")
    print("    - ~2 data points extracted (after aggregation)")
    print("\n  AFTER FIX:")
    print(f"    - {report.usable_records} usable records ({report.usability_rate:.1f}%)")
    print(f"    - {report.monthly_actual_count} monthly + {report.ytd_actual_count} YTD")
    print("    - Budget/Unknown properly excluded")
    print("    - Estimated unique periods: 50-80 after aggregation")

    print(f"\n{'=' * 80}")
    print("VERIFICATION COMMANDS")
    print("=" * 80)
    print("\n# Run unit tests:")
    print("uv run pytest tests/unit/forecasting/test_period_classification.py -v")
    print("\n# Run integration test:")
    print(
        'uv run pytest tests/integration/forecasting/test_timeseries_extraction.py -k "ebitda" -v'
    )
    print("\n# Test actual forecast:")
    print(
        "# Request GROUP EBITDA forecast via MCP - should produce realistic ~220-260M EUR for 2026"
    )

    print("\n" + "=" * 80)
    print("END REPORT")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
