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


# Entity search patterns for EBITDA extraction
# Each entity corresponds to a specific geographic region or segment
EBITDA_ENTITY_PATTERNS = {
    # Geographic entities (consolidated by country)
    "portugal": "Portugal EBITDA IFRS",
    "tunisia": "Tunisia EBITDA IFRS",
    "angola": "Angola EBITDA IFRS",  # Angola country total
    "brazil": "Brazil EBITDA IFRS",  # Brazil country total (in BRL)
    "lebanon": "Lebanon EBITDA IFRS",  # Lebanon country total
    # Segment totals (not consolidated GROUP)
    "cement_portugal": "Cement EBITDA IFRS",  # Portugal cement segment
    "concrete": "Concrete EBITDA IFRS",  # Concrete segment
    "aggregates": "Aggregates EBITDA IFRS",  # Aggregates segment
}

# Value thresholds to distinguish YTD from monthly values
# Large entities (Portugal, Tunisia) have YTD > €10M
# Smaller entities (Lebanon) have YTD in €1-10M range
EBITDA_VALUE_THRESHOLDS = {
    "portugal": 10000,  # €10M+ YTD
    "tunisia": 5000,  # €5M+ YTD
    "angola": 50000,  # €50M+ YTD (large in local currency)
    "brazil": 50000,  # €50M+ YTD (in BRL)
    "lebanon": 500,  # €500K+ YTD (smaller operation)
    "cement_portugal": 50000,  # €50M+ YTD
    "concrete": 500,  # Smaller segment
    "aggregates": 5000,  # €5M+ YTD
}


async def extract_ebitda_from_qdrant_chunks(
    entity: str = "portugal",
    min_points: int = 8,
) -> "TimeSeriesData":
    """Extract EBITDA from Qdrant chunks via regex parsing.

    Story 5.0.1 Enhancement: Fallback extraction when SQL financial_tables
    has incorrect/insufficient data due to table extraction issues.

    Supports multiple geographic entities:
    - portugal: Portugal consolidated EBITDA IFRS (~€155M YTD)
    - tunisia: Tunisia EBITDA IFRS (~€44M YTD)
    - angola: Angola EBITDA IFRS
    - brazil: Brazil EBITDA IFRS (in BRL)
    - lebanon: Lebanon EBITDA IFRS

    Segment totals:
    - cement_portugal: Portugal cement segment
    - concrete: Concrete segment
    - aggregates: Aggregates segment

    Args:
        entity: Geographic entity to extract (default: "portugal")
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
        extra={"entity": entity, "search_pattern": search_pattern, "min_points": min_points},
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
                            extra={"period": period, "value": ytd_value, "source": source_doc},
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
    monthly_points = []
    prev_ytd = 0.0
    for _i, p in enumerate(points):
        # Monthly value = Current YTD - Previous YTD
        monthly_value = p.value - prev_ytd
        prev_ytd = p.value

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


def parse_period_to_date(period: str, fiscal_year: int) -> datetime:
    """Parse period string (Mon-YY format) to datetime.

    Converts period strings like "Jan-25", "Dec-24" to datetime objects
    representing the first day of that month.

    Args:
        period: Period string in Mon-YY format (e.g., "Jan-25", "Dec-24")
        fiscal_year: Fiscal year as integer (e.g., 2025, 2024)

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

    # Extract month abbreviation from period (e.g., "Jan-25" -> "Jan")
    # Pattern matches anything ending with -XX, extracts the part before the hyphen
    match = re.match(r"^([A-Za-z]+)-\d{2}$", period.strip())
    if not match:
        raise ValueError(
            f"Invalid period format: '{period}'. Expected Mon-YY format (e.g., Jan-25)"
        )

    month_abbrev = match.group(1).capitalize()

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
    return datetime(fiscal_year, month, 1)


