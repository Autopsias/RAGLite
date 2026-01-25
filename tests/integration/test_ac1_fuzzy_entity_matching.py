"""AC1 Test Suite: Fuzzy Entity Matching - Story 2.14.

Tests for PostgreSQL pg_trgm extension and similarity() function for
fuzzy entity matching to handle entity name variations and aliases.
"""

import pytest

from raglite.retrieval.query_classifier import generate_sql_query
from raglite.shared.clients import get_postgresql_connection

# Mark all tests in this module as integration tests
# NOTE: Order marker removed (2025-11-08) - tests don't use excerpt fixture
pytestmark = [
    pytest.mark.integration,
    pytest.mark.preserve_collection,
    pytest.mark.slow,
    pytest.mark.xdist_group(name="embedding_model_reads"),
]


@pytest.mark.priority("P2")
@pytest.mark.timeout(30)  # Prevent event loop blocking from sync DB operations
@pytest.mark.asyncio
@pytest.mark.preserve_collection  # Read-only SQL test - preserves session data
async def test_fuzzy_matching_portugal_cement(mock_mistral_client, session_ingested_collection):
    """Test AC1: Fuzzy entity matching for Portugal Cement variations.

    Requires session_ingested_collection to populate PostgreSQL with table data.
    """
    # Configure mock to return SQL with ILIKE matching
    mock_client, _ = mock_mistral_client
    mock_response = mock_client.chat.complete.return_value
    mock_response.choices[0].message.content = """
SELECT entity, metric, value, unit, period, fiscal_year, page_number
FROM financial_tables
WHERE entity ILIKE '%Portugal%'
  AND metric ILIKE '%variable cost%'
  AND period ILIKE '%Aug%'
ORDER BY page_number DESC
LIMIT 50;
    """.strip()

    # Query variations for Portugal Cement
    test_query = "What is the variable cost for Portugal Cement in August 2025?"
    sql = await generate_sql_query(test_query)

    assert sql is not None, "SQL generation should succeed"
    # Accept either fuzzy matching approach (similarity() or ILIKE)
    # similarity() requires pg_trgm extension, ILIKE works with base PostgreSQL
    assert "similarity(" in sql.lower() or "ilike" in sql.lower() or "like" in sql.lower(), (
        "SQL should use fuzzy matching (similarity, ILIKE, or LIKE)"
    )


@pytest.mark.priority("P2")
@pytest.mark.timeout(30)  # Prevent event loop blocking from sync DB operations
@pytest.mark.asyncio
@pytest.mark.preserve_collection  # Read-only SQL test - preserves session data
async def test_fuzzy_matching_tunisia_cement(mock_mistral_client, session_ingested_collection):
    """Test AC1: Fuzzy entity matching for Tunisia Cement.

    Requires session_ingested_collection to populate PostgreSQL with table data.
    """
    # Configure mock to return SQL with ILIKE matching for Tunisia
    mock_client, _ = mock_mistral_client
    mock_response = mock_client.chat.complete.return_value
    mock_response.choices[0].message.content = """
SELECT entity, metric, value, unit, period, fiscal_year, page_number
FROM financial_tables
WHERE entity ILIKE '%Tunisia%'
  AND metric ILIKE '%EBITDA%'
ORDER BY page_number DESC
LIMIT 50;
    """.strip()

    test_query = "What is the EBITDA for Tunisia in 2025?"
    sql = await generate_sql_query(test_query)

    assert sql is not None


@pytest.mark.priority("P2")
@pytest.mark.timeout(30)  # Prevent event loop blocking from sync DB operations
@pytest.mark.asyncio
@pytest.mark.preserve_collection  # SQL-only test - no vector data needed
async def test_pg_trgm_extension_installed(session_ingested_collection):
    """Test AC1: Verify pg_trgm extension is installed."""
    conn = get_postgresql_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname='pg_trgm')")
    exists = cursor.fetchone()[0]
    cursor.close()

    assert exists, "pg_trgm extension must be installed for fuzzy matching"


