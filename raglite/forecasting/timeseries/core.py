"""Timeseries extraction - Main extraction API.

Part of Story 8.1 refactoring to split timeseries_extract.py.
"""

from typing import TYPE_CHECKING

from raglite.shared.logging import get_logger
from raglite.shared.models import TimeSeriesData, TimeSeriesPoint

if TYPE_CHECKING:
    from raglite.shared.models import QueryResult

logger = get_logger(__name__)

from raglite.forecasting.timeseries.metadata import (  # noqa: E402
    ExtractionError,
)
from raglite.forecasting.timeseries.parsing import parse_fiscal_date  # noqa: E402


def _build_extraction_prompt(
    metric: str,
    combined_text: str,
) -> str:
    """Build LLM prompt for time-series extraction.

    Args:
        metric: Metric to extract (revenue, cash_flow, expenses, ebitda)
        combined_text: Combined document excerpts

    Returns:
        Formatted prompt string
    """
    prompt_template = """\
Extract all {metric} values with their dates from the following \
financial document excerpts.

Return ONLY a JSON array of objects, each with:
- "date": the date/period (e.g., "Jan 2024", "Q3 FY24", "2024-01")
- "value": the numeric value (as a number, not string)
- "label": optional label or description

If no {metric} data is found, return an empty array: []

Document excerpts:
{combined_text}

JSON array:"""
    return prompt_template.format(metric=metric, combined_text=combined_text)


def _extract_json_from_response(llm_response: str) -> str:
    """Extract JSON from LLM response, handling markdown code blocks.

    Args:
        llm_response: Raw LLM response text

    Returns:
        Extracted JSON string

    Raises:
        ExtractionError: If JSON cannot be extracted
    """
    import json

    json_text = llm_response.strip()
    if "```" in json_text:
        import re

        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", json_text)
        if json_match:
            json_text = json_match.group(1)

    # Validate that it's valid JSON
    try:
        json.loads(json_text)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        raise ExtractionError(f"Invalid LLM response format: {e}") from e

    return json_text


def _parse_data_points(
    data_list: list[dict],
    metric: str,
) -> list[TimeSeriesPoint]:
    """Parse LLM response data into TimeSeriesPoint objects.

    Args:
        data_list: List of dicts from LLM response
        metric: Metric name for error messages

    Returns:
        List of TimeSeriesPoint objects

    Raises:
        ExtractionError: If no valid data points can be parsed
    """
    points = []
    for item in data_list:
        try:
            date = parse_fiscal_date(str(item["date"]))
            value = float(item["value"])
            label = item.get("label")
            points.append(TimeSeriesPoint(date=date, value=value, label=label))
        except (KeyError, ValueError) as e:
            logger.warning(f"Skipping invalid data point: {item}, error: {e}")
            continue

    if not points:
        raise ExtractionError(f"No valid {metric} data points could be parsed")

    # Sort by date
    points.sort(key=lambda p: p.date)

    return points


async def _retrieve_and_filter_documents(
    docs: list[str],
    metric: str,
) -> list["QueryResult"]:
    """Retrieve relevant documents and filter by specified docs.

    Args:
        docs: List of document IDs or filenames to search
        metric: Metric to extract (revenue, cash_flow, expenses, ebitda)

    Returns:
        Filtered list of QueryResult objects

    Raises:
        ExtractionError: If retrieval fails or no matching documents found
    """
    from raglite.retrieval.search import hybrid_search

    query = f"historical {metric} values by month quarter year"
    try:
        results: list[QueryResult] = await hybrid_search(
            query=query,
            top_k=10,
            enable_hybrid=True,
            auto_classify=False,
        )
    except Exception as e:
        logger.error(f"Retrieval failed: {e}", exc_info=True)
        raise ExtractionError(f"Failed to retrieve documents: {e}") from e

    if not results:
        raise ExtractionError(f"No documents found containing {metric} data")

    # Filter results by source documents if specified
    if docs:
        results = [r for r in results if any(d in r.source_document for d in docs)]
        if not results:
            raise ExtractionError(f"No matching documents found in specified files: {docs}")

    return results


async def extract_timeseries(
    docs: list[str],
    metric: str = "revenue",
) -> TimeSeriesData:
    """Extract time-series data from financial documents.

    Uses Epic 1 retrieval to find time-series mentions, then LLM extraction
    to parse values with dates into structured TimeSeriesData.

    Args:
        docs: List of document IDs or filenames to search
        metric: Metric to extract (revenue, cash_flow, expenses, ebitda)

    Returns:
        TimeSeriesData with metric_name, values, timestamps

    Raises:
        ExtractionError: If extraction fails or insufficient data found

    Example:
        >>> data = await extract_timeseries(["Q3_2024_Report.pdf"], metric="revenue")
        >>> len(data.points)
        4
    """
    import json

    from raglite.shared.clients import get_mistral_client

    logger.info(
        "Extracting time-series data",
        extra={"docs": docs, "metric": metric},
    )

    # Step 1: Retrieve relevant chunks using hybrid search
    results = await _retrieve_and_filter_documents(docs, metric)

    # Step 2: Combine chunk texts for LLM extraction
    combined_text = "\n\n---\n\n".join(
        f"Source: {r.source_document} (page {r.page_number})\n{r.text}" for r in results[:5]
    )

    # Step 3: LLM extraction prompt
    extraction_prompt = _build_extraction_prompt(metric, combined_text)

    try:
        client = get_mistral_client()
        response = client.chat.complete(
            model="mistral-large-latest",
            messages=[{"role": "user", "content": extraction_prompt}],
        )
        llm_response = response.choices[0].message.content if response.choices else ""
    except Exception as e:
        logger.error(f"LLM extraction failed: {e}", exc_info=True)
        raise ExtractionError(f"LLM extraction failed: {e}") from e

    # Step 4: Parse LLM response into TimeSeriesData
    json_text = _extract_json_from_response(llm_response)
    data_list = json.loads(json_text)

    if not data_list:
        raise ExtractionError(f"No {metric} data found in documents")

    # Convert to TimeSeriesPoint objects
    points = _parse_data_points(data_list, metric)

    logger.info(
        "Time-series extraction complete",
        extra={"metric": metric, "points_count": len(points)},
    )

    return TimeSeriesData(
        metric_name=metric,
        points=points,
        interval="raw",  # Raw extraction, normalize separately if needed
        source_documents=[r.source_document for r in results[:5]],
    )
