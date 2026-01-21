#!/usr/bin/env python
"""Initialize Qdrant collection for CI tests (runs ONCE before pytest).

This script runs BEFORE pytest to ensure the Qdrant collection exists.
It solves the xdist race condition where multiple workers try to access
a collection that doesn't exist yet because session fixtures run per-worker.

Usage (CI workflow):
    uv run python scripts/init-ci-qdrant.py

Environment Variables:
    CI - Must be "true" to run (safety check)
    QDRANT_HOST - Qdrant server host (default: localhost)
    QDRANT_PORT - Qdrant server port (default: 6335)
    QDRANT_COLLECTION - Collection name (default: financial_docs_ci)
    CI_FAST_EMBEDDING - If "true", use MiniLM dimensions (384) vs Fin-E5 (1024)

Exit Codes:
    0 - Success
    1 - Error (not in CI or Qdrant unavailable)
"""

import os
import sys
import time


def main() -> int:
    """Initialize Qdrant collection for CI tests.

    Returns:
        0 on success, 1 on error
    """
    # Safety check: Only run in CI environments
    if os.getenv("CI") != "true":
        print("⏭️  Not in CI environment (CI != 'true'), skipping collection init")
        return 0

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

    print("=" * 60)
    print("✅ CI Qdrant collection ready for pytest!")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
