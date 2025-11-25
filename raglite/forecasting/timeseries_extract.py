"""Time-series data extraction from financial documents.

Story 4.1: Extracts temporal financial metrics for forecasting.
Target: ~50 lines per architecture spec.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from dateutil import parser as date_parser

from raglite.shared.logging import get_logger
from raglite.shared.models import TimeSeriesData, TimeSeriesPoint

if TYPE_CHECKING:
    from raglite.shared.models import QueryResult

logger = get_logger(__name__)


class ExtractionError(Exception):
    """Exception raised when time-series extraction fails."""

    pass


def parse_fiscal_date(date_str: str, fiscal_year_start_month: int = 7) -> datetime:
    """Parse fiscal period labels and date formats into datetime.

    Handles various date formats including:
    - Fiscal periods: "Q3 FY24", "FY2024 Q2", "FY24"
    - Standard dates: "Jan 2024", "2024-01", "1/2024", "January 2024"
    - ISO dates: "2024-01-15"

    Args:
        date_str: Date string to parse
        fiscal_year_start_month: Month when fiscal year starts (default: 7 = July)

    Returns:
        datetime object representing the start of the period

    Raises:
        ValueError: If date string cannot be parsed

    Example:
        >>> parse_fiscal_date("Q3 FY24")  # Fiscal Q3 = Jan-Mar (FY24 starts Jul 2023)
        datetime(2024, 1, 1)
        >>> parse_fiscal_date("Jan 2024")
        datetime(2024, 1, 1)
    """
    date_str = date_str.strip().upper()

    # Handle fiscal year patterns: "Q3 FY24", "FY2024 Q2", "FY24", "Q1 2024"
    import re

    # Pattern: Q[1-4] FY[YY|YYYY] or FY[YY|YYYY] Q[1-4]
    fiscal_pattern = r"(?:Q([1-4])\s*)?FY(\d{2,4})(?:\s*Q([1-4]))?"
    match = re.search(fiscal_pattern, date_str)

    if match:
        quarter = match.group(1) or match.group(3)
        year_str = match.group(2)

        # Handle 2-digit years
        year = int(year_str)
        if year < 100:
            year = 2000 + year

        if quarter:
            # Map fiscal quarters to calendar months (assuming July FY start)
            # FY Q1 = Jul-Sep, Q2 = Oct-Dec, Q3 = Jan-Mar, Q4 = Apr-Jun
            quarter_int = int(quarter)
            if fiscal_year_start_month == 7:
                quarter_to_month = {1: 7, 2: 10, 3: 1, 4: 4}
                month = quarter_to_month[quarter_int]
                # Q3 and Q4 are in the calendar year matching FY year
                # Q1 and Q2 are in the previous calendar year
                if quarter_int in (1, 2):
                    year -= 1
            else:
                # Generic fiscal year mapping (Jan start = calendar year)
                quarter_to_month = {1: 1, 2: 4, 3: 7, 4: 10}
                month = quarter_to_month[quarter_int]

            return datetime(year, month, 1)
        else:
            # Full fiscal year - return start of FY
            if fiscal_year_start_month == 7:
                return datetime(year - 1, 7, 1)
            return datetime(year, fiscal_year_start_month, 1)

    # Pattern: Q[1-4] [YYYY] (calendar quarter)
    calendar_q_pattern = r"Q([1-4])\s*(\d{4})"
    match = re.search(calendar_q_pattern, date_str)
    if match:
        quarter = int(match.group(1))
        year = int(match.group(2))
        month = (quarter - 1) * 3 + 1  # Q1=1, Q2=4, Q3=7, Q4=10
        return datetime(year, month, 1)

    # Fallback to dateutil parser for standard date formats
    try:
        parsed = date_parser.parse(date_str)
        return datetime(
            parsed.year, parsed.month, parsed.day, parsed.hour, parsed.minute, parsed.second
        )
    except (ValueError, TypeError) as e:
        raise ValueError(f"Cannot parse date: {date_str}") from e


def normalize_to_interval(data: TimeSeriesData, interval: str) -> TimeSeriesData:
    """Normalize time-series data to consistent time intervals.

    Aggregates data points to the specified interval using averaging.

    Args:
        data: TimeSeriesData with points at various intervals
        interval: Target interval: "monthly", "quarterly", "yearly"

    Returns:
        TimeSeriesData with points normalized to the specified interval

    Raises:
        ValueError: If interval is not supported

    Example:
        >>> data = TimeSeriesData(metric_name="revenue", points=[...], interval="daily")
        >>> normalized = normalize_to_interval(data, "monthly")
    """
    if interval not in ("monthly", "quarterly", "yearly"):
        raise ValueError(f"Unsupported interval: {interval}. Use 'monthly', 'quarterly', 'yearly'")

    if not data.points:
        return TimeSeriesData(
            metric_name=data.metric_name,
            points=[],
            interval=interval,
            source_documents=data.source_documents,
        )

    # Group points by interval bucket
    buckets: dict[str, list[TimeSeriesPoint]] = {}

    for point in data.points:
        if interval == "monthly":
            bucket_key = point.date.strftime("%Y-%m")
        elif interval == "quarterly":
            quarter = (point.date.month - 1) // 3 + 1
            bucket_key = f"{point.date.year}-Q{quarter}"
        else:  # yearly
            bucket_key = str(point.date.year)

        if bucket_key not in buckets:
            buckets[bucket_key] = []
        buckets[bucket_key].append(point)

    # Aggregate points in each bucket (average)
    normalized_points = []
    for bucket_key, points in sorted(buckets.items()):
        avg_value = sum(p.value for p in points) / len(points)

        # Use first point's date as representative
        if interval == "monthly":
            year, month = map(int, bucket_key.split("-"))
            bucket_date = datetime(year, month, 1)
        elif interval == "quarterly":
            year_str, q_str = bucket_key.split("-Q")
            quarter = int(q_str)
            bucket_date = datetime(int(year_str), (quarter - 1) * 3 + 1, 1)
        else:  # yearly
            bucket_date = datetime(int(bucket_key), 1, 1)

        normalized_points.append(
            TimeSeriesPoint(date=bucket_date, value=avg_value, label=bucket_key)
        )

    return TimeSeriesData(
        metric_name=data.metric_name,
        points=normalized_points,
        interval=interval,
        source_documents=data.source_documents,
    )


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
    from raglite.retrieval.search import hybrid_search
    from raglite.shared.clients import get_claude_client

    logger.info(
        "Extracting time-series data",
        extra={"docs": docs, "metric": metric},
    )

    # Step 1: Retrieve relevant chunks using hybrid search
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

    # Step 2: Combine chunk texts for LLM extraction
    combined_text = "\n\n---\n\n".join(
        f"Source: {r.source_document} (page {r.page_number})\n{r.text}" for r in results[:5]
    )

    # Step 3: LLM extraction prompt
    extraction_prompt = f"""Extract all {metric} values with their dates from the following financial document excerpts.

Return ONLY a JSON array of objects, each with:
- "date": the date/period (e.g., "Jan 2024", "Q3 FY24", "2024-01")
- "value": the numeric value (as a number, not string)
- "label": optional label or description

If no {metric} data is found, return an empty array: []

Document excerpts:
{combined_text}

JSON array:"""

    try:
        client = get_claude_client()
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[{"role": "user", "content": extraction_prompt}],
        )
        llm_response = response.content[0].text
    except Exception as e:
        logger.error(f"LLM extraction failed: {e}", exc_info=True)
        raise ExtractionError(f"LLM extraction failed: {e}") from e

    # Step 4: Parse LLM response into TimeSeriesData
    import json

    try:
        # Extract JSON from response (may have markdown code blocks)
        json_text = llm_response.strip()
        if "```" in json_text:
            # Extract JSON from code block
            import re

            json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", json_text)
            if json_match:
                json_text = json_match.group(1)

        data_list = json.loads(json_text)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        raise ExtractionError(f"Invalid LLM response format: {e}") from e

    if not data_list:
        raise ExtractionError(f"No {metric} data found in documents")

    # Convert to TimeSeriesPoint objects
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
