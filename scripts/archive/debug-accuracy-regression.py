"""Debug why accuracy regressed from 52% to 46% after query preprocessing."""

import asyncio

from raglite.retrieval.multi_index_search import multi_index_search
from raglite.retrieval.query_classifier import classify_query
from raglite.retrieval.query_preprocessing import preprocess_query_for_table_search
from tests.fixtures.ground_truth import GROUND_TRUTH_QA


async def debug_single_query(qa):
    """Debug how a single query is processed."""
    question = qa["question"]
    print(f"\nQuery: {question}")
    print("=" * 80)

    # Step 1: Query classification
    query_type = classify_query(question)
    print(f"1. Classification: {query_type.value}")

    # Step 2: Query preprocessing (used in SQL search)
    keywords, filters = preprocess_query_for_table_search(question)
    print("2. Preprocessing:")
    print(f"   Keywords: {keywords}")
    print(f"   Filters:  {filters}")

    # Step 3: Execute multi-index search
    try:
        results = await multi_index_search(question, top_k=5)
        print(f"3. Results: {len(results)} chunks returned")
        if results:
            print(f"   Top result source: {results[0].source}")
            print(f"   Top result score: {results[0].score:.4f}")
    except Exception as e:
        print(f"3. Error: {e}")


async def main():
    """Analyze first 5 queries to understand classification and preprocessing."""
    print("=" * 80)
    print("DEBUG: Accuracy Regression Analysis")
    print("=" * 80)

    for qa in GROUND_TRUTH_QA[:5]:
        await debug_single_query(qa)

    print("\n" + "=" * 80)
    print("Analysis Summary:")
    print("=" * 80)
    print()
    print("Key hypothesis: Query classification might be routing some queries")
    print("to SQL-only mode, and those are failing completely instead of falling")
    print("back to vector search.")
    print()
    print("If classification routes to SQL_ONLY and SQL returns 0 results,")
    print("the fallback should switch to vector search - check if this is working.")


if __name__ == "__main__":
    asyncio.run(main())
