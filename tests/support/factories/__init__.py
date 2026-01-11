"""Test data factories package - facade for backward compatibility.

This package provides factory functions for generating test data with realistic
values using faker. All factories support overrides for specific test scenarios.

Public API (re-exported from _legacy):
- Document factories: create_document_metadata, create_chunk
- Query factories: create_query, create_query_result, create_qdrant_scored_point
- Database factories: create_sql_table_row, create_inspection_catalog
- Response factories: create_mcp_tool_response

Example Usage:
    from tests.support.factories import create_document_metadata, create_chunk

    # Default financial document
    doc = create_document_metadata()

    # Create chunk with custom content
    chunk = create_chunk(content="Revenue was $100M in Q3")
"""

# Re-export all public API from sub-modules for backward compatibility
from .database_factories import (
    create_database_query_result,
    create_financial_table_row,
    create_financial_table_rows,
    create_inspection_catalog,
    create_sql_table_row,
    create_sql_table_rows,
)
from .document_factories import (
    create_chunk,
    create_chunks,
    create_document_metadata,
    create_document_metadatas,
)
from .query_factories import (
    create_qdrant_scored_point,
    create_qdrant_scored_points,
    create_queries,
    create_query,
    create_query_result,
    create_query_results,
)
from .response_factories import (
    cleanup_test_data,
    create_mcp_tool_response,
)

__all__ = [
    # Document factories
    "create_document_metadata",
    "create_document_metadatas",
    "create_chunk",
    "create_chunks",
    # Query factories
    "create_query",
    "create_queries",
    "create_query_result",
    "create_query_results",
    "create_qdrant_scored_point",
    "create_qdrant_scored_points",
    # Database factories
    "create_financial_table_row",
    "create_financial_table_rows",
    "create_sql_table_row",
    "create_sql_table_rows",
    "create_inspection_catalog",
    "create_database_query_result",
    # Response factories
    "create_mcp_tool_response",
    # Cleanup
    "cleanup_test_data",
]
