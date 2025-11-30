#!/usr/bin/env python3
"""Import Qdrant collection data from cached export.

Restores points from JSON files exported by export-qdrant-snapshot.py,
allowing CI to skip PDF ingestion when data hasn't changed.

Usage:
    python scripts/import-qdrant-snapshot.py --input .qdrant-export
"""

import argparse
import json
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from qdrant_client import QdrantClient  # noqa: E402
from qdrant_client.models import Distance, PointStruct, SparseVector, VectorParams  # noqa: E402

from raglite.shared.config import settings  # noqa: E402

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def import_qdrant_data(input_dir: Path) -> None:
    """Import Qdrant collection data from JSON files.

    Args:
        input_dir: Directory containing export files
    """
    if not input_dir.exists():
        logger.error(f"Input directory not found: {input_dir}")
        sys.exit(1)

    # Check for empty collection marker
    if (input_dir / "empty_collection").exists():
        logger.info("Cache indicates empty collection, nothing to import")
        return

    points_file = input_dir / "points.json"
    if not points_file.exists():
        logger.error(f"Points file not found: {points_file}")
        sys.exit(1)

    logger.info(f"Loading points from {points_file}")
    with open(points_file) as f:
        data = json.load(f)

    collection_name = data["collection_name"]
    points_data = data["points"]
    total_points = len(points_data)

    logger.info(f"Found {total_points} points to import for collection '{collection_name}'")

    if total_points == 0:
        logger.info("No points to import")
        return

    logger.info(f"Connecting to Qdrant at {settings.qdrant_host}:{settings.qdrant_port}")
    client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)

    # Recreate collection with proper config
    try:
        client.delete_collection(collection_name)
        logger.info(f"Deleted existing collection '{collection_name}'")
    except Exception:
        pass  # Collection didn't exist

    # Determine vector configuration from first point
    first_point = points_data[0]
    vectors_config = {}

    if "dense" in first_point.get("vector", {}):
        dense_vec = first_point["vector"]["dense"]
        vectors_config["dense"] = VectorParams(
            size=len(dense_vec),
            distance=Distance.COSINE,
        )

    # Create collection
    from qdrant_client.models import SparseVectorParams

    sparse_vectors_config = {}
    if "sparse" in first_point.get("vector", {}):
        sparse_vectors_config["sparse"] = SparseVectorParams()

    client.create_collection(
        collection_name=collection_name,
        vectors_config=vectors_config
        if vectors_config
        else VectorParams(
            size=settings.embedding_dimension,
            distance=Distance.COSINE,
        ),
        sparse_vectors_config=sparse_vectors_config if sparse_vectors_config else None,
    )
    logger.info(f"Created collection '{collection_name}'")

    # Import points in batches
    batch_size = 100
    for i in range(0, total_points, batch_size):
        batch = points_data[i : i + batch_size]
        points = []

        for point_data in batch:
            # Reconstruct vectors
            vectors = {}
            for name, vec in point_data.get("vector", {}).items():
                if isinstance(vec, dict) and "indices" in vec:
                    # Sparse vector
                    vectors[name] = SparseVector(
                        indices=vec["indices"],
                        values=vec["values"],
                    )
                else:
                    # Dense vector
                    vectors[name] = vec

            points.append(
                PointStruct(
                    id=point_data["id"],
                    vector=vectors if vectors else None,
                    payload=point_data.get("payload", {}),
                )
            )

        client.upsert(collection_name=collection_name, points=points)
        logger.info(f"  Imported {min(i + batch_size, total_points)}/{total_points} points...")

    # Verify import
    collection_info = client.get_collection(collection_name)
    logger.info(f"✅ Import complete: {collection_info.points_count} points in collection")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Import Qdrant collection from cache")
    parser.add_argument(
        "--input",
        type=str,
        default=".qdrant-export",
        help="Input directory containing export files",
    )
    args = parser.parse_args()

    input_dir = Path(args.input)

    try:
        import_qdrant_data(input_dir)
        return 0
    except Exception as e:
        logger.error(f"Import failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
