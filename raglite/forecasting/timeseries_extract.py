"""Time-series data extraction from financial documents.

Story 4.1: Extracts temporal financial metrics for forecasting.
Target: ~50 lines per architecture spec.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from dateutil import parser as date_parser

from raglite.forecasting.regressor_fetch import fetch_single_regressor
from raglite.ingestion.entity_normalizer import get_entity_ilike_pattern, normalize_entity
from raglite.shared.logging import get_logger
from raglite.shared.models import TimeSeriesData, TimeSeriesPoint

if TYPE_CHECKING:
    from raglite.shared.models import QueryResult

logger = get_logger(__name__)


class ExtractionError(Exception):
    """Exception raised when time-series extraction fails."""

    pass


class MetricValidationError(ExtractionError):
    """Exception for metric validation failures.

    Story 5.0.4 AC3: Structured error with available metrics list.

    Raised when a metric exists in the database but has insufficient data points
    for reliable forecasting (<8 data points required).

    DATABASE FIX (2025-12-03): Now inherits from ExtractionError to maintain
    backward compatibility with existing test assertions.

    Attributes:
        metric_name: Name of the metric that failed validation
        data_points_found: Number of data points actually found
        minimum_required: Minimum data points required (typically 8)
        available_metrics: List of alternative metrics that have sufficient data
    """

    def __init__(
        self,
        metric_name: str,
        data_points_found: int,
        minimum_required: int,
        available_metrics: list[str],
    ):
        """Initialize MetricValidationError with detailed context.

        Args:
            metric_name: Name of the metric that failed
            data_points_found: Actual number of data points found
            minimum_required: Minimum data points required for forecasting
            available_metrics: List of metrics with sufficient data (for suggestions)
        """
        self.metric_name = metric_name
        self.data_points_found = data_points_found
        self.minimum_required = minimum_required
        self.available_metrics = available_metrics

        # Construct helpful error message
        available_list = ", ".join(available_metrics[:5]) if available_metrics else "none"
        if len(available_metrics) > 5:
            available_list += f" (and {len(available_metrics) - 5} more)"

        super().__init__(
            f"Metric '{metric_name}' has {data_points_found} data points "
            f"(minimum {minimum_required} required for reliable forecasting). "
            f"Available metrics with sufficient data: {available_list}"
        )


# DEPRECATED (Story 5.0.4): Entity-based EBITDA extraction replaced by dynamic metric discovery
# These patterns are no longer used by extract_timeseries_from_sql() which now supports
# any metric with sufficient data points. extract_ebitda_from_qdrant_chunks() still uses
# these for fallback compatibility but will be removed in future versions.
#
# Entity search patterns for EBITDA extraction (DEPRECATED)
EBITDA_ENTITY_PATTERNS = {
    # Geographic entities (consolidated by country)
    "portugal": "Portugal EBITDA IFRS",
    "tunisia": "Tunisia EBITDA IFRS",
    "angola": "Angola EBITDA IFRS",
    "brazil": "Brazil EBITDA IFRS",
    "lebanon": "Lebanon EBITDA IFRS",
    # Segment totals (not consolidated GROUP)
    "cement_portugal": "Cement EBITDA IFRS",
    "concrete": "Concrete EBITDA IFRS",
    "aggregates": "Aggregates EBITDA IFRS",
}

# Value thresholds for YTD vs monthly detection (DEPRECATED)
EBITDA_VALUE_THRESHOLDS = {
    "portugal": 10000,  # €10M+ YTD
    "tunisia": 5000,  # €5M+ YTD
    "angola": 50000,  # €50M+ YTD
    "brazil": 50000,  # €50M+ YTD
    "lebanon": 500,  # €500K+ YTD
    "cement_portugal": 50000,  # €50M+ YTD
    "concrete": 500,  # Smaller segment
    "aggregates": 5000,  # €5M+ YTD
}

# Story 6.15: Qdrant metric_category mapping for fallback extraction
# Maps user-facing metric names to Qdrant payload.metric_category values
# Used when SQL extraction fails or returns insufficient data
METRIC_CATEGORY_MAP = {
    # Financial metrics
    "revenue": "Revenue",
    "turnover": "Revenue",
    "sales": "Revenue",
    "ebitda": "EBITDA",
    # Volume metrics
    "sales_volume": "Production Volume",
    "production_volume": "Production Volume",
    "capacity_utilization": "Production Volume",
    # Cost metrics
    "variable_cost": "Operating Expenses",
    "operating_expenses": "Operating Expenses",
    "fixed_costs": "Operating Expenses",
    # Other
    "cash_flow": "Cash Flow",
    "capex": "Capital Expenditure",
}

# Story 6.15: Search text patterns for Qdrant text-based fallback
# Used when metric_category filter returns no results
METRIC_SEARCH_PATTERNS = {
    "revenue": ["Turnover", "Revenue"],
    "turnover": ["Turnover", "Revenue"],
    "sales_volume": ["Sales Volumes", "Sales Volume", "Sales kton"],
    "variable_cost": ["Variable Cost", "Variable Costs"],
    "capacity_utilization": ["Frequency Ratio", "Capacity Utilization"],
    "ebitda": ["EBITDA IFRS", "EBITDA"],
    "cash_flow": ["Cash Flow", "Operating Cash Flow"],
    "capex": ["Capital Expenditure", "CAPEX"],
}

# Story 6.15: Entity detection patterns for Variable Cost extraction
# Maps entity names to contextual patterns found in financial documents
ENTITY_PATTERNS = {
    "portugal": ["Portugal", "PT", "Custos Variáveis", "EUR/ton", "EUR/m³"],
    "tunisia": ["Tunisia", "TN", "TND", "Tunisie", "TND/ton"],
    "brazil": ["Brazil", "BR", "BRL", "Brasil", "BRL/ton"],
}

# Story 6.15 Task 2.5: Currency conversion rates to EUR
# Used to normalize Tunisia (TND) and Brazil (BRL) Variable Cost values to EUR/ton
# for cross-entity comparison and forecasting
CURRENCY_TO_EUR = {
    "TND": 0.31,  # 1 TND ≈ 0.31 EUR (Tunisian Dinar to Euro)
    "BRL": 0.18,  # 1 BRL ≈ 0.18 EUR (Brazilian Real to Euro)
    "EUR": 1.0,  # 1 EUR = 1 EUR (Portugal, baseline)
}


def detect_entity(text: str) -> str | None:
    """Detect geographic entity from chunk text.

    Story 6.15: Identifies Portugal/Tunisia/Brazil from context patterns
    to filter Variable Cost data by entity.

    Args:
        text: Chunk text to analyze for entity indicators

    Returns:
        Canonical entity name ('portugal', 'tunisia', 'brazil') or None if undetectable

    Example:
        >>> detect_entity("Portugal Variable Cost EUR/ton")
        'portugal'
        >>> detect_entity("Brazil BRL/ton Custos")
        'brazil'
        >>> detect_entity("Unknown text")
        None
    """
    import re

    text_upper = text.upper()

    # Priority order: Check country-specific patterns first (country names, currencies)
    # then fall back to language patterns (which may be shared)

    # Check Tunisia patterns first (most specific: TND currency, Tunisia/Tunisie country names)
    for pattern in ENTITY_PATTERNS["tunisia"]:
        # M1 FIX: Use word boundaries to avoid false positives (e.g., "TN" vs "TNT")
        pattern_upper = pattern.upper()
        if len(pattern_upper) <= 3:  # Short patterns like "TN", "BR", "PT" need word boundaries
            if re.search(rf"\b{re.escape(pattern_upper)}\b", text_upper):
                return "tunisia"
        else:
            if pattern_upper in text_upper:
                return "tunisia"

    # Check Brazil patterns (BRL currency, Brazil/Brasil country name)
    for pattern in ENTITY_PATTERNS["brazil"]:
        pattern_upper = pattern.upper()
        if len(pattern_upper) <= 3:  # Short patterns like "BR" need word boundaries
            if re.search(rf"\b{re.escape(pattern_upper)}\b", text_upper):
                return "brazil"
        else:
            if pattern_upper in text_upper:
                return "brazil"

    # Check Portugal patterns (EUR currency, Portugal/PT)
    # Note: "Custos Variáveis" can appear in both Portugal and Brazil contexts,
    # so we check it last after more specific indicators
    for pattern in ENTITY_PATTERNS["portugal"]:
        pattern_upper = pattern.upper()
        if len(pattern_upper) <= 3:  # Short patterns like "PT" need word boundaries
            if re.search(rf"\b{re.escape(pattern_upper)}\b", text_upper):
                return "portugal"
        else:
            if pattern_upper in text_upper:
                return "portugal"

    return None  # Unknown entity


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
    from raglite.shared.models import TimeSeriesData, TimeSeriesPoint

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

        from datetime import datetime

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
            parsed.year,
            parsed.month,
            parsed.day,
            parsed.hour,
            parsed.minute,
            parsed.second,
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


def parse_period_to_date(period: str, fiscal_year: int) -> datetime:
    """Parse period string (Mon-YY format) to datetime.

    Converts period strings like "Jan-25", "Dec-24" to datetime objects
    representing the first day of that month.

    BUG FIX (P0): Extract year from period suffix to prevent duplicate dates.
    Previously ignored year suffix and used fiscal_year parameter, causing
    "Jan-24" and "Jan-25" to both map to same date when processing multi-year data.

    Args:
        period: Period string in Mon-YY format (e.g., "Jan-25", "Dec-24")
        fiscal_year: Fiscal year as integer (DEPRECATED - now extracted from period suffix)

    Returns:
        datetime object for the first day of the period month

    Raises:
        ValueError: If period format is invalid or month name not recognized

    Example:
        >>> parse_period_to_date("Jan-25", 2025)
        datetime(2025, 1, 1)
        >>> parse_period_to_date("Dec-24", 2024)
        datetime(2024, 12, 1)
    """
    import re

    # BUG FIX: Parse period suffix to determine actual year
    # "Jan-24" → year = 2024, "Jan-25" → year = 2025
    match = re.match(r"^([A-Za-z]+)-(\d{2})$", period.strip())
    if not match:
        raise ValueError(
            f"Invalid period format: '{period}'. Expected Mon-YY format (e.g., Jan-25)"
        )

    month_abbrev = match.group(1).capitalize()
    year_suffix = int(match.group(2))
    year = 2000 + year_suffix  # 24 → 2024, 25 → 2025

    # Month name to integer mapping
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

    if month_abbrev not in month_map:
        raise ValueError(
            f"Invalid month abbreviation: '{month_abbrev}'. "
            f"Expected one of: {', '.join(month_map.keys())}"
        )

    month = month_map[month_abbrev]
    return datetime(year, month, 1)


def prefer_group_level(entity: str | None, metric: str) -> str | None:
    """For metrics that aggregate regionally, prefer GROUP-level data.

    Story 6.10.1 AC5: For aggregate metrics like EBITDA,
    prefer GROUP-level consolidated data to avoid mixing regional data
    which causes high MAPE from aggregating incompatible data sources.

    Story 6.10.4 Fix: Return None for non-aggregate metrics to disable
    entity filtering (allow all entities). Previously returned "Group"
    by default which caused 10/12 SKIPs due to missing GROUP-level data.

    Story 6.10.4 Revenue Fix: Removed "revenue" and "turnover" from GROUP
    metrics because turnover data in database has entity="Currency (1000 EUR)",
    not "GROUP". Filtering by GROUP returns 0 rows causing 101,488% MAPE.

    Args:
        entity: Requested entity (may be None)
        metric: Metric name being extracted

    Returns:
        'Group' for aggregate metrics when no specific entity requested,
        original entity if specified, or None to disable entity filter.
    """
    # Story 6.10.4: Only EBITDA has actual GROUP-level data in database
    # Revenue/turnover doesn't have GROUP entity - uses "Currency (1000 EUR)"
    # Sales Volume and Capacity Utilization also lack GROUP-level rows
    GROUP_PREFERRED_METRICS: set[str] = {"ebitda"}  # Only EBITDA has GROUP data

    # Normalize metric name for comparison
    metric_lower = metric.lower().strip()

    # If this is a GROUP-preferred metric and no specific entity requested
    if metric_lower in GROUP_PREFERRED_METRICS and entity is None:
        return "Group"

    # Return entity if specified, None otherwise (no filtering for non-aggregate metrics)
    return entity


async def extract_timeseries_from_sql(
    metric: str = "revenue",
    min_points: int = 6,  # FIX (2025-12-01): Lowered from 8 to allow GROUP data with missing months
    aggregation: str = "sum",  # Story 6.10.4: "sum" or "max" - use "max" for revenue/turnover
    entity: str | None = None,  # Story 6.15 Task 3: Entity filter for multi-entity metrics
) -> TimeSeriesData:
    """Extract time-series data from PostgreSQL financial_tables.

    Story 5.0.4 AC2, AC5: Dynamic metric support - works for ANY financial metric
    with 8+ data points, not just hardcoded metrics. No entity disambiguation needed.

    Primary extraction method for forecasting - uses structured SQL data
    rather than LLM extraction from document chunks. Queries the
    financial_tables for rows matching the metric name with valid
    period and fiscal_year values.

    For EBITDA metrics, automatically uses consolidated GROUP entity values
    to avoid double-counting regional breakdowns (Brazil, Tunisia, etc.).

    Story 6.10.4: Added aggregation parameter to handle metrics where multiple
    values per period exist (e.g., turnover has both actual values and ratios).
    Use "max" for revenue/turnover to get the actual value instead of summing
    all sub-components.

    Story 6.15 Task 3: Added entity parameter for filtering multi-entity metrics
    like Variable Cost. When entity is specified, SQL query filters by normalized
    entity name (e.g., "portugal" -> matches "Portugal", "PT", etc.).

    Args:
        metric: Metric name to extract (e.g., "revenue", "expenses", "ebitda", "capex", "margins")
                Supports any metric found in financial_tables with sufficient data points.
        min_points: Minimum number of data points required (default: 6)
        aggregation: "sum" (default) or "max" - aggregation method for multiple values per period.
                     Use "max" for revenue/turnover where largest value is actual amount.
        entity: Optional entity filter (e.g., "portugal", "tunisia", "brazil").
                When specified, filters SQL results to entity-specific data.
                If None, uses prefer_group_level() logic for aggregate metrics.

    Returns:
        TimeSeriesData with metric_name, chronologically sorted points, interval

    Raises:
        ExtractionError: If insufficient data (<min_points) or SQL query fails

    Example:
        >>> # Extract any metric dynamically
        >>> data = await extract_timeseries_from_sql(metric="revenue", min_points=6)
        >>> len(data.points) >= 6
        True
        >>> # EBITDA uses consolidated GROUP values automatically
        >>> ebitda_data = await extract_timeseries_from_sql(metric="ebitda")
        >>> ebitda_data.metric_name
        'ebitda'
        >>> # Variable Cost filtered by entity
        >>> vc_data = await extract_timeseries_from_sql(metric="variable_cost", entity="portugal")
        >>> vc_data.metric_name
        'variable_cost'
    """
    from raglite.shared.clients import get_postgresql_connection

    # Metric name synonyms mapping (revenue → turnover for Secil reports)
    # Story 6.26: Restored "ebitda" → "EBITDA IFRS" mapping
    # EBITDA IFRS has 20 YTD periods with GROUP entity (verified Dec 2025)
    # Plain "EBITDA" only has line-item breakdowns (entity="Currency (1000 EUR)"), not consolidated GROUP values
    # The "only 7 periods" claim was incorrect - actual data shows 20 distinct YTD periods
    METRIC_SYNONYMS = {
        "revenue": "turnover",
        "revenues": "turnover",
        "sales": "turnover",
        "ebitda": "EBITDA IFRS",  # Story 6.26: Restored - routes to consolidated YTD data
    }

    # Apply synonym mapping if metric matches a known synonym
    metric_search = METRIC_SYNONYMS.get(metric.lower(), metric)

    # Metrics requiring entity filter for proper consolidation
    # These metrics have multiple entity rows (geographic, segments) that would sum incorrectly
    # Format: metric -> (entity_filter, prefer_ytd_data)
    #
    # Story 6.10.4: Only EBITDA IFRS has GROUP-level consolidated data in database
    # - turnover: has entity="Currency (1000 EUR)", NOT "GROUP" - filter removed
    # - sales volume: no GROUP rows available - filter removed
    # - capacity utilization: no GROUP rows available - filter removed
    ENTITY_FILTERS: dict[str, tuple[str | None, bool]] = {
        # Story 6.26: RESTORED GROUP filter for EBITDA IFRS
        # Format: (entity_filter, prefer_ytd)
        # Without GROUP filter, SUM aggregates ALL entities (Portugal+Angola+Brazil+Tunisia+Lebanon+GROUP)
        # which produces values 4-5x higher than correct GROUP-only consolidated values.
        # GROUP row contains the consolidated total - we must NOT sum geographic segments.
        "EBITDA IFRS": ("GROUP", True),  # Filter to GROUP entity only, use YTD period format
        # Story 6.10.4: Removed turnover, sales volume, capacity utilization
        # because they don't have GROUP-level data rows (GROUP filter = 0 results)
    }

    # Story 6.26: Metrics that should use MAX aggregation instead of SUM
    # Use MAX when multiple documents report the same period (duplicates from document versions)
    # GROUP values are consolidated totals - summing duplicates produces wrong results
    METRICS_USE_MAX_AGGREGATION = {"EBITDA IFRS", "ebitda ifrs"}
    if metric_search in METRICS_USE_MAX_AGGREGATION:
        aggregation = "max"
        logger.info(
            f"Using MAX aggregation for {metric_search} (prevents duplicate document summing)",
            extra={"metric": metric_search, "aggregation": aggregation},
        )

    # Story 6.15 Task 3: Override entity filter if user explicitly specifies entity parameter
    # This allows filtering by entity for ANY metric, not just those in ENTITY_FILTERS
    if entity is not None:
        # User-specified entity filter takes precedence
        # Normalize entity and add to filters
        canonical_entity = normalize_entity(entity)
        if canonical_entity:
            ENTITY_FILTERS[metric_search] = (canonical_entity, False)
            logger.info(
                "User-specified entity filter applied",
                extra={"metric": metric, "entity": entity, "canonical": canonical_entity},
            )
    else:
        # Story 6.10.1 AC5: Dynamically add GROUP filter for aggregate metrics
        # using prefer_group_level() to catch metrics not explicitly listed above
        preferred_entity = prefer_group_level(None, metric)
        if preferred_entity == "Group" and metric_search not in ENTITY_FILTERS:
            # Add dynamic GROUP filter for this aggregate metric
            ENTITY_FILTERS[metric_search] = ("GROUP", False)
            logger.debug(
                "Dynamic GROUP filter applied via prefer_group_level",
                extra={"metric": metric, "metric_search": metric_search},
            )

    # STRATEGY: Always try exact match first, fall back to wildcard if no results
    # This prevents aggregating multiple variants (EBITDA, EBITDA IFRS, EBITDA Portugal, etc.)
    # User can request specific variants by exact name (e.g., "EBITDA Portugal")

    logger.info(
        "Extracting time-series from SQL",
        extra={
            "metric": metric,
            "metric_search": metric_search,
            "min_points": min_points,
            "synonym_applied": metric_search != metric.lower(),
            "strategy": "exact_first_then_wildcard",
        },
    )

    try:
        conn = get_postgresql_connection()
        cursor = conn.cursor()

        # Query financial_tables for matching metric rows
        # ENHANCEMENT (Story 5.0.1 Post-UAT): Aggregate multiple rows per period to get consolidated values
        # DEDUPLICATION FIX: Each Performance Review report contains historical data, so Dec-24 appears
        # in all 10 reports (2025-01 through 2025-10). We must deduplicate by selecting ONLY the most
        # recent document per period to avoid summing duplicate historical data 10x.
        #
        # Strategy:
        # 1. CTE identifies latest document per period using MAX(document_id) (2025-10 > 2025-09...)
        # 2. Join to get ALL rows from that latest document only
        # 3. GROUP BY period to aggregate business units within that single document
        # 4. Filter out budget rows (B Apr-25) to keep only actuals
        #
        # EXACT-MATCH-FIRST STRATEGY (Story 5.0.4 Enhancement):
        # Try exact match first to avoid aggregating multiple metric variants
        # Fall back to wildcard LIKE only if exact match returns no results

        # Try exact match first
        metric_condition = "metric = %s"
        metric_param = metric_search
        match_type = "exact"

        # Apply entity filter if metric requires it (e.g., EBITDA IFRS → GROUP only)
        # Story 6.10.1: Use normalized entity matching via get_entity_ilike_pattern()
        # which returns a complete SQL clause like "entity ILIKE ANY(ARRAY['%Group%', '%Conso%', ...])"
        entity_filter = ""
        prefer_ytd = False
        filter_config = ENTITY_FILTERS.get(metric_search)
        if filter_config:
            required_entity, prefer_ytd = filter_config
            # Story 6.25: Only apply entity filter if required_entity is not None
            # This allows YTD mode without entity filtering (for EBITDA IFRS)
            if required_entity is not None:
                # Story 6.10.1 AC1-AC3: Normalize entity and use ILIKE pattern for all aliases
                # This eliminates entity mixing (e.g., GROUP vs Portugal vs Brazil data)
                canonical_entity = normalize_entity(required_entity)
                # get_entity_ilike_pattern returns complete clause: "entity ILIKE ANY(ARRAY[...])"
                entity_clause = get_entity_ilike_pattern(canonical_entity or required_entity)
                entity_filter = f"AND {entity_clause}"
                logger.info(
                    "Applying normalized entity filter for consolidated metric",
                    extra={
                        "metric": metric_search,
                        "required_entity": required_entity,
                        "canonical_entity": canonical_entity,
                        "entity_clause_preview": entity_clause[:80] + "..."
                        if len(entity_clause) > 80
                        else entity_clause,
                        "prefer_ytd": prefer_ytd,
                    },
                )
            else:
                # Story 6.25: YTD mode without entity filtering
                logger.info(
                    "Using YTD period mode without entity filter",
                    extra={"metric": metric_search, "prefer_ytd": prefer_ytd},
                )

        # nosec B608 - SQL query uses parameterized internal variables only
        # Story 5.0.4 Fix: Infer fiscal_year from period when NULL (e.g., "Jan-25" → 2025)
        # This addresses data quality issue where only 33% of rows have fiscal_year populated

        # Story 6.10.4: Determine aggregation function - SUM for most metrics, MAX for revenue/turnover
        # Security: Validate aggregation parameter to prevent SQL injection
        if aggregation.lower() not in ["sum", "max", "avg", "min", "count"]:
            raise ValueError(f"Invalid aggregation function: {aggregation}")
        agg_func = "MAX" if aggregation.lower() == "max" else "SUM"

        # Helper function to build query with current metric_condition and entity_filter
        # FIX (2025-12-01): For YTD metrics (like EBITDA IFRS), extract only YTD periods
        def build_query() -> str:
            # Different period matching based on prefer_ytd flag
            if prefer_ytd:
                # YTD mode: Match "YTD  Mon-YY" format (e.g., "YTD  Jun-25")
                # Regex extracts first Mon-YY after YTD prefix, handles malformed data
                # Note: %% is escaped to produce single % for LIKE clause (psycopg2 requirement)
                # Excludes: "YTD  B Mon-YY" where B comes immediately after YTD (budget-only rows)
                # NOTE (2025-12-01): We do NOT match "Total YTD Mon ..." format from misparsed
                # June 2025 document because it uses different metric values (EBITDA vs EBITDA IFRS)
                period_match = """
                      AND period ~ '^YTD\\s+[A-Z][a-z]{2}-[0-9]{2}'
                      AND period NOT LIKE 'YTD  B %%'
                      AND period NOT LIKE 'YTD B %%'"""
                # Extract month: first Mon-YY occurrence (e.g., "YTD  Jun-25" → "Jun-25")
                # Note: period_extract is a regular string interpolated into f-string,
                # so {2} should NOT be escaped - f-string only processes top-level {} not nested
                period_extract = "(REGEXP_MATCH(period, '([A-Z][a-z]{2}-[0-9]{2})'))[1]"
                is_ytd_flag = "TRUE"
            else:
                # Standard mode: Match "Mon-YY" format
                period_match = "AND period ~ '^[A-Z][a-z]{2}-[0-9]{2}$'"
                period_extract = "period"
                is_ytd_flag = "FALSE"

            # Security: Validate all SQL fragments before interpolation
            # These are internally generated constants, not user input
            if not isinstance(metric_condition, str) or ";" in metric_condition:
                raise ValueError("Invalid metric condition")
            if not isinstance(entity_filter, str) or ";" in entity_filter:
                raise ValueError("Invalid entity filter")

            # All interpolated variables are internally controlled constants or validated above
            # nosec B608 - SQL query uses validated internal variables only, not user input
            return f"""
                WITH periods_with_year AS (
                    -- Extract fiscal year from period when fiscal_year is NULL
                    -- For YTD data: "YTD  Apr-25" → Apr-25 → 2025
                    -- For standard: "Jan-25" → 2025
                    SELECT
                        -- Extract the Mon-YY portion (strip YTD prefix if present)
                        {period_extract} as clean_period,
                        -- Flag whether this is YTD data
                        {is_ytd_flag} as is_ytd,
                        -- Infer fiscal year from the Mon-YY suffix (e.g., "Jun-25" → 2025)
                        2000 + CAST(SUBSTRING(period FROM '[0-9]{{2}}$') AS INTEGER) as inferred_fiscal_year,
                        document_id,
                        value,
                        entity,
                        metric
                    FROM financial_tables
                    WHERE {metric_condition}
                      AND period IS NOT NULL
                      {period_match}
                      AND value IS NOT NULL
                      {entity_filter}
                ),
                latest_doc_per_period AS (
                    -- For each period (using clean period without YTD prefix), identify the most recent document
                    SELECT
                        clean_period,
                        inferred_fiscal_year,
                        MAX(document_id) as latest_doc
                    FROM periods_with_year
                    GROUP BY clean_period, inferred_fiscal_year
                )
                SELECT
                    ft.clean_period as period,
                    ft.inferred_fiscal_year as fiscal_year,
                    {agg_func}(ft.value) as total_value,
                    COUNT(*) as row_count,
                    MAX(ft.document_id) as source_doc,
                    BOOL_OR(ft.is_ytd) as is_ytd_data
                FROM periods_with_year ft
                INNER JOIN latest_doc_per_period ld
                    ON ft.clean_period = ld.clean_period
                    AND ft.inferred_fiscal_year = ld.inferred_fiscal_year
                    AND ft.document_id = ld.latest_doc
                GROUP BY ft.clean_period, ft.inferred_fiscal_year
                HAVING {agg_func}(ft.value) <> 0
                -- FIX (2025-12-09): Changed from > 0 to <> 0 to support cost metrics (negative values)
                -- FIX (2025-12-01): Sort chronologically, not alphabetically
                -- "Apr-25" should come AFTER "Feb-25", not before
                ORDER BY ft.inferred_fiscal_year, TO_DATE(ft.clean_period, 'Mon-YY')
            """

        # Try exact match first
        query = build_query()

        logger.debug(
            "Executing SQL query (exact match first)",
            extra={
                "metric_condition": metric_condition,
                "metric_param": metric_param,
                "match_type": match_type,
                "query_preview": query[:500],
            },
        )

        cursor.execute(query, (metric_param,))
        rows = cursor.fetchall()

        # If no results with exact match, try wildcard as fallback
        if not rows and match_type == "exact":
            logger.info(
                "No results with exact match, trying wildcard fallback",
                extra={"metric_search": metric_search},
            )

            # Switch to wildcard matching
            metric_condition = "LOWER(metric) LIKE %s"
            metric_param = f"%{metric_search.lower()}%"
            match_type = "wildcard"

            query = build_query()
            cursor.execute(query, (metric_param,))
            rows = cursor.fetchall()

            if rows:
                logger.info(
                    "Wildcard fallback succeeded",
                    extra={"rows_found": len(rows), "metric_param": metric_param},
                )

        cursor.close()

        if not rows:
            logger.warning(
                "No SQL data found for metric",
                extra={"metric": metric, "rows_found": 0},
            )

            # Story 5.0.4 AC3: Suggest available metrics when metric not found
            from raglite.forecasting.metrics import list_available_metrics

            try:
                available_info = await list_available_metrics(min_points=min_points, use_cache=True)
                available_names = [m.name for m in available_info if m.can_forecast]

                raise ExtractionError(
                    f"No data found in financial_tables for metric '{metric}'. "
                    f"Available metrics: {', '.join(available_names[:5])}"
                    + (
                        f" (and {len(available_names) - 5} more)"
                        if len(available_names) > 5
                        else ""
                    )
                )
            except ExtractionError:
                # Re-raise ExtractionError as-is
                raise
            except Exception:
                # If metrics discovery fails, use simple error
                raise ExtractionError(
                    f"No data found in financial_tables for metric '{metric}' "
                    f"with valid period and fiscal_year"
                ) from None

        # Parse rows into TimeSeriesPoint objects
        # Each row is now aggregated and deduplicated: (period, fiscal_year, total_value, row_count, source_doc, is_ytd_data)
        points = []
        source_documents = set()  # FIX (2025-12-01): Track unique source documents
        is_ytd_data = False  # Track if any row is YTD data (for conversion later)
        for (
            period_str,
            fiscal_year,
            total_value,
            row_count,
            source_doc,
            row_is_ytd,
        ) in rows:
            if source_doc:
                source_documents.add(source_doc)
            if row_is_ytd:
                is_ytd_data = True
            try:
                date = parse_period_to_date(period_str, fiscal_year)
                # Extract document month from source_doc (e.g., "2025-10 Performance Review" → "2025-10")
                doc_month = source_doc.split()[0] if source_doc else "unknown"

                # Story 6.24.1: Filter year values (2000-2099) that were accidentally captured as metrics
                # Issue: Year column headers (2021, 2022, 2023, 2024) being captured as metric values
                # Impacts: Capacity Utilization (64% MAPE), Thermal Energy (25% MAPE)
                if total_value is not None and 2000 <= total_value <= 2099:
                    logger.warning(
                        "Filtered year-like value from metric data",
                        extra={
                            "metric": metric,
                            "value": total_value,
                            "period": period_str,
                            "fiscal_year": fiscal_year,
                            "source_doc": source_doc,
                        },
                    )
                    continue

                points.append(
                    TimeSeriesPoint(
                        date=date,
                        value=float(total_value),
                        label=f"{period_str} (FY{fiscal_year}, {row_count} rows from {doc_month} report)",
                    )
                )
            except (ValueError, TypeError) as e:
                logger.warning(
                    "Skipping invalid data point from SQL",
                    extra={
                        "period": period_str,
                        "fiscal_year": fiscal_year,
                        "total_value": total_value,
                        "row_count": row_count,
                        "error": str(e),
                    },
                )
                continue

        if not points:
            raise ExtractionError(
                f"No valid data points could be parsed from SQL for metric '{metric}'"
            )

        # Check minimum points threshold (Story 5.0.4 AC3)
        if len(points) < min_points:
            logger.warning(
                "Insufficient SQL data points",
                extra={
                    "metric": metric,
                    "points_found": len(points),
                    "min_required": min_points,
                },
            )

            # Story 5.0.4 AC3: Provide helpful error with available metrics
            # Import here to avoid circular dependency
            from raglite.forecasting.metrics import list_available_metrics

            try:
                # Fetch available metrics to provide suggestions
                available_info = await list_available_metrics(min_points=min_points, use_cache=True)
                available_names = [m.name for m in available_info if m.can_forecast]

                # Raise MetricValidationError with suggestions
                raise MetricValidationError(
                    metric_name=metric,
                    data_points_found=len(points),
                    minimum_required=min_points,
                    available_metrics=available_names,
                )
            except MetricValidationError:
                # Re-raise MetricValidationError as-is
                raise
            except Exception as metrics_error:
                # If metrics discovery fails, fall back to simpler error
                logger.warning(
                    "Could not fetch available metrics for error message",
                    extra={"error": str(metrics_error)},
                )
                raise ExtractionError(
                    f"Insufficient data: found {len(points)} points, need {min_points} minimum"
                ) from None

        # Sort by date (should already be sorted, but ensure it)
        points.sort(key=lambda p: p.date)

        # BUG FIX (P0 Fix #2): Deduplication safety net for duplicate dates
        # Multi-year documents create duplicate dates when same period extracted multiple times
        # Aggregate by taking the value with largest absolute magnitude (most authoritative)
        from collections import defaultdict

        date_to_points: dict[datetime, list[TimeSeriesPoint]] = defaultdict(list)
        for p in points:
            date_to_points[p.date].append(p)

        if len(date_to_points) < len(points):
            # Duplicates detected - aggregate them
            logger.warning(
                "Duplicate dates detected in time-series data - aggregating by taking value with largest magnitude",
                extra={
                    "metric": metric,
                    "total_points": len(points),
                    "unique_dates": len(date_to_points),
                    "duplicates_removed": len(points) - len(date_to_points),
                },
            )

            deduplicated_points = []
            for date_val in sorted(date_to_points.keys()):
                date_points = date_to_points[date_val]
                # Take the point with the largest absolute value (most authoritative)
                best_point = max(
                    date_points, key=lambda p: abs(p.value) if p.value is not None else 0
                )
                deduplicated_points.append(best_point)

            points = deduplicated_points

        # FIX (2025-12-01): Convert YTD cumulative values to monthly deltas
        # YTD values accumulate: Feb=23M, Mar=39M, Apr=51M, ... Sep=151M
        # Prophet needs periodic values: Feb=23M, Mar=16M (39-23), Apr=12M (51-39), ...
        # Without this conversion, Prophet sees artificial growth pattern and forecasts wrong.
        #
        # BUG FIX (P0): Detect year boundaries and reset YTD baseline
        if is_ytd_data and len(points) > 1:
            logger.info(
                "Converting YTD cumulative values to monthly deltas",
                extra={
                    "metric": metric,
                    "points_count": len(points),
                    "ytd_values": [f"€{p.value:.1f}M" for p in points[:5]],
                },
            )

            monthly_points = []
            prev_ytd = 0.0
            prev_date = None
            for p in points:
                # BUG FIX: Detect year gap and reset YTD baseline
                if prev_date is not None:
                    if p.date.year != prev_date.year:
                        # Year boundary - reset baseline
                        logger.info(
                            f"Year boundary detected: {prev_date.strftime('%b-%y')} → {p.date.strftime('%b-%y')} - resetting YTD baseline",
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

                # FIX (2025-12-01): Detect month gaps and interpolate
                # If we jump from May to Jul (missing June), split the delta evenly
                if prev_date is not None:
                    months_gap = (p.date.year - prev_date.year) * 12 + (
                        p.date.month - prev_date.month
                    )
                    # Only interpolate within same year (avoid crossing year boundary)
                    if months_gap > 1 and p.date.year == prev_date.year:
                        # Split combined delta across missing months
                        monthly_avg = monthly_value / months_gap
                        logger.info(
                            f"Detected {months_gap - 1} missing month(s), interpolating",
                            extra={
                                "gap_start": prev_date.strftime("%b-%y"),
                                "gap_end": p.date.strftime("%b-%y"),
                                "combined_delta": monthly_value,
                                "per_month_avg": monthly_avg,
                            },
                        )
                        # Create synthetic points for missing months
                        from dateutil.relativedelta import relativedelta

                        for gap_month_offset in range(1, months_gap):
                            gap_date = prev_date + relativedelta(months=gap_month_offset)
                            gap_label = gap_date.strftime("%b-%y")
                            monthly_points.append(
                                TimeSeriesPoint(
                                    date=gap_date,
                                    value=monthly_avg,
                                    label=f"{gap_label} Monthly (interpolated)",
                                )
                            )
                        # The current point also gets the averaged value
                        monthly_value = monthly_avg

                prev_ytd = p.value
                prev_date = p.date

                # Update label to reflect monthly conversion
                period_label = (
                    p.label.split(" (")[0] if p.label and " (" in p.label else (p.label or "")
                )

                monthly_points.append(
                    TimeSeriesPoint(
                        date=p.date,
                        value=monthly_value,
                        label=f"{period_label} Monthly (converted from YTD)",
                    )
                )

                logger.debug(
                    f"YTD→Monthly: {period_label} YTD €{p.value:.1f}M → Monthly €{monthly_value:.1f}M",
                    extra={
                        "period": period_label,
                        "ytd": p.value,
                        "monthly": monthly_value,
                    },
                )

            points = monthly_points
            logger.info(
                "YTD→Monthly conversion complete",
                extra={
                    "metric": metric,
                    "monthly_values": [f"€{p.value:.1f}M" for p in points[:5]],
                },
            )

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
                    new_std = (
                        statistics.stdev(normalized_values) if len(normalized_values) > 1 else 0
                    )

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
        # Story 6.24.1: Also reject year-like values before clamping
        PERCENTAGE_METRICS = {
            "frequency ratio",
            "capacity_utilization",
            "capacity utilization",
            "utilization",
        }
        metric_lower_check = metric.lower()
        if metric_lower_check in PERCENTAGE_METRICS:
            original_points = points
            filtered_points = []
            year_filtered_count = 0

            for p in points:
                if p.value is None:
                    continue
                # Story 6.24.1: Filter year values (2000-2099) before clamping
                if 2000 <= p.value <= 2099:
                    logger.warning(
                        f"Rejected year value {p.value} for percentage metric {metric}",
                        extra={
                            "metric": metric,
                            "value": p.value,
                            "date": p.date.isoformat() if p.date else None,
                        },
                    )
                    year_filtered_count += 1
                    continue

                # Apply 0-100 clamping for valid percentage values
                clamped_value = min(max(p.value, 0), 100)
                filtered_points.append(
                    TimeSeriesPoint(date=p.date, value=clamped_value, label=p.label)
                )

            points = filtered_points

            # Log if any year values were filtered
            if year_filtered_count > 0:
                logger.warning(
                    f"Filtered {year_filtered_count} year-like values from percentage metric",
                    extra={
                        "metric": metric,
                        "year_filtered": year_filtered_count,
                        "points_remaining": len(points),
                    },
                )

            # Log if any values were clamped
            clamped_count = sum(
                1
                for orig, new in zip(original_points, points, strict=False)
                if orig.value != new.value
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

        # Story 6.23: Cost metrics absolute value transformation
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
        if metric_lower_check in COST_METRICS:
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
                    f"Converted {negative_count} negative cost values to absolute values",
                    extra={
                        "metric": metric,
                        "negative_values": negative_count,
                        "total_points": len(points),
                        "avg_before": sum(p.value for p in original_points if p.value is not None)
                        / len(original_points),
                        "avg_after": sum(p.value for p in points if p.value is not None)
                        / len(points),
                    },
                )

        # Calculate date range for logging
        min_date = points[0].date.strftime("%Y-%m-%d")
        max_date = points[-1].date.strftime("%Y-%m-%d")

        logger.info(
            "SQL extraction successful",
            extra={
                "metric": metric,
                "points": len(points),
                "date_range": f"{min_date} to {max_date}",
                "is_ytd_data": is_ytd_data,
            },
        )

        # Story 6.26: Scale validation for EBITDA to catch line-item extraction errors
        # Secil Group EBITDA should be in EUR millions (€100-200M/year), not EUR thousands
        # If average extracted value is < €1M, we're likely extracting line-item breakdowns
        # instead of consolidated GROUP values. This is a critical safety net.
        EBITDA_METRICS = {"ebitda", "ebitda ifrs"}
        if metric.lower() in EBITDA_METRICS and points:
            avg_value = sum(p.value for p in points if p.value is not None) / len(points)
            # €1M threshold: monthly EBITDA for Secil Group should be €10-20M
            # YTD values in database are in EUR millions (e.g., 139.37 = €139.37M)
            # If avg < 1.0, we're extracting wrong data (line items avg €97)
            if avg_value < 1.0:
                logger.error(
                    f"EBITDA scale validation FAILED: avg={avg_value:.2f}, expected EUR millions",
                    extra={
                        "metric": metric,
                        "avg_value": avg_value,
                        "points_count": len(points),
                        "sample_values": [p.value for p in points[:5]],
                    },
                )
                raise ExtractionError(
                    f"EBITDA values too small (avg={avg_value:.2f}). Expected EUR millions for Group EBITDA. "
                    "Data may be extracting line-item breakdowns instead of consolidated values. "
                    "Check that 'ebitda' maps to 'EBITDA IFRS' in METRIC_SYNONYMS."
                )
            else:
                logger.info(
                    f"EBITDA scale validation PASSED: avg={avg_value:.2f}M EUR",
                    extra={"metric": metric, "avg_value": avg_value},
                )

        return TimeSeriesData(
            metric_name=metric,
            points=points,
            interval="monthly",  # Period column represents monthly data
            source_documents=sorted(source_documents),  # FIX (2025-12-01): Track source documents
        )

    except MetricValidationError as e:
        # Story 6.15: For ANY metric with insufficient SQL data, try Qdrant fallback
        # Qdrant often has more complete data from document chunks than PostgreSQL
        # (generalizes original EBITDA-only fallback from Story 5.0.4 AC3)
        logger.warning(
            f"SQL extraction has insufficient {metric} data, trying Qdrant fallback",
            extra={
                "metric": metric,
                "sql_points": e.data_points_found,
                "min_required": e.minimum_required,
            },
        )
        try:
            # CRITICAL: Some metrics require specialized extraction functions
            # - EBITDA: YTD-to-monthly conversion (without it: 154% MAPE regression)
            # - Variable Cost: European decimal format handling (without it: 338% MAPE)
            # Other metrics use the generic function
            qdrant_result: TimeSeriesData | None
            if metric.lower() == "ebitda":
                qdrant_result = await extract_ebitda_from_qdrant_chunks(
                    entity="portugal", min_points=min_points
                )
            elif metric.lower() in ["variable_cost", "variable cost"]:
                qdrant_result = await extract_variable_cost_from_qdrant_chunks(
                    entity="portugal", min_points=min_points
                )
            else:
                qdrant_result = await extract_metric_from_qdrant_chunks(
                    metric=metric, min_points=min_points, entity="portugal"
                )
            if qdrant_result:
                return qdrant_result
            logger.warning(
                f"Qdrant fallback returned no data for {metric}",
                extra={"metric": metric},
            )
        except Exception as qdrant_error:
            logger.warning(
                f"Qdrant fallback failed for {metric}, re-raising original MetricValidationError",
                extra={"metric": metric, "qdrant_error": str(qdrant_error)},
            )
        # Re-raise validation error if Qdrant fallback fails or returns no data
        raise
    except ExtractionError as e:
        # Story 6.15: For ANY metric, try Qdrant fallback when SQL extraction fails
        # This handles cases where table extraction corrupted PostgreSQL data
        # but raw chunk text in Qdrant still contains correct values
        # (generalizes original EBITDA-only fallback from Story 5.0.1)
        logger.warning(
            f"SQL extraction failed for {metric}, trying Qdrant chunk fallback",
            extra={
                "metric": metric,
                "entity": "portugal",
                "original_error": str(e),
            },
        )
        try:
            # CRITICAL: Some metrics require specialized extraction functions
            # - EBITDA: YTD-to-monthly conversion (without it: 154% MAPE regression)
            # - Variable Cost: European decimal format handling (without it: 338% MAPE)
            # Other metrics use the generic function
            qdrant_result: TimeSeriesData | None = None  # type: ignore[no-redef]
            if metric.lower() == "ebitda":
                qdrant_result = await extract_ebitda_from_qdrant_chunks(
                    entity="portugal", min_points=min_points
                )
            elif metric.lower() in ["variable_cost", "variable cost"]:
                qdrant_result = await extract_variable_cost_from_qdrant_chunks(
                    entity="portugal", min_points=min_points
                )
            else:
                qdrant_result = await extract_metric_from_qdrant_chunks(
                    metric=metric, min_points=min_points, entity="portugal"
                )
            if qdrant_result:
                return qdrant_result
            logger.warning(
                f"Qdrant fallback returned no data for {metric}",
                extra={"metric": metric},
            )
        except Exception as qdrant_error:
            logger.error(
                f"Both SQL and Qdrant extraction failed for {metric}",
                extra={
                    "metric": metric,
                    "entity": "portugal",
                    "sql_error": str(e),
                    "qdrant_error": str(qdrant_error),
                },
            )
            raise ExtractionError(
                f"{metric} extraction failed. SQL: {e}. Qdrant: {qdrant_error}"
            ) from qdrant_error
        # Re-raise original error if Qdrant fallback returns no data
        raise
    except Exception as e:
        # DATABASE FIX: Handle transaction errors with connection reset
        # When a SQL error occurs (e.g., type casting, syntax error), PostgreSQL
        # aborts the transaction. Subsequent queries fail with:
        # "current transaction is aborted, commands ignored until end of transaction block"
        #
        # Solution: Reset the connection to clear the aborted transaction state
        error_msg = str(e).lower()
        if "transaction" in error_msg and "aborted" in error_msg:
            logger.warning(
                "PostgreSQL transaction aborted - resetting connection",
                extra={"metric": metric, "error": str(e)},
            )
            from raglite.shared.clients import reset_postgresql_connection

            reset_postgresql_connection()

        # Catch SQL connection errors, query errors, etc.
        logger.error(
            "SQL extraction failed",
            extra={"metric": metric, "error": str(e)},
            exc_info=True,
        )
        raise ExtractionError(f"SQL query failed: {e}") from e


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
    from raglite.shared.clients import get_mistral_client

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


# =============================================================================
# Story 6.24: External Data Extraction
# =============================================================================

# Maps forecast variable names to (source_name, metric_name) in external_data_points
EXTERNAL_SOURCE_MAPPINGS: dict[str, tuple[str, str]] = {
    "ttf_gas_price": ("ICE_TTF_Gas", "settlement_price"),
    "petcoke_price": ("ICE_API2_Coal", "settlement_price"),
    "co2_eua_price": ("CO2_EUA", "co2_eua_price"),
}


async def extract_external_timeseries(
    metric: str,
    min_points: int = 8,
) -> TimeSeriesData | None:
    """Extract time series from external_data_points table.

    Story 6.24: External Data Integration for Forecasting

    Queries external commodity data (TTF Gas, Petcoke/API2 Coal, CO2 EUA)
    from PostgreSQL external_data_points table.

    Args:
        metric: Forecast variable name (e.g., "ttf_gas_price", "petcoke_price")
        min_points: Minimum data points required (default 8)

    Returns:
        TimeSeriesData with extracted points, or None if insufficient data

    Example:
        >>> data = await extract_external_timeseries("ttf_gas_price")
        >>> print(f"{len(data.points)} points from {data.points[0].date}")
    """
    from raglite.shared.clients import get_postgresql_connection

    # Check if metric has external source mapping
    if metric not in EXTERNAL_SOURCE_MAPPINGS:
        logger.warning(f"No external source mapping for metric: {metric}")
        return None

    source_name, metric_name = EXTERNAL_SOURCE_MAPPINGS[metric]

    logger.info(
        "Extracting external time series",
        extra={"metric": metric, "source": source_name, "db_metric": metric_name},
    )

    conn = get_postgresql_connection()
    cursor = conn.cursor()

    try:
        query = """
            SELECT edp.date, edp.value, edp.unit
            FROM external_data_points edp
            JOIN external_data_sources eds ON edp.source_id = eds.id
            WHERE eds.source_name = %s
              AND edp.metric_name = %s
              AND edp.deleted_at IS NULL
            ORDER BY edp.date ASC
        """

        cursor.execute(query, (source_name, metric_name))
        rows = cursor.fetchall()

        if len(rows) < min_points:
            logger.warning(
                f"Insufficient external data for {metric}",
                extra={"found": len(rows), "required": min_points},
            )
            return None

        # Convert to TimeSeriesPoint objects
        points = []
        for date_val, value, unit in rows:
            # Convert date to datetime for consistency
            dt = datetime.combine(date_val, datetime.min.time())
            points.append(TimeSeriesPoint(date=dt, value=float(value), label=unit))

        # Story 6.24: Resample daily data to monthly to match SECIL internal data frequency
        # This is critical for consistent forecasting and MAPE comparison
        if len(points) > 50:  # Only resample if we have enough daily data
            import pandas as pd

            df = pd.DataFrame([(p.date, p.value) for p in points], columns=["date", "value"])
            df["date"] = pd.to_datetime(df["date"])
            df = df.set_index("date")

            # Resample to month-end, taking the mean
            monthly = df.resample("ME").mean().dropna()

            if len(monthly) >= min_points:
                points = [
                    TimeSeriesPoint(
                        date=datetime.combine(idx.date(), datetime.min.time()),
                        value=float(row["value"]),
                        label="monthly_avg",
                    )
                    for idx, row in monthly.iterrows()
                ]

                logger.info(
                    "Resampled external data from daily to monthly",
                    extra={
                        "metric": metric,
                        "daily_points": len(rows),
                        "monthly_points": len(points),
                    },
                )

        logger.info(
            "External time series extracted",
            extra={
                "metric": metric,
                "source": source_name,
                "points": len(points),
                "date_range": f"{points[0].date.date()} to {points[-1].date.date()}",
            },
        )

        return TimeSeriesData(
            metric_name=metric,
            points=points,
            interval="monthly",  # Resampled to monthly for consistency
            source_documents=[f"external:{source_name}"],
        )

    except Exception as e:
        logger.error(
            f"Failed to extract external time series for {metric}",
            extra={"error": str(e)},
            exc_info=True,
        )
        return None

    finally:
        cursor.close()


async def extract_external_regressor_timeseries(
    metric: str,
    min_points: int = 6,
) -> TimeSeriesData | None:
    """Extract external regressor as standalone time series for validation.

    Story 6.24.4: Enables validation of external-only metrics by reusing
    regressor fetch logic. This bridges the gap between regressor system
    and validation system.

    Args:
        metric: Regressor name (e.g., "euribor_3m", "diesel", "gdp_growth")
        min_points: Minimum data points required (default 6)

    Returns:
        TimeSeriesData with points, or None if insufficient data

    Example:
        >>> data = await extract_external_regressor_timeseries("euribor_3m")
        >>> print(f"{len(data.points)} points from {data.points[0].date}")

    Note:
        All external regressors are assumed to be monthly frequency.
        NaN and infinite values are filtered out during conversion.
    """
    import math
    from datetime import timedelta

    try:
        # Fetch last 5 years of data (sufficient for forecasting validation)
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=int(365.25 * 5))  # Accounts for leap years

        logger.info(
            "Fetching external regressor as time series",
            extra={"metric": metric, "start_date": start_date, "end_date": end_date},
        )

        # Use regressor fetch infrastructure
        series = await fetch_single_regressor(metric, start_date, end_date)

        if series is None or len(series) == 0:
            logger.warning(
                "No data returned for external metric",
                extra={"metric": metric, "points": len(series) if series is not None else 0},
            )
            return None

        if len(series) < min_points:
            logger.warning(
                "Insufficient data for external metric",
                extra={"metric": metric, "points": len(series), "min_required": min_points},
            )
            return None

        # Convert pandas Series to TimeSeriesData, filtering NaN/Inf values
        points = []
        filtered_count = 0
        for idx, val in series.items():
            # Filter out NaN and infinite values (Issue #4 fix)
            if not isinstance(val, (int, float)) or math.isnan(val) or math.isinf(val):
                filtered_count += 1
                logger.debug(
                    "Filtered invalid value from external regressor",
                    extra={"metric": metric, "date": idx, "value": val},
                )
                continue

            points.append(
                TimeSeriesPoint(
                    date=idx.to_pydatetime(),
                    value=float(val),
                    label=f"{metric}_{idx.strftime('%Y-%m')}",
                )
            )

        if filtered_count > 0:
            logger.warning(
                "Filtered NaN/Inf values from external regressor",
                extra={"metric": metric, "filtered": filtered_count, "retained": len(points)},
            )

        if len(points) < min_points:
            logger.warning(
                "Insufficient valid data after filtering for external metric",
                extra={"metric": metric, "valid_points": len(points), "min_required": min_points},
            )
            return None

        logger.info(
            "Extracted time series for external regressor",
            extra={
                "metric": metric,
                "points": len(points),
                "date_range": f"{points[0].date.date()} to {points[-1].date.date()}",
            },
        )

        return TimeSeriesData(
            metric_name=metric,
            points=points,
            interval="monthly",  # External regressors are monthly
            source_documents=[f"external:{metric}"],
        )

    except Exception as e:
        logger.error(
            "Failed to extract external regressor time series",
            extra={"metric": metric, "error": str(e)},
            exc_info=True,
        )
        return None
