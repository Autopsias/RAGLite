#!/usr/bin/env python3
"""Clean production database and ingest documents with verification.

This script safely cleans the production database and ingests documents
one by one with verification steps.

**IMPORTANT:** This script requires typed confirmation for destructive operations.
You must type the exact phrase "DELETE ALL FINANCIAL DOCUMENTS, TABLES, AND
VECTOR EMBEDDINGS FROM PRODUCTION" to proceed with cleanup.

Usage:
    python scripts/cleanup-and-reingest.py /path/to/folder --first-only
    python scripts/cleanup-and-reingest.py /path/to/folder --continue-from=2
"""

import asyncio
import os
import sys
import time
from pathlib import Path

# Ensure production environment
os.environ["APP_ENV"] = "production"

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from qdrant_client import QdrantClient
from qdrant_client.models import Distance

from raglite.ingestion.document_ingestion import ingest_document
from raglite.ingestion.storage import create_collection
from raglite.shared.config import settings
from raglite.shared.logging import get_logger
from raglite.shared.safety import OperationType, SafetyGuard

logger = get_logger(__name__)


def cleanup_production_database(guard: SafetyGuard) -> bool:
    """Clean production database (DESTRUCTIVE).

    Returns:
        True if successful, False otherwise
    """
    # Require typed confirmation for destructive operation
    guard.require_typed_confirmation(
        "cleanup_production", "financial documents, tables, and vector embeddings"
    )

    # Check if operation is allowed (after typed confirmation)
    guard.check_operation("cleanup_production", OperationType.DESTRUCTIVE, force_data_loss=True)

    try:
        # Connect to production Qdrant
        _qdrant = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)

        # Delete existing collection
        collection_name = settings.qdrant_collection_name
        try:
            _qdrant.delete_collection(collection_name)
            print(f"  ✅ Deleted collection '{collection_name}'")
            logger.warning(
                "Production collection deleted",
                extra={"collection": collection_name},
            )
        except Exception:
            print(f"  ℹ️  Collection '{collection_name}' did not exist")

        # Also clean PostgreSQL (if tables exist)
        import psycopg2

        conn = psycopg2.connect(
            host=settings.postgres_host,
            port=settings.postgres_port,
            dbname=settings.postgres_db,
            user=settings.postgres_user,
            password=settings.postgres_password,
        )
        cursor = conn.cursor()

        # Check if actual tables exist (financial_chunks and financial_tables)
        cursor.execute(
            """
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name IN ('financial_chunks', 'financial_tables')
        """
        )
        existing_tables = [row[0] for row in cursor.fetchall()]

        if existing_tables:
            # Delete all data from actual tables used by the ingestion pipeline
            if "financial_tables" in existing_tables:
                cursor.execute("DELETE FROM financial_tables")
                print("  ✅ Cleaned financial_tables")
            if "financial_chunks" in existing_tables:
                cursor.execute("DELETE FROM financial_chunks")
                print("  ✅ Cleaned financial_chunks")
            conn.commit()
        else:
            print("  ℹ️  PostgreSQL tables do not exist yet (will be created during ingestion)")

        conn.close()

        return True

    except Exception as e:
        logger.error("Cleanup failed", extra={"error": str(e)})
        print(f"  ❌ ERROR: {e}")
        return False


def initialize_production(guard: SafetyGuard) -> bool:
    """Initialize production databases.

    Returns:
        True if successful, False otherwise
    """
    print("\n--- Initializing Production Databases ---")

    guard.check_operation("initialize_production", OperationType.ADDITIVE)

    try:
        # Create Qdrant collection
        _qdrant = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)

        print(f"  Creating Qdrant collection '{settings.qdrant_collection_name}'...")
        create_collection(
            collection_name=settings.qdrant_collection_name,
            vector_size=settings.embedding_dimension,
            distance=Distance.COSINE,
        )
        print("  ✅ Qdrant collection created successfully")

        # Create PostgreSQL tables
        import psycopg2

        print("  Creating PostgreSQL tables...")
        conn = psycopg2.connect(
            host=settings.postgres_host,
            port=settings.postgres_port,
            dbname=settings.postgres_db,
            user=settings.postgres_user,
            password=settings.postgres_password,
        )
        cursor = conn.cursor()

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

        conn.commit()
        conn.close()
        print("  ✅ PostgreSQL tables created successfully")

        return True

    except Exception as e:
        logger.error("Initialization failed", extra={"error": str(e)})
        print(f"  ❌ ERROR: {e}")
        return False


