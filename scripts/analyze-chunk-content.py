"""Analyze what's actually in the chunks to understand why natural language queries fail."""

from psycopg2.extras import RealDictCursor

from raglite.shared.clients import get_postgresql_connection


def analyze_chunks():
    """Analyze chunk content to understand query mismatch."""
    print("=" * 80)
    print("Analyzing Chunk Content for Query Matching")
    print("=" * 80)

    conn = get_postgresql_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    # Test 1: Find chunks that match individual keywords
    print("\n1. Chunks matching 'variable cost':")
    print("-" * 80)
    cursor.execute("""
        SELECT
            content,
            reporting_period,
            metric_category,
            page_number,
            chunk_index
        FROM financial_chunks
        WHERE content_tsv @@ plainto_tsquery('english', 'variable cost')
          AND section_type = 'Table'
        LIMIT 3;
    """)
    for row in cursor.fetchall():
        print(f"\nPage {row['page_number']}, Chunk {row['chunk_index']}")
        print(f"Period: {row['reporting_period']}")
        print(f"Category: {row['metric_category']}")
        print(f"Content preview: {row['content'][:200]}...")

    # Test 2: Check if ANY chunk has both "variable cost" AND date references
    print("\n\n2. Checking for chunks with 'variable cost' + date mentions:")
    print("-" * 80)
    cursor.execute("""
        SELECT
            content,
            reporting_period,
            page_number,
            chunk_index,
            content_tsv @@ plainto_tsquery('english', '2025') as has_2025,
            content_tsv @@ plainto_tsquery('english', 'August') as has_august
        FROM financial_chunks
        WHERE content_tsv @@ plainto_tsquery('english', 'variable cost')
          AND section_type = 'Table'
        LIMIT 5;
    """)
    results = cursor.fetchall()
    for row in results:
        print(f"\nPage {row['page_number']}, Chunk {row['chunk_index']}")
        print(f"Has '2025': {row['has_2025']}, Has 'August': {row['has_august']}")
        print(f"Period metadata: {row['reporting_period']}")
        print(f"Content: {row['content'][:150]}...")

    # Test 3: Check how dates are stored in the data
    print("\n\n3. Sample chunks with reporting_period metadata:")
    print("-" * 80)
    cursor.execute("""
        SELECT DISTINCT
            reporting_period,
            COUNT(*) as chunk_count
        FROM financial_chunks
        WHERE reporting_period IS NOT NULL
        GROUP BY reporting_period
        ORDER BY chunk_count DESC
        LIMIT 10;
    """)
    print("\nReporting periods in database:")
    for row in cursor.fetchall():
        print(f"  {row['reporting_period']}: {row['chunk_count']} chunks")

    # Test 4: Try searching with just metadata filter (no text search)
    print("\n\n4. Testing metadata-based filtering:")
    print("-" * 80)
    cursor.execute("""
        SELECT COUNT(*) as count
        FROM financial_chunks
        WHERE reporting_period LIKE '%2025%'
          AND content_tsv @@ plainto_tsquery('english', 'variable cost');
    """)
    count = cursor.fetchone()["count"]
    print(f"Chunks with 'variable cost' AND reporting_period containing '2025': {count}")

    # Test 5: What if we just use keywords without temporal qualifiers?
    print("\n\n5. Testing simplified keyword extraction:")
    print("-" * 80)

    test_queries = [
        ("What is the variable cost per ton in August 2025?", "variable cost ton"),
        ("What is the EBITDA margin for the Secil Group in August 2025?", "EBITDA margin"),
        ("What is the thermal energy cost per ton in August 2025?", "thermal energy cost ton"),
    ]

    for full_query, simplified in test_queries:
        cursor.execute(
            """
            SELECT COUNT(*) as matches
            FROM financial_chunks
            WHERE content_tsv @@ plainto_tsquery('english', %s)
              AND section_type = 'Table';
        """,
            (simplified,),
        )
        matches = cursor.fetchone()["matches"]
        print(f"\nOriginal: '{full_query}'")
        print(f"Simplified: '{simplified}' → {matches} matches")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    analyze_chunks()
