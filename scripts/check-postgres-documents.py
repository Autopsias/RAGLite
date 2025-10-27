#!/usr/bin/env python3
"""Check which documents are in PostgreSQL."""

from raglite.shared.clients import get_postgresql_connection

conn = get_postgresql_connection()
cursor = conn.cursor()

# Check document_ids
cursor.execute("""
    SELECT document_id, COUNT(*) as row_count
    FROM financial_tables
    GROUP BY document_id
    ORDER BY row_count DESC;
""")

print("Documents in PostgreSQL:")
for doc_id, count in cursor.fetchall():
    print(f"  - {doc_id}: {count:,} rows")

cursor.close()
conn.close()
