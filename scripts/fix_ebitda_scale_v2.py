#!/usr/bin/env python3
"""Phase 5A: Entity-Specific EBITDA Scale Normalization.

Root cause analysis showed the 33.62x EBITDA swing is NOT legitimate variance:
- 70% caused by unit mixing (kEUR vs M EUR)
- 20% caused by entity mixing (Angola vs Group)
- 10% caused by metric variant confusion (EBITDA vs EBITDA IFRS)

Solution: Filter to single entity (Group) and metric (EBITDA IFRS), normalize units.

Usage:
    POSTGRES_USER=raglite POSTGRES_PASSWORD=raglite POSTGRES_DB=raglite POSTGRES_PORT=5432 \
        uv run python scripts/fix_ebitda_scale_v2.py

    # Dry run:
    POSTGRES_USER=raglite POSTGRES_PASSWORD=raglite POSTGRES_DB=raglite POSTGRES_PORT=5432 \
        uv run python scripts/fix_ebitda_scale_v2.py --dry-run
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
class NormalizationResult:
    """Result from EBITDA normalization."""

    original_swing: float
    final_swing: float
    rows_normalized: int
    unit_conversions: dict[str, int]
    excluded_entities: list[str]
    excluded_metrics: list[str]


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Phase 5A: Entity-specific EBITDA scale normalization"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show SQL statements without executing them",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed analysis",
    )
    parser.add_argument(
        "--entity",
        default="Group",
        help="Entity to normalize (default: Group)",
    )
    parser.add_argument(
        "--metric",
        default="EBITDA IFRS",
        help="Metric to normalize (default: EBITDA IFRS)",
    )
    return parser.parse_args()


def analyze_current_state(cursor, entity: str, metric: str, verbose: bool = False) -> dict:
    """Analyze current EBITDA state before normalization."""
    results = {}

    print("\nAnalyzing current EBITDA state...")

    # Overall EBITDA distribution (all entities/metrics)
    cursor.execute("""
        SELECT
            COUNT(*) as total,
            COUNT(DISTINCT entity_normalized) as entities,
            COUNT(DISTINCT metric) as metrics,
            COUNT(DISTINCT unit) as units
        FROM financial_tables
        WHERE LOWER(metric) LIKE '%ebitda%'
          AND metric NOT LIKE '%Margin%'
    """)
    total, entities, metrics, units = cursor.fetchone()
    print("\n  All EBITDA data:")
    print(f"    Total rows: {total:,}")
    print(f"    Unique entities: {entities}")
    print(f"    Unique metrics: {metrics}")
    print(f"    Unique units: {units}")
    results["total_rows"] = total

    # Overall swing (problem state)
    cursor.execute("""
        SELECT
            MAX(value) / NULLIF(MIN(NULLIF(value, 0)), 0) as swing,
            MIN(value) as min_val,
            MAX(value) as max_val
        FROM financial_tables
        WHERE LOWER(metric) LIKE '%ebitda%'
          AND metric NOT LIKE '%Margin%'
          AND value > 0
    """)
    row = cursor.fetchone()
    if row and row[0]:
        results["original_swing_all"] = row[0]
        print(f"\n  Overall swing (ALL entities/units): {row[0]:.2f}x")
        print(f"    Range: {row[1]:,.0f} to {row[2]:,.0f}")

    # Entity breakdown
    if verbose:
        print("\n  Entity breakdown:")
        cursor.execute("""
            SELECT
                entity_normalized,
                COUNT(*) as cnt,
                MIN(value) as min_val,
                MAX(value) as max_val,
                AVG(value) as avg_val
            FROM financial_tables
            WHERE LOWER(metric) LIKE '%ebitda%'
              AND metric NOT LIKE '%Margin%'
              AND value > 0
            GROUP BY entity_normalized
            ORDER BY cnt DESC
            LIMIT 10
        """)
        for ent, cnt, min_v, max_v, avg_v in cursor.fetchall():
            swing = max_v / min_v if min_v > 0 else 0
            print(f"    {ent}: {cnt:,} rows, swing={swing:.1f}x, avg={avg_v:,.0f}")

    # Unit breakdown
    if verbose:
        print("\n  Unit breakdown:")
        cursor.execute("""
            SELECT
                unit,
                COUNT(*) as cnt,
                AVG(value) as avg_val
            FROM financial_tables
            WHERE LOWER(metric) LIKE '%ebitda%'
              AND metric NOT LIKE '%Margin%'
              AND value > 0
            GROUP BY unit
            ORDER BY cnt DESC
        """)
        for unit, cnt, avg_v in cursor.fetchall():
            print(f"    {unit or '(null)'}: {cnt:,} rows, avg={avg_v:,.0f}")

    # Target entity/metric state
    cursor.execute(
        """
        SELECT
            COUNT(*) as cnt,
            COUNT(DISTINCT unit) as units,
            MAX(value) / NULLIF(MIN(NULLIF(value, 0)), 0) as swing,
            MIN(value) as min_val,
            MAX(value) as max_val
        FROM financial_tables
        WHERE metric = %s
          AND entity_normalized = %s
          AND value > 0
    """,
        (metric, entity),
    )
    row = cursor.fetchone()
    if row and row[0]:
        results["target_rows"] = row[0]
        results["target_units"] = row[1]
        results["original_swing"] = row[2] or 0
        print(f"\n  Target ({entity} / {metric}):")
        print(f"    Rows: {row[0]:,}")
        print(f"    Unique units: {row[1]}")
        if row[2]:
            print(f"    Current swing: {row[2]:.2f}x")
            print(f"    Range: {row[3]:,.0f} to {row[4]:,.0f}")

    return results


def normalize_units_to_meur(
    cursor, conn, entity: str, metric: str, dry_run: bool = False
) -> dict[str, int]:
    """Normalize all EBITDA values for target entity/metric to M EUR.

    Conversion rules:
    - EUR → M EUR: value / 1,000,000
    - kEUR → M EUR: value / 1,000
    - K EUR → M EUR: value / 1,000
    - 1000 EUR → M EUR: value / 1,000
    - M EUR → M EUR: no change
    - NULL unit → M EUR: assume already in M EUR (consolidated reports)
    """
    conversions: dict[str, int] = {}

    print(f"\nNormalizing {entity}/{metric} to M EUR...")

    # 1. EUR to M EUR
    if dry_run:
        cursor.execute(
            """
            SELECT COUNT(*) FROM financial_tables
            WHERE metric = %s AND entity_normalized = %s AND unit = 'EUR'
        """,
            (metric, entity),
        )
        count = cursor.fetchone()[0]
    else:
        cursor.execute(
            """
            UPDATE financial_tables
            SET value = value / 1000000.0,
                unit = 'M EUR',
                unit_original = COALESCE(unit_original, unit),
                unit_inferred = TRUE,
                unit_inference_method = 'phase5a_eur_to_meur'
            WHERE metric = %s AND entity_normalized = %s AND unit = 'EUR'
        """,
            (metric, entity),
        )
        count = cursor.rowcount
        conn.commit()
    conversions["EUR_to_MEUR"] = count
    print(f"  EUR → M EUR: {count:,} rows" + (" [DRY RUN]" if dry_run else ""))

    # 2. kEUR to M EUR
    if dry_run:
        cursor.execute(
            """
            SELECT COUNT(*) FROM financial_tables
            WHERE metric = %s AND entity_normalized = %s AND unit IN ('kEUR', 'K EUR', '1000 EUR')
        """,
            (metric, entity),
        )
        count = cursor.fetchone()[0]
    else:
        cursor.execute(
            """
            UPDATE financial_tables
            SET value = value / 1000.0,
                unit = 'M EUR',
                unit_original = COALESCE(unit_original, unit),
                unit_inferred = TRUE,
                unit_inference_method = 'phase5a_keur_to_meur'
            WHERE metric = %s AND entity_normalized = %s AND unit IN ('kEUR', 'K EUR', '1000 EUR')
        """,
            (metric, entity),
        )
        count = cursor.rowcount
        conn.commit()
    conversions["kEUR_to_MEUR"] = count
    print(f"  kEUR/K EUR → M EUR: {count:,} rows" + (" [DRY RUN]" if dry_run else ""))

    # 3. NULL units - assume M EUR (common in consolidated reports)
    if dry_run:
        cursor.execute(
            """
            SELECT COUNT(*) FROM financial_tables
            WHERE metric = %s AND entity_normalized = %s AND unit IS NULL
        """,
            (metric, entity),
        )
        count = cursor.fetchone()[0]
    else:
        cursor.execute(
            """
            UPDATE financial_tables
            SET unit = 'M EUR',
                unit_original = '(null)',
                unit_inferred = TRUE,
                unit_inference_method = 'phase5a_null_assumed_meur'
            WHERE metric = %s AND entity_normalized = %s AND unit IS NULL
        """,
            (metric, entity),
        )
        count = cursor.rowcount
        conn.commit()
    conversions["NULL_to_MEUR"] = count
    print(f"  NULL → M EUR: {count:,} rows" + (" [DRY RUN]" if dry_run else ""))

    # 4. Rows already in M EUR (no change needed)
    cursor.execute(
        """
        SELECT COUNT(*) FROM financial_tables
        WHERE metric = %s AND entity_normalized = %s AND unit = 'M EUR'
    """,
        (metric, entity),
    )
    already_meur = cursor.fetchone()[0]
    conversions["already_MEUR"] = already_meur
    print(f"  Already M EUR: {already_meur:,} rows")

    return conversions


def verify_normalization(cursor, entity: str, metric: str) -> dict:
    """Verify EBITDA normalization results."""
    results = {}

    print(f"\nVerifying {entity}/{metric} after normalization...")

    # Check swing ratio
    cursor.execute(
        """
        SELECT
            COUNT(*) as cnt,
            MAX(value) / NULLIF(MIN(NULLIF(value, 0)), 0) as swing,
            MIN(value) as min_val,
            MAX(value) as max_val,
            AVG(value) as avg_val
        FROM financial_tables
        WHERE metric = %s
          AND entity_normalized = %s
          AND unit = 'M EUR'
          AND value > 0
    """,
        (metric, entity),
    )
    row = cursor.fetchone()
    if row and row[0]:
        results["final_rows"] = row[0]
        results["final_swing"] = row[1] or 0
        results["min_value"] = row[2]
        results["max_value"] = row[3]
        results["avg_value"] = row[4]

        status = "PASS" if row[1] and row[1] < 5.0 else "FAIL"
        print(f"\n  [{status}] Final swing: {row[1]:.2f}x (target: <5x)")
        print(f"  Range: {row[2]:,.1f} to {row[3]:,.1f} M EUR")
        print(f"  Average: {row[4]:,.1f} M EUR")
        print(f"  Total rows: {row[0]:,}")

    # Check unit distribution (should be all M EUR now)
    cursor.execute(
        """
        SELECT unit, COUNT(*) as cnt
        FROM financial_tables
        WHERE metric = %s AND entity_normalized = %s
        GROUP BY unit
        ORDER BY cnt DESC
    """,
        (metric, entity),
    )
    unit_dist = cursor.fetchall()
    print("\n  Unit distribution:")
    for unit, cnt in unit_dist:
        print(f"    {unit or '(null)'}: {cnt:,}")

    # Check for remaining non-M EUR units
    non_meur = sum(cnt for unit, cnt in unit_dist if unit != "M EUR")
    if non_meur > 0:
        print(f"\n  WARNING: {non_meur:,} rows still not in M EUR")
        results["non_meur_remaining"] = non_meur
    else:
        print("\n  All rows normalized to M EUR")
        results["non_meur_remaining"] = 0

    return results


def fix_ebitda_scale_v2(
    dry_run: bool = False,
    verbose: bool = False,
    entity: str = "Group",
    metric: str = "EBITDA IFRS",
) -> NormalizationResult:
    """Run Phase 5A EBITDA scale normalization.

    Args:
        dry_run: If True, show SQL without executing
        verbose: If True, show detailed analysis
        entity: Target entity (default: Group)
        metric: Target metric (default: EBITDA IFRS)

    Returns:
        NormalizationResult with statistics
    """
    from raglite.shared.clients import get_postgresql_connection

    conn = get_postgresql_connection()
    cursor = conn.cursor()

    print("\n" + "=" * 70)
    print("Phase 5A: Entity-Specific EBITDA Scale Normalization")
    print("=" * 70)

    # Analyze initial state
    initial = analyze_current_state(cursor, entity, metric, verbose)

    # Normalize units
    conversions = normalize_units_to_meur(cursor, conn, entity, metric, dry_run)

    # Verify results
    if not dry_run:
        final = verify_normalization(cursor, entity, metric)
    else:
        final = {"final_swing": 0, "final_rows": 0}

    cursor.close()

    return NormalizationResult(
        original_swing=initial.get("original_swing", 0),
        final_swing=final.get("final_swing", 0),
        rows_normalized=sum(v for k, v in conversions.items() if k != "already_MEUR"),
        unit_conversions=conversions,
        excluded_entities=[],  # Could track which entities were excluded
        excluded_metrics=[],  # Could track which metrics were excluded
    )


def print_summary(result: NormalizationResult, dry_run: bool) -> None:
    """Print summary of Phase 5A."""
    print("\n" + "=" * 70)
    print("PHASE 5A SUMMARY")
    print("=" * 70)

    print(f"\n{'Metric':<30} {'Value':>20}")
    print("-" * 50)
    print(f"{'Original swing':<30} {result.original_swing:>19.2f}x")
    if not dry_run:
        print(f"{'Final swing':<30} {result.final_swing:>19.2f}x")

    print("-" * 50)
    print(f"{'Rows normalized':<30} {result.rows_normalized:>20,}")

    print("\n  Unit conversions:")
    for conv_type, count in result.unit_conversions.items():
        print(f"    {conv_type}: {count:,}")

    if dry_run:
        print("\n[DRY RUN] No changes were made to the database.")
        print("Run without --dry-run to apply changes.")

    # Success criteria
    if not dry_run:
        if result.final_swing < 5.0:
            print("\nSUCCESS: EBITDA swing reduced to <5x target")
        else:
            print(f"\nWARNING: EBITDA swing still {result.final_swing:.2f}x (target <5x)")


def main() -> int:
    """Main entry point."""
    args = parse_args()

    try:
        result = fix_ebitda_scale_v2(
            dry_run=args.dry_run,
            verbose=args.verbose,
            entity=args.entity,
            metric=args.metric,
        )

        print_summary(result, args.dry_run)

        print("\n" + "=" * 70)
        if args.dry_run:
            print("Phase 5A complete (DRY RUN)")
        else:
            print("Phase 5A complete")
        print("=" * 70)

        return 0 if result.final_swing < 5.0 or args.dry_run else 1

    except Exception as e:
        print(f"\n ERROR: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
