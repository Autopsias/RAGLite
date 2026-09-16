"""Document and chunk test data factories.

Provides factory functions for generating DocumentMetadata and Chunk instances
with realistic financial content using faker.
"""

import os
from typing import Any

from faker import Faker

from raglite.shared.models import Chunk, DocumentMetadata

_FAKER_SEED = int(os.getenv("FAKER_SEED", "42"))
fake = Faker()
Faker.seed(_FAKER_SEED)


def create_document_metadata(**overrides: Any) -> DocumentMetadata:
    """Create sample document metadata with realistic values.

    Args:
        **overrides: Override specific fields (filename, doc_type, page_count, etc.)

    Returns:
        DocumentMetadata instance with generated or overridden values

    Example:
        # Default quarterly report
        doc = create_document_metadata()

        # Annual report with 100 pages
        doc = create_document_metadata(
            filename="Annual_Report_2024.pdf",
            page_count=100
        )
    """
    defaults = {
        "filename": f"{fake.company()}_Q{fake.random_int(1, 4)}_{fake.year()}.pdf",
        "doc_type": "PDF",
        "ingestion_timestamp": fake.iso8601(),
        "page_count": fake.random_int(10, 200),
        "source_path": f"/tmp/{fake.file_name(extension='pdf')}",
    }
    defaults.update(overrides)
    return DocumentMetadata(**defaults)


def create_document_metadatas(count: int, **overrides: Any) -> list[DocumentMetadata]:
    """Create multiple document metadata instances.

    Args:
        count: Number of documents to create
        **overrides: Override fields for ALL documents

    Returns:
        List of DocumentMetadata instances

    Example:
        # Create 5 quarterly reports
        docs = create_document_metadatas(5)
    """
    return [create_document_metadata(**overrides) for _ in range(count)]


def create_chunk(metadata: DocumentMetadata | None = None, **overrides: Any) -> Chunk:
    """Create sample chunk with realistic financial content.

    Args:
        metadata: Optional DocumentMetadata (creates default if not provided)
        **overrides: Override specific fields (content, page_number, embedding, etc.)

    Returns:
        Chunk instance with generated or overridden values

    Example:
        # Random financial chunk
        chunk = create_chunk()

        # Specific revenue statement
        chunk = create_chunk(
            content="Q3 revenue was $50M, up 20% YoY",
            page_number=5
        )

        # Chunk with custom metadata
        doc = create_document_metadata(filename="Custom.pdf")
        chunk = create_chunk(metadata=doc)
    """
    if metadata is None:
        metadata = create_document_metadata()

    # Generate realistic financial content variations
    content_templates = [
        f"Revenue for Q{fake.random_int(1, 4)} was ${fake.random_int(10, 500)}M, up {fake.random_int(5, 50)}% YoY.",
        f"Operating expenses increased {fake.random_int(5, 30)}% to ${fake.random_int(5, 100)}M.",
        f"Net income for the period was ${fake.random_int(10, 200)}M, representing a {fake.random_int(5, 40)}% margin.",
        f"Cash position at end of quarter: ${fake.random_int(50, 500)}M.",
        f"{fake.company()} reported EBITDA of ${fake.random_int(20, 300)}M for the fiscal year.",
    ]

    defaults = {
        "chunk_id": f"chunk-{fake.uuid4()}",
        "content": fake.random_element(content_templates),
        "metadata": metadata,
        "page_number": fake.random_int(1, metadata.page_count),
        "embedding": [fake.pyfloat(min_value=-1, max_value=1) for _ in range(1024)],
    }
    defaults.update(overrides)
    return Chunk(**defaults)


def create_chunks(
    count: int, metadata: DocumentMetadata | None = None, **overrides: Any
) -> list[Chunk]:
    """Create multiple chunks sharing the same document metadata.

    Args:
        count: Number of chunks to create
        metadata: Optional shared DocumentMetadata (creates default if not provided)
        **overrides: Override fields for ALL chunks

    Returns:
        List of Chunk instances

    Example:
        # Create 10 chunks from same document
        chunks = create_chunks(10)

        # Create 5 chunks from specific document
        doc = create_document_metadata(filename="Report.pdf")
        chunks = create_chunks(5, metadata=doc)
    """
    if metadata is None:
        metadata = create_document_metadata()
    return [create_chunk(metadata=metadata, **overrides) for _ in range(count)]
