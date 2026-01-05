"""Timeseries extraction - Generic metric extraction from Qdrant.

Part of Story 8.1 refactoring to split timeseries_extract.py.
"""

from typing import TYPE_CHECKING, Any

from raglite.forecasting.timeseries.parsing import parse_period_to_date  # noqa: E402
from raglite.shared.logging import get_logger
from raglite.shared.models import TimeSeriesData, TimeSeriesPoint

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)

from raglite.forecasting.timeseries.metadata import (  # noqa: E402
    METRIC_CATEGORY_MAP,
    METRIC_SEARCH_PATTERNS,
)

# Metric type constants
PERCENTAGE_METRICS = {
    "frequency ratio",
    "capacity_utilization",
    "capacity utilization",
    "utilization",
}

COST_METRICS = {
    "electrical energy",
    "electricity",
    "electricity_cost",
    "thermal energy",
    "thermal",
    "thermal_cost",
    "fuel_cost",
    "variable cost",
    "variable_cost",
}


def _parse_chunk_metadata(
    point: Any,
    search_patterns: list[str],
) -> tuple[str | None, float | None, str]:
    """Extract metadata and numeric value from a Qdrant chunk.

    Args:
        point: Qdrant point with payload
        search_patterns: List of patterns to search for in text

    Returns:
        Tuple of (period, value, source_document)
    """
    import re

    text = point.payload.get("text", "")
    source_doc = point.payload.get("source_document", "unknown")
    reporting_period = point.payload.get("reporting_period", "")

    # Extract document period from filename (e.g., "2025-10 Performance Review" → Oct-25)
    doc_match = re.search(r"(\d{4})-(\d{2})", source_doc)
    if not doc_match:
        # Try to get from reporting_period payload
        if reporting_period:  # Fix: Check None before regex
            period_match = re.search(r"([A-Za-z]{3})-(\d{2})", reporting_period)
        else:
            period_match = None
        if period_match:
            period = f"{period_match.group(1).title()}-{period_match.group(2)}"
            # Extract first numeric value from text
            value = _extract_numeric_from_text(text, search_patterns)
            return (period, value, source_doc)
        return (None, None, source_doc)

    doc_year = int(doc_match.group(1))
    doc_month = int(doc_match.group(2))

    # Find lines containing our search patterns
    lines = text.split("\n")
    for line in lines:
        for search_pattern in search_patterns:
            if search_pattern.lower() in line.lower():
                # Parse the markdown table row
                cells = [c.strip() for c in line.split("|") if c.strip()]

                # Extract numeric values
                numeric_values = []
                for cell in cells:
                    clean = cell.replace(",", "").replace(".", "").replace("€", "").strip()
                    num_match = re.match(r"^-?\d+$", clean)
                    if num_match:
                        try:
                            val = int(num_match.group(0))
                            numeric_values.append(val)
                        except ValueError:
                            continue

                if numeric_values:
                    # Convert to period format (Oct-25)
                    month_abbr = [
                        "Jan",
                        "Feb",
                        "Mar",
                        "Apr",
                        "May",
                        "Jun",
                        "Jul",
                        "Aug",
                        "Sep",
                        "Oct",
                        "Nov",
                        "Dec",
                    ][doc_month - 1]
                    period = f"{month_abbr}-{doc_year % 100:02d}"

                    # Use the largest absolute value
                    best_value = max(numeric_values, key=abs)

                    return (period, float(best_value), source_doc)

    return (None, None, source_doc)


def _extract_numeric_from_text(text: str, search_patterns: list[str]) -> float | None:
    """Extract numeric value from text matching search patterns.

    Args:
        text: Text to search
        search_patterns: Patterns to match

    Returns:
        Numeric value or None
    """
    import re

    lines = text.split("\n")
    for line in lines:
        for search_pattern in search_patterns:
            if search_pattern.lower() in line.lower():
                cells = [c.strip() for c in line.split("|") if c.strip()]
                for cell in cells:
                    clean = cell.replace(",", "").replace("€", "").strip()
                    num_match = re.match(r"^-?[\d.]+$", clean)
                    if num_match:
                        try:
                            val = float(num_match.group(0))
                            if abs(val) > 0.01:  # Skip zero values
                                return val
                        except ValueError:
                            continue
    return None


