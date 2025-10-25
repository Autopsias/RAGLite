"""Check if content_tsv column is populated and working."""

from psycopg2.extras import RealDictCursor

from raglite.shared.clients import get_postgresql_connection


def main():
    conn = get_postgresql_connection()
    cursor = cursor = conn.cursor(cursor_factory=RealDictCursor)

    print("=" * 80)
    print("Checking content_tsv Column")
    print("=" * 80)

    # Check if column exists
    print("\n[1] Checking if content_tsv column exists...")
    cursor.execute("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'financial_chunks'
        AND column_name = 'content_tsv';
    """)
    result = cursor.fetchone()
    if result:
        print(f"✅ Column exists: {result['column_name']} ({result['data_type']})")
    else:
        print("❌ CRITICAL: content_tsv column does NOT exist!")
        return

    # Check if it's populated
    print("\n[2] Checking if content_tsv is populated...")
    cursor.execute("""
        SELECT
            COUNT(*) as total,
            COUNT(content_tsv) as populated,
            COUNT(*) - COUNT(content_tsv) as null_count
        FROM financial_chunks;
    """)
    result = cursor.fetchone()
    print(f"Total rows: {result['total']}")
    print(f"Populated: {result['populated']}")
    print(f"NULL: {result['null_count']}")

    if result["null_count"] > 0:
        print(f"❌ CRITICAL: {result['null_count']} chunks have NULL content_tsv!")
    else:
        print("✅ All chunks have content_tsv populated")

    # Check sample content_tsv values
    print("\n[3] Sample content_tsv values...")
    cursor.execute("""
        SELECT
            chunk_index,
            LEFT(content, 50) as content_preview,
            content_tsv::text as tsvector_value
        FROM financial_chunks
        LIMIT 3;
    """)
    rows = cursor.fetchall()
    for i, row in enumerate(rows, 1):
        print(f"\nChunk {i} (index {row['chunk_index']}):")
        print(f"  Content: {row['content_preview']}...")
        tsv = row["tsvector_value"]
        if tsv:
            print(f"  TSVector: {tsv[:100]}...")
        else:
            print("  TSVector: NULL ❌")

    # Test direct ts_query
    print("\n[4] Testing direct plainto_tsquery...")
    test_terms = ["cost", "variable", "EBITDA", "thermal", "energy"]
    for term in test_terms:
        cursor.execute("SELECT plainto_tsquery('english', %s)::text as query;", (term,))
        result = cursor.fetchone()
        print(f"  '{term}' → {result['query']}")

    # Test manual tsvector matching
    print("\n[5] Testing manual content search (bypassing tsvector)...")
    cursor.execute("""
        SELECT COUNT(*) as matches
        FROM financial_chunks
        WHERE content ILIKE '%variable%cost%';
    """)
    result = cursor.fetchone()
    print(f"  Manual 'variable cost' search: {result['matches']} matches")

    cursor.execute("""
        SELECT COUNT(*) as matches
        FROM financial_chunks
        WHERE content ILIKE '%EBITDA%';
    """)
    result = cursor.fetchone()
    print(f"  Manual 'EBITDA' search: {result['matches']} matches")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
