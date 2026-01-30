"""SQL row parsing for timeseries extraction.

Part of Story 8.1 refactoring to split sql_extraction.py.
Handles conversion of SQL rows to TimeSeriesPoint objects with filtering and validation.

EBITDA bug fix (2026-01-29): Fixed document source tracking to normalize
document_id format for proper source document display.
"""

from dataclasses import dataclass

from raglite.forecasting.timeseries.parsing import parse_period_to_date
from raglite.shared.logging import get_logger
from raglite.shared.models import TimeSeriesPoint

logger = get_logger(__name__)


def _normalize_document_name(doc_id: str | None) -> str:
    """Normalize document_id to readable format.

    EBITDA bug fix: Converts document_id format to human-readable name.
    "2025-08_Performance_Review_CONSO_v1" -> "2025-08 Performance Review CONSO v1"

    Args:
        doc_id: Raw document_id from database (may contain underscores)

    Returns:
        Normalized document name with spaces, or "unknown" if None
    """
    if not doc_id:
        return "unknown"

    # Replace underscores with spaces for readability
    # This handles both "2025-08_Performance_Review_CONSO_v1" format
    # and preserves already-normalized names
    normalized = doc_id.replace("_", " ")

    return normalized


@dataclass
class ParsedTimeSeriesData:
    """Container for parsed time series data with unit metadata.

    Phase 2 data quality: Preserves unit information for explicit normalization.
    """

    points: list[TimeSeriesPoint]
    units: list[str | None]
    source_documents: set[str]
    is_ytd_data: bool


def parse_sql_rows_to_points(
    rows: list[tuple],
    metric: str,
) -> tuple[list[TimeSeriesPoint], set[str], bool]:
    """Parse SQL rows into TimeSeriesPoint objects.

    Story 6.24.1: Filters year values (2000-2099) that were captured as metrics.

    Args:
        rows: SQL result rows (period, fiscal_year, total_value, row_count, source_doc, is_ytd, unit)
        metric: Metric name for logging

    Returns:
        Tuple of (points, source_documents, is_ytd_data)

    Note:
        For backward compatibility, returns tuple. Use parse_sql_rows_with_units()
        for unit-aware parsing.
    """
    parsed = parse_sql_rows_with_units(rows, metric)
    return parsed.points, parsed.source_documents, parsed.is_ytd_data


def parse_sql_rows_with_units(
    rows: list[tuple],
    metric: str,
) -> ParsedTimeSeriesData:
    """Parse SQL rows into TimeSeriesPoint objects with unit metadata.

    Phase 2 data quality: Preserves unit column for explicit normalization.

    Args:
        rows: SQL result rows (period, fiscal_year, total_value, row_count, source_doc, is_ytd, unit)
        metric: Metric name for logging

    Returns:
        ParsedTimeSeriesData with points, units, source_documents, and is_ytd_data
    """
    points = []
    units: list[str | None] = []
    source_documents: set[str] = set()
    is_ytd_data = False

    for row in rows:
        # Handle both old (6-tuple) and new (7-tuple with unit) format
        if len(row) >= 7:
            period_str, fiscal_year, total_value, row_count, source_doc, row_is_ytd, unit = row[:7]
        else:
            period_str, fiscal_year, total_value, row_count, source_doc, row_is_ytd = row[:6]
            unit = None

        # EBITDA bug fix: Normalize document name for proper tracking
        normalized_doc = _normalize_document_name(source_doc)
        if normalized_doc != "unknown":
            source_documents.add(normalized_doc)
        if row_is_ytd:
            is_ytd_data = True

        try:
            date = parse_period_to_date(period_str, fiscal_year)
            # EBITDA bug fix: Use normalized name for doc_month extraction
            doc_month = normalized_doc.split()[0] if normalized_doc != "unknown" else "unknown"

            # Story 6.24.1: Filter year values (2000-2099)
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
            units.append(unit)
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

    return ParsedTimeSeriesData(
        points=points,
        units=units,
        source_documents=source_documents,
        is_ytd_data=is_ytd_data,
    )
