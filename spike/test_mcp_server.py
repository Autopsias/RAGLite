"""Test script for MCP server functionality.

Tests:
1. Tool discovery (health_check and query_financial_documents tools)
2. Health check execution
3. Query tool with sample financial query
"""

import asyncio
import sys
from pathlib import Path

import pytest

# Add spike directory to path
sys.path.insert(0, str(Path(__file__).parent))

from mcp_server import QueryRequest, check_health, execute_query  # noqa: E402


@pytest.mark.asyncio
async def test_health_check():
    """Test the health_check tool."""
    print("=" * 60)
    print("TEST 1: Health Check")
    print("=" * 60)

    try:
        result = await check_health()
        print("✓ Health check executed successfully\n")
        print("Status:")
        for key, value in result.items():
            if isinstance(value, dict):
                print(f"  {key}:")
                for k, v in value.items():
                    print(f"    {k}: {v}")
            else:
                print(f"  {key}: {value}")

        return result.get("qdrant") == "healthy"

    except Exception as e:
        print(f"✗ Health check failed: {e}")
        return False


@pytest.mark.asyncio
async def test_query_tool():
    """Test the query_financial_documents tool."""
    print("\n" + "=" * 60)
    print("TEST 2: Query Tool - Sample Financial Query")
    print("=" * 60)

    # Sample query
    test_query = "What are the main health and safety metrics?"

    try:
        request = QueryRequest(query=test_query, top_k=3)
        result = await execute_query(request)

        print("✓ Query executed successfully\n")
        print(f"Query: {result.query}")
        print(f"Results returned: {result.results_count}\n")

        for i, res in enumerate(result.results, 1):
            print(f"Result {i}:")
            print(f"  Score: {res.score:.4f}")
            print(f"  Source: {res.source_document}")
            print(f"  Page: {res.page_number}")
            print(f"  Chunk: {res.chunk_index}")
            print(f"  Words: {res.word_count}")
            print(f"  Text preview: {res.text[:150]}...")
            print()

        return result.results_count > 0

    except Exception as e:
        print(f"✗ Query tool failed: {e}")
        import traceback

        traceback.print_exc()
        return False


@pytest.mark.asyncio
async def test_multiple_queries():
    """Test with multiple diverse queries."""
    print("\n" + "=" * 60)
    print("TEST 3: Multiple Query Types")
    print("=" * 60)

    test_queries = [
        "What is the total revenue?",
        "Describe the safety performance",
        "What are the key metrics in the document?",
    ]

    results = []

    for query in test_queries:
        try:
            request = QueryRequest(query=query, top_k=2)
            result = await execute_query(request)
            results.append(result.results_count > 0)
            print(f"✓ Query '{query}': {result.results_count} results")

        except Exception as e:
            print(f"✗ Query '{query}' failed: {e}")
            results.append(False)

    success_rate = sum(results) / len(results) * 100
    print(f"\nSuccess rate: {success_rate:.1f}% ({sum(results)}/{len(results)} queries)")

    return all(results)


async def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("MCP SERVER FUNCTIONALITY TESTS")
    print("=" * 60 + "\n")

    # Test 1: Health check
    health_ok = await test_health_check()

    if not health_ok:
        print("\n⚠️  Health check failed. Ensure Qdrant is running and collection exists.")
        return

    # Test 2: Query tool
    query_ok = await test_query_tool()

    # Test 3: Multiple queries
    multi_ok = await test_multiple_queries()

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Health Check: {'✓ PASS' if health_ok else '✗ FAIL'}")
    print(f"Query Tool: {'✓ PASS' if query_ok else '✗ FAIL'}")
    print(f"Multiple Queries: {'✓ PASS' if multi_ok else '✗ FAIL'}")

    if health_ok and query_ok and multi_ok:
        print("\n✓ All tests passed! MCP server is functional.")
    else:
        print("\n⚠️  Some tests failed. Review errors above.")


if __name__ == "__main__":
    asyncio.run(main())
