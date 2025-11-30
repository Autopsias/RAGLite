#!/usr/bin/env python3
"""Root Cause Analysis for Story 2.15 - 0% Accuracy Investigation.

Performs deep diagnostic analysis to identify why all 14 normalized queries failed.

Usage:
    python scripts/root-cause-analysis-story-2.15.py

Output:
    docs/validation/story-2.15-root-cause-analysis.json
    docs/validation/story-2.15-rca-report.md
"""

import asyncio
import json
import time
from dataclasses import dataclass
from pathlib import Path

from raglite.retrieval.multi_index_search import multi_index_search
from raglite.retrieval.query_classifier import classify_query
from raglite.retrieval.search import hybrid_search, search_documents
from raglite.retrieval.sql_table_search import search_tables_sql
from raglite.shared.clients import get_postgresql_connection
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


@dataclass
class SearchResult:
    """Detailed search result for RCA."""

    source: str  # "SQL", "Vector", "Hybrid", "Multi-Index"
    result_count: int
    sample_content: str
    contains_keywords: list[str]
    structure_type: str
    error: str | None = None


@dataclass
class RCAFindings:
    """Root cause analysis findings for a single query."""

    query_id: int
    question: str
    expected_keywords: list[str]

    # Query classification
    query_type: str

    # Search results breakdown
    multi_index_results: SearchResult
    hybrid_search_results: SearchResult | None
    sql_search_results: SearchResult | None
    vector_search_results: SearchResult | None

    # Database availability
    keywords_in_database: dict[str, bool]
    database_sample_rows: int

    # Diagnosis
    root_cause: str
    recommended_fix: str


