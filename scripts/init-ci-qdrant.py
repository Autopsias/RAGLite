#!/usr/bin/env python
"""Initialize Qdrant collection for CI tests (runs ONCE before pytest).

This script runs BEFORE pytest to ensure the Qdrant collection exists
AND is pre-populated with test data, enabling --skip-ingestion mode.

This solves:
1. xdist race condition where multiple workers try to access a non-existent collection
2. Session fixture overhead: embedding model load (60s) + PDF ingestion happens per-worker
   With pre-ingested data, workers skip embedding model loading entirely.

Usage (CI workflow):
    uv run python scripts/init-ci-qdrant.py

Environment Variables:
    CI - Must be "true" to run (safety check)
    QDRANT_HOST - Qdrant server host (default: localhost)
    QDRANT_PORT - Qdrant server port (default: 6335)
    QDRANT_COLLECTION - Collection name (default: financial_docs_ci)
    CI_FAST_EMBEDDING - If "true", use MiniLM dimensions (384) vs Fin-E5 (1024)
    APP_ENV - Must be "test" for safety (set automatically)

Exit Codes:
    0 - Success
    1 - Error (not in CI or Qdrant unavailable)
"""

import asyncio
import os
import sys
import time
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# CI test PDF paths (smallest for fastest CI)
TEST_PDF_3_PAGE = Path(__file__).parent.parent / "tests/fixtures/sample-small-3-pages.pdf"


async def ingest_test_data(collection: str, host: str, port: int) -> bool:
    """Ingest test PDF to pre-populate the collection.

    Args:
        collection: Qdrant collection name
        host: Qdrant host
        port: Qdrant port

    Returns:
        True if successful, False otherwise
    """
    if not TEST_PDF_3_PAGE.exists():
        print(f"⚠️  Test PDF not found: {TEST_PDF_3_PAGE}")
        print("   Collection will be empty (tests will run slower without --skip-ingestion)")
        return False

    try:
        # Import ingestion pipeline (deferred to avoid import errors if not in CI)
        from raglite.ingestion.pipeline import ingest_pdf

        print(f"📄 Ingesting test PDF: {TEST_PDF_3_PAGE.name}")
        start_time = time.time()

        result = await ingest_pdf(
            str(TEST_PDF_3_PAGE),
            clear_existing=False,  # Collection already created with correct config
            skip_metadata=True,  # Skip LLM metadata extraction for speed
        )

        duration = time.time() - start_time
        print(f"✅ Ingested {result.chunk_count} chunks in {duration:.1f}s")
        return True

    except Exception as e:
        print(f"⚠️  Ingestion failed: {e}")
        print("   Collection will be empty (tests will run slower without --skip-ingestion)")
        return False


def main() -> int:
    """Initialize Qdrant collection for CI tests.

    Returns:
        0 on success, 1 on error
    """
    # Safety check: Only run in CI environments
    if os.getenv("CI") != "true":
        print("⏭️  Not in CI environment (CI != 'true'), skipping collection init")
        return 0

    # Force test environment for safety
    os.environ["APP_ENV"] = "test"

    # Import Qdrant client (deferred to avoid import errors if not in CI)
    try:
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, VectorParams
    except ImportError as e:
        print(f"❌ Failed to import qdrant_client: {e}", file=sys.stderr)
        return 1

    # Configuration from environment
    host = os.getenv("QDRANT_HOST", "localhost")
    port = int(os.getenv("QDRANT_PORT", "6335"))
    collection = os.getenv("QDRANT_COLLECTION", "financial_docs_ci")

    # Determine vector dimensions based on embedding model
    # MiniLM: 384 dimensions (CI fast mode)
    # Fin-E5: 1024 dimensions (production)
    ci_fast = os.getenv("CI_FAST_EMBEDDING", "").lower() == "true"
    dimensions = 384 if ci_fast else 1024

    print("=" * 60)
    print("🔧 CI Qdrant Collection Initialization")
    print("=" * 60)
    print(f"   Host: {host}:{port}")
    print(f"   Collection: {collection}")
    print(f"   Dimensions: {dimensions} ({'MiniLM' if ci_fast else 'Fin-E5'})")
    print("=" * 60)

    # Connect to Qdrant with retries
    client = None
    max_retries = 6
    for attempt in range(1, max_retries + 1):
        try:
            client = QdrantClient(host=host, port=port, timeout=10)
            # Verify connection
            client.get_collections()
            print(f"✅ Connected to Qdrant (attempt {attempt}/{max_retries})")
            break
        except Exception as e:
            print(f"⏳ Qdrant not ready (attempt {attempt}/{max_retries}): {e}")
            if attempt < max_retries:
                time.sleep(5)
            else:
                print(
                    f"❌ Failed to connect to Qdrant after {max_retries} attempts", file=sys.stderr
                )
                return 1

    if client is None:
        print("❌ Client initialization failed", file=sys.stderr)
        return 1

    # Delete existing collection if it exists
    try:
        existing_collections = [c.name for c in client.get_collections().collections]
        if collection in existing_collections:
            client.delete_collection(collection)
            print(f"🗑️  Deleted existing collection: {collection}")
            # Wait for deletion to propagate
            time.sleep(0.5)
    except Exception as e:
        print(f"⚠️  Could not delete existing collection (may not exist): {e}")

    # Create fresh collection with NAMED vector (text-dense)
    # Must match raglite/ingestion/storage/vector_store.py line 109
    try:
        client.create_collection(
            collection_name=collection,
            vectors_config={
                "text-dense": VectorParams(size=dimensions, distance=Distance.COSINE),
            },
        )
        print(f"✅ Created collection: {collection} (vector: text-dense)")

        # Verify collection exists
        info = client.get_collection(collection)
        print(f"✅ Verified collection: {info.points_count} points, {info.vectors_count} vectors")

    except Exception as e:
        print(f"❌ Failed to create collection: {e}", file=sys.stderr)
        return 1

    # Step 2: Ingest test PDF to enable --skip-ingestion mode
    print("-" * 60)
    print("📥 Ingesting test data for --skip-ingestion mode")
    print("-" * 60)

    ingestion_success = asyncio.run(ingest_test_data(collection, host, port))

    # Verify final collection state
    try:
        info = client.get_collection(collection)
        print(f"📊 Final collection state: {info.points_count} points")
    except Exception as e:
        print(f"⚠️  Could not verify collection: {e}")

    print("=" * 60)
    if ingestion_success:
        print("✅ CI Qdrant collection ready with test data!")
        print("   Tests can use --skip-ingestion for faster execution")
    else:
        print("✅ CI Qdrant collection ready (empty)")
        print("   Tests will run slower (ingestion per session)")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
