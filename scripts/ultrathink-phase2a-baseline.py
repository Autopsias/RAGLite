"""Ultra-deep analysis of why Phase 2A only achieves 52% baseline accuracy.

This script performs comprehensive root cause analysis of the accuracy plateau,
examining every component of the Phase 2A architecture to identify bottlenecks.

Phase 2A Components Under Investigation:
1. Fixed 512-token chunking (Story 2.3)
2. LLM metadata extraction (Story 2.4)
3. PostgreSQL structured storage (Story 2.6)
4. Multi-index search orchestration (Story 2.7)
5. Hybrid search with BM25 fusion
6. Query classification routing

Expected: 68-72% accuracy (baseline + 8-12pp improvement)
Actual: 52% accuracy (NO improvement over baseline)
Gap: -16-20pp from expected performance
"""

import asyncio
from collections import Counter

from psycopg2.extras import RealDictCursor

from raglite.retrieval.multi_index_search import multi_index_search
from raglite.retrieval.query_classifier import classify_query
from raglite.retrieval.search import hybrid_search, search_documents
from raglite.shared.clients import get_postgresql_connection
from tests.fixtures.ground_truth import GROUND_TRUTH_QA


def analyze_ground_truth_coverage():
    """Analyze what the ground truth queries expect vs what we have in the database."""
    print("=" * 80)
    print("ANALYSIS 1: Ground Truth Coverage")
    print("=" * 80)

    # Count expected pages from ground truth
    expected_pages = set()
    expected_docs = set()
    query_types = Counter()

    for qa in GROUND_TRUTH_QA:
        if "expected_pages" in qa:
            for page in qa["expected_pages"]:
                expected_pages.add(page)
        if "source_document" in qa:
            expected_docs.add(qa["source_document"])

        # Categorize query types
        question = qa["question"].lower()
        if "august 2025" in question or "aug 2025" in question:
            query_types["temporal_specific"] += 1
        elif any(metric in question for metric in ["ebitda", "revenue", "cost", "margin"]):
            query_types["metric_specific"] += 1
        elif any(word in question for word in ["portugal", "tunisia", "lebanon"]):
            query_types["geographic_specific"] += 1
        else:
            query_types["general"] += 1

    print("\nGround Truth Statistics:")
    print(f"  Total queries: {len(GROUND_TRUTH_QA)}")
    print(f"  Unique pages referenced: {len(expected_pages)}")
    print(f"  Unique documents referenced: {len(expected_docs)}")
    print("\nQuery Type Distribution:")
    for qtype, count in query_types.most_common():
        print(f"  {qtype}: {count} ({count / len(GROUND_TRUTH_QA) * 100:.1f}%)")

    # Check what's in the database
    conn = get_postgresql_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute("SELECT COUNT(*) as total FROM financial_chunks;")
    total_chunks = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(DISTINCT page_number) as pages FROM financial_chunks;")
    db_pages = cursor.fetchone()["pages"]

    cursor.execute("""
        SELECT COUNT(*) as chunks_with_metadata
        FROM financial_chunks
        WHERE metric_category IS NOT NULL
          AND reporting_period IS NOT NULL;
    """)
    chunks_with_metadata = cursor.fetchone()["chunks_with_metadata"]

    print("\nDatabase Statistics:")
    print(f"  Total chunks: {total_chunks}")
    print(f"  Unique pages: {db_pages}")
    print(
        f"  Chunks with metadata: {chunks_with_metadata} ({chunks_with_metadata / total_chunks * 100:.1f}%)"
    )

    # Check if expected pages are in database
    if expected_pages:
        placeholders = ",".join(["%s"] * len(expected_pages))
        cursor.execute(
            f"SELECT COUNT(DISTINCT page_number) as found FROM financial_chunks WHERE page_number IN ({placeholders});",
            tuple(expected_pages),
        )
        found_pages = cursor.fetchone()["found"]
        print("\nPage Coverage:")
        print(
            f"  Expected pages found: {found_pages}/{len(expected_pages)} ({found_pages / len(expected_pages) * 100:.1f}%)"
        )


