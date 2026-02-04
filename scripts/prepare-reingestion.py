#!/usr/bin/env python3
"""Prepare production database for re-ingestion by cleaning existing data.

This script safely clears production databases before re-ingestion:
- Verifies backups exist
- Requires explicit confirmation
- Supports dry-run mode
- Uses SafetyGuard patterns

DANGER: This script deletes production data. Always backup first!

Usage:
    # Preview actions without executing
    python scripts/prepare-reingestion.py --dry-run

    # Execute cleanup (requires confirmation)
    python scripts/prepare-reingestion.py --force-production
"""

import argparse
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add raglite to path
sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ["APP_ENV"] = "production"

import psycopg2
from psycopg2 import sql
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from raglite.shared.config import get_settings
from raglite.shared.safety import SafetyGuard


def verify_backup_exists(max_age_hours: int = 24) -> tuple[bool, str]:
    """Verify a recent backup exists.

    Args:
        max_age_hours: Maximum age of backup in hours

    Returns:
        Tuple of (backup_exists, message)
    """
    backup_dir = Path("backups")
    if not backup_dir.exists():
        return False, f"Backup directory not found: {backup_dir}"

    # Check for recent PostgreSQL backup
    pg_backups = list(backup_dir.glob("postgresql_backup_*.sql"))
    if not pg_backups:
        return False, "No PostgreSQL backups found"

    latest_pg = max(pg_backups, key=lambda p: p.stat().st_mtime)
    pg_age = datetime.now() - datetime.fromtimestamp(latest_pg.stat().st_mtime)

    if pg_age > timedelta(hours=max_age_hours):
        return False, (
            f"Latest PostgreSQL backup is {pg_age.total_seconds() / 3600:.1f} hours old. "
            f"Run scripts/backup-all.sh to create fresh backup"
        )

    # Check for recent Qdrant snapshot
    qdrant_snapshots = list(backup_dir.glob("qdrant_snapshot_*"))
    if not qdrant_snapshots:
        return False, "No Qdrant snapshots found"

    latest_qdrant = max(qdrant_snapshots, key=lambda p: p.stat().st_mtime)
    qdrant_age = datetime.now() - datetime.fromtimestamp(latest_qdrant.stat().st_mtime)

    if qdrant_age > timedelta(hours=max_age_hours):
        return False, (
            f"Latest Qdrant snapshot is {qdrant_age.total_seconds() / 3600:.1f} hours old. "
            f"Run scripts/backup-all.sh to create fresh backup"
        )

    return True, (
        f"Backups found:\n"
        f"  - PostgreSQL: {latest_pg.name} ({pg_age.total_seconds() / 3600:.1f}h ago)\n"
        f"  - Qdrant: {latest_qdrant.name} ({qdrant_age.total_seconds() / 3600:.1f}h ago)"
    )


def get_confirmation() -> bool:
    """Prompt user for explicit confirmation."""
    print()
    print("=" * 80)
    print("⚠️  WARNING: DESTRUCTIVE OPERATION")
    print("=" * 80)
    print("This will DELETE all production data:")
    print("  - Qdrant collection 'financial_docs' (all vectors)")
    print("  - PostgreSQL table 'financial_tables' (all rows)")
    print("  - PostgreSQL table 'financial_chunks' (all rows)")
    print()
    print("This action CANNOT be undone without restoring from backup!")
    print("=" * 80)
    print()

    response = input("Type 'DELETE' (in all caps) to confirm: ")
    return response == "DELETE"


def cleanup_qdrant(client: QdrantClient, dry_run: bool = False) -> None:
    """Recreate Qdrant collection."""
    collection_name = "financial_docs"

    if dry_run:
        print(f"[DRY RUN] Would delete collection: {collection_name}")
        print("[DRY RUN] Would recreate collection with vector_size=768, distance=Cosine")
        return

    print(f"Deleting Qdrant collection: {collection_name}")
    try:
        client.delete_collection(collection_name=collection_name)
        print("✅ Collection deleted")
    except Exception as e:
        print(f"ℹ️  Collection may not exist: {e}")

    print(f"Recreating Qdrant collection: {collection_name}")
    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=768, distance=Distance.COSINE),
    )
    print("✅ Collection recreated")


