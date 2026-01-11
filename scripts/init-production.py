#!/usr/bin/env python3
"""Initialize production databases with safety controls.

Story 4.0.7: Three-Mode Database Operation System

This script initializes production Qdrant and PostgreSQL with proper safety checks.
Unlike init-qdrant.py (which can run on either env), this script:
1. ONLY runs on production infrastructure
2. Requires explicit confirmation
3. Never deletes existing data (use deploy-to-production.py --force-data-loss for that)

Usage:
    # Initialize production collection (CREATE IF NOT EXISTS only)
    python scripts/init-production.py

    # Dry-run: Show what would be created
    python scripts/init-production.py --dry-run
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


def display_environment_info(guard: SafetyGuard) -> None:
    """Display current environment information."""
    guard.display_environment_banner()
    print(f"Target Collection: {settings.qdrant_collection_name}")
    print(f"PostgreSQL DB: {settings.postgres_db}")
    print(f"Embedding Dimension: {settings.embedding_dimension}")
    print()


def confirm_production_init() -> bool:
    """Require explicit confirmation for production initialization.

    Returns:
        True if user confirms, False otherwise
    """
    print("\n" + "=" * 60)
    print("  PRODUCTION DATABASE INITIALIZATION")
    print("=" * 60)
    print()
    print("This will create production database resources if they don't exist.")
    print("Existing data will NOT be deleted.")
    print()
    print("Type 'INIT PRODUCTION' to confirm:")

    response = input("> ").strip()

    if response == "INIT PRODUCTION":
        logger.info("Production initialization confirmed by user")
        return True
    else:
        logger.warning(
            "Confirmation failed",
            extra={"expected": "INIT PRODUCTION", "received": response},
        )
        print("\nConfirmation failed.")
        return False


def run_dry_run(guard: SafetyGuard) -> None:
    """Show what would be initialized without making changes."""
    print("\n=== DRY RUN MODE ===")
    print("The following resources would be checked/created:\n")

    print(f"1. Qdrant Collection: {settings.qdrant_collection_name}")
    print(f"   - Host: {settings.qdrant_host}:{settings.qdrant_port}")
    print(f"   - Dense vectors: {settings.embedding_dimension}d (COSINE)")
    print("   - Sparse vectors: BM25 (enabled)")
    print()

    print(f"2. PostgreSQL Database: {settings.postgres_db}")
    print(f"   - Host: {settings.postgres_host}:{settings.postgres_port}")
    print("   - Tables: documents, document_chunks")
    print()

    print("No changes made (dry-run mode)")


def initialize_qdrant_production(guard: SafetyGuard) -> bool:
    """Initialize Qdrant collection for production.

    Returns:
        True if successful, False otherwise
    """
    guard.check_operation("qdrant_init", OperationType.ADDITIVE)

    print("\n--- Initializing Qdrant Collection ---")

    try:
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance

        from raglite.ingestion.storage import create_collection

        # Connect to production Qdrant
        qdrant = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)

        # Check if collection already exists
        collections = qdrant.get_collections().collections
        collection_names = [c.name for c in collections]

        if settings.qdrant_collection_name in collection_names:
            collection_info = qdrant.get_collection(settings.qdrant_collection_name)
            print(f"  Collection '{settings.qdrant_collection_name}' already exists")
            print(f"  Current vectors count: {collection_info.vectors_count}")
            print(f"  Current points count: {collection_info.points_count}")
            print("  Skipping creation (no changes needed)")
            return True

        # Create new collection
        print(f"  Creating collection '{settings.qdrant_collection_name}'...")
        create_collection(
            collection_name=settings.qdrant_collection_name,
            vector_size=settings.embedding_dimension,
            distance=Distance.COSINE,
        )
        print(f"  Collection '{settings.qdrant_collection_name}' created successfully")
        logger.info(
            "Production Qdrant collection created",
            extra={"collection": settings.qdrant_collection_name},
        )
        return True

    except Exception as e:
        logger.error("Qdrant initialization failed", extra={"error": str(e)})
        print(f"  ERROR: {e}")
        return False


def initialize_postgresql_production(guard: SafetyGuard) -> bool:
    """Initialize PostgreSQL tables for production.

    Returns:
        True if successful, False otherwise
    """
    guard.check_operation("postgresql_init", OperationType.ADDITIVE)

    print("\n--- Initializing PostgreSQL Tables ---")

    try:
        import psycopg2

        # Connect to production PostgreSQL
        conn = psycopg2.connect(
            host=settings.postgres_host,
            port=settings.postgres_port,
            dbname=settings.postgres_db,
            user=settings.postgres_user,
            password=settings.postgres_password,
        )
        cursor = conn.cursor()

        # Check if tables exist
        cursor.execute(
            """
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name IN ('documents', 'document_chunks')
        """
        )
        existing_tables = [row[0] for row in cursor.fetchall()]

        if "documents" in existing_tables and "document_chunks" in existing_tables:
            # Count rows
            cursor.execute("SELECT COUNT(*) FROM documents")
            doc_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM document_chunks")
            chunk_count = cursor.fetchone()[0]

            print("  Tables already exist:")
            print(f"    - documents: {doc_count} rows")
            print(f"    - document_chunks: {chunk_count} rows")
            print("  Skipping creation (no changes needed)")
            conn.close()
            return True

        # Create tables if they don't exist
        print("  Creating tables...")

        # Documents table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                file_path TEXT,
                file_hash TEXT,
                total_pages INTEGER,
                total_chunks INTEGER,
                ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata JSONB DEFAULT '{}'::jsonb
            )
        """
        )
        print("    - documents table created")

        # Document chunks table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS document_chunks (
                id TEXT PRIMARY KEY,
                document_id TEXT REFERENCES documents(id) ON DELETE CASCADE,
                chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL,
                page_numbers INTEGER[],
                section_type TEXT,
                metadata JSONB DEFAULT '{}'::jsonb,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )
        print("    - document_chunks table created")

        # Create indexes
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON document_chunks(document_id)
        """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_documents_filename ON documents(filename)
        """
        )
        print("    - indexes created")

        conn.commit()
        conn.close()

        logger.info("Production PostgreSQL tables created")
        return True

    except Exception as e:
        logger.error("PostgreSQL initialization failed", extra={"error": str(e)})
        print(f"  ERROR: {e}")
        return False


