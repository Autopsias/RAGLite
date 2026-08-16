"""Re-classify entity_level for all rows in financial_tables.

Uses the improved entity_level classifier with metric context inference
to reduce unknown rate from ~35% to <20% for EBITDA and similar metrics.

Prerequisites:
    - Run ./scripts/backup-postgresql.sh before executing
    - Production PostgreSQL must be running on port 5432

Usage:
    uv run python scripts/reclassify-entity-levels.py
    uv run python scripts/reclassify-entity-levels.py --dry-run
"""

import argparse

import psycopg2

from raglite.ingestion.classification.entity_level_classifier import classify_entity_level

BATCH_SIZE = 1000


def main() -> None:
    parser = argparse.ArgumentParser(description="Re-classify entity_level column")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    args = parser.parse_args()

    conn = psycopg2.connect(
        host="localhost", port=5432, dbname="raglite", user="raglite", password="raglite"
    )
    cursor = conn.cursor()

    # Fetch all rows with entity, unit, metric for reclassification
    cursor.execute("SELECT id, entity, unit, metric, entity_level FROM financial_tables")
    rows = cursor.fetchall()
    print(f"Total rows: {len(rows)}")

    updates: list[tuple[str, int]] = []
    level_changes: dict[str, int] = {}

    for row_id, entity, unit, metric, current_level in rows:
        entity_str = entity or ""
        unit_str = unit or ""
        metric_str = metric or ""

        result = classify_entity_level(entity_str, unit=unit_str, metric=metric_str)
        new_level = result.entity_level.value

        if new_level != current_level:
            updates.append((new_level, row_id))
            key = f"{current_level or 'NULL'} -> {new_level}"
            level_changes[key] = level_changes.get(key, 0) + 1

    print(f"\nRows to update: {len(updates)}")
    print("\nChanges breakdown:")
    for change, count in sorted(level_changes.items(), key=lambda x: -x[1]):
        print(f"  {change}: {count}")

    if args.dry_run:
        print("\n[DRY RUN] No changes written.")
        cursor.close()
        conn.close()
        return

    if not updates:
        print("\nNo changes needed.")
        cursor.close()
        conn.close()
        return

    # Batch update
    update_cursor = conn.cursor()
    for i in range(0, len(updates), BATCH_SIZE):
        batch = updates[i : i + BATCH_SIZE]
        update_cursor.executemany(
            "UPDATE financial_tables SET entity_level = %s WHERE id = %s",
            batch,
        )
        conn.commit()
        print(f"  Committed batch {i // BATCH_SIZE + 1} ({len(batch)} rows)")

    update_cursor.close()
    cursor.close()
    conn.close()
    print(f"\nDone. Updated {len(updates)} rows.")


if __name__ == "__main__":
    main()
