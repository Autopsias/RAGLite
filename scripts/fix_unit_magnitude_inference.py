#!/usr/bin/env python3
"""Phase B: Magnitude-based unit inference.

Infers units from value magnitude for rows with NULL or ambiguous units.
Uses metric type + value magnitude to determine the most likely unit.

Prerequisites:
    - Run fix_unit_audit_columns.py first (Phase D)
    - Run fix_unit_standardization.py first (Phase A)

Usage:
    POSTGRES_USER=raglite POSTGRES_PASSWORD=raglite POSTGRES_DB=raglite POSTGRES_PORT=5432 \
        uv run python scripts/fix_unit_magnitude_inference.py

    # Dry run (show SQL without executing):
    POSTGRES_USER=raglite POSTGRES_PASSWORD=raglite POSTGRES_DB=raglite POSTGRES_PORT=5432 \
        uv run python scripts/fix_unit_magnitude_inference.py --dry-run
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

# Suppress verbose logging unless DEBUG is set
if not os.getenv("DEBUG"):
    logging.getLogger("raglite").setLevel(logging.WARNING)


# Financial metric keywords (for M EUR vs kEUR inference)
FINANCIAL_KEYWORDS = [
    "ebitda",
    "turnover",
    "revenue",
    "income",
    "profit",
    "cost",
    "expense",
    "capex",
    "opex",
    "cash",
    "debt",
    "asset",
    "liability",
    "equity",
    "margin",
    "sales",
    "interest",
    "tax",
    "depreciation",
    "amortization",
    "investment",
    "dividend",
    "budget",
    "forecast",
    "actual",
]

# Production metric keywords (for kton vs Mton inference)
PRODUCTION_KEYWORDS = [
    "volume",
    "production",
    "capacity",
    "clinker",
    "cement",
    "aggregate",
    "concrete",
    "ready-mix",
    "readymix",
    "output",
    "sales volume",
    "dispatch",
    "shipment",
]

# Energy metric keywords
ENERGY_KEYWORDS = [
    "electrical",
    "electric",
    "thermal",
    "energy",
    "power",
    "consumption",
    "kwh",
    "mwh",
    "gwh",
    "gj",
    "heat",
    "fuel",
]


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Infer units from value magnitude for NULL/EUR units"
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


def build_financial_pattern() -> str:
    """Build SQL pattern for financial metrics."""
    patterns = "|".join(FINANCIAL_KEYWORDS)
    return f"({patterns})"


def build_production_pattern() -> str:
    """Build SQL pattern for production metrics."""
    patterns = "|".join(PRODUCTION_KEYWORDS)
    return f"({patterns})"


def build_energy_pattern() -> str:
    """Build SQL pattern for energy metrics."""
    patterns = "|".join(ENERGY_KEYWORDS)
    return f"({patterns})"


def infer_units_by_magnitude(dry_run: bool = False) -> dict[str, int]:
    """Infer units based on value magnitude and metric type.

    Inference rules:
    1. Financial metrics (EBITDA, revenue, etc.):
       - |value| < 500 → M EUR (consolidated millions)
       - 500 ≤ |value| < 100,000 → kEUR (thousands)
       - |value| ≥ 100,000 → kEUR (large thousands, likely mislabeled)

    2. Production metrics (volume, cement, etc.):
       - |value| < 100 → Mton (millions of tons)
       - 100 ≤ |value| < 10,000 → kton (thousands of tons)
       - |value| ≥ 10,000 → ton (raw tons)

    3. Energy metrics (electrical, thermal, etc.):
       - Based on magnitude ranges

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
    print("Phase B: Magnitude-Based Unit Inference")
    print("=" * 70)

    # Check prerequisites
    if not check_prerequisites(cursor):
        print("\n✗ ERROR: Audit columns not found!")
        print("  Run fix_unit_audit_columns.py first to preserve original units.")
        return {"error": 1}

    # Step 1: Analyze current state of NULL/EUR units
    print("\nStep 1: Analyzing rows eligible for magnitude inference...")
    cursor.execute("""
        SELECT
            CASE
                WHEN unit IS NULL THEN 'NULL'
                WHEN unit = '' THEN 'EMPTY'
                WHEN unit = 'EUR' THEN 'EUR'
                ELSE 'OTHER'
            END as unit_status,
            COUNT(*) as cnt
        FROM financial_tables
        WHERE (unit IS NULL OR unit = '' OR unit = 'EUR')
          AND value IS NOT NULL
          AND (unit_inferred IS NULL OR unit_inferred = FALSE)
        GROUP BY 1
        ORDER BY cnt DESC
    """)
    status_counts = cursor.fetchall()
    print("  Eligible rows by unit status:")
    for status, cnt in status_counts:
        print(f"    {status}: {cnt:,}")

    # Step 2: Infer M EUR for financial metrics with small magnitudes
    # These are consolidated figures in millions
    print("\nStep 2: Inferring M EUR for financial metrics (magnitude < 500)...")

    financial_pattern = build_financial_pattern()
    m_eur_sql = f"""
        UPDATE financial_tables
        SET unit = 'M EUR',
            unit_inferred = TRUE,
            unit_inference_method = 'magnitude_financial_millions',
            unit_confidence = 'medium'
        WHERE (unit IS NULL OR unit = '' OR unit = 'EUR')
          AND value IS NOT NULL
          AND ABS(value) > 0.1
          AND ABS(value) < 500
          AND LOWER(metric) ~ '{financial_pattern}'
          AND (unit_inferred IS NULL OR unit_inferred = FALSE)
    """

    if dry_run:
        cursor.execute(f"""
            SELECT COUNT(*), MIN(ABS(value)), MAX(ABS(value)), AVG(ABS(value))
            FROM financial_tables
            WHERE (unit IS NULL OR unit = '' OR unit = 'EUR')
              AND value IS NOT NULL
              AND ABS(value) > 0.1
              AND ABS(value) < 500
              AND LOWER(metric) ~ '{financial_pattern}'
              AND (unit_inferred IS NULL OR unit_inferred = FALSE)
        """)
        row = cursor.fetchone()
        print(f"  [DRY RUN] Would infer M EUR for {row[0]:,} rows")
        print(f"    Value range: {row[1]:.2f} to {row[2]:.2f} (avg: {row[3]:.2f})")
        results["m_eur_inferred"] = row[0]
    else:
        cursor.execute(m_eur_sql)
        results["m_eur_inferred"] = cursor.rowcount
        conn.commit()
        print(f"  Inferred M EUR: {results['m_eur_inferred']:,} rows")

    # Step 3: Infer kEUR for financial metrics with medium magnitudes
    print("\nStep 3: Inferring kEUR for financial metrics (500 ≤ magnitude < 100,000)...")

    k_eur_sql = f"""
        UPDATE financial_tables
        SET unit = 'kEUR',
            unit_inferred = TRUE,
            unit_inference_method = 'magnitude_financial_thousands',
            unit_confidence = 'medium'
        WHERE (unit IS NULL OR unit = '' OR unit = 'EUR')
          AND value IS NOT NULL
          AND ABS(value) >= 500
          AND ABS(value) < 100000
          AND LOWER(metric) ~ '{financial_pattern}'
          AND (unit_inferred IS NULL OR unit_inferred = FALSE)
    """

    if dry_run:
        cursor.execute(f"""
            SELECT COUNT(*), MIN(ABS(value)), MAX(ABS(value)), AVG(ABS(value))
            FROM financial_tables
            WHERE (unit IS NULL OR unit = '' OR unit = 'EUR')
              AND value IS NOT NULL
              AND ABS(value) >= 500
              AND ABS(value) < 100000
              AND LOWER(metric) ~ '{financial_pattern}'
              AND (unit_inferred IS NULL OR unit_inferred = FALSE)
        """)
        row = cursor.fetchone()
        print(f"  [DRY RUN] Would infer kEUR for {row[0]:,} rows")
        if row[1]:
            print(f"    Value range: {row[1]:.2f} to {row[2]:.2f} (avg: {row[3]:.2f})")
        results["k_eur_mid_inferred"] = row[0]
    else:
        cursor.execute(k_eur_sql)
        results["k_eur_mid_inferred"] = cursor.rowcount
        conn.commit()
        print(f"  Inferred kEUR: {results['k_eur_mid_inferred']:,} rows")

    # Step 4: Infer kEUR for financial metrics with large magnitudes (likely mislabeled as EUR)
    print("\nStep 4: Inferring kEUR for large magnitudes (≥ 100,000, likely mislabeled)...")

    k_eur_large_sql = f"""
        UPDATE financial_tables
        SET unit = 'kEUR',
            unit_inferred = TRUE,
            unit_inference_method = 'magnitude_financial_mislabeled',
            unit_confidence = 'low'
        WHERE (unit IS NULL OR unit = '' OR unit = 'EUR')
          AND value IS NOT NULL
          AND ABS(value) >= 100000
          AND ABS(value) < 10000000
          AND LOWER(metric) ~ '{financial_pattern}'
          AND (unit_inferred IS NULL OR unit_inferred = FALSE)
    """

    if dry_run:
        cursor.execute(f"""
            SELECT COUNT(*), MIN(ABS(value)), MAX(ABS(value)), AVG(ABS(value))
            FROM financial_tables
            WHERE (unit IS NULL OR unit = '' OR unit = 'EUR')
              AND value IS NOT NULL
              AND ABS(value) >= 100000
              AND ABS(value) < 10000000
              AND LOWER(metric) ~ '{financial_pattern}'
              AND (unit_inferred IS NULL OR unit_inferred = FALSE)
        """)
        row = cursor.fetchone()
        print(f"  [DRY RUN] Would infer kEUR for {row[0]:,} rows")
        if row[1]:
            print(f"    Value range: {row[1]:.2f} to {row[2]:.2f} (avg: {row[3]:.2f})")
        results["k_eur_large_inferred"] = row[0]
    else:
        cursor.execute(k_eur_large_sql)
        results["k_eur_large_inferred"] = cursor.rowcount
        conn.commit()
        print(f"  Inferred kEUR: {results['k_eur_large_inferred']:,} rows")

    # Step 5: Infer production units (kton, Mton)
    print("\nStep 5: Inferring production units (kton, Mton)...")

    production_pattern = build_production_pattern()

    # kton for medium volumes (100-10000)
    kton_sql = f"""
        UPDATE financial_tables
        SET unit = 'kton',
            unit_inferred = TRUE,
            unit_inference_method = 'magnitude_production_kton',
            unit_confidence = 'medium'
        WHERE (unit IS NULL OR unit = '' OR unit = 'ton')
          AND value IS NOT NULL
          AND ABS(value) >= 100
          AND ABS(value) < 10000
          AND LOWER(metric) ~ '{production_pattern}'
          AND (unit_inferred IS NULL OR unit_inferred = FALSE)
    """

    if dry_run:
        cursor.execute(f"""
            SELECT COUNT(*) FROM financial_tables
            WHERE (unit IS NULL OR unit = '' OR unit = 'ton')
              AND value IS NOT NULL
              AND ABS(value) >= 100
              AND ABS(value) < 10000
              AND LOWER(metric) ~ '{production_pattern}'
              AND (unit_inferred IS NULL OR unit_inferred = FALSE)
        """)
        row = cursor.fetchone()
        print(f"  [DRY RUN] Would infer kton for {row[0]:,} rows")
        results["kton_inferred"] = row[0]
    else:
        cursor.execute(kton_sql)
        results["kton_inferred"] = cursor.rowcount
        conn.commit()
        print(f"  Inferred kton: {results['kton_inferred']:,} rows")

    # Mton for small volumes (< 100) - consolidated production in millions of tons
    mton_sql = f"""
        UPDATE financial_tables
        SET unit = 'Mton',
            unit_inferred = TRUE,
            unit_inference_method = 'magnitude_production_mton',
            unit_confidence = 'medium'
        WHERE (unit IS NULL OR unit = '')
          AND value IS NOT NULL
          AND ABS(value) > 0.1
          AND ABS(value) < 100
          AND LOWER(metric) ~ '{production_pattern}'
          AND (unit_inferred IS NULL OR unit_inferred = FALSE)
    """

    if dry_run:
        cursor.execute(f"""
            SELECT COUNT(*) FROM financial_tables
            WHERE (unit IS NULL OR unit = '')
              AND value IS NOT NULL
              AND ABS(value) > 0.1
              AND ABS(value) < 100
              AND LOWER(metric) ~ '{production_pattern}'
              AND (unit_inferred IS NULL OR unit_inferred = FALSE)
        """)
        row = cursor.fetchone()
        print(f"  [DRY RUN] Would infer Mton for {row[0]:,} rows")
        results["mton_inferred"] = row[0]
    else:
        cursor.execute(mton_sql)
        results["mton_inferred"] = cursor.rowcount
        conn.commit()
        print(f"  Inferred Mton: {results['mton_inferred']:,} rows")

    # Step 6: Infer energy units
    print("\nStep 6: Inferring energy units (GWh, GJ)...")

    energy_pattern = build_energy_pattern()

    # GWh for electrical energy
    gwh_sql = """
        UPDATE financial_tables
        SET unit = 'GWh',
            unit_inferred = TRUE,
            unit_inference_method = 'magnitude_energy_gwh',
            unit_confidence = 'medium'
        WHERE (unit IS NULL OR unit = '')
          AND value IS NOT NULL
          AND ABS(value) > 0
          AND ABS(value) < 10000
          AND LOWER(metric) ~ '(electrical|electric|power|kwh|mwh|gwh)'
          AND (unit_inferred IS NULL OR unit_inferred = FALSE)
    """

    if dry_run:
        cursor.execute("""
            SELECT COUNT(*) FROM financial_tables
            WHERE (unit IS NULL OR unit = '')
              AND value IS NOT NULL
              AND ABS(value) > 0
              AND ABS(value) < 10000
              AND LOWER(metric) ~ '(electrical|electric|power|kwh|mwh|gwh)'
              AND (unit_inferred IS NULL OR unit_inferred = FALSE)
        """)
        row = cursor.fetchone()
        print(f"  [DRY RUN] Would infer GWh for {row[0]:,} rows")
        results["gwh_inferred"] = row[0]
    else:
        cursor.execute(gwh_sql)
        results["gwh_inferred"] = cursor.rowcount
        conn.commit()
        print(f"  Inferred GWh: {results['gwh_inferred']:,} rows")

    # GJ for thermal energy
    gj_sql = """
        UPDATE financial_tables
        SET unit = 'GJ',
            unit_inferred = TRUE,
            unit_inference_method = 'magnitude_energy_gj',
            unit_confidence = 'medium'
        WHERE (unit IS NULL OR unit = '')
          AND value IS NOT NULL
          AND ABS(value) > 0
          AND LOWER(metric) ~ '(thermal|heat|fuel|gj)'
          AND (unit_inferred IS NULL OR unit_inferred = FALSE)
    """

    if dry_run:
        cursor.execute("""
            SELECT COUNT(*) FROM financial_tables
            WHERE (unit IS NULL OR unit = '')
              AND value IS NOT NULL
              AND ABS(value) > 0
              AND LOWER(metric) ~ '(thermal|heat|fuel|gj)'
              AND (unit_inferred IS NULL OR unit_inferred = FALSE)
        """)
        row = cursor.fetchone()
        print(f"  [DRY RUN] Would infer GJ for {row[0]:,} rows")
        results["gj_inferred"] = row[0]
    else:
        cursor.execute(gj_sql)
        results["gj_inferred"] = cursor.rowcount
        conn.commit()
        print(f"  Inferred GJ: {results['gj_inferred']:,} rows")

    # Step 7: Show remaining NULL units summary
    print("\nStep 7: Remaining NULL/empty units after inference...")
    cursor.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN unit IS NULL THEN 1 ELSE 0 END) as null_count,
            SUM(CASE WHEN unit = '' THEN 1 ELSE 0 END) as empty_count,
            SUM(CASE WHEN unit_inferred = TRUE THEN 1 ELSE 0 END) as inferred_count
        FROM financial_tables
    """)
    row = cursor.fetchone()
    total, null_cnt, empty_cnt, inferred_cnt = row
    print(f"  Total rows: {total:,}")
    print(f"  NULL units: {null_cnt:,} ({100.0 * null_cnt / total:.1f}%)")
    print(f"  Empty units: {empty_cnt:,} ({100.0 * empty_cnt / total:.1f}%)")
    print(f"  Inferred units: {inferred_cnt:,} ({100.0 * inferred_cnt / total:.1f}%)")

    # Show top remaining NULL unit metrics
    print("\n  Top 20 metrics with NULL units remaining:")
    cursor.execute("""
        SELECT metric, COUNT(*) as cnt
        FROM financial_tables
        WHERE unit IS NULL AND (unit_inferred IS NULL OR unit_inferred = FALSE)
        GROUP BY metric
        ORDER BY cnt DESC
        LIMIT 20
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
        results = infer_units_by_magnitude(dry_run=args.dry_run)

        if "error" in results:
            return 1

        print("\n" + "=" * 70)
        print("RESULTS SUMMARY")
        print("=" * 70)
        for key, value in results.items():
            print(f"  {key}: {value:,}")

        total_inferred = sum(v for k, v in results.items() if "inferred" in k)
        print(f"\n  Total units inferred: {total_inferred:,}")

        if args.dry_run:
            print("\n[DRY RUN] No changes were made to the database.")
            print("Run without --dry-run to apply changes.")

        print("\n✓ Phase B complete. Magnitude-based inference applied.")
        print("  Next step: Run scripts/fix_unit_context_inference.py (Phase C)")

        return 0

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
