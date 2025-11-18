"""
Unit extraction and inference for table data.

This module provides:
1. Unit pattern extraction from table structures
2. Statistical unit detection
3. LLM-based context-aware unit inference
4. Async batch processing for performance

Handles orientation-aware unit detection for transposed, normal, and junk-column tables.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from docling.document_converter import ConversionResult
    from docling_core.types.doc import TableItem

logger = logging.getLogger(__name__)

# Global semaphore for rate limiting Mistral API calls (max 10 concurrent)
# Prevents hitting rate limits while allowing significant parallelization
MISTRAL_SEMAPHORE = asyncio.Semaphore(10)


def _extract_units_normal(table_cells: list, unit_patterns: list[str]) -> dict[int, str]:
    """Extract units from normal table (entities in columns, metrics in rows).

    Strategy priorities for normal tables:
    1. Check for dedicated unit row (usually row 0, 1, or 2)
    2. Extract from row headers/metric names (e.g., "Revenue (EUR)")
    3. Extract from column headers

    Args:
        table_cells: List of table cells
        unit_patterns: List of unit pattern strings to match

    Returns:
        Dictionary mapping row index to unit string for normal tables

    Example:
        Normal table:
        Row 0: Entity    | GROUP   | PORTUGAL | ANGOLA
        Row 1: Unit      | EUR     | EUR      | EUR
        Row 2: Revenue   | 100M    | 50M      | 50M

        Returns: {0: 'EUR', 1: 'EUR', 2: 'EUR'} (from unit row)

        Alternative pattern (metric names with units):
        Row 0: Entity         | GROUP   | PORTUGAL | ANGOLA
        Row 1: Revenue (EUR)  | 100M    | 50M      | 50M

        Returns: {1: 'EUR'} (extracted from metric name)
    """
    units = {}

    # Strategy 1: Check for dedicated unit row (usually row 0, 1, or 2)
    for row_idx in [0, 1, 2]:
        row_cells = [c for c in table_cells if c.start_row_offset_idx == row_idx]

        if not row_cells:
            continue

        # Count cells with unit patterns
        unit_count = sum(
            1
            for c in row_cells
            if c.text and any(p.lower() in c.text.lower() for p in unit_patterns)
        )

        # If >60% of cells in this row contain units, it's a unit row
        if unit_count / len(row_cells) > 0.60:
            logger.info(
                "Found dedicated unit row in normal table",
                extra={
                    "row_index": row_idx,
                    "unit_count": unit_count,
                    "total_cells": len(row_cells),
                    "ratio": round(unit_count / len(row_cells), 3),
                },
            )

            # Extract units from this row
            for cell in row_cells:
                if cell.text and cell.text.strip():
                    units[cell.start_col_offset_idx] = cell.text.strip()

            return units

    # Strategy 2: Extract from row headers (metric names with units in parentheses)
    row_headers = [c for c in table_cells if c.start_col_offset_idx == 0]

    for cell in row_headers:
        if not cell.text:
            continue

        # Parse "Metric (Unit)" pattern
        match = re.search(r"\(([^)]+)\)", cell.text)
        if match:
            unit = match.group(1).strip()
            # Verify it's a valid unit pattern
            if any(p.lower() in unit.lower() for p in unit_patterns):
                units[cell.start_row_offset_idx] = unit
                logger.debug(
                    "Extracted unit from metric name",
                    extra={
                        "row_index": cell.start_row_offset_idx,
                        "metric": cell.text,
                        "unit": unit,
                    },
                )

    # Strategy 3: Extract from column headers (if units appear there)
    col_headers = [c for c in table_cells if c.column_header]
    for cell in col_headers:
        if not cell.text:
            continue

        # Check if header contains unit pattern
        for pattern in unit_patterns:
            if pattern.lower() in cell.text.lower():
                units[cell.start_col_offset_idx] = pattern
                break

    logger.info(
        "Normal table unit extraction completed",
        extra={
            "units_found": len(units),
            "extraction_strategies": "unit_row,metric_names,column_headers",
        },
    )

    return units


def _extract_units_entity_column_junk(
    table_cells: list, unit_patterns: list[str]
) -> dict[int, str]:
    """Extract units from Type B tables (junk column 0, entities in column 1).

    Structure:
    - Column 0: Numeric junk/indices (14.003, 8.430, 26, etc.)
    - Column 1: Entity names (Portugal, Portugal Cement, etc.)
    - Headers: Metric categories (Total R SUSTAINING, Total D DEVELOPMENT, etc.)

    Strategy:
    1. Check column headers for unit patterns (e.g., "CAPEX (EUR million)")
    2. Check rows 3-5 for dedicated unit row (beyond typical 0-2)
    3. Fallback to cell-level parsing

    Args:
        table_cells: List of table cells
        unit_patterns: List of unit pattern strings

    Returns:
        Dictionary mapping column index to unit string
    """
    units = {}

    # Strategy 1: Check column headers for unit patterns
    headers = [c for c in table_cells if c.column_header]
    for header in headers:
        if not header.text:
            continue

        # Check for pattern like "Total R SUSTAINING (EUR million)"
        match = re.search(r"\(([^)]+)\)", header.text)
        if match:
            potential_unit = match.group(1).strip()
            if any(p.lower() in potential_unit.lower() for p in unit_patterns):
                units[header.start_col_offset_idx] = potential_unit
                logger.debug(
                    "Extracted unit from header",
                    extra={"col_idx": header.start_col_offset_idx, "unit": potential_unit},
                )

    # Strategy 2: Check rows 3-5 for dedicated unit row (beyond typical 0-2)
    if not units:
        for row_idx in [3, 4, 5]:
            row_cells = [
                c for c in table_cells if c.start_row_offset_idx == row_idx and not c.column_header
            ]

            if not row_cells:
                continue

            # Count cells with unit patterns
            unit_count = sum(
                1
                for c in row_cells
                if c.text and any(p.lower() in c.text.lower() for p in unit_patterns)
            )

            # If >70% of cells contain units, it's a unit row
            if unit_count / len(row_cells) > 0.70:
                logger.info(
                    "Found dedicated unit row in Type B table",
                    extra={
                        "row_index": row_idx,
                        "unit_count": unit_count,
                        "total_cells": len(row_cells),
                        "ratio": round(unit_count / len(row_cells), 3),
                    },
                )

                # Extract units from this row
                for cell in row_cells:
                    if cell.text and cell.text.strip():
                        units[cell.start_col_offset_idx] = cell.text.strip()

                return units

    # Strategy 3: Check if all data cells have embedded units
    # (This means units might be in the data itself)
    if not units:
        logger.info(
            "No explicit units found in Type B table - units may be embedded in data",
            extra={"table_type": "entity_column_junk"},
        )

    return units


def _detect_unit_column_statistical(
    cells: list, unit_patterns: list[str], threshold: float = 0.60, min_samples: int = 3
) -> tuple[bool, float]:
    """Detect if a column contains units using statistical threshold analysis.

    This implements a production-grade framework for unit detection that works
    for ANY financial document, replacing the flawed "first 3 cells" positional
    sampling approach.

    Strategy:
    1. PRIMARY: Statistical analysis across ALL cells with configurable threshold
    2. SECONDARY: Pattern concentration in middle section (rows 3-10)
    3. FALLBACK: Extended unit patterns for edge cases

    Args:
        cells: List of cells to analyze
        unit_patterns: List of unit pattern strings to match
        threshold: Minimum ratio of cells with units (default: 0.60 = 60%)
        min_samples: Minimum number of cells required for analysis

    Returns:
        Tuple of (has_units: bool, confidence: float)
        - has_units: True if column contains units above threshold
        - confidence: Detection confidence score (0.0-1.0)

    Example:
        >>> cells = [cell1, cell2, cell3, ...] # 14 cells
        >>> patterns = ['EUR', 'ton', 'kt', '%']
        >>> has_units, confidence = _detect_unit_column_statistical(cells, patterns)
        >>> # has_units=True, confidence=0.857 if 12/14 cells match
    """
    if not cells:
        return False, 0.0

    # Filter to non-empty cells
    non_empty_cells = [cell for cell in cells if cell.text and cell.text.strip()]

    if len(non_empty_cells) < min_samples:
        # Not enough samples for statistical analysis
        return False, 0.0

    # STRATEGY 1: Statistical analysis across ALL cells
    cells_with_units = [
        cell for cell in non_empty_cells if any(pattern in cell.text for pattern in unit_patterns)
    ]

    unit_ratio = len(cells_with_units) / len(non_empty_cells)

    if unit_ratio >= threshold:
        # HIGH CONFIDENCE: Meets statistical threshold
        return True, unit_ratio

    # STRATEGY 2: Check middle section concentration (rows 3-10)
    # Units often concentrated in middle of table, sparse at edges
    middle_cells = [
        cell
        for cell in non_empty_cells
        if hasattr(cell, "start_row_offset_idx") and 3 <= cell.start_row_offset_idx <= 10
    ]

    if len(middle_cells) >= 3:
        middle_with_units = [
            cell for cell in middle_cells if any(pattern in cell.text for pattern in unit_patterns)
        ]
        middle_ratio = len(middle_with_units) / len(middle_cells)

        if middle_ratio >= 0.70:  # 70% in middle section
            # MEDIUM CONFIDENCE: Strong concentration in middle
            return True, 0.50 + (middle_ratio * 0.30)  # 0.50-0.80 confidence range

    # STRATEGY 3: Extended unit patterns (fallback)
    # Check for verbal unit indicators that might be missed
    extended_patterns = [
        "million",
        "billion",
        "thousand",
        "M€",
        "k€",
        "bn",
        "mn",
        "ratio",
        "rate",
        "percentage",
        "pct",
        "pts",
        "bps",
        "basis points",
        "people",
        "FTE",
        "headcount",
        "employees",
        "staff",
        "hours",
        "days",
        "months",
        "years",
        "weeks",
    ]

    extended_matches = [
        cell
        for cell in non_empty_cells
        if any(pattern.lower() in cell.text.lower() for pattern in extended_patterns)
    ]

    extended_ratio = len(extended_matches) / len(non_empty_cells)

    if extended_ratio >= 0.50:  # 50% threshold for extended patterns
        # LOW-MEDIUM CONFIDENCE: Extended patterns detected
        return True, 0.30 + (extended_ratio * 0.30)  # 0.30-0.60 confidence range

    # NO DETECTION: Column does not contain units
    return False, unit_ratio  # Return actual ratio for logging


def _parse_value_unit(text: str) -> tuple[float | None, str | None]:
    """Parse numeric value and unit from cell text."""
    if not text:
        return None, None

    text = text.strip().replace(",", ".")

    # Try to extract number
    number_match = re.search(r"[-+]?\d*\.?\d+", text)
    if number_match:
        try:
            value = float(number_match.group())
            # Extract unit (anything after the number)
            unit_text = text[number_match.end() :].strip()
            unit = unit_text if unit_text else None
            return value, unit
        except ValueError:
            return None, None

    return None, None


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
    from raglite.shared.config import settings

    # Check if Mistral API key is configured
    if not settings.mistral_api_key:
        logger.debug(
            "Mistral API key not configured - skipping unit inference", extra={"metric": metric}
        )
        return None

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

    # Construct prompt for Mistral
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

    user_prompt = f"""DOCUMENT CONTEXT:
{context_str}

