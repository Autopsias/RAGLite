"""LLM-based unit inference with context awareness.

This module provides synchronous LLM-based unit inference for tables
when rule-based extraction fails. Uses Mistral Small for cost-effective inference.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from docling.document_converter import ConversionResult
    from docling_core.types.doc import TableItem

from raglite.ingestion.adaptive_table.core import extract_page_context, get_table_caption
from raglite.shared.config import settings

logger = logging.getLogger(__name__)


def _build_inference_prompts(
    metric: str,
    entity: str | None,
    table_caption: str | None,
    section_heading: str | None,
    page_title: str | None,
    nearby_text: list[str] | None,
) -> tuple[str, str]:
    """Build prompts for LLM-based unit inference.

    Args:
        metric: Metric name (e.g., "EBITDA IFRS", "Variable Cost")
        entity: Entity name if available (e.g., "GROUP", "Portugal")
        table_caption: Table caption/title from Docling
        section_heading: Section header above table
        page_title: Page title or largest text on page
        nearby_text: List of text elements near table

    Returns:
        Tuple of (system_prompt, user_prompt) for Mistral API
    """
    # Build context string
    context_parts = []
    if page_title:
        context_parts.append(f"Page Title: {page_title}")
    if section_heading:
        context_parts.append(f"Section Heading: {section_heading}")
    if table_caption:
        context_parts.append(f"Table Caption: {table_caption}")
    if nearby_text:
        context_parts.append(f"Nearby Text: {', '.join(nearby_text[:3])}")

    context_str = "\n".join(context_parts) if context_parts else "No context available"

    # Build metric string
    metric_str = f"Metric: {metric}"
    if entity:
        metric_str += f" (Entity: {entity})"

    # Construct system prompt
    system_prompt = """You are analyzing a financial document table to infer the unit for a metric.

TASK:
Based on the document context, determine the most likely unit for this metric.

GUIDELINES:
1. Look for explicit unit statements in context (e.g., "All values in EUR million")
2. Consider common units for this metric type:
   - EBITDA, Net Income, Revenue → Meur, EUR million
   - Cost per ton, Price per ton → Eur/ton, EUR/ton
   - Production volume → kton, Mton
   - Ratios, margins → %
   - Days, periods → days
   - CAPEX → Meur, EUR million
3. If multiple possibilities exist, choose the most specific one mentioned in context
4. If no clear unit can be determined, respond with "UNKNOWN"

RESPONSE FORMAT:
Return ONLY the unit string (e.g., "Meur", "Eur/ton", "%", "kton") or "UNKNOWN".
Do NOT include explanations or additional text."""

    # Construct user prompt
    user_prompt = f"""DOCUMENT CONTEXT:
{context_str}

