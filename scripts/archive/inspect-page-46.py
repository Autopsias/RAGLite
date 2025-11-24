#!/usr/bin/env python3
"""Inspect chunks from page 46 to see what was actually extracted."""

from qdrant_client import QdrantClient

# Connect to Qdrant
client = QdrantClient(url="http://localhost:6333")

# Get all points
collection_name = "financial_docs"
points = client.scroll(
    collection_name=collection_name, limit=500, with_payload=True, with_vectors=False
)[0]

print("\nSearching for chunks from page 46...")
print("=" * 80)

page_46_chunks = []
for point in points:
    page = point.payload.get("page_number", "?")
    if page == 46:
        page_46_chunks.append(
            {
                "chunk_id": point.payload.get("chunk_id", "?"),
                "text": point.payload.get("text", ""),
                "word_count": point.payload.get("word_count", 0),
            }
        )

print(f"\nFound {len(page_46_chunks)} chunks from page 46")
print("=" * 80)

for i, chunk in enumerate(page_46_chunks[:5], 1):  # Show first 5 chunks
    print(f"\n--- Chunk {i} (ID: {chunk['chunk_id']}, Words: {chunk['word_count']}) ---")
    print(chunk["text"][:500])  # Show first 500 chars
    print("...")

if not page_46_chunks:
    print("\n❌ NO CHUNKS FROM PAGE 46 FOUND!")