METRIC INFORMATION:
{metric_str}"""

    try:
        # Call Mistral API
        from mistralai.models import AssistantMessage, SystemMessage, ToolMessage, UserMessage

        from raglite.shared.clients import get_mistral_client

        client = get_mistral_client()

        messages: list[AssistantMessage | SystemMessage | ToolMessage | UserMessage] = [
            SystemMessage(content=system_prompt),
            UserMessage(content=user_prompt),
        ]
        response = client.chat.complete(
            model=settings.metadata_extraction_model,  # "mistral-small-latest"
            messages=messages,
            temperature=0.0,  # Deterministic inference
            max_tokens=50,
        )

        # Extract inferred unit
        response_content = response.choices[0].message.content
        if not response_content or not isinstance(response_content, str):
            logger.debug("Empty response from Mistral", extra={"metric": metric, "entity": entity})
            return None

        inferred_unit: str = response_content.strip()

        # Validate response
        if inferred_unit == "UNKNOWN" or not inferred_unit:
            logger.debug(
                "Unit inference returned UNKNOWN", extra={"metric": metric, "entity": entity}
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

    except Exception as e:
        logger.warning(
            "Unit inference failed", extra={"metric": metric, "entity": entity, "error": str(e)}
        )
        return None


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
            "Mistral API key not configured - skipping unit inference", extra={"metric": metric}
        )
        return None

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

    # Construct prompt for Mistral
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

    user_prompt = f"""DOCUMENT CONTEXT:
{context_str}