METRIC INFORMATION:
{metric_str}"""

    return system_prompt, user_prompt


def _call_mistral_for_unit_inference(
    system_prompt: str,
    user_prompt: str,
) -> str | None:
    """Call Mistral API for unit inference.

    Args:
        system_prompt: System prompt with inference guidelines
        user_prompt: User prompt with context and metric information

    Returns:
        Raw response content from Mistral, or None if API call fails
    """
    try:
        from mistralai.models import AssistantMessage, SystemMessage, ToolMessage, UserMessage

        from raglite.shared.clients import get_mistral_client

        client = get_mistral_client()

        messages: list[AssistantMessage | SystemMessage | ToolMessage | UserMessage] = [
            SystemMessage(content=system_prompt),
            UserMessage(content=user_prompt),
        ]
        response = client.chat.complete(
            model=settings.metadata_extraction_model,
            messages=messages,
            temperature=0.0,
            max_tokens=50,
        )

        content: str = response.choices[0].message.content
        return content

    except Exception as e:
        logger.warning(
            "Mistral API call failed",
            extra={"error": str(e)},
        )
        return None


def _validate_inference_response(
    response_content: str | None,
    metric: str,
    entity: str | None,
) -> str | None:
    """Validate and extract unit from LLM response.

    Args:
        response_content: Raw response content from Mistral
        metric: Metric name (for logging)
        entity: Entity name (for logging)

    Returns:
        Validated unit string, or None if response is invalid
    """
    if not response_content or not isinstance(response_content, str):
        logger.debug(
            "Empty response from Mistral",
            extra={"metric": metric, "entity": entity},
        )
        return None

    inferred_unit: str = response_content.strip()

    if inferred_unit == "UNKNOWN" or not inferred_unit:
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


def _infer_unit_from_context(
    metric: str,
    entity: str | None,
    table_caption: str | None,
    section_heading: str | None,
    page_title: str | None,
    nearby_text: list[str] | None,
) -> str | None:
    """Infer unit for a metric using LLM-based context analysis.

    Uses Mistral Small to analyze document context (titles, headers, captions) and
    infer the most likely unit for a metric when explicit unit extraction fails.

    This implements Phase 2.7.5 production strategy for handling implicit units
    that are common in financial documents (e.g., "All values in EUR million").

    Args:
        metric: Metric name (e.g., "EBITDA IFRS", "Variable Cost")
        entity: Entity name if available (e.g., "GROUP", "Portugal")
        table_caption: Table caption/title from Docling
        section_heading: Section header above table
        page_title: Page title or largest text on page
        nearby_text: List of text elements near table

    Returns:
        Inferred unit string (e.g., "EUR million", "Eur/ton"), or None if inference fails

    Example:
        >>> unit = _infer_unit_from_context(
        ...     metric="EBITDA IFRS",
        ...     entity="GROUP",
        ...     section_heading="Group Consolidated Results (EUR Million)",
        ...     table_caption="EBITDA by Region",
        ...     page_title="Financial Performance Report 2025",
        ...     nearby_text=["All monetary values in EUR million unless noted"]
        ... )
        >>> print(unit)
        'Meur'  # Inferred from section heading and context
    """
    # Check if Mistral API key is configured
    if not settings.mistral_api_key:
        logger.debug(
            "Mistral API key not configured - skipping unit inference",
            extra={"metric": metric},
        )
        return None

    # Build prompts
    system_prompt, user_prompt = _build_inference_prompts(
        metric=metric,
        entity=entity,
        table_caption=table_caption,
        section_heading=section_heading,
        page_title=page_title,
        nearby_text=nearby_text,
    )

    # Call Mistral API
    response_content = _call_mistral_for_unit_inference(system_prompt, user_prompt)

    if response_content is None:
        logger.warning(
            "Unit inference failed",
            extra={"metric": metric, "entity": entity},
        )
        return None

    # Validate response
    return _validate_inference_response(response_content, metric, entity)


def _apply_context_aware_unit_inference(
    rows: list[dict[str, Any]], table_item: TableItem, result: ConversionResult
) -> list[dict[str, Any]]:
    """Apply LLM-based unit inference to rows with missing units.

    This is the main entry point for Phase 2.7.5 context-aware unit inference.
    It implements a hybrid strategy:
    1. Use explicit units when available (Phase 2.7.4)
    2. Infer units using LLM for rows with unit=None
    3. Cache inferred units for metric/entity consistency

    Args:
        rows: List of extracted row dictionaries (may have unit=None)
        table_item: Docling TableItem (for context extraction)
        result: Docling ConversionResult (for document-level context)

    Returns:
        Updated rows with inferred units where possible

    Example:
        >>> rows_in = [
        ...     {'metric': 'EBITDA IFRS', 'entity': 'GROUP', 'value': 128.825, 'unit': None},
        ...     {'metric': 'EBITDA IFRS', 'entity': 'PORTUGAL*', 'value': 91.438, 'unit': None}
        ... ]
        >>> rows_out = _apply_context_aware_unit_inference(rows_in, table_item, result)
        >>> rows_out[0]['unit']
        'Meur'  # Inferred from context
    """

    # Extract document context
    page_context = extract_page_context(table_item, result)
    section_heading = page_context.get("section_heading")
    nearby_text = page_context.get("nearby_text", [])
    page_title = page_context.get("page_title")

    # Get table caption from Docling
    table_caption = get_table_caption(table_item)

    # Cache for inferred units (metric -> unit)
    unit_cache: dict[str, str] = {}

    # Statistics
    inference_count = 0
    cache_hit_count = 0

    # Process rows
    for row in rows:
        # Skip rows that already have explicit units
        if row.get("unit") is not None:
            continue

        metric = row.get("metric")
        entity = row.get("entity")

        if not metric:
            continue  # Cannot infer without metric

        # Check cache first (metric-based consistency)
        cache_key = metric  # Use metric as key (same metric = same unit typically)
        if cache_key in unit_cache:
            row["unit"] = unit_cache[cache_key]
            row["unit_source"] = "cached_inference"
            cache_hit_count += 1
            continue

        # Infer unit using LLM
        inferred_unit = _infer_unit_from_context(
            metric=metric,
            entity=entity,
            table_caption=table_caption,
            section_heading=section_heading,
            page_title=page_title,
            nearby_text=nearby_text,
        )

        if inferred_unit:
            row["unit"] = inferred_unit
            row["unit_source"] = "llm_inference"
            unit_cache[cache_key] = inferred_unit  # Cache for next rows
            inference_count += 1

    # Log statistics
    total_null_units = sum(1 for row in rows if row.get("unit") is None)
    logger.info(
        "Context-aware unit inference complete",
        extra={
            "total_rows": len(rows),
            "inferred_count": inference_count,
            "cache_hits": cache_hit_count,
            "remaining_null": total_null_units,
        },
    )

    return rows