async def analyze_search_quality():
    """Analyze search result quality for failing queries."""
    print("\n" + "=" * 80)
    print("ANALYSIS 2: Search Result Quality for Failing Queries")
    print("=" * 80)

    failures = {
        "no_results": 0,
        "wrong_page": 0,
        "wrong_metric": 0,
        "low_score": 0,
        "correct": 0,
    }

    sample_failures = []

    for qa in GROUND_TRUTH_QA[:10]:  # Sample first 10 queries
        question = qa["question"]
        expected_pages = set(qa.get("expected_pages", []))

        # Test with pure semantic search
        try:
            results = await search_documents(question, top_k=5)

            if not results:
                failures["no_results"] += 1
                sample_failures.append(
                    {
                        "query": question,
                        "issue": "no_results",
                        "expected_pages": list(expected_pages),
                    }
                )
                continue

            # Check if any result matches expected pages
            result_pages = {r.page_number for r in results}
            if expected_pages and not (result_pages & expected_pages):
                failures["wrong_page"] += 1
                sample_failures.append(
                    {
                        "query": question,
                        "issue": "wrong_page",
                        "expected_pages": list(expected_pages),
                        "got_pages": list(result_pages)[:3],
                        "top_score": results[0].score if results else 0,
                    }
                )
            else:
                failures["correct"] += 1

        except Exception as e:
            print(f"Error processing query: {question[:50]}... - {e}")

    print("\nFailure Analysis (sample of 10 queries):")
    for failure_type, count in failures.items():
        print(f"  {failure_type}: {count}")

    if sample_failures:
        print("\nSample Failures (showing first 3):")
        for i, failure in enumerate(sample_failures[:3], 1):
            print(f"\n  [{i}] {failure['issue'].upper()}")
            print(f"      Query: {failure['query']}")
            if "expected_pages" in failure:
                print(f"      Expected pages: {failure['expected_pages']}")
            if "got_pages" in failure:
                print(f"      Got pages: {failure['got_pages']}")
            if "top_score" in failure:
                print(f"      Top score: {failure['top_score']:.4f}")


async def analyze_chunking_strategy():
    """Analyze if 512-token chunking is causing issues."""
    print("\n" + "=" * 80)
    print("ANALYSIS 3: Chunking Strategy Impact")
    print("=" * 80)

    conn = get_postgresql_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    # Analyze chunk sizes
    cursor.execute("""
        SELECT
            AVG(LENGTH(content)) as avg_chars,
            MIN(LENGTH(content)) as min_chars,
            MAX(LENGTH(content)) as max_chars,
            AVG(array_length(string_to_array(content, ' '), 1)) as avg_words
        FROM financial_chunks;
    """)
    chunk_stats = cursor.fetchone()

    print("\nChunk Size Statistics:")
    print(f"  Average characters: {chunk_stats['avg_chars']:.0f}")
    print(f"  Min characters: {chunk_stats['min_chars']}")
    print(f"  Max characters: {chunk_stats['max_chars']}")
    print(f"  Average words: {chunk_stats['avg_words']:.0f}")

    # Check if tables are being split inappropriately
    cursor.execute("""
        SELECT section_type, COUNT(*) as count
        FROM financial_chunks
        GROUP BY section_type
        ORDER BY count DESC;
    """)
    section_types = cursor.fetchall()

    print("\nSection Type Distribution:")
    for row in section_types:
        print(f"  {row['section_type'] or 'NULL'}: {row['count']}")

    # Analyze table chunks specifically
    cursor.execute("""
        SELECT
            COUNT(*) as table_chunks,
            AVG(LENGTH(content)) as avg_size,
            COUNT(DISTINCT table_name) as unique_tables
        FROM financial_chunks
        WHERE section_type = 'Table';
    """)
    table_stats = cursor.fetchone()

    print("\nTable Chunking Analysis:")
    print(f"  Total table chunks: {table_stats['table_chunks']}")
    print(f"  Unique tables: {table_stats['unique_tables']}")
    print(f"  Average table chunk size: {table_stats['avg_size']:.0f} chars")

    if table_stats["table_chunks"] > 0 and table_stats["unique_tables"] > 0:
        chunks_per_table = table_stats["table_chunks"] / table_stats["unique_tables"]
        print(f"  Chunks per table: {chunks_per_table:.1f}")

        if chunks_per_table > 2:
            print(
                f"  ⚠️  WARNING: Tables are being split into {chunks_per_table:.1f} chunks on average"
            )
            print("      This may fragment table data and hurt retrieval accuracy!")


