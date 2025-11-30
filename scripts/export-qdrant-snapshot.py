#!/usr/bin/env python3
"""Export Qdrant collection data for caching in CI.

Exports all points from the financial_docs collection to JSON files
that can be restored later to skip ingestion.

Usage:
    python scripts/export-qdrant-snapshot.py --output .qdrant-export
"""

import argparse
import json
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from qdrant_client import QdrantClient  # noqa: E402

from raglite.shared.config import settings  # noqa: E402

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def export_qdrant_data(output_dir: Path) -> None:
    """Export Qdrant collection data to JSON files.

    Args:
        output_dir: Directory to store export files
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Connecting to Qdrant at {settings.qdrant_host}:{settings.qdrant_port}")
    client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)

    collection_name = settings.qdrant_collection_name

    # Check if collection exists
    try:
        collection_info = client.get_collection(collection_name)
        total_points = collection_info.points_count
        logger.info(f"Found collection '{collection_name}' with {total_points} points")
    except Exception as e:
        logger.error(f"Collection '{collection_name}' not found: {e}")
        sys.exit(1)

    if total_points == 0:
        logger.warning("Collection is empty, nothing to export")
        # Create empty marker file
        (output_dir / "empty_collection").touch()
        return

    # Export points in batches
    batch_size = 100
    all_points = []
    offset = None

    logger.info(f"Exporting {total_points} points in batches of {batch_size}...")

    while True:
        # Scroll through points
        points, next_offset = client.scroll(
            collection_name=collection_name,
            limit=batch_size,
            offset=offset,
            with_payload=True,
            with_vectors=True,
        )

        if not points:
            break

        # Convert points to serializable format
        for point in points:
            point_data = {
                "id": str(point.id),
                "payload": point.payload,
                "vector": {},
            }

            # Handle both dense and sparse vectors
            if point.vector:
                if isinstance(point.vector, dict):
                    # Named vectors (dense + sparse)
                    for name, vec in point.vector.items():
                        if hasattr(vec, "indices"):
                            # Sparse vector
                            point_data["vector"][name] = {
                                "indices": list(vec.indices),
                                "values": list(vec.values),
                            }
                        else:
                            # Dense vector
                            point_data["vector"][name] = list(vec)
                else:
                    # Single unnamed vector
                    point_data["vector"]["default"] = list(point.vector)

            all_points.append(point_data)

        logger.info(f"  Exported {len(all_points)}/{total_points} points...")

        if next_offset is None:
            break
        offset = next_offset

    # Save to JSON file
    export_file = output_dir / "points.json"
    with open(export_file, "w") as f:
        json.dump(
            {
                "collection_name": collection_name,
                "total_points": len(all_points),
                "points": all_points,
            },
            f,
        )

    # Save collection config
    config_file = output_dir / "collection_config.json"
    with open(config_file, "w") as f:
        json.dump(
            {
                "collection_name": collection_name,
                "vectors_count": collection_info.vectors_count,
                "points_count": collection_info.points_count,
            },
            f,
            indent=2,
        )

    logger.info(f"✅ Exported {len(all_points)} points to {export_file}")
    logger.info(f"   Export size: {export_file.stat().st_size / 1024 / 1024:.2f} MB")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Export Qdrant collection for caching")
    parser.add_argument(
        "--output",
        type=str,
        default=".qdrant-export",
        help="Output directory for export files",
    )
    args = parser.parse_args()

    output_dir = Path(args.output)

    try:
        export_qdrant_data(output_dir)
        return 0
    except Exception as e:
        logger.error(f"Export failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
