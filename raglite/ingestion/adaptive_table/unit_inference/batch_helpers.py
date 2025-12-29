"""Helper functions for async batch unit inference.

This module contains utilities for building prompts, parsing responses,
and managing context for batch LLM unit inference operations.
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


def build_context_string(
    page_title: str | None,
    section_heading: str | None,
    table_caption: str | None,
    nearby_text: list[str] | None,
) -> str:
    """Build context string from available document elements.

    Args:
        page_title: Page title or largest text on page
        section_heading: Section header above table
        table_caption: Table caption/title from Docling
        nearby_text: List of text elements near table

    Returns:
        Formatted context string for LLM prompt
    """
    context_parts = []
    if page_title:
        context_parts.append(f"Page Title: {page_title}")
    if section_heading:
        context_parts.append(f"Section Heading: {section_heading}")
    if table_caption:
        context_parts.append(f"Table Caption: {table_caption}")
    if nearby_text:
        context_parts.append(f"Nearby Text: {', '.join(nearby_text[:3])}")

    return "\n".join(context_parts) if context_parts else "No context available"


def build_metric_string(metric: str, entity: str | None) -> str:
    """Build metric description string.

    Args:
        metric: Metric name (e.g., "EBITDA IFRS", "Variable Cost")
        entity: Entity name if available (e.g., "GROUP", "Portugal")

    Returns:
        Formatted metric string
    """
    metric_str = f"Metric: {metric}"
    if entity:
        metric_str += f" (Entity: {entity})"
    return metric_str


def build_batch_metrics_list(rows_batch: list[tuple[int, dict[str, Any]]]) -> str:
    """Build formatted list of metrics for batch inference.

    Args:
        rows_batch: List of (index, row) tuples

    Returns:
        Newline-separated string of indexed metrics
    """
    metrics_list = []
    for idx, row in rows_batch:
        metric = row.get("metric", "Unknown")
        entity = row.get("entity")
        metric_str = f"{idx}. {build_metric_string(metric, entity)}"
        metrics_list.append(metric_str)

    return "\n".join(metrics_list)


def get_single_inference_system_prompt() -> str:
    """Get system prompt for single-metric unit inference.

    Returns:
        System prompt string
    """
    return """You are analyzing a financial document table to infer the unit for a metric.

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


def get_batch_inference_system_prompt() -> str:
    """Get system prompt for batch unit inference.

    Returns:
        System prompt string
    """
    return """You are analyzing a financial document table to infer units for multiple metrics.

TASK:
Infer the most likely unit for each metric based on the document context.

GUIDELINES:
1. Look for explicit unit statements in context (e.g., "All values in EUR million")
2. Common units by metric type:
   - EBITDA, Net Income, Revenue → Meur, EUR million
   - Cost per ton, Price per ton → Eur/ton, EUR/ton
   - Production volume → kton, Mton
   - Ratios, margins → %
   - Days, periods → days
   - CAPEX → Meur, EUR million
3. Return "UNKNOWN" if no clear unit can be determined

RESPONSE FORMAT:
Return JSON array with format: {"index": <number>, "unit": "<unit or UNKNOWN>"}
Example: [{"index": 0, "unit": "Meur"}, {"index": 1, "unit": "Eur/ton"}, {"index": 2, "unit": "UNKNOWN"}]

IMPORTANT: Return ONLY the JSON array, no explanations."""


def build_user_prompt(context_str: str, content: str) -> str:
    """Build user prompt with context and content.

    Args:
        context_str: Document context string
        content: Metric information or metrics list

    Returns:
        Formatted user prompt
    """
    return f"""DOCUMENT CONTEXT:
{context_str}

METRIC INFORMATION:
{content}"""


def parse_batch_json_response(
    response_content: str,
    rows_batch: list[tuple[int, dict[str, Any]]],
) -> list[tuple[int, dict[str, Any], str | None]]:
    """Parse JSON response from batch inference.

    Args:
        response_content: Raw response content from LLM
        rows_batch: Original batch of (index, row) tuples

    Returns:
        List of (index, row, inferred_unit) tuples

    Raises:
        json.JSONDecodeError: If response is not valid JSON
    """
    # Extract JSON from response (may have markdown code blocks)
    json_str = response_content.strip()
    if json_str.startswith("```"):
        # Remove markdown code blocks
        json_str = json_str.split("```")[1]
        if json_str.startswith("json"):
            json_str = json_str[4:]
        json_str = json_str.strip()

    inferred_units = json.loads(json_str)

    # Map results back to rows
    results = []
    unit_map = {item["index"]: item["unit"] for item in inferred_units}

    for idx, row in rows_batch:
        unit = unit_map.get(idx)
        if unit and unit != "UNKNOWN":
            results.append((idx, row, unit))
        else:
            results.append((idx, row, None))

    logger.info(
        f"Batch inference complete: {len([r for r in results if r[2]])} units inferred from {len(rows_batch)} rows"
    )

    return results


def validate_single_inference_response(response_content: str | None) -> str | None:
    """Validate and clean single inference response.

    Args:
        response_content: Raw response from LLM

    Returns:
        Cleaned unit string or None if invalid/unknown
    """
    if not response_content or not isinstance(response_content, str):
        return None

    inferred_unit = response_content.strip()

    if inferred_unit == "UNKNOWN" or not inferred_unit:
        return None

    return inferred_unit
