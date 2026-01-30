"""SQL row parsing for timeseries extraction.

Part of Story 8.1 refactoring to split sql_extraction.py.
Handles conversion of SQL rows to TimeSeriesPoint objects with filtering and validation.

EBITDA bug fix (2026-01-29): Fixed document source tracking to normalize
document_id format for proper source document display.

EBITDA Data Quality Fix (2026-01-30): Added period classification integration
for filtering budget data from actuals and logging classification reports.
"""

from dataclasses import dataclass

from raglite.forecasting.timeseries.parsing import parse_period_to_date
from raglite.forecasting.timeseries.period_classification import (
    ClassificationReport,
    ClassifiedPeriod,
    classify_period,
    generate_classification_report,
    validate_period_homogeneity,
)
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
    EBITDA Data Quality Fix (2026-01-30): Added classification_report field.
    """

    points: list[TimeSeriesPoint]
    units: list[str | None]
    source_documents: set[str]
    is_ytd_data: bool
    classification_report: ClassificationReport | None = None


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
    EBITDA Data Quality Fix (2026-01-30): Added period classification and logging.

    Args:
        rows: SQL result rows (period, fiscal_year, total_value, row_count, source_doc, is_ytd, unit)
        metric: Metric name for logging

    Returns:
        ParsedTimeSeriesData with points, units, source_documents, is_ytd_data, and classification_report
    """
    points = []
    units: list[str | None] = []
    source_documents: set[str] = set()
    is_ytd_data = False

    # EBITDA Data Quality Fix: Classify periods for logging and validation
    all_periods = [row[0] if len(row) > 0 else None for row in rows]
    classification_report = generate_classification_report(all_periods)

    # Log classification report for diagnostics
    _log_classification_report(metric, classification_report)

    # Classify and collect usable periods for homogeneity check
    classified_periods: list[ClassifiedPeriod] = [classify_period(p) for p in all_periods]
    is_homogeneous, homogeneity_info = validate_period_homogeneity(classified_periods)

    if not is_homogeneous:
        logger.warning(
            "Period mixing detected in extraction",
            extra={
                "metric": metric,
                "homogeneity_info": homogeneity_info,
            },
        )

    # Issue 3B Fix (2026-01-30): Track filtered periods for logging
    filtered_budget_count = 0
    filtered_unknown_count = 0

    for idx, row in enumerate(rows):
        # Handle both old (6-tuple) and new (7-tuple with unit) format
        if len(row) >= 7:
            period_str, fiscal_year, total_value, row_count, source_doc, row_is_ytd, unit = row[:7]
        else:
            period_str, fiscal_year, total_value, row_count, source_doc, row_is_ytd = row[:6]
            unit = None

        # Issue 3B Fix (2026-01-30): Use pre-computed period classification
        # Skip BUDGET, YTD_BUDGET, and UNKNOWN periods to prevent mixing
        # and use normalized period for YTD data to enable proper parsing
        classified = classified_periods[idx] if idx < len(classified_periods) else None

        if classified and not classified.is_usable:
            if classified.period_type.name.startswith("BUDGET"):
                filtered_budget_count += 1
            else:
                filtered_unknown_count += 1
            continue  # Skip non-usable periods (BUDGET, YTD_BUDGET, UNKNOWN)

        # Issue 3B Fix: Use normalized period for parsing if available
        # This handles YTD periods: "YTD Dec-21" -> normalized="Dec-21"
        # The normalized period matches the parse_period_to_date regex
        parse_period = period_str
        if classified and classified.normalized:
            parse_period = classified.normalized
            # If we're using a YTD normalized period, mark data as YTD
            if classified.period_type.name == "YTD_ACTUAL":
                is_ytd_data = True

        # EBITDA bug fix: Normalize document name for proper tracking
        normalized_doc = _normalize_document_name(source_doc)
        if normalized_doc != "unknown":
            source_documents.add(normalized_doc)
        if row_is_ytd:
            is_ytd_data = True

        try:
            date = parse_period_to_date(parse_period, fiscal_year)
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
                    "parse_period": parse_period,
                    "fiscal_year": fiscal_year,
                    "total_value": total_value,
                    "row_count": row_count,
                    "error": str(e),
                },
            )
            continue

    # Log filtered counts for Issue 3B diagnostics
    if filtered_budget_count > 0 or filtered_unknown_count > 0:
        logger.info(
            "Period classification filtering applied",
            extra={
                "metric": metric,
                "filtered_budget": filtered_budget_count,
                "filtered_unknown": filtered_unknown_count,
                "remaining_points": len(points),
            },
        )

    return ParsedTimeSeriesData(
        points=points,
        units=units,
        source_documents=source_documents,
        is_ytd_data=is_ytd_data,
        classification_report=classification_report,
    )


def _log_classification_report(metric: str, report: ClassificationReport) -> None:
    """Log classification report for diagnostics.

    EBITDA Data Quality Fix (2026-01-30): Log period classification breakdown
    to help diagnose data quality issues.

    Args:
        metric: Metric name for context
        report: Classification report to log
    """
    # Always log usability rate for monitoring
    if report.total_records > 0:
        log_level = "info" if report.usability_rate >= 50 else "warning"
        log_func = logger.info if log_level == "info" else logger.warning

        log_func(
            "Period classification report",
            extra={
                "metric": metric,
                "total_records": report.total_records,
                "usable_records": report.usable_records,
                "usability_rate": f"{report.usability_rate:.1f}%",
                "monthly_actual": report.monthly_actual_count,
                "ytd_actual": report.ytd_actual_count,
                "budget_excluded": report.budget_count,
                "ytd_budget_excluded": report.ytd_budget_count,
                "unknown_excluded": report.unknown_count,
            },
        )
