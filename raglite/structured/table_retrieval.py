"""PostgreSQL table retrieval for structured data queries.

Story 2.7 Implementation: Full-text search against PostgreSQL financial_chunks
table using pg_tsvector for keyword matching and metadata filtering.

This module provides SQL-based table retrieval for queries requiring precise
data lookups (e.g., "What is the exact revenue in Q3?", "Show me the cost table").
"""

import logging
from typing import Any, cast

import psycopg2
from psycopg2.extras import RealDictCursor

from raglite.shared.clients import get_postgresql_connection

logger = logging.getLogger(__name__)


# Security: Whitelist allowed metadata fields to prevent SQL injection
# Only these columns can be used in WHERE clause filters
ALLOWED_FILTER_FIELDS = {
    "company_name",
    "metric_category",
    "reporting_period",
    "time_granularity",
    "section_type",
    "units",
    "table_name",
    "document_id",
    "page_number",
}


class TableRetrievalError(Exception):
    """Exception raised when table retrieval fails."""

    pass


def _validate_table_search_request(query: str) -> None:
    """Validate table search request parameters.

    Args:
        query: Search query string

    Raises:
        ValueError: If query is empty or invalid
    """
    if not query or not query.strip():
        raise ValueError("Query cannot be empty")


def _validate_table_filter_request(filters: dict[str, Any] | None) -> None:
    """Validate metadata filter request parameters.

    Args:
        filters: Optional metadata filters dictionary

    Raises:
        TableRetrievalError: If invalid filter field is provided
    """
    if filters:
        for field in filters.keys():
            if field not in ALLOWED_FILTER_FIELDS:
                raise TableRetrievalError(
                    f"Invalid filter field: {field}. "
                    f"Allowed fields: {', '.join(sorted(ALLOWED_FILTER_FIELDS))}"
                )


def _execute_table_search(query: str, top_k: int) -> list[Any]:
    """Execute PostgreSQL full-text search query.

    Args:
        query: Natural language query
        top_k: Number of results to return

    Returns:
        List of database rows from search

    Raises:
        TableRetrievalError: If query execution fails
    """
    try:
        conn = get_postgresql_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Story 2.7 AC2: Full-text search using PostgreSQL ts_rank
        # Use websearch_to_tsquery for natural language queries (OR logic for high recall)
        sql_query = """
            SELECT
                content AS text,
                ts_rank(content_tsv, websearch_to_tsquery('english', %s)) AS score,
                document_id,
                page_number,
                chunk_index,
                company_name,
                metric_category,
                reporting_period,
                time_granularity,
                section_type,
                units,
                table_context,
                table_name
            FROM financial_chunks
            WHERE
                content_tsv @@ websearch_to_tsquery('english', %s)
                AND section_type = 'Table'  -- Prioritize table content (correct column)
            ORDER BY score DESC
            LIMIT %s;
        """

        cursor.execute(sql_query, (query, query, top_k))
        rows = cast(list[Any], cursor.fetchall())
        return rows

    except psycopg2.Error as e:
        error_msg = f"PostgreSQL query failed: {e}"
        logger.error(
            "PostgreSQL table search failed",
            extra={"query": query[:100], "error": str(e), "error_code": e.pgcode},
            exc_info=True,
        )
        raise TableRetrievalError(error_msg) from e


def _build_metadata_filter_query(
    filters: dict[str, Any] | None, query: str
) -> tuple[str, list[Any]]:
    """Build SQL WHERE clause and parameters for metadata filtering.

    Args:
        filters: Optional metadata filters dictionary
        query: Search query string

    Returns:
        Tuple of (where_clause_string, parameters_list)

    Raises:
        TableRetrievalError: If invalid filter field is provided
    """
    # Build WHERE clause with filters
    # Use websearch_to_tsquery for natural language OR logic (same as search_tables)
    where_conditions = ["content_tsv @@ websearch_to_tsquery('english', %s)"]
    params: list[Any] = [query]  # Type hint to allow str, int, or other filter values

    # Add metadata filters with SQL injection protection
    if filters:
        for field, value in filters.items():
            # Security check: Only allow whitelisted field names
            if field not in ALLOWED_FILTER_FIELDS:
                raise TableRetrievalError(
                    f"Invalid filter field: {field}. "
                    f"Allowed fields: {', '.join(sorted(ALLOWED_FILTER_FIELDS))}"
                )
            # Support LIKE pattern matching for values with wildcards (%)
            # This enables temporal queries like "Aug-25%" to match "Aug-25 YTD", "Aug-25", etc.
            if isinstance(value, str) and "%" in value:
                # Use LIKE for pattern matching (safe after whitelist validation)
                where_conditions.append(f"{field} LIKE %s")  # nosec B608
            else:
                # Use exact equality for non-pattern values
                where_conditions.append(f"{field} = %s")  # nosec B608
            params.append(value)

    where_clause = " AND ".join(where_conditions)
    return where_clause, params


