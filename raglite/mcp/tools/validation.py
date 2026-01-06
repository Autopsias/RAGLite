"""Validation MCP tools."""

import asyncio
from datetime import UTC, date, datetime, timedelta

from raglite.main import mcp
from raglite.shared.logging import get_logger
from raglite.shared.models import (
    ModelPerformanceDetail,
    RegressorDataPoint,
    RegressorDataResponse,
    RegressorInfo,
    RegressorListResponse,
    ValidationResponse,
    VariableValidationDetail,
)

logger = get_logger(__name__)


@mcp.tool()
async def validate_forecasting_accuracy(
    metrics: list[str] | None = None,
    mape_method: str = "holdout",
    include_model_breakdown: bool = True,
    timeout_seconds: float = 300.0,
) -> ValidationResponse:
    """Run forecasting validation and return accuracy metrics.
    Story 6.22 AC1: MCP tool for forecasting validation.
    Validates forecasting accuracy across cement industry variables using
    holdout, walk-forward, or cross-validation MAPE methods.
    Args:
        metrics: List of metric names to validate (default: all 12 cement variables)
        mape_method: MAPE calculation method - 'holdout', 'walkforward', or 'cv' (default: 'holdout')
        include_model_breakdown: Include per-model MAPE breakdown (default: True)
        timeout_seconds: Maximum execution time in seconds (default: 300.0 = 5 minutes)
    Returns:
        ValidationResponse with per-variable results, quality gate status, and summary
    Raises:
        Exception: If validation fails or times out
    """
    try:
        from scripts.validate_forecasting_unified import run_unified_validation
    except ImportError as e:
        logger.error("Failed to import validation script", extra={"error": str(e)})
        return ValidationResponse(
            timestamp=datetime.now(UTC).isoformat(),
            runtime_seconds=0.0,
            mape_method=mape_method,
            variables_tested=0,
            variables_passed=0,
            pass_rate=0.0,
            average_mape=0.0,
            quality_gate_passed=False,
            variable_cost_mape=None,
            average_mase=None,
            average_fqs=None,
            controllable_mase=None,
            controllable_fqs=None,
            variable_results=[],
            model_performance=None,
        )
    logger.info(
        "Validation started",
        extra={
            "metrics": metrics or "all",
            "mape_method": mape_method,
            "include_breakdown": include_model_breakdown,
            "timeout_seconds": timeout_seconds,
        },
    )
    try:
        result = await asyncio.wait_for(
            run_unified_validation(
                variables=metrics,
                mape_method=mape_method,
                fail_fast=False,
                quiet=True,
            ),
            timeout=timeout_seconds,
        )
        variable_details = [
            VariableValidationDetail(
                variable_name=var_result.variable_name,
                display_name=var_result.display_name,
                target_mape=var_result.target_mape,
                actual_mape=var_result.actual_mape,
                passed=var_result.passed,
                ensemble_weights=var_result.ensemble_weights,
                best_model=var_result.best_model,
                actual_mase=var_result.metrics.mase if var_result.metrics else None,
                actual_smape=var_result.metrics.smape if var_result.metrics else None,
                actual_bias=var_result.metrics.bias if var_result.metrics else None,
                fqs=var_result.metrics.fqs if var_result.metrics else None,
                primary_metric_used=getattr(var_result, "primary_metric_used", "mape"),
                mase_only_pass=getattr(var_result, "mase_only_pass", False),
            )
            for var_result in result.variable_results
        ]
        model_perf = None
        if include_model_breakdown and result.model_performance:
            model_perf = {
                name: ModelPerformanceDetail(
                    model_name=stats.model_name,
                    avg_mape=stats.avg_mape,
                    variables_used=stats.variables_used,
                )
                for name, stats in result.model_performance.items()
            }
        logger.info(
            "Validation completed",
            extra={
                "variables_tested": result.variables_tested,
                "variables_passed": result.variables_passed,
                "runtime_seconds": result.runtime_seconds,
                "quality_gate": "PASS"
                if result.quality_gate and result.quality_gate.passed
                else "FAIL",
            },
        )
        return ValidationResponse(
            timestamp=result.timestamp,
            runtime_seconds=result.runtime_seconds,
            mape_method=result.mape_method,
            variables_tested=result.variables_tested,
            variables_passed=result.variables_passed,
            pass_rate=result.pass_rate,
            average_mape=result.average_mape,
            quality_gate_passed=result.quality_gate.passed if result.quality_gate else False,
            variable_cost_mape=result.quality_gate.variable_cost_mape
            if result.quality_gate
            else None,
            average_mase=result.average_mase,
            average_fqs=result.average_fqs,
            controllable_mase=result.quality_gate.controllable_mase
            if result.quality_gate
            else None,
            controllable_fqs=result.quality_gate.controllable_fqs if result.quality_gate else None,
            variable_results=variable_details,
            model_performance=model_perf,
        )
    except TimeoutError:
        logger.warning(
            "Validation timed out",
            extra={"timeout_seconds": timeout_seconds},
        )
        return ValidationResponse(
            timestamp=datetime.now(UTC).isoformat(),
            runtime_seconds=timeout_seconds,
            mape_method=mape_method,
            variables_tested=0,
            variables_passed=0,
            pass_rate=0.0,
            average_mape=0.0,
            quality_gate_passed=False,
            variable_cost_mape=None,
            average_mase=None,
            average_fqs=None,
            controllable_mase=None,
            controllable_fqs=None,
            variable_results=[],
            model_performance=None,
        )
    except Exception as e:
        logger.error("Validation failed", extra={"error": str(e)})
        raise


