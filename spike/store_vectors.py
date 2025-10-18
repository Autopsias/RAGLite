"""Store embeddings in Qdrant for Week 0 Integration Spike."""

import json
import time
import uuid
from typing import Any

from config import EMBEDDING_DIMENSION, QDRANT_COLLECTION_NAME, QDRANT_URL
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams


def create_qdrant_collection(
    client: QdrantClient,
    collection_name: str = QDRANT_COLLECTION_NAME,
    vector_size: int = EMBEDDING_DIMENSION,
    distance: Distance = Distance.COSINE,
) -> bool:
    """
    Create a Qdrant collection for storing document embeddings.

    Args:
        client: Qdrant client instance
        collection_name: Name of the collection to create
        vector_size: Dimension of the embedding vectors
        distance: Distance metric to use (Cosine for embeddings)

    Returns:
        True if collection created successfully
    """
    # Check if collection already exists
    collections = client.get_collections().collections
    existing = [c.name for c in collections]

    if collection_name in existing:
        print(f"⚠️  Collection '{collection_name}' already exists. Deleting...")
        client.delete_collection(collection_name)

    # Create collection
    print(f"Creating collection: {collection_name}")
    print(f"  Vector size: {vector_size}")
    print(f"  Distance metric: {distance.name}\n")

    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=vector_size, distance=distance),
    )

    print(f"✓ Collection '{collection_name}' created successfully\n")
    return True


def store_embeddings_in_qdrant(
    embeddings_path: str = "spike_embeddings.json",
    client: QdrantClient = None,
    collection_name: str = QDRANT_COLLECTION_NAME,
    batch_size: int = 100,
) -> dict[str, Any]:
    """
    Load embeddings and store them in Qdrant.

    Args:
        embeddings_path: Path to embeddings JSON file
        client: Qdrant client (will create if None)
        collection_name: Name of the collection
        batch_size: Number of vectors to upload per batch

    Returns:
        Dictionary with storage statistics
    """
    # Create Qdrant client if not provided
    if client is None:
        print(f"Connecting to Qdrant at: {QDRANT_URL}")
        client = QdrantClient(url=QDRANT_URL)
        print("✓ Connected to Qdrant\n")

    # Load embeddings
    print(f"Loading embeddings from: {embeddings_path}")
    with open(embeddings_path, encoding="utf-8") as f:
        embeddings_data = json.load(f)

    chunks = embeddings_data["chunks"]
    print(f"✓ Loaded {len(chunks)} chunks with embeddings\n")

    # Create collection
    create_qdrant_collection(client, collection_name)

    # Prepare points for upload
    print(f"Preparing {len(chunks)} points for upload...")
    points = []

    for chunk in chunks:
        # Create point with embedding and metadata
        point = PointStruct(
            id=str(uuid.uuid4()),  # Generate unique ID
            vector=chunk["embedding"],
            payload={
                "chunk_id": chunk["chunk_id"],
                "text": chunk["text"],
                "word_count": chunk["word_count"],
                "char_count": chunk["char_count"],
                "source_document": chunk["metadata"]["source_document"],
                "page_number": chunk["metadata"]["page_number"],
                "chunk_index": chunk["metadata"]["chunk_index"],
                "total_chunks": chunk["metadata"]["total_chunks"],
            },
        )
        points.append(point)

    # Upload in batches
    print(f"Uploading points in batches of {batch_size}...\n")
    start_time = time.time()

    total_batches = (len(points) + batch_size - 1) // batch_size

    for i in range(0, len(points), batch_size):
        batch_num = (i // batch_size) + 1
        batch_points = points[i : i + batch_size]

        print(f"Uploading batch {batch_num}/{total_batches} ({len(batch_points)} points)...")

        client.upsert(collection_name=collection_name, points=batch_points)

    upload_time = time.time() - start_time

    # Verify storage
    print("\nVerifying storage...")
    collection_info = client.get_collection(collection_name)

    print(f"\n{'=' * 60}")
    print("QDRANT STORAGE SUMMARY")
    print(f"{'=' * 60}")
    print(f"Collection: {collection_name}")
    print(f"Total vectors stored: {collection_info.points_count}")
    print(f"Vector dimension: {collection_info.config.params.vectors.size}")
    print(f"Distance metric: {collection_info.config.params.vectors.distance.name}")
    print(f"Upload time: {upload_time:.2f} seconds")
    print(f"Upload rate: {len(points) / upload_time:.2f} vectors/second")
    print(f"{'=' * 60}\n")

    return {
        "collection_name": collection_name,
        "vectors_stored": collection_info.points_count,
        "vector_dimension": collection_info.config.params.vectors.size,
        "distance_metric": collection_info.config.params.vectors.distance.name,
        "upload_time_seconds": round(upload_time, 2),
        "upload_rate_vectors_per_second": round(len(points) / upload_time, 2),
    }


def test_qdrant_search(
    client: QdrantClient,
    collection_name: str = QDRANT_COLLECTION_NAME,
    embeddings_path: str = "spike_embeddings.json",
    top_k: int = 3,
):
    """
    Test Qdrant search functionality with a sample query.

    Args:
        client: Qdrant client
        collection_name: Name of the collection
        embeddings_path: Path to embeddings (to get a sample vector)
        top_k: Number of results to return
    """
    print("Testing Qdrant search functionality...")

    # Load embeddings to get a test vector
    with open(embeddings_path, encoding="utf-8") as f:
        embeddings_data = json.load(f)

    # Use first chunk's embedding as test query
    test_vector = embeddings_data["chunks"][0]["embedding"]
    test_text = embeddings_data["chunks"][0]["text"][:100]

    print("\nTest query (first chunk preview):")
    print(f"  {test_text}...\n")

    # Perform search using updated API with named vectors (Story 2.1 hybrid search)
    search_results = client.query_points(
        collection_name=collection_name,
        query=test_vector,
        using="text-dense",  # Named vector for hybrid search
        limit=top_k,
    ).points

    print(f"Top {top_k} search results:")
    for i, result in enumerate(search_results):
        print(f"\n  Result {i + 1}:")
        print(f"    Score: {result.score:.4f}")
        print(f"    Chunk ID: {result.payload.get('chunk_id')}")
        print(f"    Text preview: {result.payload.get('text', '')[:80]}...")

    print("\n✓ Search test successful!\n")


if __name__ == "__main__":
    # Create Qdrant client
    client = QdrantClient(url=QDRANT_URL)

    # Store embeddings
    stats = store_embeddings_in_qdrant(client=client)

    # Test search
    test_qdrant_search(client=client)

    print("✓ Qdrant storage complete!")
    print(f"  Collection: {stats['collection_name']}")
    print(f"  Vectors: {stats['vectors_stored']}")
    print(f"  Dimension: {stats['vector_dimension']}")
    print(f"  Upload time: {stats['upload_time_seconds']}s")
