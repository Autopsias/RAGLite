"""Helper functions for async batch unit inference.

This module contains extracted logic from _apply_context_aware_unit_inference_async
to reduce function size and improve maintainability.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

from raglite.shared.config import settings

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


def _prepare_rows_for_inference(
    rows: list[dict[str, Any]],
    unit_cache: dict[str, str],
) -> tuple[list[tuple[int, dict[str, Any]]], int, int]:
    """Prepare rows for LLM inference by applying rules and cache.

    This function implements the first pass of the inference strategy:
    1. Skip rows with explicit units
    2. Try rule-based inference (AC2: 80% API reduction)
    3. Check cache for metric-based consistency
    4. Build list of rows needing LLM inference

    Args:
        rows: List of extracted row dictionaries (may have unit=None)
        unit_cache: Shared cache for cross-document unit inference

    Returns:
        Tuple of:
        - List of (index, row) tuples needing LLM inference
        - Count of cache hits
        - Count of rule-inferred units
    """
    rows_needing_inference: list[tuple[int, dict[str, Any]]] = []
    cache_hit_count = 0
    rule_inferred_count = 0

    from raglite.ingestion.adaptive_table.unit_inference.rules import infer_unit_from_rules

    for idx, row in enumerate(rows):
        # Skip rows that already have explicit units
        if row.get("unit") is not None:
            continue

        metric = row.get("metric")

        if not metric:
            continue  # Cannot infer without metric

        # Strategy 1: Try rule-based inference FIRST (AC2: 80% API reduction)
        rule_unit = infer_unit_from_rules(metric)
        if rule_unit:
            row["unit"] = rule_unit
            row["unit_source"] = "rule"
            unit_cache[metric] = rule_unit  # Cache for consistency
            rule_inferred_count += 1
            continue

        # Strategy 2: Check cache (metric-based consistency)
        cache_key = metric
        if cache_key in unit_cache:
            row["unit"] = unit_cache[cache_key]
            row["unit_source"] = "cached_inference"
            cache_hit_count += 1
            continue

        # Strategy 3: Add to LLM inference queue (fallback for tables only if configured)
        # Only use LLM for table chunks if unit_inference_llm_tables_only is True
        if settings.unit_inference_llm_tables_only:
            # Check if this row is from a table chunk
            # For now, add to inference queue (table detection happens at caller level)
            rows_needing_inference.append((idx, row))
        else:
            # Use LLM for all chunks
            rows_needing_inference.append((idx, row))

    return rows_needing_inference, cache_hit_count, rule_inferred_count


def _process_batch_inference_results(
    batch_results: list[Any],
    rows_needing_inference: list[tuple[int, dict[str, Any]]],
    unit_cache: dict[str, str],
) -> int:
    """Process results from batch LLM inference.

    Updates rows with inferred units, caches results for consistency,
    and returns the count of successful inferences.

    Args:
        batch_results: Results from asyncio.gather() on batch tasks
        rows_needing_inference: List of (index, row) tuples that were inferred
        unit_cache: Shared cache to update with successful inferences

    Returns:
        Count of successful LLM inferences
    """
    inference_count = 0

    # Flatten batch results
    results: list[tuple[int, dict[str, Any], str | None]] = []
    for batch_result in batch_results:
        if isinstance(batch_result, BaseException):
            logger.warning(f"Batch inference failed: {batch_result}")
            continue
        results.extend(batch_result)

    # Process results
    for result_item in results:
        if isinstance(result_item, Exception):
            logger.warning(f"Unit inference task failed: {result_item}")
            continue

        idx, row, inferred_unit = result_item

        if inferred_unit:
            row["unit"] = inferred_unit
            row["unit_source"] = "llm_inference"
            # Cache for consistency across rows with same metric
            metric = row.get("metric")
            if metric:
                unit_cache[metric] = inferred_unit
            inference_count += 1

    return inference_count


def _log_inference_statistics(
    rows: list[dict[str, Any]],
    rows_needing_inference: list[tuple[int, dict[str, Any]]],
    inference_count: int,
    cache_hit_count: int,
    rule_inferred_count: int,
) -> None:
    """Log statistics about unit inference performance.

    Args:
        rows: All rows processed
        rows_needing_inference: Rows that required LLM inference
        inference_count: Count of successful LLM inferences
        cache_hit_count: Count of cache hits
        rule_inferred_count: Count of rule-based inferences
    """
    total_null_units = sum(1 for row in rows if row.get("unit") is None)
    batch_count = (len(rows_needing_inference) + 19) // 20 if rows_needing_inference else 0
    total_with_units = len(rows) - total_null_units
    api_calls_avoided = rule_inferred_count + cache_hit_count

    logger.info(
        "Unit inference complete (Rule-based + LLM hybrid)",
        extra={
            "total_rows": len(rows),
            "rule_inferred_count": rule_inferred_count,
            "llm_inferred_count": inference_count,
            "cache_hits": cache_hit_count,
            "remaining_null": total_null_units,
            "total_with_units": total_with_units,
            "batch_count": batch_count,
            "batch_size": 20,
            "api_calls_avoided": api_calls_avoided,
            "api_reduction_pct": round(100 * api_calls_avoided / max(total_with_units, 1), 1),
        },
    )


async def _execute_batch_inference(
    rows_needing_inference: list[tuple[int, dict[str, Any]]],
    table_caption: str | None,
    section_heading: str | None,
    page_title: str | None,
    nearby_text: list[str] | None,
    client: Any,
) -> list[Any]:
    """Execute batch LLM inference for rows needing unit inference.

    Groups rows into batches of 20 and processes them concurrently using
    asyncio.gather with rate limiting via semaphore.

    Args:
        rows_needing_inference: List of (index, row) tuples needing inference
        table_caption: Table caption from Docling
        section_heading: Section header above table
        page_title: Page title
        nearby_text: Text elements near table
        client: Shared Mistral client

    Returns:
        List of batch results from asyncio.gather()
    """
    import asyncio

    # Group rows into batches of 20 for efficient API usage
    BATCH_SIZE = 20
    batches = []
    for i in range(0, len(rows_needing_inference), BATCH_SIZE):
        batch = rows_needing_inference[i : i + BATCH_SIZE]
        batches.append(batch)

    logger.info(
        f"Processing {len(rows_needing_inference)} rows in {len(batches)} batches (batch_size={BATCH_SIZE})"
    )

    # Import here to avoid circular dependency
    from raglite.ingestion.adaptive_table.unit_inference.async_batch._legacy import (
        _infer_units_batch_async,
    )

    # Process batches concurrently (rate-limited by semaphore)
    batch_tasks = [
        _infer_units_batch_async(
            batch, table_caption, section_heading, page_title, nearby_text, client
        )
        for batch in batches
    ]
    batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

    return batch_results