METRIC INFORMATION:
{metric_str}"""

    # Acquire semaphore for rate limiting + apply timeout
    async with MISTRAL_SEMAPHORE:
        try:
            async with asyncio.timeout(5.0):  # 5-second timeout per call
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
                    model=settings.metadata_extraction_model,  # "mistral-small-latest"
                    messages=messages,
                    temperature=0.0,  # Deterministic inference
                    max_tokens=50,
                )

                # Extract inferred unit
                response_content = response.choices[0].message.content
                if not response_content or not isinstance(response_content, str):
                    logger.debug(
                        "Empty response from Mistral", extra={"metric": metric, "entity": entity}
                    )
                    return None

                inferred_unit: str = response_content.strip()

                # Validate response
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

        except TimeoutError:
            logger.warning(
                "Unit inference timeout (5s)", extra={"metric": metric, "entity": entity}
            )
            return None
        except Exception as e:
            logger.warning(
                "Unit inference failed", extra={"metric": metric, "entity": entity, "error": str(e)}
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

    # Build context string once for batch
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

    # Build batch prompt with all metrics
    metrics_list = []
    for idx, row in rows_batch:
        metric = row.get("metric", "Unknown")
        entity = row.get("entity")
        metric_str = f"{idx}. Metric: {metric}"
        if entity:
            metric_str += f" (Entity: {entity})"
        metrics_list.append(metric_str)

    metrics_str = "\n".join(metrics_list)

    system_prompt = """You are analyzing a financial document table to infer units for multiple metrics.

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

    user_prompt = f"""DOCUMENT CONTEXT:
{context_str}

METRICS TO ANALYZE:
{metrics_str}"""

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
    from .core import _extract_page_context, _get_table_caption

    # Extract document context
    page_context = _extract_page_context(table_item, result)
    section_heading = page_context.get("section_heading")
    nearby_text = page_context.get("nearby_text", [])
    page_title = page_context.get("page_title")

    # Get table caption from Docling
    table_caption = _get_table_caption(table_item)

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