def cleanup_postgresql(conn_str: str, dry_run: bool = False) -> None:
    """Truncate PostgreSQL tables."""
    tables = ["financial_tables", "financial_chunks"]

    if dry_run:
        for table in tables:
            print(f"[DRY RUN] Would truncate table: {table}")
        return

    # SafetyGuard check for production operations
    guard = SafetyGuard()
    guard.check_operation("TRUNCATE TABLE financial_tables, financial_chunks")

    conn = psycopg2.connect(conn_str)
    try:
        with conn.cursor() as cur:
            for table in tables:
                print(f"Truncating table: {table}")
                # Use sql.Identifier to prevent SQL injection
                cur.execute(sql.SQL("TRUNCATE TABLE {} CASCADE").format(sql.Identifier(table)))
                print(f"✅ Table truncated: {table}")
        conn.commit()
        print("✅ PostgreSQL cleanup complete")
    finally:
        conn.close()


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Prepare production database for re-ingestion")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview actions without executing",
    )
    parser.add_argument(
        "--force-production",
        action="store_true",
        help="Required flag to confirm production operation",
    )
    parser.add_argument(
        "--skip-backup-check",
        action="store_true",
        help="Skip backup verification (DANGEROUS - not recommended)",
    )
    args = parser.parse_args()

    print("=" * 80)
    print("PRODUCTION DATABASE CLEANUP FOR RE-INGESTION")
    print("=" * 80)
    print(f"Dry run: {args.dry_run}")
    print(f"Force production: {args.force_production}")
    print("=" * 80)
    print()

    # Dry run mode - preview actions
    if args.dry_run:
        print("[DRY RUN] Would perform the following actions:")
        print()
        print("1. Verify backup exists (age < 24 hours)")
        print("2. Delete Qdrant collection 'financial_docs'")
        print("3. Recreate Qdrant collection with same schema")
        print("4. TRUNCATE PostgreSQL table 'financial_tables'")
        print("5. TRUNCATE PostgreSQL table 'financial_chunks'")
        print()
        print("[DRY RUN] No actual changes made")
        return 0

    # Production mode - safety checks
    if not args.force_production:
        print("❌ ERROR: Use --force-production flag for production operations")
        print()
        print("This is a safety measure to prevent accidental data loss.")
        print()
        print("Run with:")
        print("  python scripts/prepare-reingestion.py --force-production")
        return 1

    # Verify backup exists (unless explicitly skipped)
    if not args.skip_backup_check:
        print("Verifying backup exists...")
        backup_ok, backup_msg = verify_backup_exists()
        if not backup_ok:
            print(f"❌ ERROR: {backup_msg}")
            print()
            print("Create a backup first:")
            print("  ./scripts/backup-all.sh")
            return 1
        print(f"✅ {backup_msg}")
    else:
        print("⚠️  WARNING: Backup verification skipped!")

    # Get explicit user confirmation
    if not get_confirmation():
        print("❌ Cleanup aborted by user")
        return 1

    print()
    print("Proceeding with cleanup...")
    print()

    # Get settings
    settings = get_settings()

    try:
        # Cleanup Qdrant
        print("=" * 80)
        print("QDRANT CLEANUP")
        print("=" * 80)
        qdrant_client = QdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
        )
        cleanup_qdrant(qdrant_client)

        print()

        # Cleanup PostgreSQL
        print("=" * 80)
        print("POSTGRESQL CLEANUP")
        print("=" * 80)
        cleanup_postgresql(settings.pg_connection_string)

        print()
        print("=" * 80)
        print("✅ CLEANUP COMPLETE")
        print("=" * 80)
        print()
        print("Next steps:")
        print("  1. Run: python scripts/reingest-all-documents.py")
        print("  2. Validate: python scripts/validate-classification-coverage.py")
        print("  3. Check accuracy: python scripts/validate-classification-accuracy.py")
        print()

        return 0

    except Exception as e:
        print()
        print("=" * 80)
        print("❌ CLEANUP FAILED")
        print("=" * 80)
        print(f"Error: {e}")
        print()
        print("Rollback procedure:")
        print("  1. Restore PostgreSQL:")
        print(
            "     docker exec -i raglite-postgresql psql -U raglite -d raglite < backups/postgresql_backup_*.sql"
        )
        print("  2. Restore Qdrant: See backups/README.md for snapshot recovery")
        print()
        return 1


if __name__ == "__main__":
    sys.exit(main())
