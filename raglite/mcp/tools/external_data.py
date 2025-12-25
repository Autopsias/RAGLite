"""External Data MCP tools."""

import json
import time
from datetime import date, datetime, timedelta

from raglite.external_data.storage import ExternalDataStorage
from raglite.main import mcp
from raglite.mcp.models import (
    ExternalDataPoint,
    ExternalDataQueryRequest,
    ExternalDataQueryResponse,
)
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


@mcp.tool()
async def refresh_external_data(source_name: str | None = None) -> str:
    """Manually trigger external data refresh.
    Story 6.5 AC4: MCP tool for manual triggering of external data refresh.
    This tool allows manual refresh of external data sources outside the
    scheduled refresh times. Useful for:
    - Immediate data updates before analysis
    - Recovery from stale data situations
    - Testing data source connectivity
    **Data Sources:**
    - IPMA: Portuguese weather data
    - OMIE: Iberian electricity prices
    - CO2_EUA: EU carbon emission prices
    - INE_BuildingPermits: Portuguese building permit statistics
    - BPstat_MortgageLoans: Portuguese mortgage loan data
    - EUOil_Diesel: EU diesel fuel prices
    - INE_ConstructionOutput: Portuguese construction output index
    - ATIC_CementConsumption: Portuguese cement consumption
    Args:
        source_name: Specific source to refresh. If None, refreshes ALL sources.
                     Valid values: IPMA, OMIE, CO2_EUA, INE_BuildingPermits,
                     BPstat_MortgageLoans, EUOil_Diesel, INE_ConstructionOutput,
                     ATIC_CementConsumption
    Returns:
        JSON string with refresh status for each source including:
        - success: Whether refresh succeeded
        - records_updated: Number of records updated
        - duration_seconds: Time taken for refresh
        - error_message: Error details if failed
    Example - Refresh all sources:
        >>> result = await refresh_external_data()
        >>> print(result)
        {"total_sources": 8, "successful": 7, "failed": 1, ...}
    Example - Refresh specific source:
        >>> result = await refresh_external_data(source_name="IPMA")
        >>> print(result)
        {"source_name": "IPMA", "success": true, "records_updated": 7, ...}
    """
    import json

    from raglite.external_data.refresh import (
        refresh_all_sources,
        refresh_source,
    )

    logger.info(
        "Manual refresh triggered",
        extra={"source_name": source_name or "all"},
    )
    try:
        if source_name is None:
            bulk_result = await refresh_all_sources()
            response = {
                "total_sources": bulk_result.total_sources,
                "successful": bulk_result.successful,
                "failed": bulk_result.failed,
                "total_duration_seconds": round(bulk_result.total_duration_seconds, 2),
                "results": [
                    {
                        "source_name": r.source_name,
                        "success": r.success,
                        "records_updated": r.records_updated,
                        "duration_seconds": round(r.duration_seconds, 2),
                        "error_message": r.error_message,
                        "attempts": r.attempts,
                    }
                    for r in bulk_result.results
                ],
            }
        else:
            single_result = await refresh_source(source_name)
            response = {
                "source_name": single_result.source_name,
                "success": single_result.success,
                "records_updated": single_result.records_updated,
                "duration_seconds": round(single_result.duration_seconds, 2),
                "error_message": single_result.error_message,
                "attempts": single_result.attempts,
            }
        if source_name is None:
            success_status = bulk_result.successful == bulk_result.total_sources
        else:
            success_status = single_result.success
        logger.info(
            "Manual refresh completed",
            extra={
                "source_name": source_name or "all",
                "success": success_status,
            },
        )
        return json.dumps(response, indent=2)
    except ValueError as e:
        logger.warning(
            "Manual refresh failed - invalid source",
            extra={"source_name": source_name, "error": str(e)},
        )
        return json.dumps({"error": str(e)})
    except Exception as e:
        logger.error(
            "Manual refresh failed",
            extra={
                "source_name": source_name or "all",
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        return json.dumps({"error": f"Refresh failed: {e}"})


def _parse_date_range(date_range: str) -> tuple[date, date]:
    today = date.today()
    shortcuts = {
        "last_30_days": (today - timedelta(days=30), today),
        "last_90_days": (today - timedelta(days=90), today),
        "last_year": (today - timedelta(days=365), today),
        "last_quarter": (today - timedelta(days=90), today),
        "ytd": (date(today.year, 1, 1), today),
    }
    if date_range.lower() in shortcuts:
        return shortcuts[date_range.lower()]
    if ":" in date_range:
        parts = date_range.split(":")
        if len(parts) != 2:
            raise ValueError(
                f"Invalid date range format: {date_range}. Expected 'YYYY-MM-DD:YYYY-MM-DD'"
            )
        try:
            start = datetime.strptime(parts[0].strip(), "%Y-%m-%d").date()
            end = datetime.strptime(parts[1].strip(), "%Y-%m-%d").date()
            return start, end
        except ValueError as e:
            raise ValueError(f"Invalid date format in range: {e}") from e
    raise ValueError(
        f"Invalid date_range: '{date_range}'. "
        "Use ISO format 'YYYY-MM-DD:YYYY-MM-DD' or shortcuts: last_30_days, last_90_days, last_year, last_quarter, ytd"
    )


def _get_visualization_hint(record_count: int, data_type: str | None) -> str:
    if record_count == 0:
        return "No data available for visualization"
    elif record_count == 1:
        return "Single value - display as card or gauge"
    elif record_count <= 12:
        return "Bar chart recommended for comparison"
    elif data_type == "time_series":
        return "Line chart recommended for time-series trend analysis"
    else:
        return "Line chart or area chart recommended"


def _query_single_source(
    storage: "ExternalDataStorage",
    source_name: str,
    start_date: date,
    end_date: date,
    metric: str | None,
) -> list[ExternalDataQueryResponse]:
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
) -> list[ExternalDataQueryResponse]:
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


def _format_response(results: list[ExternalDataQueryResponse], original_source: str) -> str:
    if not results:
        return json.dumps(
            {
                "message": f"No data found for source '{original_source}'",
                "available_sources": "Use source='all' to list available sources",
            }
        )
    if len(results) == 1:
        r = results[0]
        return json.dumps(
            {
                "source": r.source_name,
                "frequency": r.data_frequency,
                "last_refresh": r.last_refresh.isoformat() if r.last_refresh else None,
                "record_count": r.record_count,
                "visualization_hint": r.visualization_hint,
                "data": [
                    {
                        "date": dp.date.isoformat(),
                        "metric": dp.metric_name,
                        "value": dp.value,
                        "unit": dp.unit,
                    }
                    for dp in r.data_points
                ],
            },
            indent=2,
        )
    return json.dumps(
        {
            "query": "multi-source",
            "sources_queried": len(results),
            "total_records": sum(r.record_count for r in results),
            "results": [
                {
                    "source": r.source_name,
                    "frequency": r.data_frequency,
                    "last_refresh": r.last_refresh.isoformat() if r.last_refresh else None,
                    "record_count": r.record_count,
                    "visualization_hint": r.visualization_hint,
                    "data": [
                        {
                            "date": dp.date.isoformat(),
                            "metric": dp.metric_name,
                            "value": dp.value,
                            "unit": dp.unit,
                        }
                        for dp in r.data_points[:10]
                    ],
                    "truncated": len(r.data_points) > 10,
                }
                for r in results
            ],
        },
        indent=2,
    )


@mcp.tool()
async def query_external_data(request: ExternalDataQueryRequest) -> str:
    from raglite.external_data.storage import ExternalDataStorage
    from raglite.shared.database import get_session

    start_time = time.time()
    logger.info(
        "External data query",
        extra={
            "source": request.source,
            "date_range": request.date_range,
            "metric": request.metric,
        },
    )
    session = None
    try:
        start_date, end_date = _parse_date_range(request.date_range)
        session = get_session()
        storage = ExternalDataStorage(session)
        if request.source.lower() == "all":
            results = _query_all_sources(storage, start_date, end_date, request.metric)
        else:
            results = _query_single_source(
                storage, request.source, start_date, end_date, request.metric
            )
        elapsed_ms = (time.time() - start_time) * 1000
        logger.info(
            "External data query complete",
            extra={
                "source": request.source,
                "record_count": sum(r.record_count for r in results),
                "duration_ms": elapsed_ms,
            },
        )
        return _format_response(results, request.source)
    except ValueError as e:
        logger.warning("External data query failed", extra={"error": str(e)})
        return json.dumps({"error": str(e), "source": request.source})
    except Exception as e:
        logger.error(
            "External data query failed",
            extra={
                "source": request.source,
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        return json.dumps({"error": f"Query failed: {e}", "source": request.source})
    finally:
        if session:
            session.close()
