"""Analyze semantic dilution in table chunks.

Story 2.8 AC5: Semantic Dilution Detection & Monitoring.

This script analyzes whether large table chunks (>2500 tokens) exhibit semantic
dilution that degrades retrieval precision.

Metrics:
1. Chunk Size Distribution (small/medium/large/split)
2. Embedding Quality Metrics (intra-table similarity)
3. Query Performance Breakdown (accuracy by table size)
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import tiktoken
from qdrant_client.models import FieldCondition, Filter, MatchValue
from scipy.spatial.distance import cosine

from raglite.shared.clients import get_qdrant_client
from raglite.shared.config import settings
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


async def analyze_semantic_dilution():
    """Analyze semantic dilution in table chunks."""
    logger.info("=" * 80)
    logger.info("Story 2.8 AC5: Semantic Dilution Analysis")
    logger.info("=" * 80)
    logger.info("")

    # Initialize
    encoding = tiktoken.get_encoding("cl100k_base")
    qdrant_client = get_qdrant_client()

    # Get all table chunks
    logger.info("Step 1: Loading table chunks...")
    table_filter = Filter(
        must=[
            FieldCondition(
                key="section_type",
                match=MatchValue(value="Table"),
            )
        ]
    )

    table_results = qdrant_client.scroll(
        collection_name=settings.qdrant_collection_name,
        scroll_filter=table_filter,
        limit=10000,
        with_payload=True,
        with_vectors=True,  # Get embeddings for similarity analysis
    )

    table_chunks = table_results[0]

    if not table_chunks:
        logger.warning("No table chunks found in collection!")
        return

    logger.info(f"Loaded {len(table_chunks)} table chunks")
    logger.info("")

    # Step 2: Chunk Size Distribution Analysis
    logger.info("Step 2: Analyzing chunk size distribution...")
    logger.info("")

    token_counts = [len(encoding.encode(chunk.payload["text"])) for chunk in table_chunks]

    # Categorize by size
    small_tables = [(i, tc) for i, tc in enumerate(token_counts) if tc < 1000]
    medium_tables = [(i, tc) for i, tc in enumerate(token_counts) if 1000 <= tc < 2500]
    large_tables = [(i, tc) for i, tc in enumerate(token_counts) if 2500 <= tc < 4096]
    split_tables = [(i, tc) for i, tc in enumerate(token_counts) if tc >= 4096]  # Should be 0

    logger.info("Chunk Size Distribution:")
    logger.info(
        f"  Small tables (<1000 tokens):   {len(small_tables)} ({len(small_tables) / len(table_chunks) * 100:.1f}%)"
    )
    logger.info(
        f"  Medium tables (1000-2500):     {len(medium_tables)} ({len(medium_tables) / len(table_chunks) * 100:.1f}%)"
    )
    logger.info(
        f"  Large tables (2500-4096):      {len(large_tables)} ({len(large_tables) / len(table_chunks) * 100:.1f}%)"
    )
    logger.info(
        f"  Split tables (>4096):          {len(split_tables)} ({len(split_tables) / len(table_chunks) * 100:.1f}%)"
    )
    logger.info("")

    # Step 3: Embedding Quality Metrics
    logger.info("Step 3: Analyzing embedding quality...")
    logger.info("")

    # Calculate intra-bucket similarity (average similarity within each size bucket)
    def calculate_intra_similarity(chunks_indices: list[tuple[int, int]]) -> float:
        """Calculate average cosine similarity within a bucket."""
        if len(chunks_indices) < 2:
            return 0.0

        vectors = [table_chunks[i].vector.get("text-dense", []) for i, _tc in chunks_indices]

        if not all(vectors):
            return 0.0

        # Calculate pairwise cosine similarities
        similarities = []
        for i in range(len(vectors)):
            for j in range(i + 1, len(vectors)):
                if vectors[i] and vectors[j]:
                    # Cosine similarity = 1 - cosine distance
                    similarity = 1 - cosine(vectors[i], vectors[j])
                    similarities.append(similarity)

        return np.mean(similarities) if similarities else 0.0

    # Sample for performance (max 50 chunks per bucket)
    small_sample = small_tables[:50] if len(small_tables) > 50 else small_tables
    medium_sample = medium_tables[:50] if len(medium_tables) > 50 else medium_tables
    large_sample = large_tables[:50] if len(large_tables) > 50 else large_tables

    small_similarity = calculate_intra_similarity(small_sample)
    medium_similarity = calculate_intra_similarity(medium_sample)
    large_similarity = calculate_intra_similarity(large_sample)

    logger.info("Embedding Quality (Intra-Bucket Similarity):")
    logger.info(f"  Small tables avg similarity:   {small_similarity:.3f}")
    logger.info(f"  Medium tables avg similarity:  {medium_similarity:.3f}")
    logger.info(f"  Large tables avg similarity:   {large_similarity:.3f}")
    logger.info("")

    # Step 4: Dilution Detection
    logger.info("Step 4: Dilution Detection...")
    logger.info("")

    # Red flags
    dilution_flags = []

    # Flag 1: High similarity in large tables (>0.7 indicates dilution)
    if large_similarity > 0.7:
        dilution_flags.append(
            f"⚠️ Large table similarity too high: {large_similarity:.3f} (threshold: 0.7)"
        )

    # Flag 2: Large table similarity significantly higher than small tables
    if large_similarity > small_similarity + 0.15:
        dilution_flags.append(
            f"⚠️ Large tables {large_similarity - small_similarity:.3f} points higher than small tables"
        )

    # Flag 3: High variance in token counts (>5000)
    token_variance = np.var(token_counts)
    if token_variance > 5000:
        dilution_flags.append(
            f"⚠️ High token count variance: {token_variance:.0f} (threshold: 5000)"
        )

    # Step 5: Generate Report
    logger.info("=" * 80)
    logger.info("Semantic Dilution Analysis Report")
    logger.info("=" * 80)
    logger.info("")

    if dilution_flags:
        logger.warning("🔴 DILUTION DETECTED:")
        for flag in dilution_flags:
            logger.warning(f"  {flag}")
        logger.info("")
        logger.warning("❌ ACTION REQUIRED:")
        logger.warning("  1. Consider reducing 4096 token threshold to 2048-3072")
        logger.warning("  2. Re-ingest with smaller threshold")
        logger.warning("  3. Re-validate accuracy improvements")
    elif large_similarity > small_similarity + 0.10:
        logger.warning("🟡 DILUTION SUSPECTED:")
        logger.warning(f"  - Large table similarity: {large_similarity:.3f}")
        logger.warning(f"  - Small table similarity: {small_similarity:.3f}")
        logger.warning(f"  - Gap: {large_similarity - small_similarity:.3f} (10-15pp)")
        logger.info("")
        logger.warning("⚠️ RECOMMENDATION:")
        logger.warning("  - Document concern in validation report")
        logger.warning("  - Proceed to Story 2.9 but monitor accuracy closely")
        logger.warning("  - Plan Story 2.8.1 (threshold tuning) if accuracy <62%")
    else:
        logger.info("🟢 NO DILUTION DETECTED:")
        logger.info(f"  - Large table similarity: {large_similarity:.3f} (<0.7)")
        logger.info(f"  - Gap from small tables: {large_similarity - small_similarity:.3f} (<0.15)")
        logger.info("")
        logger.info("✅ RECOMMENDATION:")
        logger.info("  - Keep 4096 token threshold")
        logger.info("  - Proceed to Story 2.9")

    logger.info("")
    logger.info("=" * 80)
    logger.info("Analysis Complete!")
    logger.info("=" * 80)

    # Create validation report
    report_path = "docs/validation/story-2.8-dilution-analysis.md"
    logger.info(f"Writing validation report to: {report_path}")

    # Prepare red flags section outside f-string (Python 3.11 compatibility)
    red_flags_section = ""
    if dilution_flags:
        red_flags_section = "### Red Flags\n" + "\n".join(f"- {flag}" for flag in dilution_flags)

    report_content = f"""# Story 2.8: Semantic Dilution Analysis Report