def main() -> int:
    """Main entry point for production initialization."""
    parser = argparse.ArgumentParser(
        description="Initialize production databases safely",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be created without making changes",
    )

    args = parser.parse_args()

    # Initialize SafetyGuard
    guard = SafetyGuard()

    # Display environment info
    display_environment_info(guard)

    # Validate we're on production
    if guard.is_test:
        print("Error: This script is for production initialization only.")
        print("Current environment appears to be TEST.")
        print(f"  Qdrant port: {settings.qdrant_port} (expected 6333 for production)")
        print()
        print("For test environment, use:")
        print("  python scripts/init-qdrant.py  (with APP_ENV=test)")
        return 1

    # Dry run mode
    if args.dry_run:
        run_dry_run(guard)
        return 0

    # Production initialization
    if not confirm_production_init():
        return 1

    print("\n=== INITIALIZING PRODUCTION DATABASES ===")

    try:
        # Initialize Qdrant
        qdrant_ok = initialize_qdrant_production(guard)

        # Initialize PostgreSQL
        postgres_ok = initialize_postgresql_production(guard)

        # Summary
        print("\n=== INITIALIZATION SUMMARY ===")
        print(f"  Qdrant: {'OK' if qdrant_ok else 'FAILED'}")
        print(f"  PostgreSQL: {'OK' if postgres_ok else 'FAILED'}")

        if qdrant_ok and postgres_ok:
            print("\n Production databases initialized successfully!")
            logger.info("Production initialization completed successfully")
            return 0
        else:
            print("\n Some initializations failed. Check logs for details.")
            return 1

    except ProductionProtectionError as e:
        print(f"\nBlocked by SafetyGuard: {e}")
        return 1

    except Exception as e:
        print(f"\nInitialization failed: {e}")
        logger.exception("Production initialization failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
