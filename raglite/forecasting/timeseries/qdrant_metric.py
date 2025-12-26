"""Timeseries extraction - Generic metric extraction from Qdrant.

Part of Story 8.1 refactoring to split timeseries_extract.py.
"""

from typing import TYPE_CHECKING

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
    import re

    from qdrant_client.models import FieldCondition, Filter, MatchText, MatchValue

    from raglite.shared.clients import get_qdrant_client
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

    client = get_qdrant_client()
    collection = settings.qdrant_collection_name

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

    if not results:
        logger.warning(
            f"No Qdrant chunks found for metric: {metric}",
            extra={"category": category, "patterns": search_patterns},
        )
        return None

    # Parse values from markdown table rows
    # Extract (period, value) pairs from chunks
    metric_data: dict[str, float] = {}  # period -> value
    source_documents: set[str] = set()

    for point in results:
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
                                            if period not in metric_data or abs(val) > abs(
                                                metric_data[period]
                                            ):
                                                metric_data[period] = val
                                                source_documents.add(source_doc)
                                            break
                                    except ValueError:
                                        continue
            continue

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

                        if period not in metric_data or abs(best_value) > abs(metric_data[period]):
                            metric_data[period] = float(best_value)
                            source_documents.add(source_doc)

    if not metric_data:
        logger.warning(
            f"No values extracted from Qdrant chunks for metric: {metric}",
            extra={"chunks_found": len(results)},
        )
        return None

    # Convert to TimeSeriesPoint objects
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

    if len(points) < min_points:
        logger.warning(
            f"Insufficient data from Qdrant for {metric}: found {len(points)} points, need {min_points}",
            extra={"metric": metric, "points_found": len(points), "min_required": min_points},
        )
        return None

    # Sort by date
    points.sort(key=lambda p: p.date)

    # BUG FIX (P0 Fix #3): Unit Normalization + Outlier Detection (Story 6.23)
    # Electricity Cost (650% MAPE) and Thermal Energy (276% MAPE) have mixed units:
    # - Most values: -400 to -600 (EUR/ton, correct units)
    # - Outliers: -7,023, -21,203 (kEUR thousands, wrong units)
    # - Dec-23 extreme: -17,801 (database corruption)
    #
    # Strategy:
    # 1. Detect outliers >3σ from median (not mean, to avoid outlier influence)
    # 2. For outliers >1000x median, divide by 1000 (kEUR → EUR normalization)
    # 3. Filter remaining outliers >3σ after normalization
    import statistics

    if points:
        values = [abs(p.value) for p in points if p.value is not None]
        if values and len(values) >= 6:
            median_value = statistics.median(values)

            # Step 1: Identify unit inconsistency outliers (kEUR vs EUR)
            # If a value is >5x median, it's likely in wrong units (kEUR instead of EUR)
            # Example: median=-431, outlier=-21,203 → ratio=49x → normalize
            normalized_points = []
            for p in points:
                if p.value is None:
                    continue

                abs_val = abs(p.value)
                ratio = abs_val / median_value if median_value > 0 else 0

                # BUG FIX: Normalize values >5x median (likely kEUR → EUR)
                if ratio > 5.0:
                    # Divide by 1000 to convert kEUR to EUR
                    normalized_value = p.value / 1000
                    logger.info(
                        f"Normalized kEUR to EUR: {p.value:.0f} → {normalized_value:.2f} ({ratio:.1f}x median)",
                        extra={
                            "metric": metric,
                            "date": p.date.strftime("%Y-%m-%d"),
                            "original": p.value,
                            "normalized": normalized_value,
                            "ratio": ratio,
                        },
                    )
                    normalized_points.append(
                        TimeSeriesPoint(
                            date=p.date,
                            value=normalized_value,
                            label=f"{p.label} (normalized kEUR→EUR)",
                        )
                    )
                else:
                    normalized_points.append(p)

            points = normalized_points

            # Step 2: Filter extreme outliers after normalization
            # Recalculate median after normalization
            normalized_values = [abs(p.value) for p in points if p.value is not None]
            if normalized_values and len(normalized_values) >= 6:
                new_median = statistics.median(normalized_values)
                new_std = statistics.stdev(normalized_values) if len(normalized_values) > 1 else 0

                # Filter points >2.5σ from median (extreme outliers indicating data corruption)
                # Story 6.23: Using 2.5σ instead of 3σ for energy costs due to high volatility
                # and data quality issues (mixed units, database corruption)
                filtered_points = []
                outlier_count = 0
                for p in points:
                    if p.value is None:
                        continue

                    abs_val = abs(p.value)
                    deviation = abs(abs_val - new_median)

                    # Keep points within 2.5σ of median (stricter for energy cost metrics)
                    if deviation <= 2.5 * new_std or new_std == 0:
                        filtered_points.append(p)
                    else:
                        outlier_count += 1
                        logger.warning(
                            f"Filtered extreme outlier: {p.value:.2f} (deviation: {deviation:.2f}, threshold: {2.5 * new_std:.2f})",
                            extra={
                                "metric": metric,
                                "date": p.date.strftime("%Y-%m-%d"),
                                "value": p.value,
                                "median": new_median,
                                "std": new_std,
                            },
                        )

                if outlier_count > 0:
                    logger.info(
                        f"Removed {outlier_count} extreme outliers from {metric}",
                        extra={
                            "metric": metric,
                            "outliers_removed": outlier_count,
                            "points_remaining": len(filtered_points),
                        },
                    )
                    points = filtered_points

    # BUG FIX (P0 Fix #4): Capacity Utilization Bounds
    # Percentage metrics cannot exceed 100% (physically impossible)
    # Enforce 0-100 range for percentage-based metrics
    PERCENTAGE_METRICS = {
        "frequency ratio",
        "capacity_utilization",
        "capacity utilization",
        "utilization",
    }
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
        # Log if any values were clamped
        clamped_count = sum(
            1 for orig, new in zip(original_points, points, strict=False) if orig.value != new.value
        )
        if clamped_count > 0:
            logger.warning(
                f"Clamped {clamped_count} percentage values to 0-100 range",
                extra={
                    "metric": metric,
                    "clamped_count": clamped_count,
                    "total_points": len(points),
                },
            )

    # Story 6.23: Cost metrics absolute value transformation (Qdrant fallback)
    # Cost metrics (electricity, thermal, variable cost) are recorded as negative values
    # in financial statements, but forecasting requires positive magnitudes
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
    if metric_lower in COST_METRICS:
        original_points = points
        points = [
            TimeSeriesPoint(
                date=p.date, value=abs(p.value) if p.value is not None else None, label=p.label
            )
            for p in points
            if p.value is not None
        ]
        # Log transformation stats
        negative_count = sum(1 for p in original_points if p.value is not None and p.value < 0)
        if negative_count > 0:
            logger.info(
                f"Converted {negative_count} negative cost values to absolute values (Qdrant)",
                extra={
                    "metric": metric,
                    "negative_values": negative_count,
                    "total_points": len(points),
                    "avg_before": sum(p.value for p in original_points if p.value is not None)
                    / len(original_points),
                    "avg_after": sum(p.value for p in points if p.value is not None) / len(points),
                },
            )

    logger.info(
        f"Qdrant extraction successful for {metric}",
        extra={
            "metric": metric,
            "points": len(points),
            "date_range": f"{points[0].date} to {points[-1].date}",
            "source_documents": list(source_documents)[:5],
        },
    )

    return TimeSeriesData(
        metric_name=metric_lower,
        points=points,
        interval="monthly",
        source_documents=sorted(source_documents),
    )
