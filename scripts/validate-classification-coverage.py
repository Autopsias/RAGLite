#!/usr/bin/env python3
"""Validate classification coverage after re-ingestion.

This script checks that all table rows have classification fields populated:
- period_type
- value_type
- entity_level

Reports coverage percentages and generates markdown report.

Exit codes:
    0 - 100% coverage achieved
    1 - Coverage < 100% (has NULL values)
"""

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ["APP_ENV"] = "production"

from datetime import datetime

import psycopg2
from psycopg2 import sql

from raglite.shared.config import get_settings


def query_coverage(conn_str: str) -> dict:
    """Query PostgreSQL for classification coverage.

    Returns:
        Dictionary with coverage statistics
    """
    conn = psycopg2.connect(conn_str)
    try:
        with conn.cursor() as cur:
            # Get total counts and NULL counts
            cur.execute(
                """
                SELECT
                    COUNT(*) as total_rows,
                    COUNT(period_type) as with_period_type,
                    COUNT(value_type) as with_value_type,
                    COUNT(entity_level) as with_entity_level,
                    SUM(CASE WHEN period_type IS NULL THEN 1 ELSE 0 END) as null_period_type,
                    SUM(CASE WHEN value_type IS NULL THEN 1 ELSE 0 END) as null_value_type,
                    SUM(CASE WHEN entity_level IS NULL THEN 1 ELSE 0 END) as null_entity_level
                FROM financial_tables;
            """
            )
            row = cur.fetchone()

            return {
                "total_rows": row[0],
                "with_period_type": row[1],
                "with_value_type": row[2],
                "with_entity_level": row[3],
                "null_period_type": row[4],
                "null_value_type": row[5],
                "null_entity_level": row[6],
            }
    finally:
        conn.close()


def query_breakdown(conn_str: str, field: str) -> list[tuple]:
    """Query breakdown by classification field.

    Args:
        conn_str: PostgreSQL connection string
        field: Field name (period_type, value_type, entity_level)

    Returns:
        List of (value, count, percentage) tuples
    """
    # Validate field against whitelist to prevent SQL injection
    allowed_fields = ["period_type", "value_type", "entity_level"]
    if field not in allowed_fields:
        raise ValueError(f"Invalid field: {field}. Must be one of {allowed_fields}")

    conn = psycopg2.connect(conn_str)
    try:
        with conn.cursor() as cur:
            # Use sql.Identifier for safe SQL composition
            query = sql.SQL(
                """
                SELECT {field}, COUNT(*) as count,
                       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 1) as percentage
                FROM financial_tables
                WHERE {field} IS NOT NULL
                GROUP BY {field}
                ORDER BY count DESC;
            """
            ).format(field=sql.Identifier(field))
            cur.execute(query)
            return cur.fetchall()
    finally:
        conn.close()


def generate_report(coverage: dict, breakdowns: dict, output_path: Path) -> None:
    """Generate markdown coverage report.

    Args:
        coverage: Coverage statistics
        breakdowns: Breakdowns by field
        output_path: Output file path
    """
    with open(output_path, "w") as f:
        f.write("# Classification Coverage Report\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        # Overall coverage
        f.write("## Overall Coverage\n\n")
        f.write(f"**Total rows:** {coverage['total_rows']}\n\n")

        f.write("| Field | Populated | NULL | Coverage |\n")
        f.write("|-------|-----------|------|----------|\n")

        for field in ["period_type", "value_type", "entity_level"]:
            populated = coverage[f"with_{field}"]
            null_count = coverage[f"null_{field}"]
            total = coverage["total_rows"]
            coverage_pct = 100 * populated / max(total, 1)

            f.write(f"| {field} | {populated} | {null_count} | {coverage_pct:.1f}% |\n")

        # Breakdowns
        for field, breakdown in breakdowns.items():
            f.write(f"\n## {field} Breakdown\n\n")
            f.write("| Classification | Count | Percentage |\n")
            f.write("|----------------|-------|------------|\n")

            for value, count, percentage in breakdown:
                f.write(f"| {value} | {count:,} | {percentage}% |\n")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Validate classification coverage")
    parser.add_argument(
        "--output",
        default="docs/sprint-artifacts/classification-coverage-report.md",
        help="Output report path (default: docs/sprint-artifacts/classification-coverage-report.md)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed output",
    )
    args = parser.parse_args()

    print("=" * 80)
    print("CLASSIFICATION COVERAGE VALIDATION")
    print("=" * 80)
    print()

    # Get settings
    settings = get_settings()

    # Build connection string from settings
    conn_str = (
        f"postgresql://{settings.postgres_user}:{settings.postgres_password}"
        f"@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
    )

    # Query coverage
    print("Querying classification coverage...")
    coverage = query_coverage(conn_str)

    total_rows = coverage["total_rows"]
    print(f"Total rows: {total_rows:,}")
    print()

    # Check each field
    all_covered = True
    for field in ["period_type", "value_type", "entity_level"]:
        populated = coverage[f"with_{field}"]
        null_count = coverage[f"null_{field}"]
        coverage_pct = 100 * populated / max(total_rows, 1)

        status = "✅" if null_count == 0 else "❌"
        print(f"{status} {field}: {populated:,}/{total_rows:,} ({coverage_pct:.1f}%)")

        if null_count > 0:
            all_covered = False
            if args.verbose:
                print(f"   WARNING: {null_count:,} rows have NULL {field}")

    print()

    # Query breakdowns
    print("Querying classification breakdowns...")
    breakdowns = {}
    for field in ["period_type", "value_type", "entity_level"]:
        breakdowns[field] = query_breakdown(conn_str, field)

        if args.verbose:
            print(f"\n{field} breakdown:")
            for value, count, percentage in breakdowns[field][:5]:  # Top 5
                print(f"  {value}: {count:,} ({percentage}%)")

    print()

    # Generate report
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Generating report: {output_path}")
    generate_report(coverage, breakdowns, output_path)
    print("✅ Report saved")

    print()
    print("=" * 80)
    if all_covered:
        print("✅ VALIDATION PASSED - 100% COVERAGE")
        print("=" * 80)
        return 0
    else:
        print("❌ VALIDATION FAILED - INCOMPLETE COVERAGE")
        print("=" * 80)
        print("Some rows have NULL classification fields.")
        print("Review the report for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
