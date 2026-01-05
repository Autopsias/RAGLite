"""Response formatting utilities for external data queries."""

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from raglite.mcp.models import ExternalDataQueryResponse


def _get_visualization_hint(record_count: int, data_type: str | None) -> str:
    """Generate visualization hint based on data characteristics.

    Args:
        record_count: Number of data points available
        data_type: Type of data (e.g., "time_series", "index")

    Returns:
        Human-readable visualization recommendation

    Examples:
        >>> _get_visualization_hint(0, "time_series")
        'No data available for visualization'

        >>> _get_visualization_hint(1, "time_series")
        'Single value - display as card or gauge'

        >>> _get_visualization_hint(10, "index")
        'Bar chart recommended for comparison'
    """
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


def _format_response(results: list["ExternalDataQueryResponse"], original_source: str) -> str:
    """Format query results as JSON string.

    Args:
        results: List of query responses from data sources
        original_source: Original source name from request (for error messages)

    Returns:
        JSON-formatted string with query results

    Examples:
        >>> # Empty results
        >>> _format_response([], "NonExistent")
        '{"message": "No data found for source \\'NonExistent\\'", ...}'

        >>> # Single source
        >>> _format_response([response], "INE_BuildingPermits")
        '{"source": "INE_BuildingPermits", "frequency": "monthly", ...}'

        >>> # Multi-source
        >>> _format_response([response1, response2], "all")
        '{"query": "multi-source", "sources_queried": 2, ...}'
    """
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
