"""Vector similarity search and retrieval for natural language queries.

Performs semantic search using Fin-E5 embeddings and Qdrant vector database.
Supports hybrid search (BM25 + semantic) for improved keyword precision (Story 2.1).

This module maintains backward compatibility by re-exporting all functions from
the refactored domain modules.
"""

# Core search functionality
from raglite.retrieval.search.core import (
    QueryError,
    generate_query_embedding,
    get_metric_names,
    search_documents,
)

# Enrichment
from raglite.retrieval.search.enrichment import enrich_results_with_metadata

# Fusion algorithms
from raglite.retrieval.search.fusion import (
    fuse_search_results,
    fuse_sql_vector_results,
)

# Hybrid search orchestration
from raglite.retrieval.search.hybrid_search import hybrid_search

# Query reformulation
from raglite.retrieval.search.reformulation import (
    TIME_PERIOD_PATTERNS,
    _remove_time_periods,
    reformulate_query,
    search_with_reformulation,
)

__all__ = [
    # Core
    "QueryError",
    "generate_query_embedding",
    "get_metric_names",
    "search_documents",
    # Reformulation
    "TIME_PERIOD_PATTERNS",
    "_remove_time_periods",
    "reformulate_query",
    "search_with_reformulation",
    # Fusion
    "fuse_search_results",
    "fuse_sql_vector_results",
    # Hybrid
    "hybrid_search",
    # Enrichment
    "enrich_results_with_metadata",
]
