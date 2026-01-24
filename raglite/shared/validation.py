"""Data integrity validation for RAGLite dual-storage architecture.

Validates synchronization between Qdrant (vectors) and PostgreSQL (tables)
to detect and prevent data drift.

Story: Fix PostgreSQL Data Synchronization Gap
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from raglite.shared.logging import get_logger

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)


def normalize_document_id(doc_id: str) -> str:
    """Normalize document ID by removing file extension.

    Qdrant stores source_document with .pdf extension, while PostgreSQL
    stores document_id without extension. This normalizes for comparison.

    Args:
        doc_id: Document identifier (may or may not have extension)

    Returns:
        Normalized document ID without extension
    """
    # Strip common document extensions
    for ext in (".pdf", ".xlsx", ".xls", ".csv"):
        if doc_id.lower().endswith(ext):
            return doc_id[: -len(ext)]
    return doc_id


class DatabaseCounts(BaseModel):
    """Document and row counts from a database."""

    vectors: int = Field(default=0, description="Number of vector points/rows")
    documents: int = Field(default=0, description="Number of unique documents")


class DataIntegrityResult(BaseModel):
    """Result of data integrity check between Qdrant and PostgreSQL.

    Used by check_database_health MCP tool to report synchronization status.
    """

    is_synchronized: bool = Field(..., description="True if all documents exist in both databases")
    qdrant: DatabaseCounts = Field(..., description="Qdrant collection statistics")
    postgresql: DatabaseCounts = Field(..., description="PostgreSQL table statistics")
    missing_in_postgresql: list[str] = Field(
        default_factory=list,
        description="Document IDs present in Qdrant but not in PostgreSQL",
    )
    missing_in_qdrant: list[str] = Field(
        default_factory=list,
        description="Document IDs present in PostgreSQL but not in Qdrant",
    )
    recommendations: list[str] = Field(
        default_factory=list, description="Suggested actions to fix data drift"
    )


async def get_qdrant_documents() -> tuple[int, set[str]]:
    """Get vector count and unique document IDs from Qdrant.

    Returns:
        Tuple of (vector_count, set of document_ids)
    """
    from qdrant_client import QdrantClient

    client = QdrantClient(
        host=os.getenv("QDRANT_HOST", "localhost"),
        port=int(os.getenv("QDRANT_PORT", "6333")),
    )

    # Get collection info for vector count
    collection_info = client.get_collection("financial_docs")
    vector_count = collection_info.points_count

    # Get unique document IDs via scrolling
    documents: set[str] = set()
    offset = None
    batch_size = 100

    while True:
        result = client.scroll(
            collection_name="financial_docs",
            limit=batch_size,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )

        points, next_offset = result

        for point in points:
            source_doc = point.payload.get("source_document")
            if source_doc:
                documents.add(source_doc)

        if next_offset is None:
            break
        offset = next_offset

    return vector_count, documents


async def get_postgresql_documents() -> tuple[int, set[str]]:
    """Get row count and unique document IDs from PostgreSQL financial_tables.

    Returns:
        Tuple of (row_count, set of document_ids)
    """
    from sqlalchemy import create_engine, text

    from raglite.shared.config import settings

    # Use settings-based URL to respect APP_ENV (test vs production)
    db_url = os.getenv(
        "DATABASE_URL",
        f"postgresql://{settings.postgres_user}:{settings.postgres_password}@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}",
    )
    engine = create_engine(db_url)

    with engine.connect() as conn:
        # Get total row count
        row_result = conn.execute(text("SELECT COUNT(*) FROM financial_tables"))
        row_count = row_result.scalar() or 0

        # Get unique document IDs
        doc_result = conn.execute(text("SELECT DISTINCT document_id FROM financial_tables"))
        documents = {row[0] for row in doc_result}

    return row_count, documents


async def check_data_integrity() -> DataIntegrityResult:
    """Check synchronization between Qdrant and PostgreSQL.

    Compares document IDs in both databases and generates recommendations
    for fixing any data drift.

    Returns:
        DataIntegrityResult with synchronization status and recommendations
    """
    logger.info("Checking data integrity between Qdrant and PostgreSQL")

    try:
        # Get data from both sources
        qdrant_vectors, qdrant_docs = await get_qdrant_documents()
        postgresql_rows, postgresql_docs = await get_postgresql_documents()

        # Normalize document IDs for comparison
        # Qdrant stores with .pdf extension, PostgreSQL stores without
        qdrant_normalized = {normalize_document_id(doc): doc for doc in qdrant_docs}
        postgresql_normalized = {normalize_document_id(doc): doc for doc in postgresql_docs}

        # Find discrepancies using normalized keys
        missing_keys_in_postgresql = set(qdrant_normalized.keys()) - set(
            postgresql_normalized.keys()
        )
        missing_keys_in_qdrant = set(postgresql_normalized.keys()) - set(qdrant_normalized.keys())

        # Map back to original document names for reporting
        missing_in_postgresql = {qdrant_normalized[key] for key in missing_keys_in_postgresql}
        missing_in_qdrant = {postgresql_normalized[key] for key in missing_keys_in_qdrant}

        # Determine sync status
        is_synchronized = len(missing_in_postgresql) == 0 and len(missing_in_qdrant) == 0

        # Generate recommendations
        recommendations = []
        if missing_in_postgresql:
            recommendations.append(
                f"Run backfill script: python scripts/backfill-postgresql-tables.py "
                f"({len(missing_in_postgresql)} documents need table extraction)"
            )
        if missing_in_qdrant:
            recommendations.append(
                f"Re-ingest documents to Qdrant: {len(missing_in_qdrant)} documents "
                f"exist in PostgreSQL but not in Qdrant"
            )
        if is_synchronized:
            recommendations.append("All documents are synchronized - no action needed")

        result = DataIntegrityResult(
            is_synchronized=is_synchronized,
            qdrant=DatabaseCounts(vectors=qdrant_vectors, documents=len(qdrant_docs)),
            postgresql=DatabaseCounts(vectors=postgresql_rows, documents=len(postgresql_docs)),
            missing_in_postgresql=sorted(missing_in_postgresql),
            missing_in_qdrant=sorted(missing_in_qdrant),
            recommendations=recommendations,
        )

        # Log results
        if is_synchronized:
            logger.info(
                "Data integrity check passed",
                extra={
                    "qdrant_docs": len(qdrant_docs),
                    "postgresql_docs": len(postgresql_docs),
                },
            )
        else:
            logger.warning(
                "Data integrity check found drift",
                extra={
                    "qdrant_docs": len(qdrant_docs),
                    "postgresql_docs": len(postgresql_docs),
                    "missing_in_postgresql": len(missing_in_postgresql),
                    "missing_in_qdrant": len(missing_in_qdrant),
                },
            )

        return result

    except Exception as e:
        logger.error(f"Data integrity check failed: {e}")
        return DataIntegrityResult(
            is_synchronized=False,
            qdrant=DatabaseCounts(),
            postgresql=DatabaseCounts(),
            recommendations=[f"Error during integrity check: {e}"],
        )
