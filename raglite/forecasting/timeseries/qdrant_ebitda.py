"""Timeseries extraction - EBITDA extraction from Qdrant.

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
    EBITDA_ENTITY_PATTERNS,
    EBITDA_VALUE_THRESHOLDS,
    ExtractionError,
)


async def extract_ebitda_from_qdrant_chunks(
    entity: str = "portugal",
    min_points: int = 6,  # FIX (2025-12-01): Lowered from 8 for consistency
) -> "TimeSeriesData":
    """Extract EBITDA from Qdrant chunks via regex parsing.

    **DEPRECATED (Story 5.0.4):** This function is maintained for backward compatibility
    but is no longer the primary extraction method. Use extract_timeseries_from_sql()
    which supports any financial metric dynamically without hardcoded entity patterns.

    Story 5.0.1 Enhancement: Fallback extraction when SQL financial_tables
    has incorrect/insufficient data due to table extraction issues.

    Supports multiple geographic entities (DEPRECATED - use SQL extraction):
    - portugal: Portugal consolidated EBITDA IFRS (~€155M YTD)
    - tunisia: Tunisia EBITDA IFRS (~€44M YTD)
    - angola: Angola EBITDA IFRS
    - brazil: Brazil EBITDA IFRS (in BRL)
    - lebanon: Lebanon EBITDA IFRS

    Segment totals (DEPRECATED):
    - cement_portugal: Portugal cement segment
    - concrete: Concrete segment
    - aggregates: Aggregates segment

    Args:
        entity: Geographic entity to extract (default: "portugal") **DEPRECATED**
        min_points: Minimum data points required (default: 8)

    Returns:
        TimeSeriesData with EBITDA values for the specified entity

    Raises:
        ExtractionError: If insufficient data found or invalid entity
    """
    import re

    from qdrant_client.models import FieldCondition, Filter, MatchText

    from raglite.shared.clients import get_qdrant_client
    from raglite.shared.config import settings

    entity_lower = entity.lower().strip()
    if entity_lower not in EBITDA_ENTITY_PATTERNS:
        available = ", ".join(EBITDA_ENTITY_PATTERNS.keys())
        raise ExtractionError(f"Unknown entity '{entity}'. Available entities: {available}")

    search_pattern = EBITDA_ENTITY_PATTERNS[entity_lower]

    logger.info(
        "Extracting EBITDA from Qdrant chunks (fallback)",
        extra={
            "entity": entity,
            "search_pattern": search_pattern,
            "min_points": min_points,
        },
    )

    client = get_qdrant_client()
    collection = settings.qdrant_collection_name

    # Search for chunks containing the entity's EBITDA pattern
    results, _ = client.scroll(
        collection_name=collection,
        scroll_filter=Filter(
            must=[
                FieldCondition(
                    key="text",
                    match=MatchText(text=search_pattern),
                )
            ]
        ),
        limit=100,
        with_payload=True,
    )

    logger.info(
        f"Found Qdrant chunks with {search_pattern}",
        extra={"chunk_count": len(results), "entity": entity},
    )

    # Get entity-specific value threshold (YTD values must exceed this)
    value_threshold = EBITDA_VALUE_THRESHOLDS.get(entity_lower, 10000)

    # Parse consolidated EBITDA values from markdown table rows
    # Pattern: | value | value | value | Portugal EBITDA IFRS | ytd_value | ytd_value | ytd_value |
    # We want the YTD values (right side of table, larger numbers)
    ebitda_data: dict[str, float] = {}  # period -> value

    for point in results:
        text = point.payload.get("text", "")
        source_doc = point.payload.get("source_document", "unknown")

        # Extract document period from filename (e.g., "2025-10 Performance Review" → Oct-25)
        doc_match = re.search(r"(\d{4})-(\d{2})", source_doc)
        if not doc_match:
            continue

        doc_year = int(doc_match.group(1))
        doc_month = int(doc_match.group(2))

        # Find the line containing the entity's EBITDA pattern
        lines = text.split("\n")
        for line in lines:
            if search_pattern in line:
                # Parse the markdown table row
                # Split by | and extract numeric values
                cells = [c.strip() for c in line.split("|") if c.strip()]

                # Find values exceeding entity-specific threshold (YTD values)
                large_values = []
                for cell in cells:
                    # Remove formatting and parse number
                    clean = cell.replace(",", "").replace(".", "").strip()
                    # Match numbers (may have leading -)
                    num_match = re.match(r"^-?\d+$", clean)
                    if num_match:
                        val = int(num_match.group(0))
                        if abs(val) > value_threshold:  # YTD values exceed threshold
                            large_values.append(val)

                # The YTD value for the document's month should be the first large value
                # (tables show current month YTD first in the YTD section)
                if large_values:
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

                    # Use the largest value (most likely current YTD)
                    ytd_value = max(large_values)

                    # Only update if we don't have this period or new value is larger
                    if period not in ebitda_data or ytd_value > ebitda_data[period]:
                        ebitda_data[period] = ytd_value
                        logger.debug(
                            f"Found EBITDA: {period} = €{ytd_value}K",
                            extra={
                                "period": period,
                                "value": ytd_value,
                                "source": source_doc,
                            },
                        )

    if not ebitda_data:
        raise ExtractionError(
            f"No EBITDA values found for entity '{entity}' in Qdrant chunks. "
            f"Search pattern: '{search_pattern}'. "
            f"Available entities: {', '.join(EBITDA_ENTITY_PATTERNS.keys())}"
        )

    # Convert to TimeSeriesPoint objects
    points = []
    for period_str, value in ebitda_data.items():
        try:
            # Parse period (Oct-25 → 2025-10-01)
            date = parse_period_to_date(period_str, 2025)  # Default to 2025
            points.append(
                TimeSeriesPoint(
                    date=date,
                    value=float(value),
                    label=f"{period_str} YTD {entity.title()} (from Qdrant chunks)",
                )
            )
        except (ValueError, TypeError) as e:
            logger.warning(
                f"Skipping invalid period: {period_str}",
                extra={"period": period_str, "value": value, "error": str(e)},
            )

    if len(points) < min_points:
        raise ExtractionError(
            f"Insufficient data from Qdrant: found {len(points)} points, need {min_points}"
        )

    # Sort by date
    points.sort(key=lambda p: p.date)

    # CRITICAL: Convert YTD cumulative values to monthly deltas for Prophet
    # YTD values accumulate: Jan=23K, Feb=36K, Mar=51K, ... Oct=155K
    # Prophet needs periodic values: Jan=23K, Feb=13K (36-23), Mar=15K (51-36), ...
    # Without this conversion, Prophet sees artificial growth pattern and forecasts wrong.
    #
    # BUG FIX (P0): Detect year boundaries and reset YTD baseline
    # Previously: Jan-25 YTD - Dec-24 YTD = negative value (wrong!)
    # Now: When year changes, reset prev_ytd to 0
    monthly_points = []
    prev_ytd = 0.0
    prev_date = None
    for _i, p in enumerate(points):
        # BUG FIX: Detect year gap and reset YTD baseline
        if prev_date is not None:
            if p.date.year != prev_date.year:
                # Year boundary - reset baseline
                prev_str = prev_date.strftime("%b-%y")
                curr_str = p.date.strftime("%b-%y")
                logger.debug(
                    f"Year boundary detected: {prev_str} → {curr_str} - resetting YTD",
                    extra={
                        "prev_year": prev_date.year,
                        "curr_year": p.date.year,
                        "prev_ytd": prev_ytd,
                    },
                )
                prev_ytd = 0.0
                monthly_value = p.value
            else:
                # Same year - normal YTD delta
                monthly_value = p.value - prev_ytd
        else:
            # First point
            monthly_value = p.value

        prev_ytd = p.value
        prev_date = p.date

        # Extract period label (e.g., "Oct-25" from "Oct-25 YTD Portugal...")
        period_label = p.label.split(" ")[0] if p.label and " " in p.label else (p.label or "")

        monthly_points.append(
            TimeSeriesPoint(
                date=p.date,
                value=monthly_value,
                label=f"{period_label} Monthly {entity.title()} (from Qdrant)",
            )
        )

        logger.debug(
            f"YTD→Monthly: {period_label} YTD €{p.value:,.0f}K → Monthly €{monthly_value:,.0f}K",
            extra={"period": period_label, "ytd": p.value, "monthly": monthly_value},
        )

    # BUG FIX (P0): Outlier detection and removal for EBITDA
    # Data quality issues cause extreme values:
    # - Dec-23: €94,388K (should be ~€10-20K, likely full-year YTD not converted)
    # - Dec-24: €-131,112K (impossible negative, data error)
    # Use IQR-based outlier detection to remove values that break forecasting.
    if len(monthly_points) >= 10:
        values = [p.value for p in monthly_points]
        sorted_values = sorted(values)
        n = len(sorted_values)
        q1 = sorted_values[n // 4]
        q3 = sorted_values[3 * n // 4]
        iqr = q3 - q1
        lower_bound = q1 - 3 * iqr  # Use 3x IQR for conservative outlier detection
        upper_bound = q3 + 3 * iqr

        original_count = len(monthly_points)
        monthly_points = [p for p in monthly_points if lower_bound <= p.value <= upper_bound]

        if len(monthly_points) < original_count:
            removed = original_count - len(monthly_points)
            logger.warning(
                f"Removed {removed} outlier(s) from EBITDA data using 3x IQR bounds",
                extra={
                    "removed_count": removed,
                    "lower_bound": lower_bound,
                    "upper_bound": upper_bound,
                    "remaining_points": len(monthly_points),
                },
            )

    logger.info(
        f"Qdrant EBITDA extraction successful for {entity}",
        extra={
            "entity": entity,
            "points": len(monthly_points),
            "date_range": f"{monthly_points[0].date} to {monthly_points[-1].date}",
            "ytd_values": [f"€{p.value:.0f}K" for p in points],
            "monthly_values": [f"€{p.value:.0f}K" for p in monthly_points],
        },
    )

    return TimeSeriesData(
        metric_name=f"ebitda_{entity.lower()}",
        points=monthly_points,
        interval="monthly",
        source_documents=[],
    )
