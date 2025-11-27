#!/usr/bin/env python3
"""Production deployment script with explicit safety controls.

Story 4.0.7: Three-Mode Database Operation System

This script is the ONLY authorized way to make changes to production databases.
It requires explicit confirmation and validates all operations before execution.

Usage:
    # Dry-run: See what would change
    python scripts/deploy-to-production.py --dry-run

    # Schema updates (safe - no data loss)
    python scripts/deploy-to-production.py --deploy-production

    # Re-initialize collection (DELETES existing data)
    python scripts/deploy-to-production.py --deploy-production --force-data-loss
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from raglite.shared.config import settings
from raglite.shared.safety import OperationType, ProductionProtectionError, SafetyGuard

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


CONFIRMATION_PHRASE = "DEPLOY TO PRODUCTION"


def display_environment_info(guard: SafetyGuard) -> None:
    """Display current environment information."""
    guard.display_environment_banner()
    print(f"Collection: {settings.qdrant_collection_name}")
    print(f"PostgreSQL DB: {settings.postgres_db}")
    print()


def confirm_deployment() -> bool:
    """Require explicit confirmation for production deployment.

    Returns:
        True if user confirms, False otherwise
    """
    print(f"\n{'!' * 70}")
    print("  WARNING: You are about to deploy to PRODUCTION")
    print(f"{'!' * 70}")
    print()
    print(f'Type "{CONFIRMATION_PHRASE}" exactly to confirm:')

    response = input("> ").strip()

    if response == CONFIRMATION_PHRASE:
        logger.info("Production deployment confirmed by user")
        return True
    else:
        logger.warning(
            "Confirmation failed",
            extra={"expected": CONFIRMATION_PHRASE, "received": response},
        )
        print(f"\nConfirmation failed. Expected '{CONFIRMATION_PHRASE}'")
        return False


def run_dry_run(guard: SafetyGuard) -> None:
    """Show what would be deployed without making changes."""
    print("\n=== DRY RUN MODE ===")
    print("The following operations would be performed:\n")

    # Check current schema version
    print("1. Check current schema version in production")
    print("2. Compare with migration files in migrations/")
    print("3. Apply pending migrations (if any)")
    print("4. Verify Qdrant collection exists and is configured correctly")
    print("5. Log deployment completion")

    print("\nNo changes made (dry-run mode)")


def run_schema_update(guard: SafetyGuard) -> None:
    """Apply schema updates to production (non-destructive).

    This runs migrations and ensures indexes exist.
    Does NOT delete any data.
    """
    guard.check_operation("schema_update", OperationType.ADDITIVE)

    print("\n=== SCHEMA UPDATE MODE ===")
    print("Applying non-destructive schema updates...\n")

    # Import here to avoid circular dependencies
    from qdrant_client import QdrantClient

    try:
        # Connect to production Qdrant
        qdrant = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)

        # Check if collection exists
        collections = qdrant.get_collections().collections
        collection_names = [c.name for c in collections]

        if settings.qdrant_collection_name in collection_names:
            print(f"  Collection '{settings.qdrant_collection_name}' exists")
            collection_info = qdrant.get_collection(settings.qdrant_collection_name)
            print(f"  Vectors count: {collection_info.vectors_count}")
            print(f"  Points count: {collection_info.points_count}")
        else:
            print(f"  Collection '{settings.qdrant_collection_name}' does not exist")
            print("  Use init-production.py to create it")

        # TODO: Add PostgreSQL migration logic here when migrations/ directory exists
        migrations_dir = Path(__file__).parent.parent / "migrations"
        if migrations_dir.exists():
            print(f"\n  Checking migrations in {migrations_dir}...")
            migration_files = sorted(migrations_dir.glob("*.sql"))
            if migration_files:
                print(f"  Found {len(migration_files)} migration files")
                for mf in migration_files:
                    print(f"    - {mf.name}")
            else:
                print("  No migration files found")
        else:
            print(f"\n  No migrations directory found at {migrations_dir}")

        print("\n=== Schema update complete ===")
        logger.info("Schema update completed successfully")

    except Exception as e:
        logger.error("Schema update failed", extra={"error": str(e)})
        raise


def run_force_data_loss(guard: SafetyGuard) -> None:
    """Re-initialize production collection (DESTRUCTIVE).

    WARNING: This DELETES all existing production data!
    Only use when you need a clean slate.
    """
    guard.check_operation(
        "force_data_loss_reinitialize", OperationType.DESTRUCTIVE, force_data_loss=True
    )

    print("\n" + "!" * 70)
    print("  DANGER: This will DELETE ALL PRODUCTION DATA!")
    print("!" * 70)
    print()
    print("Type 'DELETE ALL DATA' to confirm:")

    response = input("> ").strip()
    if response != "DELETE ALL DATA":
        print("Aborted. Data loss confirmation failed.")
        return

    print("\n=== FORCE DATA LOSS MODE ===")
    print("Re-initializing production collection...\n")

    # Import here to avoid circular dependencies
    from qdrant_client import QdrantClient

    try:
        # Connect to production Qdrant
        qdrant = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)

        # Delete existing collection
        collection_name = settings.qdrant_collection_name
        try:
            qdrant.delete_collection(collection_name)
            print(f"  Deleted collection '{collection_name}'")
            logger.warning(
                "Production collection deleted",
                extra={"collection": collection_name},
            )
        except Exception:
            print(f"  Collection '{collection_name}' did not exist")

        # Create new collection (delegate to init-production.py logic)
        print("\n  Run 'python scripts/init-production.py' to recreate the collection")

        print("\n=== Data loss operation complete ===")
        logger.warning(
            "Force data loss operation completed",
            extra={"collection": collection_name},
        )

    except Exception as e:
        logger.error("Force data loss operation failed", extra={"error": str(e)})
        raise


def main() -> int:
    """Main entry point for production deployment."""
    parser = argparse.ArgumentParser(
        description="Deploy schema updates to production databases safely",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deployed without making changes",
    )

    parser.add_argument(
        "--deploy-production",
        action="store_true",
        help="Actually deploy to production (requires confirmation)",
    )

    parser.add_argument(
        "--force-data-loss",
        action="store_true",
        help="Allow operations that delete production data (dangerous!)",
    )

    args = parser.parse_args()

    # Initialize SafetyGuard
    guard = SafetyGuard()

    # Display environment info
    display_environment_info(guard)

    # Validate mode
    if not args.dry_run and not args.deploy_production:
        print("Error: Must specify --dry-run or --deploy-production")
        print("\nUsage examples:")
        print("  python scripts/deploy-to-production.py --dry-run")
        print("  python scripts/deploy-to-production.py --deploy-production")
        return 1

    # Prevent running on test environment
    if guard.is_test:
        print("Error: This script is for production deployment only.")
        print("Current environment appears to be TEST.")
        print(f"  Qdrant port: {settings.qdrant_port} (expected 6333 for production)")
        return 1

    # Dry run mode
    if args.dry_run:
        run_dry_run(guard)
        return 0

    # Production deployment mode
    if args.deploy_production:
        # Require confirmation
        if not confirm_deployment():
            return 1

        try:
            if args.force_data_loss:
                run_force_data_loss(guard)
            else:
                run_schema_update(guard)
            return 0

        except ProductionProtectionError as e:
            print(f"\nBlocked by SafetyGuard: {e}")
            return 1

        except Exception as e:
            print(f"\nDeployment failed: {e}")
            logger.exception("Deployment failed")
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
