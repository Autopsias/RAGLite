"""Test query preprocessing and metadata-filtered table search."""

import asyncio

from psycopg2.extras import RealDictCursor

from raglite.retrieval.query_preprocessing import preprocess_query_for_table_search
from raglite.shared.clients import get_postgresql_connection
from raglite.structured.table_retrieval import search_tables_with_metadata_filter


async def test_preprocessing():
    """Test query preprocessing and search results."""
    print("=" * 80)
    print("Testing Query Preprocessing + Metadata-Filtered Search")
    print("=" * 80)

    # Test queries from ground truth
    test_queries = [
        "What is the thermal energy cost per ton in August 2025?",
        "What is the variable cost per ton in August 2025?",
        "What is the EBITDA margin for the Secil Group in August 2025?",
    ]

    for query in test_queries:
        print(f"\n{'=' * 80}")
        print(f"Query: {query}")
        print("=" * 80)

        # Step 1: Preprocess query
        keywords, filters = preprocess_query_for_table_search(query)
        print("\n1. Query Preprocessing:")
        print(f"   Original: {query}")
        print(f"   Keywords: {keywords}")
        print(f"   Filters:  {filters}")

        # Step 2: Test with search_tables_with_metadata_filter
        if filters:
            print("\n2. Testing metadata-filtered search:")
            results = await search_tables_with_metadata_filter(
                query=keywords, top_k=3, filters=filters
            )

            if results:
                print(f"   ✅ Found {len(results)} results:")
                for i, result in enumerate(results, 1):
                    print(f"\n   Result {i}:")
                    print(f"      Score: {result['score']:.4f}")
                    print(f"      Period: {result['metadata'].get('reporting_period')}")
                    print(f"      Category: {result['metadata'].get('metric_category')}")
                    print(f"      Page: {result.get('page_number')}")
                    print(f"      Content: {result['text'][:150]}...")
            else:
                print("   ❌ No results found")

                # Debug: Check if LIKE pattern is working
                conn = get_postgresql_connection()
                cursor = conn.cursor(cursor_factory=RealDictCursor)

                cursor.execute(
                    """
                    SELECT COUNT(*) as count
                    FROM financial_chunks
                    WHERE reporting_period LIKE %s
                      AND content_tsv @@ plainto_tsquery('english', %s);
                """,
                    (filters["reporting_period"], keywords),
                )
                debug_count = cursor.fetchone()["count"]
                print(f"   Debug: {debug_count} chunks match LIKE pattern + keywords")

                # Show sample reporting periods
                cursor.execute(
                    """
                    SELECT DISTINCT reporting_period
                    FROM financial_chunks
                    WHERE reporting_period LIKE %s
                    LIMIT 5;
                """,
                    (filters["reporting_period"],),
                )
                periods = cursor.fetchall()
                print(f"   Sample matching periods: {[p['reporting_period'] for p in periods]}")

        else:
            print("\n2. No filters extracted - would use standard search")

    print("\n" + "=" * 80)
    print("Test Complete")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_preprocessing())
