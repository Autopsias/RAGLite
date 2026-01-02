"""SQL row parsing for timeseries extraction.

Part of Story 8.1 refactoring to split sql_extraction.py.
Handles conversion of SQL rows to TimeSeriesPoint objects with filtering and validation.
"""

from raglite.forecasting.timeseries.parsing import parse_period_to_date
from raglite.shared.logging import get_logger
from raglite.shared.models import TimeSeriesPoint

logger = get_logger(__name__)


def parse_sql_rows_to_points(
    rows: list[tuple],
    metric: str,
) -> tuple[list[TimeSeriesPoint], set[str], bool]:
    """Parse SQL rows into TimeSeriesPoint objects.

    Story 6.24.1: Filters year values (2000-2099) that were captured as metrics.

    Args:
        rows: SQL result rows (period, fiscal_year, total_value, row_count, source_doc, is_ytd)
        metric: Metric name for logging

    Returns:
        Tuple of (points, source_documents, is_ytd_data)
    """
    points = []
    source_documents = set()
    is_ytd_data = False

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
            doc_month = source_doc.split()[0] if source_doc else "unknown"

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

    return points, source_documents, is_ytd_data