@mcp.tool()
async def list_available_regressors(
    metric: str | None = None,
) -> RegressorListResponse:
    try:
        from raglite.forecasting.regressor_config import METRIC_REGRESSORS
        from raglite.forecasting.regressor_config_data.regressor_metadata import (
            AVAILABLE_REGRESSORS,
            REGRESSOR_METADATA,
        )
    except ImportError as e:
        logger.error("Failed to import regressor config", extra={"error": str(e)})
        return RegressorListResponse(regressors=[], total_count=0, available_count=0)
    logger.info(
        "Listing regressors",
        extra={"metric_filter": metric},
    )
    if metric:
        metric_lower = metric.lower()
        # METRIC_REGRESSORS is dict[str, list[str]], returns list of regressor names
        relevant_regressors = METRIC_REGRESSORS.get(metric_lower, AVAILABLE_REGRESSORS)
    else:
        relevant_regressors = AVAILABLE_REGRESSORS
    regressors_info = []
    for reg_name in relevant_regressors:
        metadata = REGRESSOR_METADATA.get(reg_name, {})
        regressor_info = RegressorInfo(
            name=reg_name,
            display_name=metadata.get("display_name", reg_name.replace("_", " ").title()),
            source=metadata.get("source", "Unknown"),
            available=True,
            last_refresh=None,
            data_range=None,
            correlation=None,
            unit=metadata.get("unit"),
        )
        regressors_info.append(regressor_info)
    logger.info("Regressors listed", extra={"count": len(regressors_info)})
    return RegressorListResponse(
        regressors=regressors_info,
        total_count=len(regressors_info),
        available_count=len(regressors_info),
    )


@mcp.tool()
async def get_regressor_data(
    regressor: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> RegressorDataResponse:
    from raglite.forecasting.regressor_config_data.regressor_metadata import (
        REGRESSOR_METADATA,
    )
    from raglite.forecasting.regressor_fetch import fetch_single_regressor

    logger.info(
        "Fetching regressor data",
        extra={"regressor": regressor, "start_date": start_date, "end_date": end_date},
    )
    if start_date:
        start = date.fromisoformat(start_date)
    else:
        start = date.today() - timedelta(days=730)
    if end_date:
        end = date.fromisoformat(end_date)
    else:
        end = date.today()
    metadata = REGRESSOR_METADATA.get(regressor)
    if not metadata:
        raise ValueError(f"Unknown regressor: {regressor}")
    try:
        series = await fetch_single_regressor(regressor, start, end)
        if series is None or series.empty:
            raise Exception(f"No data returned for {regressor}")
        data_points = []
        for date_val, value in series.items():
            if hasattr(date_val, "date"):
                point_date = date_val.date()
            else:
                point_date = date_val
            data_points.append(RegressorDataPoint(date=point_date, value=float(value)))
        logger.info(
            "Regressor data fetched",
            extra={"regressor": regressor, "points": len(data_points)},
        )
        date_range_str = f"{data_points[0].date} to {data_points[-1].date}"
        return RegressorDataResponse(
            regressor_name=regressor,
            display_name=metadata["display_name"],
            source=metadata["source"],
            unit=metadata.get("unit"),
            data_points=data_points,
            record_count=len(data_points),
            date_range=date_range_str,
            visualization_hint="line_chart",
        )
    except Exception as e:
        logger.error(
            "Failed to fetch regressor data", extra={"regressor": regressor, "error": str(e)}
        )
        raise
