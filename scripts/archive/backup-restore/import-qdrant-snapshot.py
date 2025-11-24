"""Import Qdrant snapshot from CI cache.

This script restores a Qdrant collection from a previously exported snapshot,
allowing CI runs to skip the 25-minute ingestion process.

Usage:
    python scripts/import-qdrant-snapshot.py

    # Custom input directory
    python scripts/import-qdrant-snapshot.py --input .qdrant-export

The script will:
1. Create the collection (if needed)
2. Import all vectors and payloads
3. Verify the import succeeded

Expected time: ~30-60 seconds (vs 25 minutes for full ingestion)
"""

import argparse
import json
from pathlib import Path

from raglite.ingestion.pipeline import create_collection
from raglite.shared.clients import get_qdrant_client
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


def import_qdrant_snapshot(input_dir: str = ".qdrant-export") -> int:
    """Import Qdrant collection from snapshot.

    Args:
        input_dir: Directory containing snapshot files

    Returns:
        Number of points imported

    Raises:
        FileNotFoundError: If snapshot file doesn't exist
        ValueError: If snapshot data is invalid
    """
    input_path = Path(input_dir)
    snapshot_file = input_path / "qdrant_snapshot.json"

    if not snapshot_file.exists():
        raise FileNotFoundError(
            f"Snapshot file not found: {snapshot_file}. "
            "Run export first: python scripts/export-qdrant-snapshot.py"
        )

    logger.info(f"Importing Qdrant snapshot from: {snapshot_file}")
    logger.info(f"File size: {snapshot_file.stat().st_size / 1024 / 1024:.1f} MB")

    # Load snapshot data
    with open(snapshot_file) as f:
        snapshot_data = json.load(f)

    collection_name = snapshot_data["collection_name"]
    vector_size = snapshot_data["vector_size"]
    points = snapshot_data["points"]

    logger.info(f"Snapshot contains {len(points)} points for collection {collection_name}")

    # Get Qdrant client
    qdrant = get_qdrant_client()

    # Delete existing collection (if any)
    try:
        qdrant.delete_collection(collection_name=collection_name)
        logger.info(f"Deleted existing collection: {collection_name}")
    except Exception:
        logger.info(f"No existing collection to delete: {collection_name}")

    # Create collection
    logger.info(f"Creating collection {collection_name} (vector_size={vector_size})...")
    create_collection(collection_name=collection_name, vector_size=vector_size)

    # Import points in batches
    from qdrant_client.models import PointStruct

    batch_size = 100
    total_imported = 0

    for i in range(0, len(points), batch_size):
        batch = points[i : i + batch_size]

        batch_points = [
            PointStruct(
                id=point["id"],
                vector=point["vector"],
                payload=point["payload"],
            )
            for point in batch
        ]

        qdrant.upsert(collection_name=collection_name, points=batch_points)

        total_imported += len(batch)
        logger.info(f"Imported {total_imported}/{len(points)} points...")

    # Verify import
    import time

    time.sleep(1)  # Wait for Qdrant to commit
    final_count = qdrant.count(collection_name=collection_name).count

    if final_count != len(points):
        raise ValueError(
            f"Import verification failed: expected {len(points)} points, got {final_count}"
        )

    logger.info("✅ Import complete and verified")
    logger.info(f"   Collection: {collection_name}")
    logger.info(f"   Points: {final_count}")

    return final_count


def main():
    parser = argparse.ArgumentParser(description="Import Qdrant collection from snapshot")
    parser.add_argument(
        "--input",
        "-i",
        default=".qdrant-export",
        help="Input directory containing snapshot (default: .qdrant-export)",
    )

    args = parser.parse_args()

    try:
        count = import_qdrant_snapshot(args.input)
        print(f"\n✅ Import complete: {count} points")
    except Exception as e:
        print(f"\n❌ Import failed: {e}")
        raise


if __name__ == "__main__":
    main()