def _aggregate_by_period(
    results: list[Any],
    search_patterns: list[str],
) -> tuple[dict[str, float], set[str]]:
    """Aggregate values by time period from Qdrant chunks.

    Args:
        results: List of Qdrant points
        search_patterns: Search patterns for the metric

    Returns:
        Tuple of (metric_data dict, source_documents set)
    """
    metric_data: dict[str, float] = {}  # period -> value
    source_documents: set[str] = set()

    for point in results:
        period, value, source_doc = _parse_chunk_metadata(point, search_patterns)

        if period and value is not None:
            # Keep the largest absolute value for each period
            if period not in metric_data or abs(value) > abs(metric_data[period]):
                metric_data[period] = value
                source_documents.add(source_doc)

    return (metric_data, source_documents)


def _normalize_and_filter_outliers(
    points: list[TimeSeriesPoint],
    metric: str,
) -> list[TimeSeriesPoint]:
    """Apply unit normalization and outlier filtering.

    BUG FIX (P0 Fix #3): Unit Normalization + Outlier Detection (Story 6.23).
    Strategy: 1) Normalize values >5x median (kEUR→EUR), 2) Filter outliers >2.5σ.
    """
    import statistics

    if not points:
        return points

    values = [abs(p.value) for p in points if p.value is not None]
    if not values or len(values) < 6:
        return points

    # Step 1: Normalize unit inconsistencies (kEUR vs EUR)
    median_value = statistics.median(values)
    normalized_points = []
    for p in points:
        if p.value is None:
            continue
        abs_val = abs(p.value)
        ratio = abs_val / median_value if median_value > 0 else 0
        if ratio > 5.0:
            normalized_value = p.value / 1000
            logger.info(
                f"Normalized kEUR to EUR: {p.value:.0f} → {normalized_value:.2f}",
                extra={"metric": metric, "date": p.date.strftime("%Y-%m-%d"), "ratio": ratio},
            )
            normalized_points.append(
                TimeSeriesPoint(
                    date=p.date, value=normalized_value, label=f"{p.label} (normalized)"
                )
            )
        else:
            normalized_points.append(p)
    points = normalized_points

    # Step 2: Filter extreme outliers after normalization
    normalized_values = [abs(p.value) for p in points if p.value is not None]
    if not normalized_values or len(normalized_values) < 6:
        return points

    new_median = statistics.median(normalized_values)
    new_std = statistics.stdev(normalized_values) if len(normalized_values) > 1 else 0
    filtered_points = []
    outlier_count = 0
    for p in points:
        if p.value is None:
            continue
        abs_val = abs(p.value)
        deviation = abs(abs_val - new_median)
        if deviation <= 2.5 * new_std or new_std == 0:
            filtered_points.append(p)
        else:
            outlier_count += 1
            logger.warning(
                f"Filtered outlier: {p.value:.2f}",
                extra={"metric": metric, "date": p.date.strftime("%Y-%m-%d")},
            )

    if outlier_count > 0:
        logger.info(f"Removed {outlier_count} outliers from {metric}")

    return filtered_points


def _apply_metric_specific_transformations(
    points: list[TimeSeriesPoint],
    metric: str,
) -> list[TimeSeriesPoint]:
    """Apply metric-specific transformations (percentage bounds, cost absolute values)."""
    metric_lower = metric.lower().strip()

    # BUG FIX (P0 Fix #4): Clamp percentage metrics to 0-100 range
    if metric_lower in PERCENTAGE_METRICS:
        original_points = points
        points = [
            TimeSeriesPoint(
                date=p.date,
                value=min(max(p.value, 0), 100) if p.value is not None else None,
                label=p.label,
            )
            for p in points
            if p.value is not None
        ]
        clamped_count = sum(
            1 for orig, new in zip(original_points, points, strict=False) if orig.value != new.value
        )
        if clamped_count > 0:
            logger.warning(f"Clamped {clamped_count} percentage values to 0-100 range")

    # Story 6.23: Convert cost metrics from negative to absolute values
    if metric_lower in COST_METRICS:
        original_points = points
        points = [
            TimeSeriesPoint(
                date=p.date, value=abs(p.value) if p.value is not None else None, label=p.label
            )
            for p in points
            if p.value is not None
        ]
        negative_count = sum(1 for p in original_points if p.value is not None and p.value < 0)
        if negative_count > 0:
            logger.info(f"Converted {negative_count} negative cost values to absolute values")

    return points


