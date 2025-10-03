"""Document chunking for Week 0 Integration Spike."""

import json
from typing import List, Dict, Any
from pathlib import Path

from config import CHUNK_SIZE, CHUNK_OVERLAP


def split_into_words(text: str) -> List[str]:
    """Split text into words, preserving whitespace for reconstruction."""
    return text.split()


def chunk_text(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
    source_doc: str = "",
    page_number: int = None
) -> List[Dict[str, Any]]:
    """
    Chunk text into overlapping segments based on word count.

    Args:
        text: The text content to chunk
        chunk_size: Number of words per chunk (default: 500)
        chunk_overlap: Number of overlapping words between chunks (default: 50)
        source_doc: Source document name for metadata
        page_number: Page number for metadata

    Returns:
        List of chunk dictionaries with text and metadata
    """
    words = split_into_words(text)
    total_words = len(words)

    chunks = []
    start_idx = 0
    chunk_id = 0

    while start_idx < total_words:
        # Calculate end index for this chunk
        end_idx = min(start_idx + chunk_size, total_words)

        # Extract chunk words and rejoin
        chunk_words = words[start_idx:end_idx]
        chunk_text = " ".join(chunk_words)

        # Create chunk with metadata
        chunk = {
            "chunk_id": chunk_id,
            "text": chunk_text,
            "word_count": len(chunk_words),
            "char_count": len(chunk_text),
            "start_word_idx": start_idx,
            "end_word_idx": end_idx,
            "metadata": {
                "source_document": source_doc,
                "page_number": page_number,
                "chunk_index": chunk_id,
                "total_chunks": None  # Will be updated after all chunks created
            }
        }

        chunks.append(chunk)

        # Move to next chunk with overlap
        start_idx += chunk_size - chunk_overlap
        chunk_id += 1

    # Update total_chunks in all chunk metadata
    total_chunks = len(chunks)
    for chunk in chunks:
        chunk["metadata"]["total_chunks"] = total_chunks

    return chunks


def chunk_ingested_document(
    ingestion_result_path: str = "spike_ingestion_result.json",
    output_path: str = "spike_chunks.json"
) -> List[Dict[str, Any]]:
    """
    Chunk an ingested document from the ingestion result file.

    Args:
        ingestion_result_path: Path to the ingestion result JSON
        output_path: Path to save chunked output

    Returns:
        List of all chunks with metadata
    """
    # Load ingestion result
    with open(ingestion_result_path, 'r', encoding='utf-8') as f:
        ingestion_data = json.load(f)

    if ingestion_data.get("status") != "success":
        raise ValueError(f"Ingestion failed: {ingestion_data.get('error', 'Unknown error')}")

    source_doc = ingestion_data["file_name"]
    pages_data = ingestion_data.get("pages", [])

    print(f"Chunking document: {source_doc}")
    print(f"Total pages: {len(pages_data)}")
    print(f"Chunk size: {CHUNK_SIZE} words, Overlap: {CHUNK_OVERLAP} words\n")

    # Chunk each page separately to preserve page numbers
    all_chunks = []

    if pages_data:
        # New approach: Chunk per-page with page numbers
        for page_data in pages_data:
            page_num = page_data["page_number"]
            page_text = page_data["text"]

            if not page_text.strip():
                continue  # Skip empty pages

            page_chunks = chunk_text(
                text=page_text,
                source_doc=source_doc,
                page_number=page_num
            )
            all_chunks.extend(page_chunks)

        print(f"✓ Chunked {len(pages_data)} pages into {len(all_chunks)} chunks")
    else:
        # Fallback: Use full document text (backward compatibility)
        text_content = ingestion_data["text_content"]
        print(f"⚠️  No page-level data found, using full document text")
        print(f"Total text length: {len(text_content):,} characters")

        all_chunks = chunk_text(
            text=text_content,
            source_doc=source_doc,
            page_number=None
        )

    chunks = all_chunks

    print(f"\nTotal chunks created: {len(chunks)}")
    print(f"\nSample chunks:")
    for i, chunk in enumerate(chunks[:3]):
        print(f"\nChunk {i}:")
        print(f"  Words: {chunk['word_count']}")
        print(f"  Characters: {chunk['char_count']}")
        print(f"  Page: {chunk['metadata']['page_number']}")
        print(f"  Preview: {chunk['text'][:100]}...")

    # Calculate statistics
    avg_words = sum(c["word_count"] for c in chunks) / len(chunks)
    avg_chars = sum(c["char_count"] for c in chunks) / len(chunks)

    stats = {
        "total_chunks": len(chunks),
        "source_document": source_doc,
        "chunk_size_config": CHUNK_SIZE,
        "chunk_overlap_config": CHUNK_OVERLAP,
        "avg_words_per_chunk": round(avg_words, 2),
        "avg_chars_per_chunk": round(avg_chars, 2),
        "min_words": min(c["word_count"] for c in chunks),
        "max_words": max(c["word_count"] for c in chunks)
    }

    # Save chunks to file
    output_data = {
        "statistics": stats,
        "chunks": chunks
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*60}")
    print("CHUNKING SUMMARY")
    print(f"{'='*60}")
    print(f"Total chunks: {stats['total_chunks']}")
    print(f"Average words per chunk: {stats['avg_words_per_chunk']}")
    print(f"Average characters per chunk: {stats['avg_chars_per_chunk']:,}")
    print(f"Min/Max words: {stats['min_words']}/{stats['max_words']}")
    print(f"Output saved to: {output_path}")
    print(f"{'='*60}\n")

    return chunks


if __name__ == "__main__":
    # Run chunking
    chunks = chunk_ingested_document()

    print(f"✓ Chunking complete: {len(chunks)} chunks created")
