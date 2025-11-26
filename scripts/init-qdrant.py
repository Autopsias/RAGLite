"""Initialize Qdrant vector database collection for financial document storage.

This script creates the financial_docs collection with dense + sparse vector configuration
for hybrid search (semantic + BM25) retrieval. Idempotent - safe to run multiple times.

Usage:
    python scripts/init-qdrant.py
"""

import logging
import sys
from pathlib import Path

# Add parent directory to path to import raglite modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from qdrant_client.models import Distance  # noqa: E402

from raglite.ingestion.storage_operations import create_collection  # noqa: E402
from raglite.shared.config import settings  # noqa: E402
from raglite.shared.safety import SafetyGuard  # noqa: E402

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def initialize_qdrant_collection() -> None:
    """Initialize Qdrant collection with hybrid search configuration.

    Creates financial_docs collection if it doesn't exist:
    - Dense vectors: 1024 dimensions (Fin-E5 embeddings)
    - Sparse vectors: BM25 keyword search
    - Distance metric: COSINE (for semantic similarity)
    - Indexing: HNSW (default, O(log n) search)

    Raises:
        SystemExit: If initialization fails
    """
    # Story 4.0.6 AC4: Display environment banner before database modifications
    guard = SafetyGuard()
    guard.display_environment_banner()

    try:
        logger.info("=" * 60)
        logger.info("QDRANT COLLECTION INITIALIZATION")
        logger.info("=" * 60)

        logger.info(f"Connecting to Qdrant at {settings.qdrant_host}:{settings.qdrant_port}")
        logger.info(f"Target collection: {settings.qdrant_collection_name}")

        # Create collection (idempotent - safe to call multiple times)
        create_collection(
            collection_name=settings.qdrant_collection_name,
            vector_size=settings.embedding_dimension,
            distance=Distance.COSINE,
        )

        logger.info("✅ Qdrant collection initialization complete!")
        logger.info(f"   - Collection: {settings.qdrant_collection_name}")
        logger.info(f"   - Dense vectors: {settings.embedding_dimension}d (COSINE)")
        logger.info("   - Sparse vectors: BM25 (enabled)")
        logger.info("   - Indexing: HNSW (optimal defaults)")

    except Exception as e:
        logger.error(f"❌ Qdrant initialization failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    initialize_qdrant_collection()
