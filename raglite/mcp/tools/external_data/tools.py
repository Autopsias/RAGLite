"""External data MCP tools.

Provides MCP tools for refreshing and querying external financial data sources.
"""

import json
import time

from raglite.external_data.refresh import BulkRefreshResult, RefreshResult
from raglite.external_data.storage import ExternalDataStorage
from raglite.main import mcp
from raglite.mcp.models import ExternalDataQueryRequest
from raglite.shared.database import get_session
from raglite.shared.logging import get_logger

from .date_utils import _parse_date_range
from .query_helpers import _query_all_sources, _query_single_source
from .response_formatters import _format_response

logger = get_logger(__name__)


def _format_bulk_refresh_response(bulk_result: BulkRefreshResult) -> dict:
    """Format bulk refresh result for MCP response.

    Args:
        bulk_result: BulkRefreshResult from refresh_all_sources

    Returns:
        Formatted response dictionary
    """
    return {
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


def _format_single_refresh_response(single_result: RefreshResult) -> dict:
    """Format single source refresh result for MCP response.

    Args:
        single_result: RefreshResult from refresh_source

    Returns:
        Formatted response dictionary
    """
    return {
        "source_name": single_result.source_name,
        "success": single_result.success,
        "records_updated": single_result.records_updated,
        "duration_seconds": round(single_result.duration_seconds, 2),
        "error_message": single_result.error_message,
        "attempts": single_result.attempts,
    }


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
            response = _format_bulk_refresh_response(bulk_result)
        else:
            single_result = await refresh_source(source_name)
            response = _format_single_refresh_response(single_result)
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


@mcp.tool()
async def query_external_data(request: ExternalDataQueryRequest) -> str:
    """Query external financial data sources.

    Retrieves time-series data from configured external data sources.
    Supports querying individual sources or all sources at once.

    Args:
        request: Query parameters including source name, date range, and optional metric filter

    Returns:
        JSON string with query results including:
        - source: Data source name
        - frequency: Data refresh frequency
        - last_refresh: Timestamp of last data refresh
        - record_count: Number of records returned
        - visualization_hint: Recommended visualization type
        - data: Array of data points with date, metric, value, and unit

    Example:
        >>> result = await query_external_data(
        ...     ExternalDataQueryRequest(
        ...         source="IPMA",
        ...         date_range="last_30_days"
        ...     )
        ... )
        >>> print(result)
        {"source": "IPMA", "frequency": "daily", "data": [...], ...}

    Raises:
        ValueError: If source name or date range is invalid
    """

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
