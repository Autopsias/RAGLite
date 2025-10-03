"""Embedding generation with Fin-E5 for Week 0 Integration Spike."""

import json
import time
import numpy as np
from typing import List, Dict, Any
from pathlib import Path

from sentence_transformers import SentenceTransformer
from config import EMBEDDING_MODEL, EMBEDDING_DIMENSION


def load_embedding_model(model_name: str = EMBEDDING_MODEL) -> SentenceTransformer:
    """
    Load the Fin-E5 embedding model.

    Args:
        model_name: Name of the SentenceTransformer model

    Returns:
        Loaded SentenceTransformer model
    """
    print(f"Loading embedding model: {model_name}")
    print("This may take a few minutes on first run (model download)...\n")

    start_time = time.time()
    model = SentenceTransformer(model_name)
    load_time = time.time() - start_time

    print(f"✓ Model loaded in {load_time:.2f} seconds")
    print(f"  Embedding dimension: {model.get_sentence_embedding_dimension()}")

    return model


def generate_embeddings_batch(
    chunks: List[Dict[str, Any]],
    model: SentenceTransformer,
    batch_size: int = 32
) -> List[Dict[str, Any]]:
    """
    Generate embeddings for chunks in batches for efficiency.

    Args:
        chunks: List of chunk dictionaries with text
        model: Loaded SentenceTransformer model
        batch_size: Number of chunks to process per batch

    Returns:
        List of chunks with embeddings added
    """
    print(f"\nGenerating embeddings for {len(chunks)} chunks...")
    print(f"Batch size: {batch_size}\n")

    start_time = time.time()

    # Extract texts from chunks
    texts = [chunk["text"] for chunk in chunks]

    # Generate embeddings in batches
    all_embeddings = []
    total_batches = (len(texts) + batch_size - 1) // batch_size

    for i in range(0, len(texts), batch_size):
        batch_num = (i // batch_size) + 1
        batch_texts = texts[i:i + batch_size]

        print(f"Processing batch {batch_num}/{total_batches} ({len(batch_texts)} chunks)...")

        # Generate embeddings for batch
        batch_embeddings = model.encode(
            batch_texts,
            show_progress_bar=False,
            convert_to_numpy=True
        )

        all_embeddings.extend(batch_embeddings)

    # Add embeddings to chunks
    for chunk, embedding in zip(chunks, all_embeddings):
        chunk["embedding"] = embedding.tolist()  # Convert numpy to list for JSON
        chunk["embedding_dimension"] = len(embedding)

    embedding_time = time.time() - start_time

    print(f"\n{'='*60}")
    print("EMBEDDING GENERATION SUMMARY")
    print(f"{'='*60}")
    print(f"Total chunks processed: {len(chunks)}")
    print(f"Embedding dimension: {len(all_embeddings[0])}")
    print(f"Total generation time: {embedding_time:.2f} seconds")
    print(f"Time per chunk: {embedding_time / len(chunks):.3f} seconds")
    print(f"Throughput: {len(chunks) / embedding_time:.2f} chunks/second")
    print(f"{'='*60}\n")

    return chunks, embedding_time


def generate_embeddings_from_chunks(
    chunks_path: str = "spike_chunks.json",
    output_path: str = "spike_embeddings.json"
) -> Dict[str, Any]:
    """
    Load chunks, generate embeddings, and save results.

    Args:
        chunks_path: Path to chunked document JSON
        output_path: Path to save embeddings output

    Returns:
        Dictionary with embedding results and statistics
    """
    # Load chunks
    print(f"Loading chunks from: {chunks_path}")
    with open(chunks_path, 'r', encoding='utf-8') as f:
        chunks_data = json.load(f)

    chunks = chunks_data["chunks"]
    print(f"✓ Loaded {len(chunks)} chunks\n")

    # Load embedding model
    model = load_embedding_model()

    # Generate embeddings
    chunks_with_embeddings, embedding_time = generate_embeddings_batch(chunks, model)

    # Prepare output
    result = {
        "model": EMBEDDING_MODEL,
        "embedding_dimension": EMBEDDING_DIMENSION,
        "total_chunks": len(chunks_with_embeddings),
        "embedding_time_seconds": round(embedding_time, 2),
        "time_per_chunk_seconds": round(embedding_time / len(chunks_with_embeddings), 3),
        "throughput_chunks_per_second": round(len(chunks_with_embeddings) / embedding_time, 2),
        "chunks": chunks_with_embeddings
    }

    # Save results
    print(f"Saving embeddings to: {output_path}")

    # Save embeddings to file (this will be large)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)

    # Also save metadata only (without embeddings) for easier inspection
    metadata_path = output_path.replace('.json', '_metadata.json')
    metadata = {k: v for k, v in result.items() if k != "chunks"}
    metadata["sample_embedding_shape"] = len(chunks_with_embeddings[0]["embedding"])

    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)

    print(f"✓ Embeddings saved to: {output_path}")
    print(f"✓ Metadata saved to: {metadata_path}")

    return result


if __name__ == "__main__":
    # Run embedding generation
    result = generate_embeddings_from_chunks()

    print(f"\n✓ Embedding generation complete!")
    print(f"  Model: {result['model']}")
    print(f"  Dimension: {result['embedding_dimension']}")
    print(f"  Total chunks: {result['total_chunks']}")
    print(f"  Generation time: {result['embedding_time_seconds']}s")