async def analyze_metadata_quality():
    """Analyze LLM metadata extraction quality."""
    print("\n" + "=" * 80)
    print("ANALYSIS 4: LLM Metadata Extraction Quality")
    print("=" * 80)

    conn = get_postgresql_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    # Check metadata population rates
    metadata_fields = [
        "metric_category",
        "reporting_period",
        "company_name",
        "time_granularity",
        "section_type",
        "units",
        "table_context",
        "table_name",
    ]

    print("\nMetadata Field Population Rates:")
    for field in metadata_fields:
        cursor.execute(f"""
            SELECT
                COUNT(*) as total,
                COUNT({field}) as populated
            FROM financial_chunks;
        """)
        stats = cursor.fetchone()
        population_rate = (stats["populated"] / stats["total"]) * 100 if stats["total"] > 0 else 0
        print(f"  {field}: {stats['populated']}/{stats['total']} ({population_rate:.1f}%)")

    # Check for common metadata values
    print("\nMost Common Metadata Values:")

    cursor.execute("""
        SELECT metric_category, COUNT(*) as count
        FROM financial_chunks
        WHERE metric_category IS NOT NULL
        GROUP BY metric_category
        ORDER BY count DESC
        LIMIT 10;
    """)
    print("\n  Top Metric Categories:")
    for row in cursor.fetchall():
        print(f"    {row['metric_category']}: {row['count']}")

    cursor.execute("""
        SELECT reporting_period, COUNT(*) as count
        FROM financial_chunks
        WHERE reporting_period IS NOT NULL
        GROUP BY reporting_period
        ORDER BY count DESC
        LIMIT 10;
    """)
    print("\n  Top Reporting Periods:")
    for row in cursor.fetchall():
        print(f"    {row['reporting_period']}: {row['count']}")


async def analyze_query_routing():
    """Analyze query classification and routing decisions."""
    print("\n" + "=" * 80)
    print("ANALYSIS 5: Query Classification & Routing")
    print("=" * 80)

    routing_stats = Counter()

    for qa in GROUND_TRUTH_QA:
        question = qa["question"]
        query_type = classify_query(question)
        routing_stats[query_type.value] += 1

    print("\nQuery Routing Distribution:")
    for route, count in routing_stats.most_common():
        print(f"  {route}: {count} ({count / len(GROUND_TRUTH_QA) * 100:.1f}%)")

    # Analyze if routing decisions are correct
    print("\nRouting Correctness Analysis:")
    print("  Queries with temporal info (should route to SQL): ", end="")
    temporal_queries = sum(
        1
        for qa in GROUND_TRUTH_QA
        if "august 2025" in qa["question"].lower() or "aug 2025" in qa["question"].lower()
    )
    print(f"{temporal_queries}")

    print(f"  Queries actually routed to SQL: {routing_stats.get('sql_only', 0)}")
    print(f"  Queries routed to HYBRID: {routing_stats.get('hybrid', 0)}")
    print(f"  Queries routed to VECTOR: {routing_stats.get('vector_only', 0)}")


