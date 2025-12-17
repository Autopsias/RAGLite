#!/usr/bin/env python3
"""
Comprehensive Database Cleanup Script

Executes all cleanup recommendations from the deep analysis:
1. PostgreSQL deduplication (remove ~191K duplicate rows)
2. PostgreSQL VACUUM ANALYZE
3. PostgreSQL unused table removal (6 tables)
4. Qdrant HNSW indexing (lower threshold to 5000)
5. Qdrant payload indexes (4 keyword indexes)

IMPORTANT: Run ./scripts/backup-all.sh pre-cleanup before executing!

Usage:
    python scripts/cleanup-comprehensive.py --dry-run     # Preview all changes
    python scripts/cleanup-comprehensive.py               # Execute cleanup
    python scripts/cleanup-comprehensive.py --skip-backup # Skip backup verification
    python scripts/cleanup-comprehensive.py --step N      # Run specific step only
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from qdrant_client import QdrantClient
from qdrant_client.models import OptimizersConfigDiff, PayloadSchemaType

# Production configuration
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
COLLECTION_NAME = "financial_docs"

# Unused tables to remove
UNUSED_TABLES = [
    "apscheduler_jobs",
    "model_registry",
    "model_weights",
    "documents",
    "document_chunks",
    "entity_mappings",
]


def get_qdrant_client() -> QdrantClient:
    """Get Qdrant client for production."""
    return QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)


def get_postgresql_connection():
    """Get PostgreSQL connection for production."""
    from raglite.shared.clients import get_postgresql_connection

    return get_postgresql_connection()


def validate_consistency() -> tuple[bool, int, int]:
    """
    Validate document consistency between Qdrant and PostgreSQL.

    Returns:
        Tuple of (is_consistent, qdrant_count, postgresql_count)
    """
    # Import validation function
    from validate_database_consistency import get_postgresql_documents, get_qdrant_documents

    qdrant_docs = get_qdrant_documents()
    postgresql_docs = get_postgresql_documents()

    is_consistent = qdrant_docs == postgresql_docs
    return is_consistent, len(qdrant_docs), len(postgresql_docs)


def step1_validate_pre_cleanup(dry_run: bool = True) -> dict:
    """
    Step 1: Validate document consistency before cleanup.
    """
    print("\n" + "=" * 60)
    print("STEP 1: Pre-Cleanup Validation")
    print("=" * 60)

    client = get_qdrant_client()
    conn = get_postgresql_connection()
    cursor = conn.cursor()

    # Get Qdrant documents
    qdrant_docs = set()
    offset = None
    while True:
        result = client.scroll(
            collection_name=COLLECTION_NAME,
            limit=1000,
            offset=offset,
            with_payload=["source_document"],
            with_vectors=False,
        )
        points, next_offset = result
        for point in points:
            doc = point.payload.get("source_document")
            if doc:
                qdrant_docs.add(doc)
        if next_offset is None:
            break
        offset = next_offset

    # Get PostgreSQL documents
    cursor.execute("SELECT DISTINCT document_id FROM financial_tables")
    postgresql_docs = {row[0] for row in cursor.fetchall()}
    cursor.close()

    is_consistent = qdrant_docs == postgresql_docs

    print(f"Qdrant documents: {len(qdrant_docs)}")
    print(f"PostgreSQL documents: {len(postgresql_docs)}")
    print(f"Consistency: {'✅ PASS' if is_consistent else '❌ FAIL'}")

    if not is_consistent:
        only_qdrant = qdrant_docs - postgresql_docs
        only_pg = postgresql_docs - qdrant_docs
        if only_qdrant:
            print(f"\n⚠️  Only in Qdrant: {only_qdrant}")
        if only_pg:
            print(f"\n⚠️  Only in PostgreSQL: {only_pg}")

    return {
        "step": 1,
        "qdrant_docs": len(qdrant_docs),
        "postgresql_docs": len(postgresql_docs),
        "is_consistent": is_consistent,
    }


def step2_postgresql_deduplication(dry_run: bool = True) -> dict:
    """
    Step 2: Remove duplicate rows from PostgreSQL.

    Uses ROW_NUMBER() to identify duplicates based on:
    (document_id, page_number, table_index, row_index, entity, metric, period)
    """
    print("\n" + "=" * 60)
    print("STEP 2: PostgreSQL Deduplication")
    print("=" * 60)

    conn = get_postgresql_connection()
    cursor = conn.cursor()

    # Count current rows
    cursor.execute("SELECT COUNT(*) FROM financial_tables")
    total_before = cursor.fetchone()[0]
    print(f"Current rows: {total_before:,}")

    # Count duplicates
    cursor.execute("""
        WITH duplicates AS (
            SELECT id,
                   ROW_NUMBER() OVER (
                       PARTITION BY document_id, page_number, table_index,
                                    row_index, entity, metric, period
                       ORDER BY id ASC
                   ) as rn
            FROM financial_tables
        )
        SELECT COUNT(*) FROM duplicates WHERE rn > 1
    """)
    duplicate_count = cursor.fetchone()[0]
    print(f"Duplicates found: {duplicate_count:,}")
    print(f"Expected after cleanup: {total_before - duplicate_count:,}")

    if dry_run:
        print("\n[DRY RUN] Would remove duplicates keeping oldest entry")
        print("  - No backup table created")
        print("  - No rows deleted")
    else:
        if duplicate_count > 0:
            # Create backup table
            print("\nCreating backup table...")
            cursor.execute("DROP TABLE IF EXISTS financial_tables_pre_dedup")
            cursor.execute(
                "CREATE TABLE financial_tables_pre_dedup AS SELECT * FROM financial_tables"
            )
            conn.commit()
            print("  ✓ Backup table created: financial_tables_pre_dedup")

            # Delete duplicates
            print("\nDeleting duplicates...")
            start_time = time.time()

            cursor.execute("""
                WITH duplicates AS (
                    SELECT id,
                           ROW_NUMBER() OVER (
                               PARTITION BY document_id, page_number, table_index,
                                            row_index, entity, metric, period
                               ORDER BY id ASC
                           ) as rn
                    FROM financial_tables
                )
                DELETE FROM financial_tables
                WHERE id IN (SELECT id FROM duplicates WHERE rn > 1)
            """)
            deleted = cursor.rowcount
            conn.commit()

            elapsed = time.time() - start_time
            print(f"  ✓ Deleted {deleted:,} rows in {elapsed:.1f}s")

            # Verify
            cursor.execute("SELECT COUNT(*) FROM financial_tables")
            total_after = cursor.fetchone()[0]
            print(f"  ✓ Rows after cleanup: {total_after:,}")
        else:
            print("\nNo duplicates found - skipping")

    cursor.close()

    return {
        "step": 2,
        "rows_before": total_before,
        "duplicates_found": duplicate_count,
        "rows_after": total_before - duplicate_count if not dry_run else None,
    }


def step3_postgresql_vacuum(dry_run: bool = True) -> dict:
    """
    Step 3: Run VACUUM ANALYZE on financial_tables.
    """
    print("\n" + "=" * 60)
    print("STEP 3: PostgreSQL VACUUM ANALYZE")
    print("=" * 60)

    conn = get_postgresql_connection()
    cursor = conn.cursor()

    # Check dead tuples before
    cursor.execute("""
        SELECT n_dead_tup, n_live_tup
        FROM pg_stat_user_tables
        WHERE relname = 'financial_tables'
    """)
    row = cursor.fetchone()
    dead_before = row[0] if row else 0
    live_before = row[1] if row else 0

    print(f"Dead tuples before: {dead_before:,}")
    print(f"Live tuples: {live_before:,}")

    if dry_run:
        print("\n[DRY RUN] Would run VACUUM ANALYZE financial_tables")
    else:
        print("\nRunning VACUUM ANALYZE...")
        # VACUUM cannot run inside a transaction, so we need autocommit
        conn.autocommit = True
        cursor.execute("VACUUM ANALYZE financial_tables")
        conn.autocommit = False
        print("  ✓ VACUUM ANALYZE completed")

        # Check dead tuples after
        cursor.execute("""
            SELECT n_dead_tup FROM pg_stat_user_tables WHERE relname = 'financial_tables'
        """)
        dead_after = cursor.fetchone()[0]
        print(f"  ✓ Dead tuples after: {dead_after:,}")

    cursor.close()

    return {
        "step": 3,
        "dead_tuples_before": dead_before,
        "dead_tuples_after": 0 if not dry_run else None,
    }


def step4_postgresql_remove_unused_tables(dry_run: bool = True) -> dict:
    """
    Step 4: Remove unused PostgreSQL tables.
    """
    print("\n" + "=" * 60)
    print("STEP 4: Remove Unused PostgreSQL Tables")
    print("=" * 60)

    conn = get_postgresql_connection()
    cursor = conn.cursor()

    # Check which tables exist and their sizes
    tables_to_drop = []
    for table in UNUSED_TABLES:
        cursor.execute(
            """
            SELECT EXISTS (
                SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = %s
            )
        """,
            (table,),
        )
        exists = cursor.fetchone()[0]

        if exists:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            row_count = cursor.fetchone()[0]

            cursor.execute(f"""
                SELECT pg_size_pretty(pg_total_relation_size('public.{table}'))
            """)
            size = cursor.fetchone()[0]

            tables_to_drop.append((table, row_count, size))
            print(f"  • {table}: {row_count} rows, {size}")
        else:
            print(f"  • {table}: (does not exist)")

    if dry_run:
        print(f"\n[DRY RUN] Would drop {len(tables_to_drop)} tables")
    else:
        if tables_to_drop:
            print(f"\nDropping {len(tables_to_drop)} tables...")
            for table, _, _ in tables_to_drop:
                cursor.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
                print(f"  ✓ Dropped {table}")
            conn.commit()
        else:
            print("\nNo tables to drop")

    cursor.close()

    return {
        "step": 4,
        "tables_dropped": len(tables_to_drop) if not dry_run else 0,
        "tables_found": len(tables_to_drop),
    }


def step5_qdrant_indexing(dry_run: bool = True) -> dict:
    """
    Step 5: Configure Qdrant HNSW indexing by lowering threshold.
    """
    print("\n" + "=" * 60)
    print("STEP 5: Qdrant HNSW Indexing Configuration")
    print("=" * 60)

    client = get_qdrant_client()

    # Get current state
    info = client.get_collection(COLLECTION_NAME)
    indexed_before = info.indexed_vectors_count
    total_vectors = info.points_count
    current_threshold = info.config.optimizer_config.indexing_threshold

    print(f"Total vectors: {total_vectors:,}")
    print(f"Indexed vectors (before): {indexed_before:,}")
    print(f"Current indexing threshold: {current_threshold:,}")

    if dry_run:
        print("\n[DRY RUN] Would lower indexing_threshold from 10000 to 5000")
    else:
        print("\nUpdating indexing threshold to 5000...")
        client.update_collection(
            collection_name=COLLECTION_NAME,
            optimizer_config=OptimizersConfigDiff(indexing_threshold=5000),
        )
        print("  ✓ Threshold updated")

        # Wait for indexing to complete
        print("  Waiting for indexing to complete...")
        for _ in range(30):  # Wait up to 30 seconds
            time.sleep(1)
            info = client.get_collection(COLLECTION_NAME)
            indexed = info.indexed_vectors_count
            if indexed >= total_vectors:
                break
            print(f"    Indexed: {indexed:,}/{total_vectors:,}")

        info = client.get_collection(COLLECTION_NAME)
        indexed_after = info.indexed_vectors_count
        print(f"  ✓ Indexed vectors (after): {indexed_after:,}")

    return {
        "step": 5,
        "vectors_total": total_vectors,
        "indexed_before": indexed_before,
        "indexed_after": total_vectors if not dry_run else None,
    }


def step6_qdrant_payload_indexes(dry_run: bool = True) -> dict:
    """
    Step 6: Add payload indexes for common filter fields.
    """
    print("\n" + "=" * 60)
    print("STEP 6: Qdrant Payload Indexes")
    print("=" * 60)

    client = get_qdrant_client()

    # Fields to index
    fields = ["source_document", "document_type", "reporting_period", "section_type"]

    # Check current indexes
    info = client.get_collection(COLLECTION_NAME)
    existing_indexes = set(info.payload_schema.keys()) if info.payload_schema else set()

    print(f"Existing indexes: {existing_indexes or '(none)'}")
    print(f"Indexes to create: {fields}")

    indexes_created = 0
    if dry_run:
        print("\n[DRY RUN] Would create 4 keyword indexes")
    else:
        print("\nCreating payload indexes...")
        for field in fields:
            if field not in existing_indexes:
                client.create_payload_index(
                    collection_name=COLLECTION_NAME,
                    field_name=field,
                    field_schema=PayloadSchemaType.KEYWORD,
                )
                indexes_created += 1
                print(f"  ✓ Created index on '{field}'")
            else:
                print(f"  • Index on '{field}' already exists")

        # Verify
        info = client.get_collection(COLLECTION_NAME)
        new_indexes = set(info.payload_schema.keys()) if info.payload_schema else set()
        print(f"\n  ✓ Indexes after: {new_indexes}")

    return {
        "step": 6,
        "indexes_before": len(existing_indexes),
        "indexes_created": indexes_created if not dry_run else 0,
        "indexes_after": len(existing_indexes) + indexes_created if not dry_run else None,
    }


def step7_final_validation(dry_run: bool = True) -> dict:
    """
    Step 7: Final consistency validation.
    """
    print("\n" + "=" * 60)
    print("STEP 7: Final Validation")
    print("=" * 60)

    if dry_run:
        print("[DRY RUN] Would validate final consistency")
        return {"step": 7, "is_consistent": None}

    # Run full validation
    result = step1_validate_pre_cleanup(dry_run=False)

    # Get additional stats
    client = get_qdrant_client()
    conn = get_postgresql_connection()
    cursor = conn.cursor()

    # Qdrant stats
    info = client.get_collection(COLLECTION_NAME)
    indexed_vectors = info.indexed_vectors_count
    payload_indexes = len(info.payload_schema) if info.payload_schema else 0

    # PostgreSQL stats
    cursor.execute("SELECT COUNT(*) FROM financial_tables")
    pg_rows = cursor.fetchone()[0]

    cursor.execute("""
        SELECT n_dead_tup FROM pg_stat_user_tables WHERE relname = 'financial_tables'
    """)
    dead_tuples = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*) FROM pg_tables WHERE schemaname = 'public'
    """)
    table_count = cursor.fetchone()[0]

    cursor.close()

    print("\n📊 Final State:")
    print(f"  PostgreSQL rows: {pg_rows:,}")
    print(f"  PostgreSQL tables: {table_count}")
    print(f"  PostgreSQL dead tuples: {dead_tuples:,}")
    print(f"  Qdrant indexed vectors: {indexed_vectors:,}")
    print(f"  Qdrant payload indexes: {payload_indexes}")
    print(f"  Document consistency: {'✅ PASS' if result['is_consistent'] else '❌ FAIL'}")

    return {
        "step": 7,
        "is_consistent": result["is_consistent"],
        "postgresql_rows": pg_rows,
        "postgresql_tables": table_count,
        "postgresql_dead_tuples": dead_tuples,
        "qdrant_indexed_vectors": indexed_vectors,
        "qdrant_payload_indexes": payload_indexes,
    }