async def extract_timeseries_from_sql(
    metric: str = "revenue",
    min_points: int = 8,
    entity: str = "portugal",
) -> TimeSeriesData:
    """Extract time-series data from PostgreSQL financial_tables.

    Primary extraction method for forecasting - uses structured SQL data
    rather than LLM extraction from document chunks. Queries the
    financial_tables for rows matching the metric name with valid
    period and fiscal_year values.

    This function implements Story 5.0.1 AC2: SQL-based time-series extraction
    with fallback to hybrid search for insufficient data.

    For EBITDA metrics, supports entity-specific extraction:
    - portugal: Portugal consolidated EBITDA IFRS (~€155M YTD)
    - tunisia: Tunisia EBITDA IFRS (~€44M YTD)
    - angola: Angola EBITDA IFRS
    - brazil: Brazil EBITDA IFRS
    - lebanon: Lebanon EBITDA IFRS
    - cement_portugal, concrete, aggregates: Segment-level totals

    Args:
        metric: Metric name to extract (e.g., "revenue", "expenses", "ebitda")
        min_points: Minimum number of data points required (default: 8)
        entity: Geographic entity for EBITDA (default: "portugal")

    Returns:
        TimeSeriesData with metric_name, chronologically sorted points, interval

    Raises:
        ExtractionError: If insufficient data (<min_points) or SQL query fails

    Example:
        >>> data = await extract_timeseries_from_sql(metric="revenue", min_points=8)
        >>> len(data.points) >= 8
        True
        >>> data.interval
        'monthly'
    """
    from raglite.shared.clients import get_postgresql_connection

    # Metric name synonyms mapping (revenue → turnover for Secil reports)
    # EBITDA mapping: Use "EBITDA IFRS" to get consolidated reporting metric only
    # This avoids matching granular variants (EBITDA Portugal, EBITDA Angola, etc.)
    # which would cause double-counting when summed
    METRIC_SYNONYMS = {
        "revenue": "turnover",
        "revenues": "turnover",
        "sales": "turnover",
        "ebitda": "EBITDA IFRS",  # Consolidated IFRS reporting metric only
    }

    # Apply synonym mapping if metric matches a known synonym
    metric_search = METRIC_SYNONYMS.get(metric.lower(), metric)

    # Determine if we should use exact match (=) or wildcard (LIKE)
    # Use exact match when synonym mapping was applied to avoid matching variants
    use_exact_match = metric_search != metric.lower() and metric.lower() in METRIC_SYNONYMS

    logger.info(
        "Extracting time-series from SQL",
        extra={
            "metric": metric,
            "metric_search": metric_search,
            "min_points": min_points,
            "synonym_applied": metric_search != metric.lower(),
            "use_exact_match": use_exact_match,
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
        # EBITDA IFRS FIX: Use exact match when synonym mapped + filter to GROUP entity
        # This prevents double-counting regional breakdowns (Brazil, Tunisia, etc.)

        if use_exact_match:
            # Exact match for synonym-mapped metrics (EBITDA IFRS, turnover)
            metric_condition = "metric = %s"
            metric_param = metric_search  # Use exact casing (e.g., "EBITDA IFRS", "turnover")

            # For EBITDA IFRS, also filter to consolidated GROUP entity only
            # This excludes regional breakdowns (BRAZIL, TUNISIA, LEBANON, etc.)
            # Note: %% is escaped % for psycopg2 parameter style
            if metric_search == "EBITDA IFRS":
                entity_filter = """
                  AND (
                    entity = 'GROUP'
                    OR LOWER(entity) LIKE '%%group%%'
                    OR LOWER(entity) LIKE '%%consolidated%%'
                    OR LOWER(entity) LIKE '%%total%%'
                  )
                """
            else:
                entity_filter = ""
        else:
            # Wildcard match for user-specified metrics
            metric_condition = "LOWER(metric) LIKE %s"
            metric_param = f"%{metric_search.lower()}%"
            entity_filter = ""

        # nosec B608 - SQL query uses parameterized internal variables only
        query = f"""
            WITH latest_doc_per_period AS (
                -- For each period, identify the most recent document
                SELECT
                    period,
                    fiscal_year,
                    MAX(document_id) as latest_doc
                FROM financial_tables
                WHERE {metric_condition}
                  AND period IS NOT NULL
                  AND fiscal_year IS NOT NULL
                  AND period ~ '^[A-Z][a-z]{{2}}-[0-9]{{2}}$'
                  AND value IS NOT NULL
                  {entity_filter}
                GROUP BY period, fiscal_year
            )
            SELECT
                ft.period,
                ft.fiscal_year,
                SUM(ft.value) as total_value,
                COUNT(*) as row_count,
                MAX(ft.document_id) as source_doc
            FROM financial_tables ft
            INNER JOIN latest_doc_per_period ld
                ON ft.period = ld.period
                AND ft.fiscal_year = ld.fiscal_year
                AND ft.document_id = ld.latest_doc
            WHERE {metric_condition}
              AND ft.period ~ '^[A-Z][a-z]{{2}}-[0-9]{{2}}$'
              AND ft.value IS NOT NULL
              {entity_filter}
            GROUP BY ft.period, ft.fiscal_year
            HAVING SUM(ft.value) > 0
            ORDER BY ft.fiscal_year, ft.period
        """

        # Execute query with appropriate parameter (exact or wildcard)
        # Note: Query needs metric parameter twice (CTE and main query)
        logger.debug(
            "Executing SQL query",
            extra={
                "metric_condition": metric_condition,
                "metric_param": metric_param,
                "entity_filter_length": len(entity_filter),
                "has_entity_filter": bool(entity_filter),
                "query_preview": query[:500],
            },
        )

        # Count %s placeholders in query to verify parameter count matches
        placeholder_count = query.count("%s")
        param_count = 2  # Always pass 2 parameters (metric for CTE and main query)

        if placeholder_count != param_count:
            logger.error(
                "Parameter count mismatch",
                extra={
                    "placeholders_in_query": placeholder_count,
                    "parameters_provided": param_count,
                    "query": query,
                },
            )
            raise ExtractionError(
                f"SQL query has {placeholder_count} placeholders but {param_count} parameters provided"
            )

        cursor.execute(query, (metric_param, metric_param))
        rows = cursor.fetchall()

        cursor.close()

        if not rows:
            logger.warning(
                "No SQL data found for metric",
                extra={"metric": metric, "rows_found": 0},
            )
            raise ExtractionError(
                f"No data found in financial_tables for metric '{metric}' "
                f"with valid period and fiscal_year"
            )

        # Parse rows into TimeSeriesPoint objects
        # Each row is now aggregated and deduplicated: (period, fiscal_year, total_value, row_count, source_doc)
        points = []
        for period_str, fiscal_year, total_value, row_count, source_doc in rows:
            try:
                date = parse_period_to_date(period_str, fiscal_year)
                # Extract document month from source_doc (e.g., "2025-10 Performance Review" → "2025-10")
                doc_month = source_doc.split()[0] if source_doc else "unknown"

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

        # Check minimum points threshold
        if len(points) < min_points:
            logger.warning(
                "Insufficient SQL data points, fallback needed",
                extra={
                    "metric": metric,
                    "points_found": len(points),
                    "min_required": min_points,
                },
            )
            raise ExtractionError(
                f"Insufficient data: found {len(points)} points, need {min_points} minimum"
            )

        # Sort by date (should already be sorted, but ensure it)
        points.sort(key=lambda p: p.date)

        # Calculate date range for logging
        min_date = points[0].date.strftime("%Y-%m-%d")
        max_date = points[-1].date.strftime("%Y-%m-%d")

        logger.info(
            "SQL extraction successful",
            extra={
                "metric": metric,
                "points": len(points),
                "date_range": f"{min_date} to {max_date}",
            },
        )

        return TimeSeriesData(
            metric_name=metric,
            points=points,
            interval="monthly",  # Period column represents monthly data
            source_documents=[],  # SQL extraction doesn't track specific documents
        )

    except ExtractionError as e:
        # Story 5.0.1 Enhancement: For EBITDA, try Qdrant fallback when SQL fails
        # This handles the case where table extraction corrupted the financial_tables data
        # but the raw chunk text in Qdrant still contains correct consolidated values
        if metric.lower() == "ebitda":
            logger.warning(
                "SQL extraction failed for EBITDA, trying Qdrant chunk fallback",
                extra={"metric": metric, "entity": entity, "original_error": str(e)},
            )
            try:
                return await extract_ebitda_from_qdrant_chunks(entity=entity, min_points=min_points)
            except ExtractionError as qdrant_error:
                logger.error(
                    "Both SQL and Qdrant extraction failed for EBITDA",
                    extra={
                        "entity": entity,
                        "sql_error": str(e),
                        "qdrant_error": str(qdrant_error),
                    },
                )
                raise ExtractionError(
                    f"EBITDA extraction failed for {entity}. SQL: {e}. Qdrant: {qdrant_error}"
                ) from qdrant_error
        # For non-EBITDA metrics, re-raise the original error
        raise
    except Exception as e:
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