def _execute_filtered_search(query: str, filters: dict[str, Any] | None, top_k: int) -> list[Any]:
    """Execute filtered search query with metadata constraints.

    Args:
        query: Natural language query
        filters: Optional metadata filters
        top_k: Number of results to return

    Returns:
        List of database rows from filtered search

    Raises:
        TableRetrievalError: If query execution fails
    """
    try:
        conn = get_postgresql_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Build WHERE clause with filters
        where_clause, params = _build_metadata_filter_query(filters, query)

        # Construct SQL query
        # Security: Safe from SQL injection because:
        # 1. where_conditions uses only whitelisted field names (ALLOWED_FILTER_FIELDS)
        # 2. All values use parameterized queries (%s placeholders)
        # 3. Field names validated before string interpolation
        sql_query = f"""
            SELECT
                content AS text,
                ts_rank(content_tsv, websearch_to_tsquery('english', %s)) AS score,
                document_id,
                page_number,
                chunk_index,
                company_name,
                metric_category,
                reporting_period,
                time_granularity,
                section_type,
                units,
                table_context,
                table_name
            FROM financial_chunks
            WHERE {where_clause}
            ORDER BY score DESC
            LIMIT %s;
        """  # nosec B608

        # Add query param for ts_rank and top_k limit
        params_with_limit: list[Any] = [query] + params + [top_k]

        cursor.execute(sql_query, params_with_limit)
        rows = cast(list[Any], cursor.fetchall())
        return rows

    except psycopg2.Error as e:
        error_msg = f"PostgreSQL filtered query failed: {e}"
        logger.error(
            "PostgreSQL filtered search failed",
            extra={"query": query[:100], "filters": filters, "error": str(e)},
            exc_info=True,
        )
        raise TableRetrievalError(error_msg) from e


def _format_table_results(rows: list[Any]) -> list[dict[str, Any]]:
    """Format database rows into standardized result format.

    Args:
        rows: Raw database rows from search

    Returns:
        List of formatted result dictionaries with text, score, metadata, etc.
    """
    results = []
    for row in rows:
        # Normalize ts_rank score to [0,1] range
        # ts_rank typically returns 0.0-1.0, but can exceed 1.0 for very high relevance
        normalized_score = min(row["score"], 1.0)

        # Convert UUID to string for document_id (PostgreSQL returns UUID objects)
        document_id = row.get("document_id", "unknown")
        if document_id != "unknown":
            document_id = str(document_id)

        results.append(
            {
                "text": row["text"],
                "score": float(normalized_score),
                "metadata": {
                    "source_document": document_id,
                    "page_number": row.get("page_number"),
                    "chunk_index": row.get("chunk_index", 0),
                    "company_name": row.get("company_name"),
                    "metric_category": row.get("metric_category"),
                    "reporting_period": row.get("reporting_period"),
                    "time_granularity": row.get("time_granularity"),
                    "section_type": row.get("section_type"),
                    "units": row.get("units"),
                    "table_context": row.get("table_context"),
                    "table_name": row.get("table_name"),
                    "word_count": len(row["text"].split()),
                },
                "document_id": document_id,
                "page_number": row.get("page_number"),
            }
        )
    return results


async def search_tables(query: str, top_k: int = 5) -> list[dict[str, Any]]:
    """Search PostgreSQL table index for structured data using full-text search.

    Story 2.7 AC2: Executes PostgreSQL full-text search against financial_chunks
    table using ts_rank for relevance scoring. Prioritizes table-formatted content.

    Query Processing:
      1. Convert query to tsquery for full-text search
      2. Search content_tsv column using ts_rank
      3. Filter by data_format='table' (prioritize structured data)
      4. Return top_k results ordered by relevance

    Args:
        query: Natural language query or keyword-based query
        top_k: Number of table rows to return (default: 5)

    Returns:
        List of dictionaries with keys:
          - text: Chunk content
          - score: Relevance score (0-1, normalized from ts_rank)
          - metadata: Dict with source_document, page_number, chunk_index, etc.
          - document_id: Source document identifier
          - page_number: Page number where chunk appears

    Raises:
        TableRetrievalError: If PostgreSQL connection fails or query execution fails

    Example:
        >>> results = await search_tables("Show revenue table", top_k=5)
        >>> for result in results:
        ...     print(f"[{result['score']:.2f}] {result['text'][:100]}")
    """
    try:
        logger.info(
            "PostgreSQL table search started",
            extra={"query": query[:100], "top_k": top_k},
        )

        # Execute search using helper function
        rows = _execute_table_search(query, top_k)

        # Format results using helper function
        results = _format_table_results(rows)

        logger.info(
            "PostgreSQL table search complete",
            extra={
                "query": query[:100],
                "results_count": len(results),
                "top_score": results[0]["score"] if results else 0.0,
            },
        )

        return results

    except Exception as e:
        # Generic errors
        error_msg = f"Table search failed: {e}"
        logger.error(
            "Table search failed",
            extra={
                "query": query[:100],
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        raise TableRetrievalError(error_msg) from e


async def search_tables_with_metadata_filter(
    query: str, top_k: int = 5, filters: dict[str, Any] | None = None
) -> list[dict[str, Any]]:
    """Search PostgreSQL with additional metadata filtering.

    Enhanced version of search_tables() that supports metadata filters
    (e.g., company_name, metric_category, time_period).

    Args:
        query: Natural language query
        top_k: Number of results to return
        filters: Optional metadata filters (e.g., {'company_name': 'Secil'})

    Returns:
        List of search results matching query AND filters

    Raises:
        TableRetrievalError: If invalid filter field is provided

    Example:
        >>> results = await search_tables_with_metadata_filter(
        ...     "Show revenue",
        ...     top_k=3,
        ...     filters={'company_name': 'Secil', 'metric_category': 'Revenue'}
        ... )
    """
    try:
        # Validate filters before executing query
        _validate_table_filter_request(filters)

        # Execute filtered search using helper function
        rows = _execute_filtered_search(query, filters, top_k)

        # Format results using helper function
        results = _format_table_results(rows)

        logger.info(
            "PostgreSQL filtered search complete",
            extra={
                "query": query[:100],
                "filters": filters,
                "results_count": len(results),
            },
        )

        return results

    except TableRetrievalError:
        # Re-raise TableRetrievalError as-is (already has context)
        raise
    except Exception as e:
        error_msg = f"Filtered search failed: {e}"
        logger.error(
            "Filtered search failed",
            extra={"query": query[:100], "filters": filters, "error": str(e)},
            exc_info=True,
        )
        raise TableRetrievalError(error_msg) from e
