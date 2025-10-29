"""Test PostgreSQL table retrieval with sample ground truth queries.

Runs the exact same SQL query from table_retrieval.py to diagnose why
it's returning zero results during accuracy tests.
"""

import logging

from psycopg2.extras import RealDictCursor

from raglite.shared.clients import get_postgresql_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_table_retrieval():
    """Test table retrieval with sample queries."""
    print("=" * 80)
    print("Testing PostgreSQL Table Retrieval SQL Query")
    print("=" * 80)

    # Sample queries from ground truth that should match
    test_queries = [
        "What is the thermal energy cost per ton in August 2025?",
        "What is the variable cost per ton in August 2025?",
        "What is the EBITDA margin for the Secil Group in August 2025?",
        "What are the Scope 1 emissions in August 2025?",
        "What is the electricity cost in August 2025?",
    ]

    conn = get_postgresql_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    # Exact SQL from table_retrieval.py (line 71-92)
    sql_query = """
        SELECT
            content AS text,
            ts_rank(content_tsv, plainto_tsquery('english', %s)) AS score,
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
            content_tsv @@ plainto_tsquery('english', %s)
            AND section_type = 'Table'  -- Prioritize table content
        ORDER BY score DESC
        LIMIT %s;
    """

    print("\nTesting SQL query from table_retrieval.py:\n")

    for query in test_queries:
        print(f"\nQuery: {query}")
        print("-" * 80)

        # Execute query with top_k=5
        cursor.execute(sql_query, (query, query, 5))
        rows = cursor.fetchall()

        if rows:
            print(f"✓ Found {len(rows)} results:")
            for i, row in enumerate(rows, 1):
                print(f"  [{i}] Score: {row['score']:.4f}")
                print(f"      Page: {row['page_number']}, Chunk: {row['chunk_index']}")
                print(f"      Section: {row['section_type']}")
                print(f"      Category: {row['metric_category']}")
                print(f"      Content: {row['text'][:100]}...")
        else:
            print("❌ NO RESULTS")

            # Debug: Try without Table restriction
            debug_sql = """
                SELECT COUNT(*) as total
                FROM financial_chunks
                WHERE content_tsv @@ plainto_tsquery('english', %s);
            """
            cursor.execute(debug_sql, (query,))
            total = cursor.fetchone()["total"]
            print(f"   Debug: {total} matches WITHOUT section_type='Table' filter")

            # Debug: Try with data_format instead (maybe wrong column?)
            debug_sql2 = """
                SELECT COUNT(*) as total
                FROM financial_chunks
                WHERE content_tsv @@ plainto_tsquery('english', %s)
                  AND data_format = 'table';
            """
            try:
                cursor.execute(debug_sql2, (query,))
                total2 = cursor.fetchone()["total"]
                print(f"   Debug: {total2} matches WITH data_format='table' filter")
            except Exception as e:
                print(f"   Debug: data_format column doesn't exist ({e})")

    print("\n" + "=" * 80)
    print("Test Complete")
    print("=" * 80)


if __name__ == "__main__":
    test_table_retrieval()
