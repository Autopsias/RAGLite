#!/usr/bin/env python3
"""
Ingest test data for VS Code Test Explorer rapid iteration.

This script ingests the 4-page test PDF into Qdrant and PostgreSQL databases,
allowing tests to run with --skip-ingestion flag for 98% speedup.

Usage:
    python scripts/ingest-test-data.py

Expected runtime: ~10 seconds (vs 2638s full test suite with repeated ingestion)

After running this script once:
1. Uncomment "--skip-ingestion" in .vscode/settings.json
2. Reload VS Code window (Cmd+Shift+P → "Developer: Reload Window")
3. Run tests via Test Explorer → completes in ~1 minute instead of 44 minutes
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# CRITICAL: Set test environment BEFORE any raglite imports
os.environ["APP_ENV"] = "test"
os.environ["TESTING"] = "true"


async def main():
    """Ingest test PDF data for rapid test iteration."""
    print("\n" + "=" * 80)
    print("TEST DATA INGESTION - For VS Code Test Explorer Rapid Iteration")
    print("=" * 80)
    print("\nThis will ingest the 4-page test PDF into test databases:")
    print("  • Qdrant: localhost:6335 (collection: financial_docs_test)")
    print("  • PostgreSQL: localhost:5433 (database: raglite_test)")
    print("\nExpected runtime: ~10 seconds")
    print("=" * 80 + "\n")

    # Import after environment setup
    from raglite.ingestion.pipeline import create_collection, ingest_pdf
    from raglite.shared.clients import get_qdrant_client
    from raglite.shared.config import settings

    # Verify test environment configuration
    print("✓ Configuration verified:")
    print(f"  • APP_ENV: {settings.app_env}")
    print(f"  • Qdrant: {settings.qdrant_host}:{settings.qdrant_port}")
    print(f"  • Collection: {settings.qdrant_collection_name}")
    print(
        f"  • PostgreSQL: {settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
    )
    print()

    # Check if test PDF exists
    test_pdf = project_root / "tests/fixtures/sample-small-3-pages.pdf"
    if not test_pdf.exists():
        print(f"❌ ERROR: Test PDF not found at {test_pdf}")
        print("\nPlease ensure the test PDF exists before running this script.")
        sys.exit(1)

    print(f"✓ Test PDF found: {test_pdf.name} ({test_pdf.stat().st_size / 1024:.1f} KB)")
    print()

    # Get Qdrant client
    qdrant = get_qdrant_client()

    # Clear existing test data
    print("⚙️  Preparing test databases...")
    try:
        qdrant.delete_collection(collection_name=settings.qdrant_collection_name)
        print(f"  ✓ Cleared existing Qdrant collection: {settings.qdrant_collection_name}")
    except Exception as e:
        print(f"  ℹ️  No existing collection to clear: {e}")

    # Clear PostgreSQL
    try:
        import psycopg2

        conn_str = f"postgresql://{settings.postgres_user}:{settings.postgres_password}@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
        conn = psycopg2.connect(conn_str)
        conn.autocommit = True
        cursor = conn.cursor()

        cursor.execute("DELETE FROM financial_chunks")
        chunks_deleted = cursor.rowcount
        cursor.execute("DELETE FROM financial_tables")
        tables_deleted = cursor.rowcount

        print(f"  ✓ Cleared PostgreSQL: {tables_deleted} table rows, {chunks_deleted} chunk rows")

        cursor.close()
        conn.close()
    except Exception as e:
        print(f"  ⚠️  PostgreSQL cleanup failed (non-critical): {e}")

    # Create fresh collection
    create_collection(
        collection_name=settings.qdrant_collection_name,
        vector_size=settings.embedding_dimension,
    )
    print(f"  ✓ Created fresh collection: {settings.qdrant_collection_name}")
    print()

    # Ingest test PDF
    print(f"⚙️  Ingesting {test_pdf.name}...")
    print("  This will take ~10 seconds (Docling + embeddings + Qdrant)...")

    import time

    start_time = time.time()

    result = await ingest_pdf(
        str(test_pdf),
        clear_collection=False,  # Collection already fresh
        skip_metadata=True,  # Skip expensive LLM metadata extraction for speed
    )

    duration = time.time() - start_time

    # Verify ingestion
    count = qdrant.count(collection_name=settings.qdrant_collection_name).count

    print()
    print("✅ TEST DATA INGESTION COMPLETE")
    print(f"  • PDF: {result.filename} ({result.page_count} pages)")
    print(f"  • Chunks: {count}")
    print(f"  • Duration: {duration:.1f}s")
    print()

    # Verify PostgreSQL population
    try:
        conn = psycopg2.connect(conn_str)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM financial_tables")
        pg_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM financial_chunks")
        chunk_count = cursor.fetchone()[0]

        print(f"  • PostgreSQL: {pg_count} table rows, {chunk_count} chunk rows")

        cursor.close()
        conn.close()
    except Exception as e:
        print(f"  ⚠️  PostgreSQL verification failed: {e}")

    print()
    print("=" * 80)
    print("NEXT STEPS - Enable Skip-Ingestion Mode for 98% Speedup")
    print("=" * 80)
    print("\n1. Open .vscode/settings.json")
    print('2. Uncomment the line: // "--skip-ingestion"')
    print("3. Reload VS Code window: Cmd+Shift+P → 'Developer: Reload Window'")
    print("4. Run tests via Test Explorer → completes in ~1 minute!")
    print()
    print("To re-ingest test data later (if tests change):")
    print("  python scripts/ingest-test-data.py")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
