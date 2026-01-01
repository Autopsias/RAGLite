"""Metadata enrichment for query results.

Provides query-time metadata extraction to compensate for skipped
ingestion-time metadata extraction.
"""

import time
from typing import cast

from raglite.shared.config import settings
from raglite.shared.logging import get_logger
from raglite.shared.models import QueryResult

logger = get_logger(__name__)


async def enrich_results_with_metadata(results: list[QueryResult]) -> list[QueryResult]:
    """Enrich query results with LLM-extracted metadata at query time.

    Story 5.0.6 AC5: Compensates for skipped metadata extraction during ingestion
    by enriching top-k results with rich metadata schema at query time.

    This function enables the performance optimization of skipping metadata extraction
    during ingestion (saving 400+ API calls per document) while maintaining query
    quality through selective enrichment of only the retrieved results.

    Strategy:
    1. Extract metadata from each result's text in parallel (asyncio.gather)
    2. Apply 2.5 second timeout for entire batch (graceful degradation)
    3. If timeout occurs, return results without metadata (no failure)
    4. Attach extracted metadata to QueryResult objects

    Args:
        results: List of QueryResult objects from retrieval (typically top-5)

    Returns:
        Same QueryResult objects with metadata fields populated (or unchanged if timeout)

    Performance:
        - Parallel processing: All results enriched concurrently
        - Timeout: 2.5 seconds total (graceful degradation)
        - Cost: FREE (Mistral Small 3.2)
        - Latency budget: Fits within 5s p50, 15s p95 NFR13 target

    Example:
        >>> results = await hybrid_search("What is the EBITDA?", top_k=5)
        >>> enriched = await enrich_results_with_metadata(results)
        >>> print(enriched[0].text, enriched[0].metadata)
    """
    import asyncio

    from raglite.ingestion.embedding_generation import extract_chunk_metadata
    from raglite.shared.clients import get_mistral_client

    # AC5: Only enrich if enabled in config
    if not settings.query_time_metadata_enabled:
        logger.debug("Query-time metadata enrichment disabled (skip)")
        return results

    # AC5: Graceful degradation if no API key
    if not settings.mistral_api_key:
        logger.debug("Mistral API key not configured - skipping metadata enrichment")
        return results

    if not results:
        return results

    logger.info(
        "Enriching results with metadata at query time",
        extra={"result_count": len(results), "timeout_seconds": 2.5},
    )

    start_time = time.time()

    # Create shared Mistral client for connection pooling
    client = get_mistral_client()

    # AC5: Extract metadata for all results in parallel with timeout
    async def enrich_single_result(result: QueryResult, index: int) -> QueryResult:
        """Extract metadata for a single result with error handling."""
        try:
            # Extract metadata using existing function (reuses 15-field rich schema)
            chunk_id = f"query_result_{index}"
            metadata = await extract_chunk_metadata(result.text, chunk_id, client)

            # Story 5.0.6 AC5: Attach extracted metadata to QueryResult
            result.metadata = metadata

            logger.debug(
                "Metadata extracted and attached for result",
                extra={
                    "index": index,
                    "company_name": metadata.company_name,
                    "reporting_period": metadata.reporting_period,
                    "metric_category": metadata.metric_category,
                },
            )

            return result

        except Exception as e:
            logger.warning(
                "Metadata extraction failed for result (graceful degradation)",
                extra={"index": index, "error": str(e)},
            )
            return result

    try:
        # AC5: Parallel enrichment with 2.5s timeout
        enrichment_tasks = [enrich_single_result(r, i) for i, r in enumerate(results)]
        enriched_results = await asyncio.wait_for(
            asyncio.gather(*enrichment_tasks, return_exceptions=True), timeout=2.5
        )

        # Filter out exceptions from gather
        final_results: list[QueryResult] = []
        for i, result in enumerate(enriched_results):
            if isinstance(result, Exception):
                logger.warning(f"Enrichment task failed: {result}")
                # Use original result (not the exception)
                final_results.append(results[i])
            else:
                # Type narrowing: result is QueryResult here
                final_results.append(cast(QueryResult, result))

        elapsed_ms = (time.time() - start_time) * 1000
        logger.info(
            "Query-time metadata enrichment complete",
            extra={
                "result_count": len(final_results),
                "latency_ms": round(elapsed_ms, 1),
                "within_budget": elapsed_ms < 2500,
            },
        )

        return final_results

    except TimeoutError:
        # AC5: Graceful degradation - return results without metadata
        elapsed_ms = (time.time() - start_time) * 1000
        logger.warning(
            "Query-time metadata enrichment timed out (graceful degradation)",
            extra={"timeout_ms": 2500, "elapsed_ms": round(elapsed_ms, 1)},
        )
        return results
