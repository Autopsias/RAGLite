#!/usr/bin/env python3
"""Phase C: Context-based unit inference.

Uses metric-to-unit mapping and same-metric reference lookup to infer units
for remaining NULL values after magnitude-based inference.

Prerequisites:
    - Run fix_unit_audit_columns.py first (Phase D)
    - Run fix_unit_standardization.py first (Phase A)
    - Run fix_unit_magnitude_inference.py first (Phase B)

Usage:
    POSTGRES_USER=raglite POSTGRES_PASSWORD=raglite POSTGRES_DB=raglite POSTGRES_PORT=5432 \
        uv run python scripts/fix_unit_context_inference.py

    # Dry run (show SQL without executing):
    POSTGRES_USER=raglite POSTGRES_PASSWORD=raglite POSTGRES_DB=raglite POSTGRES_PORT=5432 \
        uv run python scripts/fix_unit_context_inference.py --dry-run
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

# Suppress verbose logging unless DEBUG is set
if not os.getenv("DEBUG"):
    logging.getLogger("raglite").setLevel(logging.WARNING)


# Metric-to-unit default mappings (based on domain knowledge)
# These are applied when magnitude inference didn't provide a clear answer
METRIC_UNIT_DEFAULTS: dict[str, str] = {
    # Financial metrics (default to M EUR for consolidated reporting)
    "EBITDA IFRS": "M EUR",
    "EBITDA": "M EUR",
    "Turnover": "M EUR",
    "Revenue": "M EUR",
    "Total Revenue": "M EUR",
    "Net Revenue": "M EUR",
    "Gross Revenue": "M EUR",
    "Operating Income": "M EUR",
    "Net Income": "M EUR",
    "Profit Before Tax": "M EUR",
    "Profit After Tax": "M EUR",
    "Income Tax": "M EUR",
    "Interest Expense": "M EUR",
    "Interest Income": "M EUR",
    "Net Interest": "M EUR",
    "CAPEX": "M EUR",
    "Capital Expenditure": "M EUR",
    "CapEx": "M EUR",
    "Operating Cash Flow": "M EUR",
    "Free Cash Flow": "M EUR",
    "Net Cash Flow": "M EUR",
    "Total Assets": "M EUR",
    "Total Liabilities": "M EUR",
    "Total Equity": "M EUR",
    "Net Debt": "M EUR",
    "Gross Debt": "M EUR",
    # Production metrics (default to kton)
    "Production": "kton",
    "Cement": "kton",
    "Clinker": "kton",
    "Cement Production": "kton",
    "Clinker Production": "kton",
    "Sales Volumes": "kton",
    "Sales Volume": "kton",
    "Aggregate": "kton",
    "Aggregates": "kton",
    "Ready-Mix": "m³",
    "Ready Mix": "m³",
    "Readymix": "m³",
    "Concrete": "m³",
    # Energy metrics
    "Electrical Energy": "GWh",
    "Electric Energy": "GWh",
    "Electricity": "GWh",
    "Electricity Consumption": "GWh",
    "Power Consumption": "GWh",
    "Thermal Energy": "GJ",
    "Heat Consumption": "GJ",
    "Fuel Consumption": "GJ",
    # Ratio/percentage metrics
    "Margin": "%",
    "EBITDA Margin": "%",
    "Net Margin": "%",
    "Gross Margin": "%",
    "Operating Margin": "%",
    "Return on Equity": "%",
    "Return on Assets": "%",
    "ROE": "%",
    "ROA": "%",
    "ROIC": "%",
    "Utilization Rate": "%",
    "Capacity Utilization": "%",
    "Growth Rate": "%",
    "YoY Growth": "%",
    "Market Share": "%",
    # Per-unit metrics
    "Variable Cost per ton": "EUR/ton",
    "Fixed Cost per ton": "EUR/ton",
    "Cost per ton": "EUR/ton",
    "Price per ton": "EUR/ton",
    "Revenue per ton": "EUR/ton",
    "CO2 Emissions per ton": "kg/ton",
    "Energy per ton": "GJ/ton",
    # Employee metrics
    "Headcount": "FTE",
    "Employees": "FTE",
    "FTE": "FTE",
    "Full Time Equivalents": "FTE",
}


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Context-based unit inference using metric mapping and reference lookup"
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


def infer_units_by_context(dry_run: bool = False) -> dict[str, int]:
    """Infer units using context (metric names, reference lookup).

    Strategies:
    1. Direct metric-to-unit mapping from METRIC_UNIT_DEFAULTS
    2. Same-metric reference lookup (find most common unit for same metric)
    3. Document pattern inference (2025 docs use specific conventions)

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
    print("Phase C: Context-Based Unit Inference")
    print("=" * 70)

    # Check prerequisites
    if not check_prerequisites(cursor):
        print("\n✗ ERROR: Audit columns not found!")
        print("  Run fix_unit_audit_columns.py first to preserve original units.")
        return {"error": 1}

    # Step 1: Show current state
    print("\nStep 1: Current NULL/empty unit distribution...")
    cursor.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN unit IS NULL OR unit = '' THEN 1 ELSE 0 END) as null_empty,
            SUM(CASE WHEN unit_inferred = TRUE THEN 1 ELSE 0 END) as already_inferred
        FROM financial_tables
    """)
    row = cursor.fetchone()
    total, null_empty, already_inferred = row
    print(f"  Total rows: {total:,}")
    print(f"  NULL/empty units: {null_empty:,} ({100.0 * null_empty / total:.1f}%)")
    print(f"  Already inferred: {already_inferred:,}")

    # Step 2: Apply direct metric-to-unit mapping
    print("\nStep 2: Applying direct metric-to-unit mapping...")
    total_mapped = 0

    for metric_name, default_unit in METRIC_UNIT_DEFAULTS.items():
        # Case-insensitive exact match
        update_sql = """
            UPDATE financial_tables
            SET unit = %s,
                unit_inferred = TRUE,
                unit_inference_method = 'metric_default',
                unit_confidence = 'medium'
            WHERE LOWER(metric) = LOWER(%s)
              AND (unit IS NULL OR unit = '')
              AND (unit_inferred IS NULL OR unit_inferred = FALSE)
        """

        if dry_run:
            cursor.execute(
                """
                SELECT COUNT(*) FROM financial_tables
                WHERE LOWER(metric) = LOWER(%s)
                  AND (unit IS NULL OR unit = '')
                  AND (unit_inferred IS NULL OR unit_inferred = FALSE)
            """,
                (metric_name,),
            )
            count = cursor.fetchone()[0]
            if count > 0:
                print(f"  [DRY RUN] '{metric_name}' → '{default_unit}': {count:,} rows")
                total_mapped += count
        else:
            cursor.execute(update_sql, (default_unit, metric_name))
            if cursor.rowcount > 0:
                print(f"  '{metric_name}' → '{default_unit}': {cursor.rowcount:,} rows")
                total_mapped += cursor.rowcount

    if not dry_run:
        conn.commit()
    results["metric_default_mapped"] = total_mapped
    print(f"  Total mapped from defaults: {total_mapped:,} rows")

    # Step 3: Same-metric reference lookup
    # Find the most common unit for each metric and apply to NULL units
    print("\nStep 3: Same-metric reference lookup...")

    reference_sql = """
        WITH metric_unit_modes AS (
            SELECT
                LOWER(metric) as metric_lower,
                MODE() WITHIN GROUP (ORDER BY unit) as common_unit,
                COUNT(*) as cnt
            FROM financial_tables
            WHERE unit IS NOT NULL
              AND unit != ''
              AND unit_inferred IS NOT TRUE
            GROUP BY LOWER(metric)
            HAVING COUNT(*) >= 3
        )
        UPDATE financial_tables ft
        SET unit = mum.common_unit,
            unit_inferred = TRUE,
            unit_inference_method = 'metric_reference',
            unit_confidence = 'medium'
        FROM metric_unit_modes mum
        WHERE LOWER(ft.metric) = mum.metric_lower
          AND (ft.unit IS NULL OR ft.unit = '')
          AND (ft.unit_inferred IS NULL OR ft.unit_inferred = FALSE)
    """

    if dry_run:
        # Count how many would be affected
        cursor.execute("""
            WITH metric_unit_modes AS (
                SELECT
                    LOWER(metric) as metric_lower,
                    MODE() WITHIN GROUP (ORDER BY unit) as common_unit,
                    COUNT(*) as cnt
                FROM financial_tables
                WHERE unit IS NOT NULL
                  AND unit != ''
                  AND unit_inferred IS NOT TRUE
                GROUP BY LOWER(metric)
                HAVING COUNT(*) >= 3
            )
            SELECT COUNT(*)
            FROM financial_tables ft
            JOIN metric_unit_modes mum ON LOWER(ft.metric) = mum.metric_lower
            WHERE (ft.unit IS NULL OR ft.unit = '')
              AND (ft.unit_inferred IS NULL OR ft.unit_inferred = FALSE)
        """)
        count = cursor.fetchone()[0]
        print(f"  [DRY RUN] Would infer from reference: {count:,} rows")
        results["metric_reference_inferred"] = count

        # Show sample mappings
        cursor.execute("""
            WITH metric_unit_modes AS (
                SELECT
                    LOWER(metric) as metric_lower,
                    MODE() WITHIN GROUP (ORDER BY unit) as common_unit,
                    COUNT(*) as cnt
                FROM financial_tables
                WHERE unit IS NOT NULL
                  AND unit != ''
                  AND unit_inferred IS NOT TRUE
                GROUP BY LOWER(metric)
                HAVING COUNT(*) >= 3
            ),
            affected AS (
                SELECT ft.metric, mum.common_unit, COUNT(*) as affected_cnt
                FROM financial_tables ft
                JOIN metric_unit_modes mum ON LOWER(ft.metric) = mum.metric_lower
                WHERE (ft.unit IS NULL OR ft.unit = '')
                  AND (ft.unit_inferred IS NULL OR ft.unit_inferred = FALSE)
                GROUP BY ft.metric, mum.common_unit
            )
            SELECT metric, common_unit, affected_cnt
            FROM affected
            ORDER BY affected_cnt DESC
            LIMIT 10
        """)
        samples = cursor.fetchall()
        if samples:
            print("  Sample mappings:")
            for metric_name, unit, cnt in samples:
                print(f"    '{metric_name}' → '{unit}': {cnt:,} rows")
    else:
        cursor.execute(reference_sql)
        results["metric_reference_inferred"] = cursor.rowcount
        conn.commit()
        print(f"  Inferred from reference: {results['metric_reference_inferred']:,} rows")

    # Step 4: Partial metric name matching
    # For metrics containing certain keywords, apply default units
    print("\nStep 4: Partial metric name matching...")

    partial_mappings = [
        ("ebitda", "M EUR"),
        ("turnover", "M EUR"),
        ("revenue", "M EUR"),
        ("capex", "M EUR"),
        ("cement", "kton"),
        ("clinker", "kton"),
        ("production", "kton"),
        ("margin", "%"),
        ("ratio", "%"),
        ("rate", "%"),
    ]

    total_partial = 0
    for keyword, default_unit in partial_mappings:
        partial_sql = """
            UPDATE financial_tables
            SET unit = %s,
                unit_inferred = TRUE,
                unit_inference_method = 'partial_match',
                unit_confidence = 'low'
            WHERE LOWER(metric) LIKE %s
              AND (unit IS NULL OR unit = '')
              AND (unit_inferred IS NULL OR unit_inferred = FALSE)
        """
        pattern = f"%{keyword}%"

        if dry_run:
            cursor.execute(
                """
                SELECT COUNT(*) FROM financial_tables
                WHERE LOWER(metric) LIKE %s
                  AND (unit IS NULL OR unit = '')
                  AND (unit_inferred IS NULL OR unit_inferred = FALSE)
            """,
                (pattern,),
            )
            count = cursor.fetchone()[0]
            if count > 0:
                print(f"  [DRY RUN] '%{keyword}%' → '{default_unit}': {count:,} rows")
                total_partial += count
        else:
            cursor.execute(partial_sql, (default_unit, pattern))
            if cursor.rowcount > 0:
                print(f"  '%{keyword}%' → '{default_unit}': {cursor.rowcount:,} rows")
                total_partial += cursor.rowcount

    if not dry_run:
        conn.commit()
    results["partial_match_inferred"] = total_partial
    print(f"  Total from partial match: {total_partial:,} rows")

    # Step 5: Document pattern inference
    # Specific patterns for 2025 performance review documents
    print("\nStep 5: Document pattern inference...")

    doc_pattern_sql = """
        UPDATE financial_tables
        SET unit = 'M EUR',
            unit_inferred = TRUE,
            unit_inference_method = 'document_pattern',
            unit_confidence = 'medium'
        WHERE (unit IS NULL OR unit = '')
          AND source_document LIKE '%2025%Performance%'
          AND LOWER(metric) ~ '(ebitda|turnover|revenue|cost|capex)'
          AND ABS(value) < 500
          AND (unit_inferred IS NULL OR unit_inferred = FALSE)
    """

    if dry_run:
        cursor.execute("""
            SELECT COUNT(*) FROM financial_tables
            WHERE (unit IS NULL OR unit = '')
              AND source_document LIKE '%2025%Performance%'
              AND LOWER(metric) ~ '(ebitda|turnover|revenue|cost|capex)'
              AND ABS(value) < 500
              AND (unit_inferred IS NULL OR unit_inferred = FALSE)
        """)
        count = cursor.fetchone()[0]
        print(f"  [DRY RUN] 2025 Performance docs → M EUR: {count:,} rows")
        results["document_pattern_inferred"] = count
    else:
        cursor.execute(doc_pattern_sql)
        results["document_pattern_inferred"] = cursor.rowcount
        conn.commit()
        print(f"  Document pattern inferred: {results['document_pattern_inferred']:,} rows")

    # Step 6: Entity-based inference
    # GROUP entity typically uses consolidated M EUR figures
    print("\nStep 6: Entity-based inference (GROUP → M EUR for financials)...")

    entity_sql = """
        UPDATE financial_tables
        SET unit = 'M EUR',
            unit_inferred = TRUE,
            unit_inference_method = 'entity_group',
            unit_confidence = 'medium'
        WHERE (unit IS NULL OR unit = '')
          AND UPPER(entity) = 'GROUP'
          AND LOWER(metric) ~ '(ebitda|turnover|revenue|income|profit|cost|capex)'
          AND ABS(value) < 500
          AND (unit_inferred IS NULL OR unit_inferred = FALSE)
    """

    if dry_run:
        cursor.execute("""
            SELECT COUNT(*) FROM financial_tables
            WHERE (unit IS NULL OR unit = '')
              AND UPPER(entity) = 'GROUP'
              AND LOWER(metric) ~ '(ebitda|turnover|revenue|income|profit|cost|capex)'
              AND ABS(value) < 500
              AND (unit_inferred IS NULL OR unit_inferred = FALSE)
        """)
        count = cursor.fetchone()[0]
        print(f"  [DRY RUN] GROUP entity → M EUR: {count:,} rows")
        results["entity_group_inferred"] = count
    else:
        cursor.execute(entity_sql)
        results["entity_group_inferred"] = cursor.rowcount
        conn.commit()
        print(f"  Entity-based inferred: {results['entity_group_inferred']:,} rows")

    # Step 7: Final summary
    print("\nStep 7: Final unit distribution summary...")
    cursor.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN unit IS NULL THEN 1 ELSE 0 END) as null_count,
            SUM(CASE WHEN unit = '' THEN 1 ELSE 0 END) as empty_count,
            SUM(CASE WHEN unit_inferred = TRUE THEN 1 ELSE 0 END) as inferred_count,
            COUNT(DISTINCT unit) as unique_units
        FROM financial_tables
    """)
    row = cursor.fetchone()
    total, null_cnt, empty_cnt, inferred_cnt, unique_units = row
    print(f"  Total rows: {total:,}")
    print(f"  NULL units: {null_cnt:,} ({100.0 * null_cnt / total:.1f}%)")
    print(f"  Empty units: {empty_cnt:,} ({100.0 * empty_cnt / total:.1f}%)")
    print(f"  Inferred units: {inferred_cnt:,} ({100.0 * inferred_cnt / total:.1f}%)")
    print(f"  Unique units: {unique_units}")

    # Show top units
    print("\n  Top 20 units after all inference:")
    cursor.execute("""
        SELECT unit, COUNT(*) as cnt,
               SUM(CASE WHEN unit_inferred = TRUE THEN 1 ELSE 0 END) as inferred
        FROM financial_tables
        WHERE unit IS NOT NULL AND unit != ''
        GROUP BY unit
        ORDER BY cnt DESC
        LIMIT 20
    """)
    top_units = cursor.fetchall()
    print(f"  {'Unit':<20} {'Total':>10} {'Inferred':>10}")
    print("  " + "-" * 42)
    for unit_val, cnt, inferred in top_units:
        print(f"  {unit_val:<20} {cnt:>10,} {inferred:>10,}")

    # Show remaining NULL metrics
    print("\n  Remaining NULL unit metrics (top 15):")
    cursor.execute("""
        SELECT metric, COUNT(*) as cnt
        FROM financial_tables
        WHERE unit IS NULL
        GROUP BY metric
        ORDER BY cnt DESC
        LIMIT 15
    """)
    remaining = cursor.fetchall()
    for metric_name, cnt in remaining:
        print(f"    {metric_name}: {cnt:,}")

    cursor.close()

    return results


def main() -> int:
    """Main entry point."""
    args = parse_args()

    try:
        results = infer_units_by_context(dry_run=args.dry_run)

        if "error" in results:
            return 1

        print("\n" + "=" * 70)
        print("RESULTS SUMMARY")
        print("=" * 70)
        for key, value in results.items():
            print(f"  {key}: {value:,}")

        total_inferred = sum(v for k, v in results.items() if "inferred" in k or "mapped" in k)
        print(f"\n  Total units inferred in Phase C: {total_inferred:,}")

        if args.dry_run:
            print("\n[DRY RUN] No changes were made to the database.")
            print("Run without --dry-run to apply changes.")

        print("\n✓ Phase C complete. Context-based inference applied.")
        print("  Next step: Run scripts/verify_unit_quality.py to validate results")

        return 0

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
