#!/usr/bin/env python3
"""Diagnose what EBITDA data looks like in retrieved chunks - try different queries."""

import asyncio
import os

os.environ["APP_ENV"] = "production"

from raglite.retrieval.search import hybrid_search


async def diagnose_chunks():
    print("🔍 Testing different search queries for EBITDA data...\n")

    queries = [
        "consolidated results EBITDA millions euros Group Secil",
        "executive summary financial performance EBITDA",
        "consolidated P&L income statement EBITDA",
        "Secil Group EBITDA results million EUR",
        "financial highlights EBITDA performance",
    ]

    for query in queries:
        print(f"\n{'=' * 80}")
        print(f'QUERY: "{query}"')
        print("=" * 80)

        results = await hybrid_search(
            query=query,
            top_k=5,
            enable_hybrid=True,
            auto_classify=False,
            enable_sql_tables=False,
        )

        for i, result in enumerate(results[:3], 1):
            print(f"\n[CHUNK {i}] Score: {result.score:.4f} | Page: {result.page_number}")
            print(f"Source: {result.source_document}")
            print("-" * 80)
            text_preview = result.text[:600]
            print(text_preview)
            if len(result.text) > 600:
                print("...")


if __name__ == "__main__":
    asyncio.run(diagnose_chunks())
