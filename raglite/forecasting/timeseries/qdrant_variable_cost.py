"""Timeseries extraction - Variable cost extraction from Qdrant.

Part of Story 8.1 refactoring to split timeseries_extract.py.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from raglite.shared.logging import get_logger
from raglite.shared.models import TimeSeriesData, TimeSeriesPoint

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)

from raglite.forecasting.timeseries.metadata import (  # noqa: E402
    CURRENCY_TO_EUR,
    detect_entity,
)


async def extract_variable_cost_from_qdrant_chunks(
    entity: str = "portugal",
    min_points: int = 6,
) -> "TimeSeriesData | None":
    """Extract Variable Cost from Qdrant chunks with European decimal handling.

    Story 6.15: Specialized extraction for Variable Cost (EUR/ton) values.

    Variable Cost data format:
    - Values in EUR/ton (e.g., 281,1 = 281.1)
    - European decimal format (comma as decimal separator)
    - Can be in parentheses for negative values: (7.718) = -7718
    - Row format: "| Variable Costs Cem | (60.102) | (64.177) |..."

    Args:
        entity: Geographic entity (default: portugal)
        min_points: Minimum required data points

    Returns:
        TimeSeriesData with Variable Cost values in EUR/ton
    """
    from raglite.shared.clients import get_qdrant_client
    from raglite.shared.config import settings
    from raglite.shared.models import TimeSeriesData

    logger.info("Extracting Variable Cost from Qdrant chunks (fallback)")

    import re  # Ensure re is available in function scope

    client = get_qdrant_client()
    collection = settings.qdrant_collection_name

    # Search patterns for Variable Cost
    search_patterns = ["Variable Cost", "Variable Costs", "Variable Costs Cem"]

    # Query Qdrant for chunks containing Variable Cost
    from qdrant_client.models import FieldCondition, Filter, MatchText

    results = []
    for pattern in search_patterns:
        batch, _ = client.scroll(
            collection_name=collection,
            scroll_filter=Filter(
                must=[
                    FieldCondition(
                        key="text",
                        match=MatchText(text=pattern),
                    )
                ]
            ),
            limit=200,
            with_payload=True,
        )
        results.extend(batch)
        if results:
            break

    if not results:
        logger.warning("No Variable Cost chunks found in Qdrant")
        return None

    logger.info(
        f"Found {len(results)} chunks for Variable Cost extraction (before entity filter)",
        extra={"total_chunks": len(results), "entity_filter": entity},
    )

    # Story 6.15: Filter chunks by entity before processing
    if entity:
        filtered_results = []
        skipped_count = 0
        for point in results:
            chunk_text = point.payload.get("text", "")
            detected = detect_entity(chunk_text)

            # Include chunk if entity matches or if entity is None (undetectable, default to include)
            if detected == entity or (detected is None and entity == "portugal"):
                filtered_results.append(point)
            else:
                skipped_count += 1

        logger.info(
            f"Entity filtering: kept {len(filtered_results)}/{len(results)} chunks (skipped {skipped_count} non-{entity})",
            extra={"entity": entity, "kept": len(filtered_results), "skipped": skipped_count},
        )
        results = filtered_results

    if not results:
        logger.warning(f"No chunks remaining after entity filter (entity={entity})")
        return None

    # Parse chunks to extract (period, value) pairs
    metric_data: dict[str, float] = {}
    source_documents: set[str] = set()

    for point in results:
        text = point.payload.get("text", "")
        source_doc = point.payload.get("source_document", "")
        # Extract period from source document name (e.g., "2025-09 Performance Review")
        doc_match = re.search(r"(\d{4})-(\d{2})", source_doc)
        if not doc_match:
            continue

        doc_year = int(doc_match.group(1))
        doc_month = int(doc_match.group(2))

        # Find Variable Cost lines
        for line in text.split("\n"):
            # Look for lines with Variable Cost
            if not any(p.lower() in line.lower() for p in search_patterns):
                continue

            # Parse the markdown table row
            cells = [c.strip() for c in line.split("|") if c.strip()]

            # Extract numeric values with European decimal handling
            for cell in cells:
                # Skip non-numeric cells
                clean = cell.strip()
                if not clean or clean.lower() in [
                    "variable cost",
                    "variable costs",
                    "variable costs cem",
                    "eur/ton",
                    "brl/ton",
                ]:
                    continue

                # Handle parentheses for negative values: (7.718) -> -7718
                is_negative = clean.startswith("(") and clean.endswith(")")
                if is_negative:
                    clean = clean[1:-1]  # Remove parentheses

                # Remove currency symbols and spaces
                clean = clean.replace("€", "").replace(" ", "").strip()

                # European decimal format: comma is decimal separator
                # Check if this looks like European format (has comma, no dot after comma)
                if "," in clean:
                    # European format: 281,1 -> 281.1
                    clean = clean.replace(".", "").replace(",", ".")
                else:
                    # American format or integer: remove commas
                    clean = clean.replace(",", "")

                # Try to parse as float
                try:
                    val = float(clean)
                    if is_negative:
                        val = -val

                    # Story 6.15 Task 2.5: Currency normalization to EUR/ton
                    # Convert Tunisia (TND) and Brazil (BRL) values to EUR for comparison
                    if entity == "tunisia":
                        # Convert TND/ton to EUR/ton
                        val = val * CURRENCY_TO_EUR["TND"]
                    elif entity == "brazil":
                        # Convert BRL/ton to EUR/ton
                        val = val * CURRENCY_TO_EUR["BRL"]
                    # Portugal is already in EUR/ton, no conversion needed

                    # Story 6.15: Entity-specific value range validation
                    # Variable cost filtering for consistency:
                    # - Should be NEGATIVE (costs are outflows)
                    # - Portugal (EUR/ton): -150 to -350 (AC3 requirement)
                    # - After currency normalization, all entities in EUR/ton should match this range
                    valid_range = False
                    if entity == "portugal":
                        # AC3: Portugal-only EUR/ton range (-150 to -350)
                        valid_range = val < 0 and -350 <= val <= -150
                    elif entity in ("tunisia", "brazil"):
                        # After currency conversion, should match Portugal EUR/ton range
                        valid_range = val < 0 and -350 <= val <= -150
                    else:
                        # General range for other entities or mixed data
                        valid_range = val < 0 and abs(val) > 100 and abs(val) < 400

                    if valid_range:
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

                        if period not in metric_data:
                            metric_data[period] = val
                            source_documents.add(source_doc)
                        break  # Found value for this line
                except ValueError:
                    continue

    if not metric_data:
        logger.warning("No Variable Cost values extracted from Qdrant")
        return None

    if len(metric_data) < min_points:
        logger.warning(
            f"Insufficient Variable Cost data: {len(metric_data)} points (need {min_points})"
        )
        return None

    # Convert to TimeSeriesPoint objects
    points = []
    for period, value in sorted(metric_data.items(), key=lambda x: x[0]):
        # Parse period (e.g., "Oct-25")
        month_str, year_str = period.split("-")
        month_map = {
            "Jan": 1,
            "Feb": 2,
            "Mar": 3,
            "Apr": 4,
            "May": 5,
            "Jun": 6,
            "Jul": 7,
            "Aug": 8,
            "Sep": 9,
            "Oct": 10,
            "Nov": 11,
            "Dec": 12,
        }
        month = month_map.get(month_str, 1)
        year = 2000 + int(year_str)

        points.append(
            TimeSeriesPoint(
                date=datetime(year, month, 1),
                value=value,
                label=period,
            )
        )

    # Sort by date
    points.sort(key=lambda p: p.date)

    logger.info(
        f"Variable Cost extraction successful: {len(points)} points",
        extra={"entity": entity, "points": len(points)},
    )

    return TimeSeriesData(
        metric_name="variable_cost",
        points=points,
        interval="monthly",
        source_documents=sorted(source_documents),
    )