async def ingest_single_document(doc_path: Path, index: int, total: int) -> bool:
    """Ingest a single document and display results.

    Returns:
        True if successful, False otherwise
    """
    print(f"\n[{index}/{total}] Ingesting: {doc_path.name}")
    print("-" * 60)
    sys.stdout.flush()
    start_time = time.time()

    try:
        metadata = await ingest_document(str(doc_path))
        elapsed = time.time() - start_time

        print(f"✅ SUCCESS in {elapsed:.1f}s")
        print(f"   Filename: {metadata.filename}")
        print(f"   Pages: {metadata.page_count}")
        print(f"   Chunks: {metadata.chunk_count}")
        sys.stdout.flush()

        return True

    except Exception as e:
        elapsed = time.time() - start_time
        print(f"❌ FAILED after {elapsed:.1f}s: {str(e)}")
        import traceback

        traceback.print_exc()
        sys.stdout.flush()
        return False


def verify_ingestion(guard: SafetyGuard) -> None:
    """Verify that data was properly ingested."""
    print("\n--- Verification ---")

    try:
        # Check Qdrant
        _qdrant = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
        collection_info = _qdrant.get_collection(settings.qdrant_collection_name)

        print(f"  Qdrant Collection '{settings.qdrant_collection_name}':")
        print(f"    Vectors count: {collection_info.vectors_count}")
        print(f"    Points count: {collection_info.points_count}")

        # Check PostgreSQL
        import psycopg2

        conn = psycopg2.connect(
            host=settings.postgres_host,
            port=settings.postgres_port,
            dbname=settings.postgres_db,
            user=settings.postgres_user,
            password=settings.postgres_password,
        )
        cursor = conn.cursor()

        # Check the actual tables used by the ingestion pipeline
        cursor.execute(
            """
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name IN ('financial_chunks', 'financial_tables')
        """
        )
        existing_tables = [row[0] for row in cursor.fetchall()]

        print("  PostgreSQL:")

        if "financial_chunks" in existing_tables:
            cursor.execute("SELECT COUNT(*) FROM financial_chunks")
            chunk_metadata_count = cursor.fetchone()[0]
            print(f"    Financial Chunks (metadata): {chunk_metadata_count}")
        else:
            print("    Financial Chunks: Table does not exist")

        if "financial_tables" in existing_tables:
            cursor.execute("SELECT COUNT(*) FROM financial_tables")
            table_rows_count = cursor.fetchone()[0]
            print(f"    Financial Tables (structured data): {table_rows_count}")
        else:
            print("    Financial Tables: Table does not exist")

        conn.close()

    except Exception as e:
        print(f"  ⚠️  Verification error: {e}")


async def main() -> int:
    """Main entry point."""
    if len(sys.argv) < 2:
        print(
            "Usage: python scripts/cleanup-and-reingest.py /path/to/folder [--first-only] [--continue-from=N]"
        )
        return 1

    folder_path = sys.argv[1]
    first_only = "--first-only" in sys.argv
    continue_from = 1

    for arg in sys.argv:
        if arg.startswith("--continue-from="):
            continue_from = int(arg.split("=")[1])

    folder = Path(folder_path)

    if not folder.exists():
        print(f"❌ Folder not found: {folder_path}")
        return 1

    # Find all PDF files
    pdf_files = sorted(folder.glob("*.pdf"))

    if not pdf_files:
        print(f"❌ No PDF files found in: {folder_path}")
        return 1

    print(f"\n📂 Found {len(pdf_files)} PDF files:")
    for i, pdf in enumerate(pdf_files, 1):
        print(f"   {i}. {pdf.name}")

    # Initialize SafetyGuard
    guard = SafetyGuard()
    guard.display_environment_banner()

    # Cleanup and initialize if starting fresh
    if continue_from == 1:
        print("\n" + "=" * 70)
        print("STEP 1: CLEANUP")
        print("=" * 70)

        if not cleanup_production_database(guard):
            print("\n❌ Cleanup failed!")
            return 1

        print("\n" + "=" * 70)
        print("STEP 2: INITIALIZE")
        print("=" * 70)

        if not initialize_production(guard):
            print("\n❌ Initialization failed!")
            return 1

    # Ingest documents
    print("\n" + "=" * 70)
    print("STEP 3: INGESTION")
    print("=" * 70)

    if first_only:
        # Ingest only the first document
        success = await ingest_single_document(pdf_files[0], 1, len(pdf_files))

        if success:
            verify_ingestion(guard)
            print("\n" + "=" * 70)
            print("✅ First document ingested successfully!")
            print("=" * 70)
            print(f"\nTo continue with remaining {len(pdf_files) - 1} documents, run:")
            print(f"  python scripts/cleanup-and-reingest.py '{folder_path}' --continue-from=2")
            return 0
        else:
            return 1
    else:
        # Ingest from continue_from to end
        successful = 0
        failed = 0

        for i in range(continue_from - 1, len(pdf_files)):
            success = await ingest_single_document(pdf_files[i], i + 1, len(pdf_files))
            if success:
                successful += 1
            else:
                failed += 1

        verify_ingestion(guard)

        print("\n" + "=" * 70)
        print("📊 FINAL SUMMARY")
        print("=" * 70)
        print(f"  Total files processed: {successful + failed}")
        print(f"  Successful: {successful}")
        print(f"  Failed: {failed}")

        return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
