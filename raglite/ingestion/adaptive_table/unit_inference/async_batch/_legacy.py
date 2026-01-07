"""Async batch processing for high-performance LLM unit inference.

This module provides async batch processing with rate limiting and connection pooling
to achieve 41x speedup over synchronous sequential inference (62 min → 1.5 min).

Implements:
- Milestone 1: Async concurrent processing (10x speedup)
- Milestone 2: Batch inference (4x additional speedup)
- Story 5.0.6 AC3: Cross-document unit cache (30% additional API reduction)
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from docling.document_converter import ConversionResult
    from docling_core.types.doc import TableItem

from raglite.ingestion.adaptive_table.core import extract_page_context, get_table_caption
from raglite.ingestion.adaptive_table.unit_inference.async_batch.helpers import (
    _execute_batch_inference,
    _log_inference_statistics,
    _prepare_rows_for_inference,
    _process_batch_inference_results,
)
from raglite.ingestion.adaptive_table.unit_inference.batch_helpers import (
    build_batch_metrics_list,
    build_context_string,
    build_metric_string,
    build_user_prompt,
    get_batch_inference_system_prompt,
    get_single_inference_system_prompt,
    parse_batch_json_response,
    validate_single_inference_response,
)
from raglite.shared.config import settings

logger = logging.getLogger(__name__)

# Global semaphore for rate limiting Mistral API calls (max 10 concurrent)
# Prevents hitting rate limits while allowing significant parallelization
MISTRAL_SEMAPHORE = asyncio.Semaphore(10)


async def _call_mistral_api_async(
    system_prompt: str,
    user_prompt: str,
    client: Any,
) -> str | None:
    """Call Mistral API with timeout and error handling.

    Args:
        system_prompt: System prompt for Mistral
        user_prompt: User prompt for Mistral
        client: Shared Mistral client

    Returns:
        Inferred unit string or None if inference fails

    Raises:
        TimeoutError: If API call times out
        Exception: For other API errors
    """
    from mistralai.models import (
        AssistantMessage,
        SystemMessage,
        ToolMessage,
        UserMessage,
    )

    messages: list[AssistantMessage | SystemMessage | ToolMessage | UserMessage] = [
        SystemMessage(content=system_prompt),
        UserMessage(content=user_prompt),
    ]

    # Call Mistral async API
    response = await client.chat.complete_async(
        model=settings.metadata_extraction_model,
        messages=messages,
        temperature=0.0,  # Deterministic inference
        max_tokens=50,
    )

    # Extract and validate response
    response_content = response.choices[0].message.content
    return validate_single_inference_response(response_content)


async def _infer_unit_from_context_async(
    metric: str,
    entity: str | None,
    table_caption: str | None,
    section_heading: str | None,
    page_title: str | None,
    nearby_text: list[str] | None,
    client: Any,  # Mistral client for connection pooling
) -> str | None:
    """Async version of _infer_unit_from_context with rate limiting and timeout.

    Uses asyncio semaphore to limit concurrent API calls to 10, preventing rate limit errors
    while achieving 10x speedup through parallelization.

    Args:
        metric: Metric name (e.g., "EBITDA IFRS", "Variable Cost")
        entity: Entity name if available (e.g., "GROUP", "Portugal")
        table_caption: Table caption/title from Docling
        section_heading: Section header above table
        page_title: Page title or largest text on page
        nearby_text: List of text elements near table
        client: Shared Mistral client for connection pooling

    Returns:
        Inferred unit string (e.g., "EUR million", "Eur/ton"), or None if inference fails

    Performance:
        - Concurrent execution with semaphore rate limiting
        - 5-second timeout per call to prevent hangs
        - Connection pooling via shared client
        - Expected: 62 min → 6 min (10x speedup for 942 rows)
    """
    from raglite.shared.config import settings

    # Check if Mistral API key is configured
    if not settings.mistral_api_key:
        logger.debug(
            "Mistral API key not configured - skipping unit inference",
            extra={"metric": metric},
        )
        return None

    # Build context and metric strings
    context_str = build_context_string(page_title, section_heading, table_caption, nearby_text)
    metric_str = build_metric_string(metric, entity)

    # Construct prompts
    system_prompt = get_single_inference_system_prompt()
    user_prompt = build_user_prompt(context_str, metric_str)

    # Acquire semaphore for rate limiting + apply timeout
    async with MISTRAL_SEMAPHORE:
        try:
            async with asyncio.timeout(5.0):  # 5-second timeout per call
                inferred_unit = await _call_mistral_api_async(system_prompt, user_prompt, client)

                if not inferred_unit:
                    logger.debug(
                        "Unit inference returned UNKNOWN",
                        extra={"metric": metric, "entity": entity},
                    )
                    return None

                logger.info(
                    "Unit inferred from context",
                    extra={
                        "metric": metric,
                        "entity": entity,
                        "inferred_unit": inferred_unit,
                        "confidence": "llm_based",
                    },
                )

                return inferred_unit

        except TimeoutError:
            logger.warning(
                "Unit inference timeout (5s)",
                extra={"metric": metric, "entity": entity},
            )
            return None
        except Exception as e:
            logger.warning(
                "Unit inference failed",
                extra={"metric": metric, "entity": entity, "error": str(e)},
            )
            return None


async def _infer_units_batch_async(
    rows_batch: list[tuple[int, dict[str, Any]]],
    table_caption: str | None,
    section_heading: str | None,
    page_title: str | None,
    nearby_text: list[str] | None,
    client: Any,
) -> list[tuple[int, dict[str, Any], str | None]]:
    """Batch inference for multiple rows in a single API call (Milestone 2).

    Groups up to 20 rows per API call for 4x speedup (942 calls → ~47 calls).

    Args:
        rows_batch: List of (index, row) tuples to infer units for
        table_caption: Table caption from Docling
        section_heading: Section header above table
        page_title: Page title
        nearby_text: Text elements near table
        client: Shared Mistral client

    Returns:
        List of (index, row, inferred_unit) tuples

    Performance:
        - Batch size: 20 rows per API call
        - Expected: 6 min → 1.5 min (4x speedup)
        - Total speedup: 62 min → 1.5 min (41x from baseline)
    """
    from raglite.shared.config import settings

    # Build context and metrics strings
    context_str = build_context_string(page_title, section_heading, table_caption, nearby_text)
    metrics_str = build_batch_metrics_list(rows_batch)

    # Construct prompts
    system_prompt = get_batch_inference_system_prompt()
    user_prompt = build_user_prompt(context_str, f"METRICS TO ANALYZE:\n{metrics_str}")

    # Acquire semaphore and call API with timeout
    async with MISTRAL_SEMAPHORE:
        try:
            async with asyncio.timeout(10.0):  # 10-second timeout for batch
                from mistralai.models import (
                    AssistantMessage,
                    SystemMessage,
                    ToolMessage,
                    UserMessage,
                )

                messages: list[AssistantMessage | SystemMessage | ToolMessage | UserMessage] = [
                    SystemMessage(content=system_prompt),
                    UserMessage(content=user_prompt),
                ]

                response = await client.chat.complete_async(
                    model=settings.metadata_extraction_model,
                    messages=messages,
                    temperature=0.0,
                    max_tokens=200,  # More tokens for batch response
                )

                # Parse JSON response
                response_content = response.choices[0].message.content
                if not response_content or not isinstance(response_content, str):
                    logger.debug(f"Empty batch response for {len(rows_batch)} rows")
                    return [(idx, row, None) for idx, row in rows_batch]

                # Try to parse JSON
                try:
                    return parse_batch_json_response(response_content, rows_batch)

                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse batch JSON response: {e}")
                    # Fall back to None for all rows
                    return [(idx, row, None) for idx, row in rows_batch]

        except TimeoutError:
            logger.warning(f"Batch inference timeout (10s) for {len(rows_batch)} rows")
            return [(idx, row, None) for idx, row in rows_batch]
        except Exception as e:
            logger.warning(f"Batch inference failed: {e}")
            return [(idx, row, None) for idx, row in rows_batch]


async def _apply_context_aware_unit_inference_async(
    rows: list[dict[str, Any]],
    table_item: TableItem,
    result: ConversionResult,
    unit_cache: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """Async version with batch processing for maximum speedup (Milestones 1 + 2).

    This implements:
    - Milestone 1: Async concurrent processing (10x speedup)
    - Milestone 2: Batch inference (4x additional speedup)
    - Story 5.0.6 AC3: Cross-document unit cache (30% additional API reduction)
    - Total: 62 min → 1.5 min (41x speedup)

    Strategy:
    1. Cache-first: Check if unit already inferred for this metric
    2. Batch grouping: Group uncached rows into batches of 20
    3. Concurrent batches: Process batches in parallel (10 concurrent via semaphore)
    4. JSON parsing: Parse structured batch responses
    5. Cache update: Store results for future rows

    Args:
        rows: List of extracted row dictionaries (may have unit=None)
        table_item: Docling TableItem (for context extraction)
        result: Docling ConversionResult (for document-level context)
        unit_cache: Optional shared cache for cross-document unit inference (AC3).
                   If None, creates local cache. If provided, enables reuse across documents.

    Returns:
        Updated rows with inferred units where possible

    Performance:
        - Milestone 1: 62 min → 6 min (async, 10 concurrent)
        - Milestone 2: 6 min → 1.5 min (batching, 20 rows/call)
        - Story 5.0.6 AC3: +30% API reduction via cross-document cache
        - Total: 942 individual calls → ~47 batch calls
        - Rate-limited: 10 concurrent batches max
        - Timeout: 10s per batch call

    Example:
        >>> rows_in = [
        ...     {'metric': 'EBITDA IFRS', 'entity': 'GROUP', 'value': 128.825, 'unit': None},
        ...     {'metric': 'EBITDA IFRS', 'entity': 'PORTUGAL*', 'value': 91.438, 'unit': None}
        ... ]
        >>> cache = {}  # Shared cache for batch
        >>> rows_out = await _apply_context_aware_unit_inference_async(rows_in, table_item, result, cache)
        >>> rows_out[0]['unit']
        'Meur'  # Inferred from context
        >>> cache['EBITDA IFRS']
        'Meur'  # Cached for next document
    """
    # Check if Mistral API key is configured
    if not settings.mistral_api_key:
        logger.debug("Mistral API key not configured - skipping async unit inference")
        return rows

    # Extract document context
    page_context = extract_page_context(table_item, result)
    section_heading = page_context.get("section_heading")
    nearby_text = page_context.get("nearby_text", [])
    page_title = page_context.get("page_title")

    # Get table caption from Docling
    table_caption = get_table_caption(table_item)

    # Create shared Mistral client for connection pooling with timeout configuration
    from raglite.shared.clients import get_mistral_client

    client = get_mistral_client()

    # AC3: Use provided cache or create local one (backward compatible)
    if unit_cache is None:
        unit_cache = {}

    # First pass: Try rule-based inference, check cache, build list for LLM inference
    rows_needing_inference, cache_hit_count, rule_inferred_count = _prepare_rows_for_inference(
        rows, unit_cache
    )

    # Second pass: Batch inference for uncached rows (Milestone 2)
    if rows_needing_inference:
        batch_results = await _execute_batch_inference(
            rows_needing_inference, table_caption, section_heading, page_title, nearby_text, client
        )
        # Process batch results and update rows with inferred units
        inference_count = _process_batch_inference_results(
            batch_results, rows_needing_inference, unit_cache
        )
    else:
        inference_count = 0

    # Log statistics (AC2 & AC6: Report API call reduction)
    _log_inference_statistics(
        rows, rows_needing_inference, inference_count, cache_hit_count, rule_inferred_count
    )

    return rows
