"""Test websearch_to_tsquery() with natural language queries.

Verifies that switching from plainto_tsquery() to websearch_to_tsquery()
resolves the zero-results issue for natural language queries.
"""

from psycopg2.extras import RealDictCursor

from raglite.shared.clients import get_postgresql_connection


def test_websearch_tsquery():
    """Test websearch_to_tsquery with sample queries."""
    print("=" * 80)
    print("Testing websearch_to_tsquery() vs plainto_tsquery()")
    print("=" * 80)

    conn = get_postgresql_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    # Test queries from ground truth
    test_queries = [
        "What is the thermal energy cost per ton in August 2025?",
        "What is the variable cost per ton in August 2025?",
        "What is the EBITDA margin for the Secil Group in August 2025?",
    ]

    for query in test_queries:
        print(f"\nQuery: {query}")
        print("-" * 80)

        # Show what both functions generate
        cursor.execute("SELECT plainto_tsquery('english', %s)::text as tsquery;", (query,))
        plain_tsquery = cursor.fetchone()["tsquery"]

        cursor.execute("SELECT websearch_to_tsquery('english', %s)::text as tsquery;", (query,))
        web_tsquery = cursor.fetchone()["tsquery"]

        print(f"  plainto_tsquery:    {plain_tsquery}")
        print(f"  websearch_to_tsquery: {web_tsquery}")

        # Test matches with plainto_tsquery (OLD - strict AND)
        cursor.execute(
            """
            SELECT COUNT(*) as matches
            FROM financial_chunks
            WHERE content_tsv @@ plainto_tsquery('english', %s)
              AND section_type = 'Table';
        """,
            (query,),
        )
        plain_matches = cursor.fetchone()["matches"]

        # Test matches with websearch_to_tsquery (NEW - OR logic)
        cursor.execute(
            """
            SELECT COUNT(*) as matches
            FROM financial_chunks
            WHERE content_tsv @@ websearch_to_tsquery('english', %s)
              AND section_type = 'Table';
        """,
            (query,),
        )
        web_matches = cursor.fetchone()["matches"]

        print(
            f"\n  Matches (plainto):    {plain_matches} {'❌ ZERO' if plain_matches == 0 else '✓'}"
        )
        print(
            f"  Matches (websearch):  {web_matches} {'✅ WORKS!' if web_matches > 0 else '❌ STILL ZERO'}"
        )

        # Get sample results with websearch_to_tsquery
        if web_matches > 0:
            cursor.execute(
                """
                SELECT
                    ts_rank(content_tsv, websearch_to_tsquery('english', %s)) AS score,
                    page_number,
                    chunk_index,
                    metric_category,
                    LEFT(content, 100) as content_preview
                FROM financial_chunks
                WHERE content_tsv @@ websearch_to_tsquery('english', %s)
                  AND section_type = 'Table'
                ORDER BY score DESC
                LIMIT 3;
            """,
                (query, query),
            )
            results = cursor.fetchall()

            print("\n  Top 3 results:")
            for i, row in enumerate(results, 1):
                print(
                    f"    [{i}] Score: {row['score']:.4f} | Page: {row['page_number']} | Chunk: {row['chunk_index']}"
                )
                print(f"        Category: {row['metric_category']}")
                print(f"        Content: {row['content_preview']}...")

    print("\n" + "=" * 80)
    print("✅ Test Complete - websearch_to_tsquery() should show matches!")
    print("=" * 80)


if __name__ == "__main__":
    test_websearch_tsquery()