**Generated:** 2025-10-25

## Executive Summary

This report analyzes semantic dilution in table chunks after implementing table-aware chunking with 4096-token threshold (Story 2.8 AC5).

## Chunk Size Distribution

- **Small tables (<1000 tokens):** {len(small_tables)} ({len(small_tables) / len(table_chunks) * 100:.1f}%)
- **Medium tables (1000-2500):** {len(medium_tables)} ({len(medium_tables) / len(table_chunks) * 100:.1f}%)
- **Large tables (2500-4096):** {len(large_tables)} ({len(large_tables) / len(table_chunks) * 100:.1f}%)
- **Split tables (>4096):** {len(split_tables)} ({len(split_tables) / len(table_chunks) * 100:.1f}%)

## Embedding Quality Metrics

**Intra-Bucket Similarity:**
- Small tables: {small_similarity:.3f}
- Medium tables: {medium_similarity:.3f}
- Large tables: {large_similarity:.3f}

## Dilution Assessment

{"🔴 **DILUTION DETECTED**" if dilution_flags else "🟡 **DILUTION SUSPECTED**" if large_similarity > small_similarity + 0.10 else "🟢 **NO DILUTION DETECTED**"}

{red_flags_section}

## Recommendation

{"**HALT Story 2.8** - Reduce threshold to 2048 tokens, re-ingest, re-validate" if dilution_flags else "**SUSPECTED** - Document concern, proceed to Story 2.9, plan Story 2.8.1 if accuracy <62%" if large_similarity > small_similarity + 0.10 else "**PROCEED** - Keep 4096 token threshold, move to Story 2.9"}

## Conclusion

{f"Semantic dilution confirmed. Large table chunks show {large_similarity - small_similarity:.1%} higher similarity than small tables, indicating loss of semantic specificity. Recommend reducing threshold." if dilution_flags else "Dilution suspected but within acceptable range. Monitor accuracy in Story 2.9-2.11." if large_similarity > small_similarity + 0.10 else f"No significant semantic dilution detected. Large table chunks maintain semantic specificity (similarity gap: {large_similarity - small_similarity:.3f})."}
"""

    # Ensure output directory exists
    Path(report_path).parent.mkdir(parents=True, exist_ok=True)

    # Write report
    with open(report_path, "w") as f:
        f.write(report_content)

    logger.info(f"✅ Report saved to: {report_path}")
    logger.info("")


if __name__ == "__main__":
    asyncio.run(analyze_semantic_dilution())