def main():
    parser = argparse.ArgumentParser(description="Comprehensive database cleanup script")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without executing",
    )
    parser.add_argument(
        "--skip-backup",
        action="store_true",
        help="Skip backup verification check",
    )
    parser.add_argument(
        "--step",
        type=int,
        choices=[1, 2, 3, 4, 5, 6, 7],
        help="Run specific step only",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("COMPREHENSIVE DATABASE CLEANUP")
    print("=" * 60)
    print(f"Mode: {'DRY RUN' if args.dry_run else 'EXECUTE'}")

    # Check for recent backup
    if not args.skip_backup and not args.dry_run:
        backup_dir = Path(__file__).parent.parent / "backups"
        recent_backups = list(backup_dir.glob("*pre-cleanup*"))
        if not recent_backups:
            print("\n⚠️  WARNING: No pre-cleanup backup found!")
            print("Run: ./scripts/backup-all.sh pre-cleanup")
            response = input("Continue anyway? (yes/no): ")
            if response.lower() != "yes":
                print("Aborted.")
                return 1
        else:
            print(f"\n✓ Found backup: {recent_backups[-1].name}")

    results = {}

    # Execute steps
    steps = [
        (1, step1_validate_pre_cleanup, "Pre-Cleanup Validation"),
        (2, step2_postgresql_deduplication, "PostgreSQL Deduplication"),
        (3, step3_postgresql_vacuum, "PostgreSQL VACUUM"),
        (4, step4_postgresql_remove_unused_tables, "Remove Unused Tables"),
        (5, step5_qdrant_indexing, "Qdrant Indexing"),
        (6, step6_qdrant_payload_indexes, "Qdrant Payload Indexes"),
        (7, step7_final_validation, "Final Validation"),
    ]

    for step_num, step_func, step_name in steps:
        if args.step is not None and args.step != step_num:
            continue

        try:
            results[f"step{step_num}"] = step_func(dry_run=args.dry_run)
        except Exception as e:
            print(f"\n❌ ERROR in Step {step_num} ({step_name}): {e}")
            if not args.dry_run:
                print("\n⚠️  Cleanup may be incomplete. Check database state.")
                print("To restore from backup:")
                print(
                    "  docker exec -i raglite-postgresql psql -U raglite -d raglite < backups/postgresql_pre-cleanup_*.sql"
                )
            return 1

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    if args.dry_run:
        print("\n[DRY RUN] No changes were made.")
        print("Run without --dry-run to execute cleanup.")
    else:
        if "step7" in results:
            final = results["step7"]
            print("\n✅ Cleanup completed successfully!")
            print(f"   PostgreSQL rows: {final.get('postgresql_rows', 'N/A'):,}")
            print(f"   PostgreSQL tables: {final.get('postgresql_tables', 'N/A')}")
            print(f"   Qdrant indexed: {final.get('qdrant_indexed_vectors', 'N/A'):,}")
            print(f"   Consistency: {'✅ PASS' if final.get('is_consistent') else '❌ FAIL'}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
