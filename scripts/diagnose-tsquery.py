"""Diagnose how plainto_tsquery handles natural language queries vs keywords."""

from psycopg2.extras import RealDictCursor

from raglite.shared.clients import get_postgresql_connection


def test_tsquery():
    """Test how plainto_tsquery converts different query types."""
    print("=" * 80)
    print("Testing plainto_tsquery() with Different Query Types")
    print("=" * 80)

    conn = get_postgresql_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    # Test queries
    queries = [
        # Simple keywords (we know these work)
        "variable cost",
        "EBITDA",
        "thermal energy",
        # Natural language (these fail)
        "What is the thermal energy cost per ton in August 2025?",
        "What is the variable cost per ton in August 2025?",
        "What is the EBITDA margin for the Secil Group in August 2025?",
        # Try just keywords from the natural language questions
        "thermal energy cost ton August 2025",
        "variable cost ton August 2025",
        "EBITDA margin Secil Group August 2025",
    ]

    for query in queries:
        print(f"\nQuery: {query}")
        print("-" * 80)

        # Show what plainto_tsquery generates
        cursor.execute("SELECT plainto_tsquery('english', %s)::text as tsquery;", (query,))
        tsquery = cursor.fetchone()["tsquery"]
        print(f"  TSQuery: {tsquery}")

        # Test how many matches this gets
        cursor.execute(
            """
            SELECT COUNT(*) as matches
            FROM financial_chunks
            WHERE content_tsv @@ plainto_tsquery('english', %s);
        """,
            (query,),
        )
        matches = cursor.fetchone()["matches"]
        print(f"  Matches: {matches}")

        # If zero matches, try to understand why
        if matches == 0:
            # Try manual keyword extraction (remove common words)
            keywords = (
                query.replace("What", "")
                .replace("is", "")
                .replace("the", "")
                .replace("in", "")
                .replace("for", "")
                .replace("?", "")
                .strip()
            )
            cursor.execute("SELECT plainto_tsquery('english', %s)::text as tsquery;", (keywords,))
            simple_tsquery = cursor.fetchone()["tsquery"]

            cursor.execute(
                """
                SELECT COUNT(*) as matches
                FROM financial_chunks
                WHERE content_tsv @@ plainto_tsquery('english', %s);
            """,
                (keywords,),
            )
            simple_matches = cursor.fetchone()["matches"]

            print(f"  Debug: Without stopwords → '{keywords}'")
            print(f"  Debug TSQuery: {simple_tsquery}")
            print(f"  Debug Matches: {simple_matches}")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    test_tsquery()
