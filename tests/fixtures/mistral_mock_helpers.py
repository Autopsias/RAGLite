"""Mistral API mock helpers for SQL generation tests.

This module provides mock SQL generation functions used by the mock_mistral_api_globally
fixture to prevent real Mistral API calls during testing.

Functions:
    generate_mock_sql: Generate query-aware SQL for table search tests
    generate_mock_metadata: Generate mock metadata for chunk enrichment tests
    generate_query_aware_sql: Alias for generate_mock_sql (same implementation)
"""

from typing import Any
from unittest.mock import MagicMock


def _extract_query_from_messages(messages: list[dict[str, Any] | Any]) -> str:
    """Extract the user query from messages.

    Args:
        messages: List of message dicts/objects containing the query

    Returns:
        Extracted query text, or empty string if not found
    """
    if not messages or len(messages) == 0:
        return ""

    # Handle both dict and object message formats
    last_msg = messages[-1]
    if isinstance(last_msg, dict):
        full_content = last_msg.get("content", "")
    else:
        full_content = getattr(last_msg, "content", "")

    # For SQL generation, extract actual query from the prompt template
    # The prompt contains: "**USER QUERY:**\n{query}\n\n**INSTRUCTIONS:**"
    if "**USER QUERY:**" in full_content:
        # Extract text after "**USER QUERY:**" and before "**INSTRUCTIONS:**"
        start_marker = "**USER QUERY:**"
        end_marker = "**INSTRUCTIONS:**"
        start_idx = full_content.find(start_marker) + len(start_marker)
        end_idx = full_content.find(end_marker)
        if end_idx > start_idx:
            return full_content[start_idx:end_idx].strip()
        else:
            return full_content[start_idx:].strip()
    else:
        # Fallback: use full content for non-SQL generation calls
        return full_content


def _build_entity_filters(query_lower: str) -> list[str]:
    """Build entity filters for WHERE clause.

    Args:
        query_lower: Lowercase query text

    Returns:
        List of entity filter conditions
    """
    entities = []
    if "portugal" in query_lower:
        entities.append("entity ILIKE '%Portugal%'")
    if "tunisia" in query_lower:
        entities.append("entity ILIKE '%Tunisia%'")
    if "angola" in query_lower:
        entities.append("entity ILIKE '%Angola%'")
    if "brazil" in query_lower:
        entities.append("entity ILIKE '%Brazil%'")
    return entities


def _build_metric_filters(query_lower: str) -> list[str]:
    """Build metric filters for WHERE clause.

    Args:
        query_lower: Lowercase query text

    Returns:
        List of metric filter conditions
    """
    metrics = []
    if "ebitda" in query_lower:
        metrics.append("metric ILIKE '%EBITDA%'")
    if "revenue" in query_lower or "turnover" in query_lower:
        metrics.append("metric ILIKE '%Revenue%'")
    # CRITICAL FIX (2025-11-24): "operating" should match BOTH "operational" AND "operating"
    # Test query "operating expenses" needs to match test data which may use either term
    if "operating" in query_lower:
        # Use OR to match both variations (operational OR operating)
        metrics.append("(metric ILIKE '%operational%' OR metric ILIKE '%operating%')")
    if "variable cost" in query_lower:
        metrics.append("metric ILIKE '%variable cost%'")
    if "currency" in query_lower:
        metrics.append("metric ILIKE '%Currency%'")
    if "frequency" in query_lower:
        metrics.append("metric ILIKE '%frequency%'")
    return metrics


def _build_period_filters(query_lower: str) -> list[str]:
    """Build period filters for WHERE clause.

    Args:
        query_lower: Lowercase query text

    Returns:
        List of period filter conditions
    """
    filters = []
    if "august" in query_lower or "aug" in query_lower:
        filters.append("period ILIKE '%Aug%'")
    if "2025" in query_lower:
        filters.append("(fiscal_year = 2025 OR fiscal_year IS NULL)")
    return filters


