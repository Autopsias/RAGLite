"""Query execution helpers for external data sources."""

from datetime import date
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from raglite.external_data.storage import ExternalDataStorage
    from raglite.mcp.models import ExternalDataQueryResponse

from .response_formatters import _get_visualization_hint


def _query_single_source(
    storage: "ExternalDataStorage",
    source_name: str,
    start_date: date,
    end_date: date,
    metric: str | None,
) -> list["ExternalDataQueryResponse"]:
    """Query a single external data source.

    Args:
        storage: ExternalDataStorage instance for data access
        source_name: Name of the data source to query
        start_date: Start date for query range
        end_date: End date for query range
        metric: Optional metric name to filter by

    Returns:
        List containing single ExternalDataQueryResponse

    Raises:
        ValueError: If source_name not found in storage

    Examples:
        >>> results = _query_single_source(storage, "IPMA", start, end, None)
        >>> len(results)
        1
    """
    from raglite.mcp.models import ExternalDataPoint, ExternalDataQueryResponse

    source = storage.get_source(source_name)
    if not source:
        raise ValueError(f"Source '{source_name}' not found. Use 'all' to list available sources.")
    data_points = storage.query_data_range(source_name, start_date, end_date, metric)
    return [
        ExternalDataQueryResponse(
            source_name=source_name,
            data_frequency=source.refresh_frequency,
            last_refresh=source.last_refresh_at,
            data_points=[
                ExternalDataPoint(
                    date=dp.date,
                    metric_name=dp.metric_name,
                    value=float(dp.value),
                    unit=dp.unit,
                )
                for dp in data_points
            ],
            visualization_hint=_get_visualization_hint(len(data_points), source.data_type),
            record_count=len(data_points),
        )
    ]


def _query_all_sources(
    storage: "ExternalDataStorage",
    start_date: date,
    end_date: date,
    metric: str | None,
) -> list["ExternalDataQueryResponse"]:
    """Query all external data sources.

    Args:
        storage: ExternalDataStorage instance for data access
        start_date: Start date for query range
        end_date: End date for query range
        metric: Optional metric name to filter by

    Returns:
        List of ExternalDataQueryResponse objects (one per source)

    Examples:
        >>> results = _query_all_sources(storage, start, end, None)
        >>> len(results) >= 1
        True
    """
    from logging import getLogger

    from raglite.mcp.models import ExternalDataPoint, ExternalDataQueryResponse

    logger = getLogger(__name__)

    sources = storage.list_sources()
    results = []
    for source in sources:
        try:
            data_points = storage.query_data_range(source.source_name, start_date, end_date, metric)
            results.append(
                ExternalDataQueryResponse(
                    source_name=source.source_name,
                    data_frequency=source.refresh_frequency,
                    last_refresh=source.last_refresh_at,
                    data_points=[
                        ExternalDataPoint(
                            date=dp.date,
                            metric_name=dp.metric_name,
                            value=float(dp.value),
                            unit=dp.unit,
                        )
                        for dp in data_points
                    ],
                    visualization_hint=_get_visualization_hint(len(data_points), source.data_type),
                    record_count=len(data_points),
                )
            )
        except Exception as e:
            logger.warning(f"Failed to query source {source.source_name}: {e}")
    return results
