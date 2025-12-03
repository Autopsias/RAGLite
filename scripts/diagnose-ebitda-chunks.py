#!/usr/bin/env python3
"""Diagnose what EBITDA data looks like in retrieved chunks."""

import asyncio
import os

os.environ["APP_ENV"] = "production"

from raglite.retrieval.search import hybrid_search


async def diagnose_chunks():
    print("🔍 Diagnosing EBITDA chunk content...\n")

    # Search for EBITDA mentions
    results = await hybrid_search(
        query="consolidated EBITDA 2025 performance review total group",
        top_k=20,
        enable_hybrid=True,
        auto_classify=False,
        enable_sql_tables=False,
    )

    print(f"Retrieved {len(results)} chunks\n")
    print("=" * 80)

    for i, result in enumerate(results[:10], 1):
        print(f"\n[CHUNK {i}] Score: {result.score:.4f}")
        print(f"Source: {result.source_document}")
        print(f"Page: {result.page_number}")
        print("-" * 80)
        print(result.text[:800])  # First 800 chars
        print("..." if len(result.text) > 800 else "")
        print("=" * 80)


if __name__ == "__main__":
    asyncio.run(diagnose_chunks())
