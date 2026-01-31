#!/usr/bin/env python3
"""Data Quality Verification Script.

Runs verification tests to measure data quality metrics before and after fixes.
Use this script to track progress on data quality remediation.

Usage (production database):
    POSTGRES_USER=raglite POSTGRES_PASSWORD=raglite POSTGRES_DB=raglite POSTGRES_PORT=5432 \\
        uv run python scripts/verify_data_quality.py

Usage (quiet mode):
    POSTGRES_USER=raglite POSTGRES_PASSWORD=raglite POSTGRES_DB=raglite POSTGRES_PORT=5432 \\
        uv run python scripts/verify_data_quality.py 2>/dev/null
"""

import logging
import os

# Suppress verbose logging unless DEBUG is set
if not os.getenv("DEBUG"):
    logging.getLogger("raglite").setLevel(logging.WARNING)

import asyncio
import sys
from dataclasses import dataclass


@dataclass
class QualityMetrics:
    """Data quality metrics for tracking."""

    metric_name: str
    total_points: int
    negative_count: int
    swing_ratio: float | None
    min_value: float | None
    max_value: float | None
    status: str


async def verify_metric(metric: str, min_points: int = 6) -> QualityMetrics:
    """Verify data quality for a specific metric."""
    from raglite.forecasting.timeseries import extract_timeseries_from_sql

    try:
        data = await extract_timeseries_from_sql(metric, min_points=min_points)
        points = data.points

        if not points:
            return QualityMetrics(
                metric_name=metric,
                total_points=0,
                negative_count=0,
                swing_ratio=None,
                min_value=None,
                max_value=None,
                status="NO_DATA",
            )

        values = [p.value for p in points if p.value is not None]
        positive_values = [v for v in values if v > 0]
        negative_count = sum(1 for v in values if v < 0)

        swing_ratio = None
        if len(positive_values) >= 2:
            swing_ratio = max(positive_values) / min(positive_values)

        return QualityMetrics(
            metric_name=metric,
            total_points=len(points),
            negative_count=negative_count,
            swing_ratio=swing_ratio,
            min_value=min(values) if values else None,
            max_value=max(values) if values else None,
            status="OK" if swing_ratio and swing_ratio < 5.0 else "HIGH_VARIANCE",
        )

    except Exception as e:
        return QualityMetrics(
            metric_name=metric,
            total_points=0,
            negative_count=0,
            swing_ratio=None,
            min_value=None,
            max_value=None,
            status=f"ERROR: {str(e)[:50]}",
        )


async def run_verification() -> None:
    """Run full verification suite."""
    print("\n" + "=" * 70)
    print("RAGLite Data Quality Verification")
    print("=" * 70)

    # Metrics to verify
    metrics_to_test = [
        "ebitda",
        "revenue",
        "capex",
        "variable_cost",
        "electrical_energy",
        "thermal_energy",
    ]

    print(f"\nTesting {len(metrics_to_test)} metrics...\n")

    # Run verification for each metric
    results: list[QualityMetrics] = []
    for metric in metrics_to_test:
        print(f"  Verifying {metric}...", end=" ", flush=True)
        result = await verify_metric(metric)
        results.append(result)
        print(result.status)

    # Print detailed results
    print("\n" + "-" * 70)
    print("DETAILED RESULTS")
    print("-" * 70)

    for r in results:
        print(f"\n{r.metric_name.upper()}")
        print(f"  Points: {r.total_points}")
        print(f"  Negatives: {r.negative_count}")
        if r.swing_ratio:
            swing_status = "✓" if r.swing_ratio < 5.0 else "✗"
            print(f"  Swing Ratio: {r.swing_ratio:.1f}x {swing_status} (target: <5x)")
        if r.min_value is not None and r.max_value is not None:
            print(f"  Range: {r.min_value:.2f} to {r.max_value:.2f}")
        print(f"  Status: {r.status}")

    # Summary table
    print("\n" + "-" * 70)
    print("SUMMARY")
    print("-" * 70)
    print(f"{'Metric':<20} {'Points':>8} {'Swing':>10} {'Status':>15}")
    print("-" * 70)

    passed = 0
    for r in results:
        swing_str = f"{r.swing_ratio:.1f}x" if r.swing_ratio else "N/A"
        status_icon = "✓" if r.status == "OK" else "✗"
        print(f"{r.metric_name:<20} {r.total_points:>8} {swing_str:>10} {status_icon:>15}")
        if r.status == "OK":
            passed += 1

    print("-" * 70)
    print(f"Passed: {passed}/{len(results)}")

    # Quality targets
    print("\n" + "=" * 70)
    print("QUALITY TARGETS")
    print("=" * 70)
    print("""
    | Metric              | Current | Target  |
    |---------------------|---------|---------|
    | EBITDA swing ratio  | ?       | <5x     |
    | Negative costs      | 88.9%   | 0% (converted) |
    | Missing units       | 42.7%   | <10%    |
    | Malformed units     | ~1%     | 0%      |
    """)


async def run_sql_quality_check() -> None:
    """Run SQL-based quality checks directly on the database."""
    print("\n" + "=" * 70)
    print("DATABASE QUALITY METRICS (Direct SQL)")
    print("=" * 70)

    from raglite.shared.clients import get_postgresql_connection

    conn = get_postgresql_connection()
    cursor = conn.cursor()

    # Quality metrics query
    cursor.execute("""
        SELECT
            COUNT(*) as total_rows,
            ROUND(100.0 * SUM(CASE WHEN value IS NULL THEN 1 ELSE 0 END) / COUNT(*)::numeric, 1) as pct_null,
            ROUND(100.0 * SUM(CASE WHEN unit IS NULL OR unit = '' THEN 1 ELSE 0 END) / COUNT(*)::numeric, 1) as pct_missing_unit,
            ROUND(100.0 * SUM(CASE WHEN value < 0 THEN 1 ELSE 0 END) / COUNT(*)::numeric, 1) as pct_negative
        FROM financial_tables
    """)
    row = cursor.fetchone()

    print(f"\nTotal Rows: {row[0]:,}")
    print(f"NULL Values: {row[1]}%")
    print(f"Missing Units: {row[2]}%")
    print(f"Negative Values: {row[3]}%")

    # EBITDA-specific metrics
    cursor.execute("""
        SELECT
            COUNT(*) as total,
            COUNT(DISTINCT unit) as unique_units,
            ROUND(MIN(value)::numeric, 2) as min_val,
            ROUND(MAX(value)::numeric, 2) as max_val
        FROM financial_tables
        WHERE LOWER(metric) LIKE '%ebitda%'
          AND entity_normalized = 'Group'
    """)
    row = cursor.fetchone()

    print("\nEBITDA (Group entity):")
    print(f"  Total Records: {row[0]}")
    print(f"  Unique Units: {row[1]}")
    print(f"  Value Range: {row[2]} to {row[3]}")

    cursor.close()


def main() -> int:
    """Main entry point."""
    try:
        # Run extraction-based verification
        asyncio.run(run_verification())

        # Run SQL-based verification
        asyncio.run(run_sql_quality_check())

        return 0
    except Exception as e:
        print(f"\nError: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