async def analyze_query(query_obj: dict) -> RCAFindings:
    """Deep analysis of a single failed query.

    Args:
        query_obj: Ground truth query object

    Returns:
        RCAFindings with complete diagnostic information
    """
    query_id = query_obj.get("id")
    question = query_obj.get("question")
    expected_keywords = query_obj.get("expected_keywords", [])

    logger.info(f"RCA: Analyzing query {query_id}: {question[:60]}...")

    # Step 1: Query Classification
    query_type_enum = classify_query(question)
    query_type = query_type_enum.value

    logger.info(f"RCA: Query classified as {query_type}")

    # Step 2: Multi-Index Search (what validation script uses)
    try:
        multi_results = await multi_index_search(question, top_k=5)

        # Extract content from results
        # SearchResult from multi_index_search has .text attribute
        contents = []
        for result in multi_results:
            if hasattr(result, "text"):
                contents.append(result.text)
            elif hasattr(result, "chunk") and hasattr(result.chunk, "content"):
                contents.append(result.chunk.content)
            elif hasattr(result, "content"):
                contents.append(result.content)
            elif hasattr(result, "chunk_text"):
                contents.append(result.chunk_text)
            else:
                # Log the result structure for diagnosis
                logger.warning(f"RCA: Unknown result structure: {type(result)} - {dir(result)}")
                contents.append(str(result))

        combined_content = " ".join(contents)

        # Check keywords
        found_keywords = [kw for kw in expected_keywords if kw.lower() in combined_content.lower()]

        multi_index_result = SearchResult(
            source="Multi-Index",
            result_count=len(multi_results),
            sample_content=combined_content[:500] if combined_content else "NO CONTENT EXTRACTED",
            contains_keywords=found_keywords,
            structure_type=str(type(multi_results[0])) if multi_results else "EMPTY",
        )
    except Exception as e:
        logger.error(f"RCA: Multi-index search failed: {e}", exc_info=True)
        multi_index_result = SearchResult(
            source="Multi-Index",
            result_count=0,
            sample_content="",
            contains_keywords=[],
            structure_type="ERROR",
            error=str(e),
        )

    # Step 3: Direct Hybrid Search (bypassing multi-index)
    try:
        hybrid_results = await hybrid_search(question, top_k=5)

        contents = []
        for result in hybrid_results:
            if hasattr(result, "chunk") and hasattr(result.chunk, "content"):
                contents.append(result.chunk.content)
            elif hasattr(result, "content"):
                contents.append(result.content)
            elif hasattr(result, "chunk_text"):
                contents.append(result.chunk_text)

        combined_content = " ".join(contents)
        found_keywords = [kw for kw in expected_keywords if kw.lower() in combined_content.lower()]

        hybrid_search_result = SearchResult(
            source="Hybrid",
            result_count=len(hybrid_results),
            sample_content=combined_content[:500] if combined_content else "NO CONTENT",
            contains_keywords=found_keywords,
            structure_type=str(type(hybrid_results[0])) if hybrid_results else "EMPTY",
        )
    except Exception as e:
        logger.error(f"RCA: Hybrid search failed: {e}", exc_info=True)
        hybrid_search_result = None

    # Step 4: Direct SQL Search
    sql_search_result = None
    try:
        # Try to get SQL query from classifier
        from raglite.retrieval.query_classifier import generate_sql_query

        sql_query = await generate_sql_query(question)
        if sql_query:
            sql_results = await search_tables_sql(sql_query)

            contents = [r.get("chunk_text", "") for r in sql_results if isinstance(r, dict)]
            combined_content = " ".join(contents)
            found_keywords = [
                kw for kw in expected_keywords if kw.lower() in combined_content.lower()
            ]

            sql_search_result = SearchResult(
                source="SQL",
                result_count=len(sql_results),
                sample_content=combined_content[:500] if combined_content else "NO CONTENT",
                contains_keywords=found_keywords,
                structure_type=str(type(sql_results[0])) if sql_results else "EMPTY",
            )
    except Exception as e:
        logger.error(f"RCA: SQL search failed: {e}", exc_info=True)

    # Step 5: Direct Vector Search
    try:
        vector_results = await search_documents(question, top_k=5)

        contents = []
        for result in vector_results:
            if hasattr(result, "chunk") and hasattr(result.chunk, "content"):
                contents.append(result.chunk.content)
            elif hasattr(result, "content"):
                contents.append(result.content)

        combined_content = " ".join(contents)
        found_keywords = [kw for kw in expected_keywords if kw.lower() in combined_content.lower()]

        vector_search_result = SearchResult(
            source="Vector",
            result_count=len(vector_results),
            sample_content=combined_content[:500] if combined_content else "NO CONTENT",
            contains_keywords=found_keywords,
            structure_type=str(type(vector_results[0])) if vector_results else "EMPTY",
        )
    except Exception as e:
        logger.error(f"RCA: Vector search failed: {e}", exc_info=True)
        vector_search_result = None

    # Step 6: Check if keywords exist in database at all
    conn = get_postgresql_connection()
    cursor = conn.cursor()

    keywords_in_db = {}
    for keyword in expected_keywords:
        cursor.execute(
            "SELECT COUNT(*) FROM financial_tables WHERE chunk_text ILIKE %s",
            (f"%{keyword}%",),
        )
        count = cursor.fetchone()[0]
        keywords_in_db[keyword] = count > 0

    # Sample database size
    cursor.execute("SELECT COUNT(*) FROM financial_tables")
    db_row_count = cursor.fetchone()[0]

    cursor.close()

    # Step 7: Diagnose root cause
    root_cause = diagnose_root_cause(
        multi_index_result,
        hybrid_search_result,
        sql_search_result,
        vector_search_result,
        keywords_in_db,
    )

    recommended_fix = generate_recommendation(root_cause, keywords_in_db)

    return RCAFindings(
        query_id=query_id,
        question=question,
        expected_keywords=expected_keywords,
        query_type=query_type,
        multi_index_results=multi_index_result,
        hybrid_search_results=hybrid_search_result,
        sql_search_results=sql_search_result,
        vector_search_results=vector_search_result,
        keywords_in_database=keywords_in_db,
        database_sample_rows=db_row_count,
        root_cause=root_cause,
        recommended_fix=recommended_fix,
    )


def diagnose_root_cause(
    multi_index: SearchResult,
    hybrid: SearchResult | None,
    sql: SearchResult | None,
    vector: SearchResult | None,
    keywords_in_db: dict[str, bool],
) -> str:
    """Diagnose the root cause of search failure.

    Args:
        multi_index: Multi-index search result
        hybrid: Hybrid search result
        sql: SQL search result
        vector: Vector search result
        keywords_in_db: Whether keywords exist in database

    Returns:
        Root cause diagnosis string
    """
    # Check if ANY keywords are in database
    any_keywords_found = any(keywords_in_db.values())

    if not any_keywords_found:
        return "KEYWORDS_NOT_IN_DATABASE: Expected keywords do not exist in financial_tables.chunk_text. Ground truth mismatch."

    # Check if multi-index returned results
    if multi_index.result_count == 0:
        return "MULTI_INDEX_NO_RESULTS: Multi-index search returned 0 results despite keywords in database. Search routing failure."

    # Check if content extraction failed
    if multi_index.sample_content == "NO CONTENT EXTRACTED":
        return "CONTENT_EXTRACTION_FAILURE: Results returned but content extraction failed. Result structure mismatch in validation script."

    # Check if results returned but keywords not found
    if multi_index.result_count > 0 and len(multi_index.contains_keywords) == 0:
        return "KEYWORD_MISMATCH: Search returned results but expected keywords not in retrieved content. Retrieval relevance issue."

    # Compare search methods
    if hybrid and hybrid.result_count > 0 and multi_index.result_count == 0:
        return "MULTI_INDEX_WRAPPER_BUG: Hybrid search works but multi-index wrapper fails. Wrapper implementation issue."

    return "UNKNOWN: Unable to diagnose root cause from available data."


