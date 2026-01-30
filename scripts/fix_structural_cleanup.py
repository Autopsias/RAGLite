#!/usr/bin/env python3
"""Phase 4A: Structural Cleanup.

Removes structurally corrupted data that blocks all analysis:
1. Empty metric rows (headers/section dividers captured as data)
2. Entity contamination in metrics
3. Future year data errors (2030, 2045)
4. Reclassify entity-named metrics

Prerequisites:
    - Run Phase 3 scripts first (unit remediation)

Usage:
    POSTGRES_USER=raglite POSTGRES_PASSWORD=raglite POSTGRES_DB=raglite POSTGRES_PORT=5432 \
        uv run python scripts/fix_structural_cleanup.py

    # Dry run (show SQL without executing):
    POSTGRES_USER=raglite POSTGRES_PASSWORD=raglite POSTGRES_DB=raglite POSTGRES_PORT=5432 \
        uv run python scripts/fix_structural_cleanup.py --dry-run
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import datetime

# Suppress verbose logging unless DEBUG is set
if not os.getenv("DEBUG"):
    logging.getLogger("raglite").setLevel(logging.WARNING)


# Entity names that appear as metrics (should be facilities/locations, not metrics)
ENTITY_NAMED_METRICS = [
    "Pataias",
    "Outão",
    "Maceira",
    "Pomerode",
    "Adrianópolis",
    "Secil Group Structure",
    "Secil HEADCOUNT EVOLUTION",
    "Secil Tunisia Headcount",
    "Lost Time Injury (2)",
    # Additional facility/location names that may appear as metrics
    "Cibra",
    "Supremo",
    "Gabès",
    "Sibline",
    "Pikaso",
]

# Metrics that are actually entity names stored in wrong field
ENTITY_CONTAMINATION_PATTERNS = [
    "CF from Operations",
    "De(in)crease Trade Working Capital",
    "CF from Operating Activities",
    "Net interest expenses",
    "Income tax paid",
    "CF from Investing Activities",
    "Interest paid",
    "Cash flow from financing",
    "Dividend paid",
    "Net increase in cash",
]

# Invalid future years (data corruption)
INVALID_FUTURE_YEARS = [2030, 2045]


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Phase 4A: Structural cleanup of corrupted data")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show SQL statements without executing them",
    )
    parser.add_argument(
        "--skip-backup",
        action="store_true",
        help="Skip creating backup tables (use with caution)",
    )
    return parser.parse_args()


def create_backup_tables(cursor, conn, dry_run: bool = False) -> dict[str, int]:
    """Create backup tables for data that will be deleted.

    Returns:
        Dict with backup table names and row counts
    """
    results: dict[str, int] = {}
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    print("\nStep 1: Creating backup tables...")

    # Backup 1: Empty metric rows
    backup_name = f"backup_empty_metrics_{timestamp}"
    if dry_run:
        cursor.execute("""
            SELECT COUNT(*) FROM financial_tables
            WHERE metric IS NULL OR metric = ''
        """)
        count = cursor.fetchone()[0]
        print(f"  [DRY RUN] Would backup {count:,} empty metric rows to {backup_name}")
        results["empty_metrics"] = count
    else:
        cursor.execute(f"""
            CREATE TABLE {backup_name} AS
            SELECT * FROM financial_tables
            WHERE metric IS NULL OR metric = ''
        """)
        cursor.execute(f"SELECT COUNT(*) FROM {backup_name}")
        count = cursor.fetchone()[0]
        conn.commit()
        print(f"  Created {backup_name}: {count:,} rows")
        results["empty_metrics"] = count

    # Backup 2: Entity contamination rows
    backup_name = f"backup_entity_contamination_{timestamp}"
    entity_list = ", ".join(f"'{e}'" for e in ENTITY_CONTAMINATION_PATTERNS)

    if dry_run:
        cursor.execute(f"""
            SELECT COUNT(*) FROM financial_tables
            WHERE entity_normalized IN ({entity_list})
        """)
        count = cursor.fetchone()[0]
        print(f"  [DRY RUN] Would backup {count:,} entity contamination rows to {backup_name}")
        results["entity_contamination"] = count
    else:
        cursor.execute(f"""
            CREATE TABLE {backup_name} AS
            SELECT * FROM financial_tables
            WHERE entity_normalized IN ({entity_list})
        """)
        cursor.execute(f"SELECT COUNT(*) FROM {backup_name}")
        count = cursor.fetchone()[0]
        conn.commit()
        print(f"  Created {backup_name}: {count:,} rows")
        results["entity_contamination"] = count

    # Backup 3: Future year rows
    backup_name = f"backup_future_years_{timestamp}"
    year_list = ", ".join(str(y) for y in INVALID_FUTURE_YEARS)

    if dry_run:
        cursor.execute(f"""
            SELECT COUNT(*) FROM financial_tables
            WHERE fiscal_year IN ({year_list})
        """)
        count = cursor.fetchone()[0]
        print(f"  [DRY RUN] Would backup {count:,} future year rows to {backup_name}")
        results["future_years"] = count
    else:
        cursor.execute(f"""
            CREATE TABLE {backup_name} AS
            SELECT * FROM financial_tables
            WHERE fiscal_year IN ({year_list})
        """)
        cursor.execute(f"SELECT COUNT(*) FROM {backup_name}")
        count = cursor.fetchone()[0]
        conn.commit()
        print(f"  Created {backup_name}: {count:,} rows")
        results["future_years"] = count

    return results


def delete_empty_metrics(cursor, conn, dry_run: bool = False) -> int:
    """Delete rows where metric is NULL or empty.

    These are typically header rows, section dividers, or formatting artifacts
    captured during ingestion.
    """
    print("\nStep 2: Deleting empty metric rows...")

    if dry_run:
        cursor.execute("""
            SELECT COUNT(*) FROM financial_tables
            WHERE metric IS NULL OR metric = ''
        """)
        count = cursor.fetchone()[0]
        print(f"  [DRY RUN] Would delete {count:,} empty metric rows")

        # Show breakdown by entity
        cursor.execute("""
            SELECT COALESCE(entity, '(null)') as entity, COUNT(*) as cnt
            FROM financial_tables
            WHERE metric IS NULL OR metric = ''
            GROUP BY entity
            ORDER BY cnt DESC
            LIMIT 10
        """)
        breakdown = cursor.fetchall()
        if breakdown:
            print("  Top entities with empty metrics:")
            for entity, cnt in breakdown:
                print(f"    {entity}: {cnt:,}")
        return count
    else:
        cursor.execute("""
            DELETE FROM financial_tables
            WHERE metric IS NULL OR metric = ''
        """)
        deleted = cursor.rowcount
        conn.commit()
        print(f"  Deleted {deleted:,} empty metric rows")
        return deleted


def delete_entity_contamination(cursor, conn, dry_run: bool = False) -> int:
    """Delete rows where entity_normalized contains metric names.

    These are structural errors where cash flow items ended up in the entity field.
    """
    print("\nStep 3: Deleting entity contamination rows...")

    entity_list = ", ".join(f"'{e}'" for e in ENTITY_CONTAMINATION_PATTERNS)

    if dry_run:
        cursor.execute(f"""
            SELECT COUNT(*) FROM financial_tables
            WHERE entity_normalized IN ({entity_list})
        """)
        count = cursor.fetchone()[0]
        print(f"  [DRY RUN] Would delete {count:,} entity contamination rows")

        # Show breakdown
        cursor.execute(f"""
            SELECT entity_normalized, COUNT(*) as cnt
            FROM financial_tables
            WHERE entity_normalized IN ({entity_list})
            GROUP BY entity_normalized
            ORDER BY cnt DESC
        """)
        breakdown = cursor.fetchall()
        if breakdown:
            print("  Contaminated entity_normalized values:")
            for entity, cnt in breakdown:
                print(f"    {entity}: {cnt:,}")
        return count
    else:
        cursor.execute(f"""
            DELETE FROM financial_tables
            WHERE entity_normalized IN ({entity_list})
        """)
        deleted = cursor.rowcount
        conn.commit()
        print(f"  Deleted {deleted:,} entity contamination rows")
        return deleted


def delete_future_years(cursor, conn, dry_run: bool = False) -> int:
    """Delete rows with invalid future years (data corruption)."""
    print("\nStep 4: Deleting invalid future year rows...")

    year_list = ", ".join(str(y) for y in INVALID_FUTURE_YEARS)

    if dry_run:
        cursor.execute(f"""
            SELECT fiscal_year, COUNT(*) as cnt
            FROM financial_tables
            WHERE fiscal_year IN ({year_list})
            GROUP BY fiscal_year
        """)
        breakdown = cursor.fetchall()
        total = sum(cnt for _, cnt in breakdown)
        print(f"  [DRY RUN] Would delete {total:,} future year rows:")
        for year, cnt in breakdown:
            print(f"    Year {year}: {cnt:,}")
        return total
    else:
        cursor.execute(f"""
            DELETE FROM financial_tables
            WHERE fiscal_year IN ({year_list})
        """)
        deleted = cursor.rowcount
        conn.commit()
        print(f"  Deleted {deleted:,} future year rows")
        return deleted


def reclassify_entity_named_metrics(cursor, conn, dry_run: bool = False) -> int:
    """Reclassify metrics that are actually facility/location names.

    These rows have facility names (like 'Pataias', 'Outão') in the metric field
    when they should be in the entity field.
    """
    print("\nStep 5: Reclassifying entity-named metrics...")

    metric_list = ", ".join(f"'{m}'" for m in ENTITY_NAMED_METRICS)

    # First, check which of these metrics actually exist
    cursor.execute(f"""
        SELECT metric, COUNT(*) as cnt
        FROM financial_tables
        WHERE metric IN ({metric_list})
        GROUP BY metric
        ORDER BY cnt DESC
    """)
    existing = cursor.fetchall()

    if not existing:
        print("  No entity-named metrics found to reclassify")
        return 0

    print(f"  Found {len(existing)} entity-named metrics:")
    for metric, cnt in existing:
        print(f"    {metric}: {cnt:,} rows")

    total = sum(cnt for _, cnt in existing)

    if dry_run:
        print(f"  [DRY RUN] Would reclassify {total:,} rows")
        return total

    # Reclassify: move metric to entity, set metric to 'Facility Data'
    cursor.execute(f"""
        UPDATE financial_tables
        SET entity = CASE WHEN entity IS NULL OR entity = '' THEN metric ELSE entity || ' - ' || metric END,
            metric = 'Facility Data',
            unit_inferred = TRUE,
            unit_inference_method = 'metric_reclassification'
        WHERE metric IN ({metric_list})
    """)
    updated = cursor.rowcount
    conn.commit()
    print(f"  Reclassified {updated:,} rows")
    return updated


def clean_malformed_units(cursor, conn, dry_run: bool = False) -> int:
    """Clean up malformed unit strings.

    Fixes issues like:
    - Carriage returns/newlines in units
    - Multiple % symbols
    - Whitespace-only units
    """
    print("\nStep 6: Cleaning malformed units...")

    # Pattern 1: Carriage returns/newlines
    if dry_run:
        cursor.execute("""
            SELECT COUNT(*) FROM financial_tables
            WHERE unit ~ E'[\\r\\n]'
        """)
        cr_count = cursor.fetchone()[0]
        print(f"  [DRY RUN] Would clean {cr_count:,} rows with CR/LF in unit")
    else:
        cursor.execute("""
            UPDATE financial_tables
            SET unit = NULL,
                unit_inferred = TRUE,
                unit_inference_method = 'malformed_cleanup'
            WHERE unit ~ E'[\\r\\n]'
        """)
        cr_count = cursor.rowcount
        print(f"  Cleaned {cr_count:,} rows with CR/LF in unit")

    # Pattern 2: Triple % or more
    if dry_run:
        cursor.execute("""
            SELECT COUNT(*) FROM financial_tables
            WHERE unit ~ '%.*%.*%'
        """)
        pct_count = cursor.fetchone()[0]
        print(f"  [DRY RUN] Would clean {pct_count:,} rows with multiple %%")
    else:
        cursor.execute("""
            UPDATE financial_tables
            SET unit = '%',
                unit_inferred = TRUE,
                unit_inference_method = 'malformed_cleanup'
            WHERE unit ~ '%.*%.*%'
        """)
        pct_count = cursor.rowcount
        print(f"  Cleaned {pct_count:,} rows with multiple %%")

    # Pattern 3: Whitespace-only
    if dry_run:
        cursor.execute("""
            SELECT COUNT(*) FROM financial_tables
            WHERE unit ~ '^\\s+$'
        """)
        ws_count = cursor.fetchone()[0]
        print(f"  [DRY RUN] Would clean {ws_count:,} rows with whitespace-only unit")
    else:
        cursor.execute("""
            UPDATE financial_tables
            SET unit = NULL,
                unit_inferred = TRUE,
                unit_inference_method = 'malformed_cleanup'
            WHERE unit ~ '^\\s+$'
        """)
        ws_count = cursor.rowcount
        print(f"  Cleaned {ws_count:,} rows with whitespace-only unit")

    if not dry_run:
        conn.commit()

    total = cr_count + pct_count + ws_count
    return total


def print_summary(results: dict[str, int], dry_run: bool) -> None:
    """Print summary of all operations."""
    print("\n" + "=" * 70)
    print("PHASE 4A SUMMARY")
    print("=" * 70)

    total_deleted = 0
    total_updated = 0

    print(f"\n{'Operation':<40} {'Rows':>15}")
    print("-" * 55)

    for key, value in results.items():
        if "deleted" in key.lower() or "backup" in key.lower():
            total_deleted += value if "deleted" in key.lower() else 0
        else:
            total_updated += value
        print(f"{key:<40} {value:>15,}")

    print("-" * 55)
    print(f"{'Total rows deleted':<40} {total_deleted:>15,}")
    print(f"{'Total rows updated':<40} {total_updated:>15,}")

    if dry_run:
        print("\n[DRY RUN] No changes were made to the database.")
        print("Run without --dry-run to apply changes.")


def structural_cleanup(dry_run: bool = False, skip_backup: bool = False) -> dict[str, int]:
    """Run all structural cleanup operations.

    Args:
        dry_run: If True, only print SQL without executing
        skip_backup: If True, skip creating backup tables

    Returns:
        Dict with counts of rows affected by each operation
    """
    from raglite.shared.clients import get_postgresql_connection

    conn = get_postgresql_connection()
    cursor = conn.cursor()
    results: dict[str, int] = {}

    print("\n" + "=" * 70)
    print("Phase 4A: Structural Cleanup")
    print("=" * 70)

    # Show initial state
    print("\nInitial State:")
    cursor.execute("SELECT COUNT(*) FROM financial_tables")
    initial_count = cursor.fetchone()[0]
    print(f"  Total rows: {initial_count:,}")

    cursor.execute("""
        SELECT COUNT(*) FROM financial_tables
        WHERE metric IS NULL OR metric = ''
    """)
    empty_metrics = cursor.fetchone()[0]
    print(f"  Empty metric rows: {empty_metrics:,} ({100.0 * empty_metrics / initial_count:.1f}%)")

    # Create backups
    if not skip_backup:
        backup_results = create_backup_tables(cursor, conn, dry_run)
        results.update({f"backup_{k}": v for k, v in backup_results.items()})

    # Execute cleanup operations
    results["deleted_empty_metrics"] = delete_empty_metrics(cursor, conn, dry_run)
    results["deleted_entity_contamination"] = delete_entity_contamination(cursor, conn, dry_run)
    results["deleted_future_years"] = delete_future_years(cursor, conn, dry_run)
    results["reclassified_metrics"] = reclassify_entity_named_metrics(cursor, conn, dry_run)
    results["cleaned_malformed_units"] = clean_malformed_units(cursor, conn, dry_run)

    # Show final state
    if not dry_run:
        print("\nFinal State:")
        cursor.execute("SELECT COUNT(*) FROM financial_tables")
        final_count = cursor.fetchone()[0]
        print(f"  Total rows: {final_count:,}")
        print(f"  Rows removed: {initial_count - final_count:,}")

        cursor.execute("""
            SELECT COUNT(*) FROM financial_tables
            WHERE metric IS NULL OR metric = ''
        """)
        remaining_empty = cursor.fetchone()[0]
        print(f"  Empty metric rows: {remaining_empty:,}")

    cursor.close()
    return results


def main() -> int:
    """Main entry point."""
    args = parse_args()

    try:
        results = structural_cleanup(dry_run=args.dry_run, skip_backup=args.skip_backup)

        print_summary(results, args.dry_run)

        print("\n" + "=" * 70)
        if args.dry_run:
            print("Phase 4A complete (DRY RUN)")
        else:
            print("Phase 4A complete")
        print("=" * 70)
        print("\nNext step: Run scripts/fix_ratio_decomposition.py (Phase 4B)")

        return 0

    except Exception as e:
        print(f"\n ERROR: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