def _query_qdrant_for_metric(
    category: str | None,
    search_patterns: list[str],
    collection: str,
) -> list:
    """Query Qdrant using category filter or text search.

    Args:
        category: Metric category for filtering (optional)
        search_patterns: Text patterns to search for
        collection: Qdrant collection name

    Returns:
        List of Qdrant points matching the query
    """
    from qdrant_client.models import FieldCondition, Filter, MatchText, MatchValue

    from raglite.shared.clients import get_qdrant_client

    client = get_qdrant_client()
    results = []

    # Try category-based filter first (more precise)
    if category:
        try:
            results, _ = client.scroll(
                collection_name=collection,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="metric_category",
                            match=MatchValue(value=category),
                        )
                    ]
                ),
                limit=300,
                with_payload=True,
            )
            logger.info(
                f"Qdrant category filter returned {len(results)} chunks",
                extra={"category": category, "chunks": len(results)},
            )
        except Exception as e:
            logger.warning(f"Category filter failed: {e}")

    # If no results, fall back to text search with patterns
    if not results and search_patterns:
        for pattern in search_patterns:
            try:
                results, _ = client.scroll(
                    collection_name=collection,
                    scroll_filter=Filter(
                        must=[
                            FieldCondition(
                                key="text",
                                match=MatchText(text=pattern),
                            )
                        ]
                    ),
                    limit=300,
                    with_payload=True,
                )
                if results:
                    logger.info(
                        f"Qdrant text search found {len(results)} chunks",
                        extra={"pattern": pattern, "chunks": len(results)},
                    )
                    break
            except Exception as e:
                logger.warning(f"Text search failed for pattern '{pattern}': {e}")

    return results


def _convert_to_timeseries_points(
    metric_data: dict[str, float],
    metric: str,
) -> list[TimeSeriesPoint]:
    """Convert period-value pairs to TimeSeriesPoint objects.

    Args:
        metric_data: Dictionary of period -> value
        metric: Metric name for labeling

    Returns:
        List of TimeSeriesPoint objects sorted by date
    """
    points = []
    for period_str, value in metric_data.items():
        try:
            date = parse_period_to_date(period_str, 2025)
            points.append(
                TimeSeriesPoint(
                    date=date,
                    value=float(value),
                    label=f"{period_str} {metric.title()} (from Qdrant chunks)",
                )
            )
        except (ValueError, TypeError) as e:
            logger.warning(
                f"Skipping invalid period: {period_str}",
                extra={"period": period_str, "value": value, "error": str(e)},
            )

    # Sort by date
    points.sort(key=lambda p: p.date)
    return points


async def extract_metric_from_qdrant_chunks(
    metric: str,
    min_points: int = 6,
    entity: str = "portugal",
) -> TimeSeriesData | None:
    """Extract ANY financial metric from Qdrant chunks.

    Story 6.15: Generalizes the EBITDA-only fallback to support all metrics.
    Uses metric_category payload filtering + text search patterns.

    Args:
        metric: Metric name (e.g., "revenue", "sales_volume", "ebitda")
        min_points: Minimum required data points
        entity: Geographic entity filter (default: portugal)

    Returns:
        TimeSeriesData or None if insufficient data
    """
    from raglite.shared.config import settings

    metric_lower = metric.lower().strip()

    # Map metric to category and search patterns
    category = METRIC_CATEGORY_MAP.get(metric_lower)
    search_patterns = METRIC_SEARCH_PATTERNS.get(metric_lower, [metric])

    logger.info(
        "Extracting metric from Qdrant chunks (fallback)",
        extra={
            "metric": metric,
            "category": category,
            "search_patterns": search_patterns,
            "min_points": min_points,
        },
    )

    # Query Qdrant for matching chunks
    results = _query_qdrant_for_metric(category, search_patterns, settings.qdrant_collection_name)

    if not results:
        logger.warning(
            f"No Qdrant chunks found for metric: {metric}",
            extra={"category": category, "patterns": search_patterns},
        )
        return None

    # Aggregate values by period from chunks
    metric_data, source_documents = _aggregate_by_period(results, search_patterns)

    if not metric_data:
        logger.warning(
            f"No values extracted from Qdrant chunks for metric: {metric}",
            extra={"chunks_found": len(results)},
        )
        return None

    # Convert to TimeSeriesPoint objects
    points = _convert_to_timeseries_points(metric_data, metric)

    if len(points) < min_points:
        logger.warning(
            f"Insufficient data from Qdrant for {metric}: found {len(points)} points, need {min_points}",
            extra={"metric": metric, "points_found": len(points), "min_required": min_points},
        )
        return None

    # Apply data quality transformations
    points = _normalize_and_filter_outliers(points, metric)
    points = _apply_metric_specific_transformations(points, metric)

    logger.info(
        f"Qdrant extraction successful for {metric}",
        extra={
            "metric": metric,
            "points": len(points),
            "date_range": f"{points[0].date} to {points[-1].date}" if points else "empty",
            "source_documents": list(source_documents)[:5],
        },
    )

    return TimeSeriesData(
        metric_name=metric_lower,
        points=points,
        interval="monthly",
        source_documents=sorted(source_documents),
    )