def generate_recommendation(root_cause: str, keywords_in_db: dict[str, bool]) -> str:
    """Generate actionable recommendation based on root cause.

    Args:
        root_cause: Diagnosed root cause
        keywords_in_db: Keyword availability in database

    Returns:
        Recommended fix
    """
    if "KEYWORDS_NOT_IN_DATABASE" in root_cause:
        missing = [kw for kw, found in keywords_in_db.items() if not found]
        return (
            f"❌ Remove or replace ground truth queries. Missing keywords: {', '.join(missing[:5])}"
        )

    if "CONTENT_EXTRACTION_FAILURE" in root_cause:
        return "🔧 Fix validation script content extraction logic. Check result structure in multi_index_search return type."

    if "MULTI_INDEX_NO_RESULTS" in root_cause:
        return "🔧 Debug multi_index_search function. Check query classification and routing logic."

    if "KEYWORD_MISMATCH" in root_cause:
        return "🔧 Review retrieval relevance. Keywords exist but not retrieved - check BM25 tuning or re-ranking."

    if "MULTI_INDEX_WRAPPER_BUG" in root_cause:
        return "🔧 Debug multi_index_search wrapper. Hybrid search works but wrapper fails to return results."

    return "🔍 Further investigation needed. Review detailed findings."


async def run_rca() -> list[RCAFindings]:
    """Run root cause analysis on all failed queries."""
    print("=" * 80)
    print("ROOT CAUSE ANALYSIS - Story 2.15 0% Accuracy")
    print("=" * 80)
    print()

    # Load normalized ground truth
    ground_truth_path = Path("tests/ground_truth_normalized.json")
    with open(ground_truth_path) as f:
        ground_truth_data = json.load(f)

    queries = ground_truth_data.get("questions", [])
    total = len(queries)

    print(f"Analyzing {total} failed queries...")
    print()

    # Analyze first 3 queries in detail (representative sample)
    sample_size = min(3, total)
    findings: list[RCAFindings] = []

    for i, query_obj in enumerate(queries[:sample_size]):
        print(f"[{i + 1}/{sample_size}] Analyzing Query {query_obj['id']}...")
        finding = await analyze_query(query_obj)
        findings.append(finding)
        print(f"  → Root Cause: {finding.root_cause}")
        print()

    return findings


