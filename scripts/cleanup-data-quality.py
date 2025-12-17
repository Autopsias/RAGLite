#!/usr/bin/env python3
"""
Data Quality Cleanup Script

Fixes identified data quality issues in production databases:
1. Qdrant: Remove 2025-08 v2 duplicate chunks (1,521 duplicates -> keep 189 unique)
2. PostgreSQL: Delete orphaned documents (part01 + sample_financial_report)
3. PostgreSQL: Fix naming inconsistency (add .pdf extension to 22 documents)

IMPORTANT: Run ./scripts/backup-all.sh before executing this script!

Usage:
    python scripts/cleanup-data-quality.py --dry-run    # Preview changes
    python scripts/cleanup-data-quality.py              # Execute cleanup
    python scripts/cleanup-data-quality.py --phase 1    # Run specific phase only
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
from collections import defaultdict
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from qdrant_client import QdrantClient
from qdrant_client.models import PointIdsList

from raglite.shared.logging import get_logger

logger = get_logger(__name__)

# Production ports
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
COLLECTION_NAME = "financial_docs"

# Target document for Qdrant cleanup
TARGET_DOCUMENT = "2025-08 Performance Review CONSO_v2.pdf"

# Orphaned documents to delete from PostgreSQL
ORPHAN_DOCUMENTS = [
    "%part01_pages001-040%",
    "%sample_financial_report%",
]


def get_qdrant_client() -> QdrantClient:
    """Get Qdrant client for production."""
    return QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)


def get_postgresql_connection():
    """Get PostgreSQL connection for production."""
    from raglite.shared.clients import get_postgresql_connection

    return get_postgresql_connection()


def phase1_qdrant_dedup(dry_run: bool = True) -> dict:
    """
    Phase 1: Remove duplicate chunks from 2025-08 v2 in Qdrant.

    Groups chunks by text content hash and keeps only the first occurrence.
    """
    print("\n" + "=" * 60)
    print("PHASE 1: Qdrant Duplicate Removal")
    print("=" * 60)
    print(f"Target document: {TARGET_DOCUMENT}")

    client = get_qdrant_client()

    # Fetch all chunks for the target document
    all_points = []
    offset = None

    while True:
        result = client.scroll(
            collection_name=COLLECTION_NAME,
            limit=100,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        points, next_offset = result

        for point in points:
            source_doc = point.payload.get("source_document", "")
            if TARGET_DOCUMENT in source_doc:
                all_points.append(point)

        if next_offset is None:
            break
        offset = next_offset

    print(f"Found {len(all_points)} chunks for target document")

    # Group by text hash
    text_groups: dict[str, list] = defaultdict(list)
    for point in all_points:
        text = point.payload.get("text", "")
        text_hash = hashlib.md5(text.encode()).hexdigest()
        text_groups[text_hash].append(point)

    unique_count = len(text_groups)
    duplicate_count = len(all_points) - unique_count

    print(f"Unique texts: {unique_count}")
    print(f"Duplicates to remove: {duplicate_count}")

    # Find IDs to delete (keep first of each group)
    ids_to_delete = []
    for text_hash, points in text_groups.items():
        if len(points) > 1:
            # Keep first, delete rest
            for point in points[1:]:
                ids_to_delete.append(point.id)

    print(f"Point IDs to delete: {len(ids_to_delete)}")

    if dry_run:
        print("\n[DRY RUN] Would delete these point IDs:")
        for pid in ids_to_delete[:10]:
            print(f"  - {pid}")
        if len(ids_to_delete) > 10:
            print(f"  ... and {len(ids_to_delete) - 10} more")
    else:
        if ids_to_delete:
            print("\nDeleting duplicate points...")
            # Delete in batches of 100
            batch_size = 100
            for i in range(0, len(ids_to_delete), batch_size):
                batch = ids_to_delete[i : i + batch_size]
                client.delete(
                    collection_name=COLLECTION_NAME,
                    points_selector=PointIdsList(points=batch),
                )
                print(f"  Deleted batch {i // batch_size + 1}: {len(batch)} points")

            print(f"✓ Deleted {len(ids_to_delete)} duplicate points")
        else:
            print("No duplicates found to delete")

    return {
        "phase": 1,
        "total_chunks": len(all_points),
        "unique_chunks": unique_count,
        "duplicates_removed": len(ids_to_delete) if not dry_run else 0,
        "duplicates_found": duplicate_count,
    }


def phase2_postgresql_orphans(dry_run: bool = True) -> dict:
    """
    Phase 2: Delete orphaned documents from PostgreSQL.

    Removes documents that exist only in PostgreSQL but not in Qdrant.
    """
    print("\n" + "=" * 60)
    print("PHASE 2: PostgreSQL Orphan Removal")
    print("=" * 60)

    conn = get_postgresql_connection()
    cursor = conn.cursor()

    # Count rows to delete
    total_to_delete = 0
    for pattern in ORPHAN_DOCUMENTS:
        cursor.execute(
            "SELECT COUNT(*) FROM financial_tables WHERE document_id LIKE %s", (pattern,)
        )
        count = cursor.fetchone()[0]
        print(f"  {pattern}: {count} rows")
        total_to_delete += count

    print(f"Total rows to delete: {total_to_delete}")

    if dry_run:
        print("\n[DRY RUN] Would delete rows matching:")
        for pattern in ORPHAN_DOCUMENTS:
            print(f"  - {pattern}")
    else:
        if total_to_delete > 0:
            print("\nDeleting orphaned documents...")
            for pattern in ORPHAN_DOCUMENTS:
                cursor.execute("DELETE FROM financial_tables WHERE document_id LIKE %s", (pattern,))
                print(f"  Deleted rows matching: {pattern}")

            conn.commit()
            print(f"✓ Deleted {total_to_delete} orphaned rows")
        else:
            print("No orphaned documents found")

    cursor.close()

    return {
        "phase": 2,
        "orphan_patterns": ORPHAN_DOCUMENTS,
        "rows_deleted": total_to_delete if not dry_run else 0,
        "rows_found": total_to_delete,
    }


def phase3_postgresql_naming(dry_run: bool = True) -> dict:
    """
    Phase 3: Fix naming inconsistency in PostgreSQL.

    Adds .pdf extension to document_id for documents missing it.
    """
    print("\n" + "=" * 60)
    print("PHASE 3: PostgreSQL Naming Fix")
    print("=" * 60)

    conn = get_postgresql_connection()
    cursor = conn.cursor()

    # Count documents without .pdf extension
    cursor.execute(
        "SELECT document_id, COUNT(*) as rows FROM financial_tables "
        "WHERE document_id NOT LIKE '%.pdf' "
        "GROUP BY document_id ORDER BY document_id"
    )
    docs_to_fix = cursor.fetchall()

    print(f"Documents without .pdf extension: {len(docs_to_fix)}")
    total_rows = sum(row[1] for row in docs_to_fix)
    print(f"Total rows affected: {total_rows}")

    if docs_to_fix:
        print("\nDocuments to rename:")
        for doc_id, count in docs_to_fix[:10]:
            print(f"  {doc_id} ({count} rows)")
        if len(docs_to_fix) > 10:
            print(f"  ... and {len(docs_to_fix) - 10} more")

    if dry_run:
        print("\n[DRY RUN] Would rename documents to add .pdf extension")
    else:
        if docs_to_fix:
            print("\nAdding .pdf extension...")
            cursor.execute(
                "UPDATE financial_tables "
                "SET document_id = document_id || '.pdf' "
                "WHERE document_id NOT LIKE '%.pdf'"
            )
            rows_updated = cursor.rowcount
            conn.commit()
            print(f"✓ Updated {rows_updated} rows")
        else:
            print("No documents need renaming")

    cursor.close()

    return {
        "phase": 3,
        "documents_fixed": len(docs_to_fix) if not dry_run else 0,
        "documents_found": len(docs_to_fix),
        "rows_affected": total_rows,
    }


def verify_results() -> dict:
    """Verify the cleanup results."""
    print("\n" + "=" * 60)
    print("VERIFICATION")
    print("=" * 60)

    # Qdrant verification
    client = get_qdrant_client()
    collection_info = client.get_collection(COLLECTION_NAME)
    total_qdrant = collection_info.points_count

    # Count 2025-08 v2 chunks
    v2_count = 0
    offset = None
    while True:
        result = client.scroll(
            collection_name=COLLECTION_NAME,
            limit=100,
            offset=offset,
            with_payload=["source_document"],
            with_vectors=False,
        )
        points, next_offset = result
        for point in points:
            source_doc = point.payload.get("source_document", "")
            if TARGET_DOCUMENT in source_doc:
                v2_count += 1
        if next_offset is None:
            break
        offset = next_offset

    print(f"Qdrant total chunks: {total_qdrant}")
    print(f"Qdrant 2025-08 v2 chunks: {v2_count}")

    # PostgreSQL verification
    conn = get_postgresql_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM financial_tables")
    total_pg = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT document_id) FROM financial_tables")
    doc_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM financial_tables WHERE document_id NOT LIKE '%.pdf'")
    without_pdf = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM financial_tables "
        "WHERE document_id LIKE '%part01%' OR document_id LIKE '%sample_financial%'"
    )
    orphans = cursor.fetchone()[0]

    cursor.close()

    print(f"PostgreSQL total rows: {total_pg}")
    print(f"PostgreSQL documents: {doc_count}")
    print(f"Documents without .pdf: {without_pdf}")
    print(f"Orphaned documents: {orphans}")

    return {
        "qdrant_total": total_qdrant,
        "qdrant_v2_chunks": v2_count,
        "postgresql_total": total_pg,
        "postgresql_documents": doc_count,
        "without_pdf_extension": without_pdf,
        "orphaned_rows": orphans,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Clean data quality issues in production databases"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without executing",
    )
    parser.add_argument(
        "--phase",
        type=int,
        choices=[1, 2, 3],
        help="Run specific phase only (1=Qdrant dedup, 2=PG orphans, 3=PG naming)",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only verify current state, no changes",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("DATA QUALITY CLEANUP SCRIPT")
    print("=" * 60)

    if args.dry_run:
        print("MODE: DRY RUN (no changes will be made)")
    else:
        print("MODE: EXECUTE (changes will be applied)")

    # Verify backup exists
    backup_dir = Path(__file__).parent.parent / "backups"
    recent_backups = list(backup_dir.glob("*20251216*"))
    if not recent_backups and not args.dry_run and not args.verify_only:
        print("\n⚠️  WARNING: No recent backup found!")
        print("Run ./scripts/backup-all.sh before proceeding.")
        response = input("Continue anyway? (yes/no): ")
        if response.lower() != "yes":
            print("Aborted.")
            return 1

    if args.verify_only:
        verify_results()
        return 0

    results = {}

    # Run phases
    if args.phase is None or args.phase == 1:
        results["phase1"] = phase1_qdrant_dedup(dry_run=args.dry_run)

    if args.phase is None or args.phase == 2:
        results["phase2"] = phase2_postgresql_orphans(dry_run=args.dry_run)

    if args.phase is None or args.phase == 3:
        results["phase3"] = phase3_postgresql_naming(dry_run=args.dry_run)

    # Verify final state
    if not args.dry_run:
        results["verification"] = verify_results()

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    if "phase1" in results:
        p1 = results["phase1"]
        print(
            f"Phase 1 (Qdrant): {p1['duplicates_found']} duplicates found, "
            f"{p1.get('duplicates_removed', 0)} removed"
        )

    if "phase2" in results:
        p2 = results["phase2"]
        print(
            f"Phase 2 (Orphans): {p2['rows_found']} rows found, {p2.get('rows_deleted', 0)} deleted"
        )

    if "phase3" in results:
        p3 = results["phase3"]
        print(
            f"Phase 3 (Naming): {p3['documents_found']} documents found, "
            f"{p3.get('documents_fixed', 0)} fixed"
        )

    if args.dry_run:
        print("\n[DRY RUN] No changes were made. Run without --dry-run to execute.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