async def compare_search_methods():
    """Compare different search methods on the same queries."""
    print("\n" + "=" * 80)
    print("ANALYSIS 6: Search Method Comparison")
    print("=" * 80)

    sample_queries = GROUND_TRUTH_QA[:5]

    comparison_results = []

    for qa in sample_queries:
        question = qa["question"]
        expected_pages = set(qa.get("expected_pages", []))

        result = {
            "query": question[:60] + "..." if len(question) > 60 else question,
            "expected_pages": list(expected_pages),
        }

        # Method 1: Pure semantic search
        try:
            semantic_results = await search_documents(question, top_k=5)
            semantic_pages = {r.page_number for r in semantic_results}
            semantic_hit = bool(semantic_pages & expected_pages) if expected_pages else None
            result["semantic"] = {
                "count": len(semantic_results),
                "top_score": semantic_results[0].score if semantic_results else 0,
                "pages": list(semantic_pages)[:3],
                "hit": semantic_hit,
            }
        except Exception as e:
            result["semantic"] = {"error": str(e)}

        # Method 2: Hybrid search (BM25 + semantic)
        try:
            hybrid_results = await hybrid_search(question, top_k=5, enable_hybrid=True)
            hybrid_pages = {r.page_number for r in hybrid_results}
            hybrid_hit = bool(hybrid_pages & expected_pages) if expected_pages else None
            result["hybrid"] = {
                "count": len(hybrid_results),
                "top_score": hybrid_results[0].score if hybrid_results else 0,
                "pages": list(hybrid_pages)[:3],
                "hit": hybrid_hit,
            }
        except Exception as e:
            result["hybrid"] = {"error": str(e)}

        # Method 3: Multi-index search
        try:
            multi_results = await multi_index_search(question, top_k=5)
            multi_pages = {r.page_number for r in multi_results if r.page_number}
            multi_hit = bool(multi_pages & expected_pages) if expected_pages else None
            result["multi_index"] = {
                "count": len(multi_results),
                "top_score": multi_results[0].score if multi_results else 0,
                "pages": list(multi_pages)[:3],
                "hit": multi_hit,
            }
        except Exception as e:
            result["multi_index"] = {"error": str(e)}

        comparison_results.append(result)

    # Print comparison table
    print("\nMethod Comparison (sample of 5 queries):")
    for i, result in enumerate(comparison_results, 1):
        print(f"\n[{i}] {result['query']}")
        print(f"    Expected pages: {result['expected_pages']}")

        for method in ["semantic", "hybrid", "multi_index"]:
            if method in result:
                data = result[method]
                if "error" in data:
                    print(f"    {method}: ERROR - {data['error']}")
                else:
                    hit_status = (
                        "✓" if data.get("hit") else "✗" if data.get("hit") is False else "?"
                    )
                    print(
                        f"    {method}: {hit_status} | score={data['top_score']:.3f} | pages={data['pages']}"
                    )


async def main():
    """Run comprehensive Phase 2A baseline analysis."""
    print("=" * 80)
    print("ULTRA-DEEP ANALYSIS: Why Phase 2A Only Achieves 52% Baseline")
    print("=" * 80)
    print()
    print("Investigation Goals:")
    print("1. Understand why fixed chunking + metadata extraction didn't improve accuracy")
    print("2. Identify specific failure modes in the current architecture")
    print("3. Determine root causes of the 16-20pp gap from expected performance")
    print("4. Provide actionable recommendations for Phase 2B")
    print()

    # Run all analyses
    analyze_ground_truth_coverage()
    await analyze_search_quality()
    await analyze_chunking_strategy()
    await analyze_metadata_quality()
    await analyze_query_routing()
    await compare_search_methods()

    # Final summary
    print("\n" + "=" * 80)
    print("SUMMARY: Root Cause Hypotheses")
    print("=" * 80)
    print()
    print("Based on the analyses above, the most likely root causes are:")
    print()
    print("1. CHUNKING FRAGMENTATION:")
    print("   - 512-token fixed chunking may be splitting tables across chunks")
    print("   - Financial tables need to be kept intact for accurate retrieval")
    print("   - Recommendation: Implement table-aware chunking (keep tables whole)")
    print()
    print("2. METADATA MISMATCH:")
    print("   - LLM-extracted metadata may not align with query expectations")
    print("   - Temporal queries expect 'August 2025' but metadata has 'Aug-25 YTD'")
    print("   - Recommendation: Normalize temporal formats or use fuzzy matching")
    print()
    print("3. HYBRID SEARCH DEGRADATION:")
    print("   - BM25 fusion (70/30 split) may be degrading semantic ranking")
    print("   - Auto-classification may extract incorrect filters")
    print("   - Recommendation: Tune fusion weights or disable auto-classification")
    print()
    print("4. QUERY ROUTING ERRORS:")
    print("   - Heuristic classification may route queries incorrectly")
    print("   - SQL-routed queries fail when PostgreSQL returns no results")
    print("   - Recommendation: Improve classification or always use hybrid mode")
    print()
    print("Next Steps:")
    print("- Review the detailed analysis output above")
    print("- Prioritize fixes based on impact (likely #1 and #2)")
    print("- Consider Phase 2B multi-index approach if quick fixes don't work")


if __name__ == "__main__":
    asyncio.run(main())