def _is_generic_table_query(
    query_lower: str,
    where_conditions: list[str],
    metrics: list[str],
    entities: list[str],
) -> bool:
    """Check if this is a generic "table for X" query.

    CRITICAL FIX (2025-11-24): For queries with ONLY metric filters and no
    temporal/entity filters, use a more permissive query to ensure CI has
    matching data. This prevents SQL returning 0 results which triggers
    vector fallback. Root cause: CI test database may have different metric
    naming than local ("operating expenses" vs "operational costs" vs
    "operating costs").

    Args:
        query_lower: Lowercase query text
        where_conditions: Current WHERE clause conditions
        metrics: Metric filters extracted from query
        entities: Entity filters extracted from query

    Returns:
        True if this is a generic table query needing permissive handling
    """
    return (
        "table" in query_lower
        and len(where_conditions) <= 1  # Only metric filter, no entity/period
        and metrics  # Has metric filter
        and not entities  # No entity filter
        and not (
            "august" in query_lower or "aug" in query_lower or "2025" in query_lower
        )  # No period filter
    )


def _build_where_clause(entities: list[str], metrics: list[str], periods: list[str]) -> str:
    """Build WHERE clause from filter lists.

    Args:
        entities: Entity filter conditions
        metrics: Metric filter conditions
        periods: Period filter conditions

    Returns:
        WHERE clause string (empty if no conditions)
    """
    where_conditions = []

    # Add entity filter (OR if multiple entities for comparison)
    if entities:
        if len(entities) == 1:
            where_conditions.append(entities[0])
        else:
            where_conditions.append("(" + " OR ".join(entities) + ")")

    # Add metric filter (OR if multiple metrics)
    if metrics:
        if len(metrics) == 1:
            where_conditions.append(metrics[0])
        else:
            where_conditions.append("(" + " OR ".join(metrics) + ")")

    # Add period filters
    where_conditions.extend(periods)

    # Construct WHERE clause
    if where_conditions:
        return "\nWHERE " + " AND ".join(where_conditions)
    return ""


def _create_mock_response(sql: str) -> MagicMock:
    """Create a MagicMock response with SQL content.

    Args:
        sql: SQL query string

    Returns:
        MagicMock response object with SQL in choices[0].message.content
    """
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message = MagicMock()
    mock_response.choices[0].message.content = sql
    return mock_response


def generate_mock_sql(messages: list[dict[str, Any] | Any], **kwargs: Any) -> MagicMock:
    """Mock SQL generation for table search - returns query-aware realistic SQL.

    Extracts entity, metric, and period filters from the natural language query
    to generate SQL with appropriate WHERE clauses, ensuring tests retrieve
    relevant table data instead of all rows.

    Args:
        messages: List of message dicts/objects containing the query
        **kwargs: Additional keyword arguments (ignored)

    Returns:
        MagicMock response object with SQL in choices[0].message.content
    """
    # Extract query from messages (last user message)
    query_text = _extract_query_from_messages(messages)
    query_lower = query_text.lower()

    # Build filter lists
    entities = _build_entity_filters(query_lower)
    metrics = _build_metric_filters(query_lower)
    periods = _build_period_filters(query_lower)

    # Construct WHERE clause
    where_clause = _build_where_clause(entities, metrics, periods)

    # Check if this is a generic table query needing permissive handling
    is_generic_table_query = _is_generic_table_query(
        query_lower,
        [where_clause],  # Simplified - just check if non-empty
        metrics,
        entities,
    )

    if is_generic_table_query:
        # PERMISSIVE QUERY: Return ANY data for generic "table for X" queries
        # This ensures SQL search returns results in CI environment
        sql = """SELECT document_id, entity, metric, value, unit, period, fiscal_year, page_number, table_caption
FROM financial_tables
ORDER BY page_number DESC
LIMIT 10;""".strip()
    else:
        # Normal query with filters
        sql = f"""SELECT document_id, entity, metric, value, unit, period, fiscal_year, page_number, table_caption
FROM financial_tables{where_clause}
ORDER BY page_number DESC
LIMIT 50;""".strip()

    return _create_mock_response(sql)


def generate_mock_metadata(messages: list[dict[str, Any] | Any], **kwargs: Any) -> MagicMock:
    """Mock metadata extraction for chunk enrichment - returns realistic JSON.

    Args:
        messages: List of message dicts/objects containing the query
        **kwargs: Additional keyword arguments (ignored)

    Returns:
        MagicMock response object with JSON in choices[0].message.content
    """
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message = MagicMock()
    mock_response.choices[
        0
    ].message.content = '{"metric_category": "Revenue", "time_period": "Q3 2025"}'
    return mock_response


# Alias for backwards compatibility and explicit naming in tests
generate_query_aware_sql = generate_mock_sql
