"""Automatic forecast updates triggered by document ingestion.

Story 4.3: Automated Forecast Updates
Target: ~50-75 lines per architecture spec.
"""

import asyncio
import time

from raglite.forecasting.hybrid import InsufficientDataError, generate_forecast
from raglite.forecasting.timeseries import ExtractionError, extract_timeseries
from raglite.shared.config import settings
from raglite.shared.logging import get_logger
from raglite.shared.models import DocumentMetadata, ForecastRefreshResult

logger = get_logger(__name__)

# Mapping of document metadata to affected metrics
# Revenue documents -> revenue forecast, expense reports -> expenses forecast
METRIC_CATEGORY_MAP = {
    "Revenue": ["revenue"],
    "EBITDA": ["ebitda", "revenue"],
    "Operating Expenses": ["expenses"],
    "Capital Expenditure": ["capex"],
    "Cash Flow": ["cash_flow"],
    "Assets": ["assets"],
    "Liabilities": ["liabilities"],
}


async def identify_affected_metrics(document_metadata: DocumentMetadata) -> list[str]:
    """Identify which forecast metrics are affected by this document.

    Story 4.3 AC2: Only refresh metrics relevant to the document type.

    Args:
        document_metadata: Metadata from ingested document

    Returns:
        List of metric names to refresh (e.g., ["revenue", "expenses"])

    Logic:
        - Uses metric_category from ExtractedMetadata if available
        - Falls back to ["revenue"] for general financial documents
    """
    # Default metrics for general financial documents
    default_metrics = ["revenue"]

    # Check if document has metric_category (from Story 2.4 metadata extraction)
    # Note: metric_category is stored in chunks, not document metadata directly
    # For now, use filename heuristics as fallback
    filename_lower = document_metadata.filename.lower()

    if "expense" in filename_lower or "cost" in filename_lower:
        return ["expenses"]
    elif "cash" in filename_lower or "cashflow" in filename_lower:
        return ["cash_flow"]
    elif "balance" in filename_lower or "asset" in filename_lower:
        return ["assets", "liabilities"]
    elif "income" in filename_lower or "revenue" in filename_lower:
        return ["revenue"]
    elif "quarterly" in filename_lower or "annual" in filename_lower:
        # General financial reports may contain multiple metrics
        return ["revenue", "expenses"]

    logger.debug(
        "Using default metrics for document",
        extra={"doc_filename": document_metadata.filename, "metrics": default_metrics},
    )
    return default_metrics


async def trigger_forecast_refresh(
    document_metadata: DocumentMetadata,
    timeout_seconds: int | None = None,
) -> ForecastRefreshResult:
    """Trigger forecast refresh after document ingestion.

    Story 4.3 AC1-AC3: Automatically refresh forecasts for affected metrics
    after a new document is ingested.

    Args:
        document_metadata: Metadata from ingested document
        timeout_seconds: Maximum time for refresh (default from settings)

    Returns:
        ForecastRefreshResult with updated metrics and timing

    Process:
        1. Identify affected metrics from document metadata
        2. Extract time-series data for new document
        3. Refresh forecasts for affected metrics only (incremental)
        4. Return summary of updates
    """
    start_time = time.time()
    timeout = timeout_seconds or settings.forecast_refresh_timeout

    logger.info(
        "Starting forecast refresh",
        extra={
            "doc_filename": document_metadata.filename,
            "timeout_seconds": timeout,
        },
    )

    metrics_refreshed: list[str] = []
    metrics_skipped: list[str] = []
    error_message: str | None = None

    try:
        async with asyncio.timeout(timeout):
            # Step 1: Identify affected metrics
            affected_metrics = await identify_affected_metrics(document_metadata)
            logger.debug(
                "Identified affected metrics",
                extra={
                    "metrics": affected_metrics,
                    "doc_filename": document_metadata.filename,
                },
            )

            # Step 2: Extract time-series and refresh each metric
            for metric in affected_metrics:
                try:
                    # Extract time-series data from the document
                    ts_data = await extract_timeseries(
                        docs=[document_metadata.filename],
                        metric=metric,
                    )

                    # Generate forecast for this metric
                    await generate_forecast(
                        metric=metric,
                        historical_data=ts_data,
                        periods_ahead=4,
                    )

                    metrics_refreshed.append(metric)
                    logger.info(
                        "Metric forecast refreshed",
                        extra={"metric": metric, "data_points": len(ts_data.points)},
                    )

                except InsufficientDataError as e:
                    reason = f"{metric}: insufficient data ({e})"
                    metrics_skipped.append(reason)
                    logger.debug(
                        "Metric skipped - insufficient data",
                        extra={"metric": metric, "error": str(e)},
                    )

                except ExtractionError as e:
                    reason = f"{metric}: extraction failed ({e})"
                    metrics_skipped.append(reason)
                    logger.debug(
                        "Metric skipped - extraction failed",
                        extra={"metric": metric, "error": str(e)},
                    )

                except Exception as e:
                    reason = f"{metric}: {type(e).__name__}"
                    metrics_skipped.append(reason)
                    logger.warning(
                        "Metric forecast refresh failed",
                        extra={"metric": metric, "error": str(e)},
                    )

    except TimeoutError:
        error_message = f"Forecast refresh timed out after {timeout} seconds"
        logger.warning(
            "Forecast refresh timeout",
            extra={
                "doc_filename": document_metadata.filename,
                "timeout_seconds": timeout,
                "metrics_refreshed": metrics_refreshed,
            },
        )

    except Exception as e:
        error_message = f"Forecast refresh failed: {e}"
        logger.error(
            "Forecast refresh failed",
            extra={"doc_filename": document_metadata.filename, "error": str(e)},
            exc_info=True,
        )

    duration_ms = int((time.time() - start_time) * 1000)

    result = ForecastRefreshResult(
        document_id=document_metadata.filename,
        metrics_refreshed=metrics_refreshed,
        metrics_skipped=metrics_skipped,
        refresh_duration_ms=duration_ms,
        success=len(metrics_refreshed) > 0 or error_message is None,
        error_message=error_message,
    )

    logger.info(
        "Forecast refresh complete",
        extra={
            "doc_filename": document_metadata.filename,
            "metrics_refreshed": metrics_refreshed,
            "metrics_skipped_count": len(metrics_skipped),
            "duration_ms": duration_ms,
            "success": result.success,
        },
    )

    return result