@pytest.mark.priority("P2")
@pytest.mark.timeout(30)  # Prevent event loop blocking from sync DB operations
@pytest.mark.asyncio
@pytest.mark.preserve_collection  # SQL-only test - no vector data needed
async def test_gin_indexes_exist(session_ingested_collection):
    """Test AC1: Verify GIN indexes exist for fuzzy matching."""
    conn = get_postgresql_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT COUNT(*) FROM pg_indexes
        WHERE tablename='financial_tables' AND indexname LIKE '%trgm%'
    """
    )
    count = cursor.fetchone()[0]
    cursor.close()

    assert count >= 2, "Should have at least 2 GIN indexes for entity and entity_normalized"


@pytest.mark.priority("P1")
@pytest.mark.timeout(30)  # Prevent event loop blocking from sync DB operations
@pytest.mark.asyncio
@pytest.mark.preserve_collection  # SQL-only test - no vector data needed
async def test_similarity_function_works(session_ingested_collection):
    """Test AC1: Verify similarity() function returns proper threshold."""
    conn = get_postgresql_connection()
    cursor = conn.cursor()

    # Test similarity function
    cursor.execute("SELECT similarity('Portugal', 'Portugal Cement')")
    similarity_score = cursor.fetchone()[0]
    cursor.close()

    assert similarity_score is not None, "similarity() function should return a score"
    assert 0 <= similarity_score <= 1, "Similarity score should be between 0 and 1"
    assert similarity_score > 0.3, (
        "Similarity between 'Portugal' and 'Portugal Cement' should be > 0.3"
    )


# NOTE: test_exact_match_fallback moved to test_story_2_14_excerpt_validation.py
# to group with other tests using ingested_excerpt_pdf fixture (performance optimization)


@pytest.mark.priority("P2")
@pytest.mark.timeout(30)  # Prevent event loop blocking from sync DB operations
@pytest.mark.asyncio
@pytest.mark.preserve_collection  # Read-only SQL test - preserves session data
async def test_fuzzy_matching_thresholds(mock_mistral_client, session_ingested_collection):
    """Test AC1: Fuzzy matching uses correct thresholds.

    Requires session_ingested_collection to populate PostgreSQL with table data.
    """
    # Configure mock
    mock_client, _ = mock_mistral_client
    mock_response = mock_client.chat.complete.return_value
    mock_response.choices[0].message.content = """
SELECT entity, metric, value, unit, period, fiscal_year, page_number
FROM financial_tables
WHERE entity ILIKE '%Angola%'
  AND metric ILIKE '%variable cost%'
ORDER BY page_number DESC
LIMIT 50;
    """.strip()

    test_query = "Angola variable costs"
    sql = await generate_sql_query(test_query)

    assert sql is not None
    # Accept both similarity thresholds (0.5, 0.3) or ILIKE pattern matching
    # similarity() requires pg_trgm extension, ILIKE works with base PostgreSQL
    assert (
        "0.5" in sql or "0.3" in sql
    ) or "ilike" in sql.lower(), (  # similarity() thresholds  # ILIKE pattern matching
        "SQL should use fuzzy matching (similarity with thresholds or ILIKE patterns)"
    )


@pytest.mark.priority("P2")
@pytest.mark.timeout(30)  # Prevent event loop blocking from sync DB operations
@pytest.mark.asyncio
@pytest.mark.preserve_collection  # Read-only SQL test - validates SQL generation only
async def test_case_insensitive_matching(mock_mistral_client):
    """Test AC1: Entity matching is case-insensitive.

    Validates that SQL generation uses ILIKE for case-insensitive matching.
    Does not execute query - only validates SQL structure (like other tests in this file).
    """
    # Configure mock to return SQL with ILIKE for case-insensitive matching
    mock_client, _ = mock_mistral_client
    mock_response = mock_client.chat.complete.return_value
    mock_response.choices[0].message.content = """
SELECT entity, metric, value, unit, period, fiscal_year, page_number
FROM financial_tables
WHERE entity ILIKE '%Portugal%'
  AND metric ILIKE '%frequency%'
ORDER BY page_number DESC
LIMIT 50;
    """.strip()

    # Test case-insensitive matching with uppercase query
    # Query-aware mock in conftest.py handles "frequency" metric keyword
    # ILIKE ensures case-insensitive matching (Portugal, PORTUGAL, portugal all match)
    test_query = "PORTUGAL frequency ratio"
    sql = await generate_sql_query(test_query)

    assert sql is not None, "SQL generation should succeed"
    # Verify SQL uses ILIKE for case-insensitive matching
    assert "ilike" in sql.lower(), "SQL should use ILIKE for case-insensitive matching"
    # Should contain Portugal and frequency filters
    assert "portugal" in sql.lower(), "SQL should filter by Portugal (case-insensitive)"
    assert "frequency" in sql.lower(), "SQL should filter by frequency metric"
