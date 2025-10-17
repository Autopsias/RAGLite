"""Vector similarity search, retrieval, and source attribution."""

from raglite.retrieval.attribution import CitationError, generate_citations
from raglite.retrieval.search import QueryError, generate_query_embedding, search_documents

__all__ = [
    "CitationError",
    "QueryError",
    "generate_citations",
    "generate_query_embedding",
    "search_documents",
]