async def generate_rca_report(findings: list[RCAFindings]):
    """Generate detailed RCA report in markdown and JSON.

    Args:
        findings: List of RCA findings
    """
    # Aggregate root causes
    root_cause_counts = {}
    for finding in findings:
        cause = finding.root_cause.split(":")[0]  # Get just the category
        root_cause_counts[cause] = root_cause_counts.get(cause, 0) + 1

    # Most common root cause
    primary_root_cause = (
        max(root_cause_counts, key=root_cause_counts.get) if root_cause_counts else "UNKNOWN"
    )

    # Generate markdown report
    md_report = f"""# Root Cause Analysis Report - Story 2.15

**Date**: {time.strftime("%Y-%m-%d %H:%M:%S")}
**Issue**: 0% accuracy on Epic 2 final validation (14/14 queries failed)
**Stories Affected**: 2.11 (Hybrid Search), 2.14 (SQL Backend), 2.15 (Ground Truth Normalization)

## Executive Summary

**Primary Root Cause**: `{primary_root_cause}`

**Root Cause Distribution**:
"""

    for cause, count in sorted(root_cause_counts.items(), key=lambda x: -x[1]):
        md_report += f"- **{cause}**: {count} queries ({count / len(findings) * 100:.0f}%)\n"

    md_report += """

## Detailed Findings

"""

    for finding in findings:
        md_report += f"""### Query {finding.query_id}: {finding.question}

**Classification**: {finding.query_type}

**Expected Keywords**: {", ".join(finding.expected_keywords)}

**Keywords in Database**:
"""
        for kw, found in finding.keywords_in_database.items():
            status = "✅" if found else "❌"
            md_report += f"- {status} `{kw}`\n"

        md_report += f"""
**Multi-Index Search**:
- Results: {finding.multi_index_results.result_count}
- Keywords Found: {len(finding.multi_index_results.contains_keywords)}/{len(finding.expected_keywords)}
- Structure: `{finding.multi_index_results.structure_type}`
- Sample Content: {finding.multi_index_results.sample_content[:200] if finding.multi_index_results.sample_content else "NONE"}...

"""

        if finding.hybrid_search_results:
            md_report += f"""**Hybrid Search (Direct)**:
- Results: {finding.hybrid_search_results.result_count}
- Keywords Found: {len(finding.hybrid_search_results.contains_keywords)}/{len(finding.expected_keywords)}

"""

        if finding.sql_search_results:
            md_report += f"""**SQL Search (Direct)**:
- Results: {finding.sql_search_results.result_count}
- Keywords Found: {len(finding.sql_search_results.contains_keywords)}/{len(finding.expected_keywords)}

"""

        md_report += f"""**Root Cause**: {finding.root_cause}

**Recommended Fix**: {finding.recommended_fix}

---

"""

    md_report += """
## Recommendations

Based on the root cause analysis, implement the following fixes in priority order:

"""

    # Generate prioritized recommendations
    unique_recs = {f.recommended_fix for f in findings}
    for i, rec in enumerate(unique_recs, 1):
        md_report += f"{i}. {rec}\n"

    md_report += """

## Next Steps

1. Implement recommended fixes above
2. Re-run validation: `python scripts/validate-epic-2-final.py`
3. If still <70% accuracy, escalate to Phase 2B (Cross-Encoder Re-Ranking)

---

*Generated by Story 2.15 RCA Script*
"""

    # Save markdown report
    output_dir = Path("docs/validation")
    output_dir.mkdir(parents=True, exist_ok=True)

    md_path = output_dir / "story-2.15-rca-report.md"
    with open(md_path, "w") as f:
        f.write(md_report)

    print(f"✅ Markdown report saved: {md_path}")

    # Save JSON data
    json_path = output_dir / "story-2.15-root-cause-analysis.json"
    json_data = {
        "metadata": {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "queries_analyzed": len(findings),
            "primary_root_cause": primary_root_cause,
            "root_cause_distribution": root_cause_counts,
        },
        "findings": [
            {
                "query_id": f.query_id,
                "question": f.question,
                "expected_keywords": f.expected_keywords,
                "query_type": f.query_type,
                "multi_index": {
                    "result_count": f.multi_index_results.result_count,
                    "keywords_found": f.multi_index_results.contains_keywords,
                    "structure_type": f.multi_index_results.structure_type,
                    "sample_content": f.multi_index_results.sample_content[:500],
                },
                "keywords_in_database": f.keywords_in_database,
                "database_rows": f.database_sample_rows,
                "root_cause": f.root_cause,
                "recommended_fix": f.recommended_fix,
            }
            for f in findings
        ],
    }

    with open(json_path, "w") as f:
        json.dump(json_data, f, indent=2)

    print(f"✅ JSON data saved: {json_path}")


async def main():
    """Main RCA execution."""
    print()
    print("Starting Root Cause Analysis...")
    print()

    try:
        findings = await run_rca()

        print("=" * 80)
        print()
        print("RCA Complete! Generating reports...")
        print()

        await generate_rca_report(findings)

        print()
        print("=" * 80)
        print("SUMMARY")
        print("=" * 80)

        # Show primary root cause
        root_causes = [f.root_cause.split(":")[0] for f in findings]
        from collections import Counter

        cause_counts = Counter(root_causes)
        primary = cause_counts.most_common(1)[0]

        print(f"Primary Root Cause: {primary[0]} ({primary[1]}/{len(findings)} queries)")
        print()
        print("Next: Review docs/validation/story-2.15-rca-report.md for detailed findings")
        print()

    except Exception as e:
        logger.error(f"RCA failed: {e}", exc_info=True)
        print(f"\n❌ RCA failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