async def _apply_context_aware_unit_inference_async(
    rows: list[dict[str, Any]], table_item: TableItem, result: ConversionResult
) -> list[dict[str, Any]]:
    """Async version with batch processing for maximum speedup (Milestones 1 + 2).

    This implements:
    - Milestone 1: Async concurrent processing (10x speedup)
    - Milestone 2: Batch inference (4x additional speedup)
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

    Returns:
        Updated rows with inferred units where possible

    Performance:
        - Milestone 1: 62 min → 6 min (async, 10 concurrent)
        - Milestone 2: 6 min → 1.5 min (batching, 20 rows/call)
        - Total: 942 individual calls → ~47 batch calls
        - Rate-limited: 10 concurrent batches max
        - Timeout: 10s per batch call

    Example:
        >>> rows_in = [
        ...     {'metric': 'EBITDA IFRS', 'entity': 'GROUP', 'value': 128.825, 'unit': None},
        ...     {'metric': 'EBITDA IFRS', 'entity': 'PORTUGAL*', 'value': 91.438, 'unit': None}
        ... ]
        >>> rows_out = await _apply_context_aware_unit_inference_async(rows_in, table_item, result)
        >>> rows_out[0]['unit']
        'Meur'  # Inferred from context
    """
    from raglite.shared.config import settings

    from .core import _extract_page_context, _get_table_caption

    # Check if Mistral API key is configured
    if not settings.mistral_api_key:
        logger.debug("Mistral API key not configured - skipping async unit inference")
        return rows

    # Extract document context
    page_context = _extract_page_context(table_item, result)
    section_heading = page_context.get("section_heading")
    nearby_text = page_context.get("nearby_text", [])
    page_title = page_context.get("page_title")

    # Get table caption from Docling
    table_caption = _get_table_caption(table_item)

    # Create shared Mistral client for connection pooling with timeout configuration
    from raglite.shared.clients import get_mistral_client

    client = get_mistral_client()

    # Cache for inferred units (metric -> unit)
    unit_cache: dict[str, str] = {}

    # Statistics
    inference_count = 0
    cache_hit_count = 0

    # First pass: Check cache and build list of rows needing inference
    rows_needing_inference: list[tuple[int, dict[str, Any]]] = []

    for idx, row in enumerate(rows):
        # Skip rows that already have explicit units
        if row.get("unit") is not None:
            continue

        metric = row.get("metric")

        if not metric:
            continue  # Cannot infer without metric

        # Check cache first (metric-based consistency)
        cache_key = metric
        if cache_key in unit_cache:
            row["unit"] = unit_cache[cache_key]
            row["unit_source"] = "cached_inference"
            cache_hit_count += 1
            continue

        # Add to inference queue
        rows_needing_inference.append((idx, row))

    # Second pass: Batch inference for uncached rows (Milestone 2)
    if rows_needing_inference:
        # Group rows into batches of 20 for efficient API usage
        BATCH_SIZE = 20
        batches = []
        for i in range(0, len(rows_needing_inference), BATCH_SIZE):
            batch = rows_needing_inference[i : i + BATCH_SIZE]
            batches.append(batch)

        logger.info(
            f"Processing {len(rows_needing_inference)} rows in {len(batches)} batches (batch_size={BATCH_SIZE})"
        )

        # Process batches concurrently (rate-limited by semaphore)
        batch_tasks = [
            _infer_units_batch_async(
                batch, table_caption, section_heading, page_title, nearby_text, client
            )
            for batch in batches
        ]
        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

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

    # Log statistics
    total_null_units = sum(1 for row in rows if row.get("unit") is None)
    batch_count = (len(rows_needing_inference) + 19) // 20 if rows_needing_inference else 0
    logger.info(
        "Async batch unit inference complete (Milestones 1+2)",
        extra={
            "total_rows": len(rows),
            "inferred_count": inference_count,
            "cache_hits": cache_hit_count,
            "remaining_null": total_null_units,
            "batch_count": batch_count,
            "batch_size": 20,
            "api_calls_saved": len(rows_needing_inference) - batch_count,
        },
    )

    return rows
