"""Diagnostic script to investigate Phase 2A zero improvement root causes."""

import sys

from psycopg2.extras import RealDictCursor

from raglite.shared.clients import get_postgresql_connection


def main():
    """Run comprehensive diagnostics on Phase 2A implementation."""
    print("=" * 80)
    print("Phase 2A Root Cause Diagnostics")
    print("=" * 80)

    try:
        conn = get_postgresql_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Check 1: Total chunks in PostgreSQL
        print("\n[CHECK 1] PostgreSQL Chunk Count")
        print("-" * 80)
        cursor.execute("SELECT COUNT(*) as total FROM financial_chunks;")
        result = cursor.fetchone()
        total_chunks = result["total"] if result else 0
        print(f"Total chunks in PostgreSQL: {total_chunks}")
        print("Expected: 264 (from ingestion)")
        if total_chunks == 0:
            print("❌ CRITICAL: PostgreSQL has NO chunks! Story 2.6 failed silently.")
        elif total_chunks == 264:
            print("✅ PostgreSQL chunk count matches ingestion")
        else:
            print(f"⚠️  WARNING: Chunk count mismatch (expected 264, got {total_chunks})")

        # Check 2: Metadata population rate
        print("\n[CHECK 2] Metadata Population Rate")
        print("-" * 80)

        metadata_fields = [
            "metric_category",
            "company_name",
            "reporting_period",
            "time_granularity",
            "section_type",
            "units",
            "table_name",
            "table_context",
        ]

        for field in metadata_fields:
            cursor.execute(
                f"SELECT COUNT(*) as populated FROM financial_chunks WHERE {field} IS NOT NULL;"
            )
            result = cursor.fetchone()
            populated = result["populated"] if result else 0
            percentage = (populated / total_chunks * 100) if total_chunks > 0 else 0
            status = "✅" if percentage > 50 else "⚠️" if percentage > 10 else "❌"
            print(f"{status} {field:20s}: {populated:3d}/{total_chunks} ({percentage:5.1f}%)")

        # Check 3: Section type distribution
        print("\n[CHECK 3] Section Type Distribution (Table vs Other)")
        print("-" * 80)
        cursor.execute("""
            SELECT
                section_type,
                COUNT(*) as count,
                ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) as percentage
            FROM financial_chunks
            GROUP BY section_type
            ORDER BY count DESC;
        """)
        rows = cursor.fetchall()
        for row in rows:
            section = row["section_type"] if row["section_type"] else "(null)"
            count = row["count"]
            pct = row["percentage"]
            print(f"  {section:20s}: {count:3d} chunks ({pct:5.1f}%)")

        # Check 4: Sample metadata for inspection
        print("\n[CHECK 4] Sample Chunk Metadata (First 3 with metadata)")
        print("-" * 80)
        cursor.execute("""
            SELECT
                chunk_index,
                page_number,
                section_type,
                metric_category,
                company_name,
                reporting_period,
                LEFT(content, 100) as content_preview
            FROM financial_chunks
            WHERE metric_category IS NOT NULL
            LIMIT 3;
        """)
        rows = cursor.fetchall()
        for i, row in enumerate(rows, 1):
            print(f"\nChunk {i}:")
            print(f"  Page: {row['page_number']}, Index: {row['chunk_index']}")
            print(f"  Section: {row['section_type']}")
            print(f"  Category: {row['metric_category']}")
            print(f"  Company: {row['company_name']}")
            print(f"  Period: {row['reporting_period']}")
            print(f"  Content: {row['content_preview']}...")

        # Check 5: Full-text search test
        print("\n[CHECK 5] PostgreSQL Full-Text Search Test")
        print("-" * 80)
        test_queries = [
            "variable cost",
            "EBITDA",
            "thermal energy",
        ]

        for query in test_queries:
            cursor.execute(
                """
                SELECT COUNT(*) as matches
                FROM financial_chunks
                WHERE content_tsv @@ plainto_tsquery('english', %s);
            """,
                (query,),
            )
            result = cursor.fetchone()
            matches = result["matches"] if result else 0
            print(f"  '{query}': {matches} matches")

        # Check 6: Table-only restriction impact
        print("\n[CHECK 6] Impact of Table-Only Restriction")
        print("-" * 80)
        for query in test_queries:
            # All chunks
            cursor.execute(
                """
                SELECT COUNT(*) as matches
                FROM financial_chunks
                WHERE content_tsv @@ plainto_tsquery('english', %s);
            """,
                (query,),
            )
            all_matches = cursor.fetchone()["matches"]

            # Table-only chunks
            cursor.execute(
                """
                SELECT COUNT(*) as matches
                FROM financial_chunks
                WHERE content_tsv @@ plainto_tsquery('english', %s)
                  AND section_type = 'Table';
            """,
                (query,),
            )
            table_matches = cursor.fetchone()["matches"]

            lost_pct = ((all_matches - table_matches) / all_matches * 100) if all_matches > 0 else 0
            print(f"  '{query}':")
            print(f"    All chunks: {all_matches} matches")
            print(f"    Table-only: {table_matches} matches")
            print(f"    Lost: {all_matches - table_matches} ({lost_pct:.1f}%)")

        print("\n" + "=" * 80)
        print("Diagnostics Complete")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ Error during diagnostics: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
