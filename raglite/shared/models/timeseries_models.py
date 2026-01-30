"""Time series and forecasting models.

Defines models for time series data, forecasts, and forecast validation.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field, field_serializer

if TYPE_CHECKING:
    import pandas as pd


# Story 4.1: Time-series data extraction models for forecasting
class TimeSeriesPoint(BaseModel):
    """Single data point in a time series.

    Story 4.1 AC2: Data points extracted with timestamps and metric labels.

    Attributes:
        date: Datetime of the data point
        value: Numeric value for the metric
        label: Optional label like "Q3 2024" or "Jan 2024"
    """

    date: datetime = Field(..., description="Datetime of the data point")
    value: float = Field(..., description="Numeric value for the metric")
    label: str | None = Field(default=None, description="Optional label like 'Q3 2024'")

    @field_serializer("date")
    def serialize_datetime(self, dt: datetime) -> str:
        """Ensure datetime is serialized as ISO 8601 with time component."""
        return dt.isoformat()


class TimeSeriesData(BaseModel):
    """Time series data for a financial metric.

    Story 4.1 AC1-AC4: Collection of time series data points with metadata.

    Attributes:
        metric_name: Name of the metric (revenue, expenses, ebitda, etc.)
        points: List of TimeSeriesPoint objects sorted by date
        interval: Time interval: "raw", "monthly", "quarterly", "yearly"
        source_documents: List of source document filenames
    """

    metric_name: str = Field(..., description="Name of the financial metric")
    points: list[TimeSeriesPoint] = Field(
        default_factory=list, description="Data points sorted by date"
    )
    interval: str = Field(
        default="raw",
        description="Time interval: 'raw', 'monthly', 'quarterly', 'yearly'",
    )
    source_documents: list[str] = Field(
        default_factory=list, description="Source document filenames"
    )

    @classmethod
    def from_series(cls, series: "pd.Series", metric_name: str = "unknown") -> "TimeSeriesData":
        """Create TimeSeriesData from a pandas Series.

        Phase 5 fix (2026-01-29): Allow conversion from pandas Series to TimeSeriesData
        for type consistency in forecasting pipelines.

        Args:
            series: pandas Series with DatetimeIndex and numeric values
            metric_name: Name of the metric

        Returns:
            TimeSeriesData object
        """
        import pandas as pd

        points = []
        for date, value in series.items():
            # Handle both Timestamp and datetime
            if isinstance(date, pd.Timestamp):
                dt = date.to_pydatetime()
            else:
                dt = (
                    datetime.combine(date, datetime.min.time())
                    if not isinstance(date, datetime)
                    else date
                )
            points.append(TimeSeriesPoint(date=dt, value=float(value)))

        return cls(
            metric_name=metric_name,
            points=sorted(points, key=lambda p: p.date),
            interval="monthly",  # Assume monthly for financial data
            source_documents=[],
        )

    @property
    def values(self) -> "pd.Series":
        """Convert to pandas Series for compatibility with forecasting models.

        Phase 5 fix (2026-01-29): Provide pandas Series interface for models expecting Series.
        """
        import pandas as pd

        dates = [p.date for p in self.points]
        values = [p.value for p in self.points]
        return pd.Series(values, index=pd.DatetimeIndex(dates))


# Story 4.2: Forecasting engine models for Prophet + LLM hybrid approach
class ForecastPoint(BaseModel):
    """Single forecast data point with confidence interval.

    Story 4.2 AC3: Forecast predictions with confidence intervals (FR19).

    Attributes:
        date: Datetime of the forecast point
        value: Predicted value (yhat from Prophet)
        lower: Lower bound of confidence interval (yhat_lower)
        upper: Upper bound of confidence interval (yhat_upper)
        label: Optional label like "Q1 2025" for display
    """

    date: datetime = Field(..., description="Datetime of the forecast point")
    value: float = Field(..., description="Predicted value (yhat)")
    lower: float = Field(..., description="Lower confidence interval (yhat_lower)")
    upper: float = Field(..., description="Upper confidence interval (yhat_upper)")
    label: str | None = Field(default=None, description="Optional label like 'Q1 2025'")

    @field_serializer("date")
    def serialize_datetime(self, dt: datetime) -> str:
        """Ensure datetime is serialized as ISO 8601 with time component.

        MCP schema validation requires 'date-time' format (e.g., '2026-02-01T00:00:00')
        not just 'date' format (e.g., '2026-02-01').
        """
        return dt.isoformat()


class ForecastResult(BaseModel):
    """Complete forecast result with predictions and reasoning.

    Story 4.2 AC1-AC7: Hybrid forecasting output combining Prophet predictions
    with LLM-generated reasoning and confidence rationale.

    Story 6.3: Extended with multi-variate forecasting fields.
    Story 6.4: Extended with ensemble model fields for multi-model forecasting.

    Attributes:
        metric_name: Name of forecasted metric (revenue, cash_flow, expenses)
        historical_data: Original time-series input data
        forecast: List of ForecastPoint predictions
        confidence_reasoning: LLM-generated explanation of confidence intervals
        basis: Description of forecast basis (e.g., "Prophet model trained on 8 quarters")
        accuracy_estimate: Expected accuracy (e.g., "±15% per NFR10")
        periods_ahead: Number of periods forecasted
        model_type: Model type - 'prophet_univariate', 'prophet_multivariate', or 'ensemble'
        accuracy_metrics: Accuracy metrics from cross-validation (RMSE, MAE, MAPE)
        regressors_used: List of external regressors used in multi-variate forecast
        improvement_vs_baseline: Percentage improvement vs Epic 4 baseline RMSE
        ensemble_models: List of models used in ensemble (Story 6.4)
        individual_predictions: Per-model predictions for transparency (Story 6.4)
        ensemble_weights: Model weights used for weighted average (Story 6.4)
    """

    metric_name: str = Field(..., description="Name of forecasted metric")
    historical_data: list[TimeSeriesPoint] = Field(
        default_factory=list, description="Original time-series input data"
    )
    forecast: list[ForecastPoint] = Field(
        default_factory=list,
        description="Forecast predictions with confidence intervals",
    )
    confidence_reasoning: str = Field(
        default="", description="LLM-generated explanation of confidence intervals"
    )
    basis: str = Field(
        default="",
        description="Forecast basis (e.g., 'Prophet model trained on 8 quarters')",
    )
    accuracy_estimate: str = Field(default="±15%", description="Expected accuracy per NFR10")
    periods_ahead: int = Field(default=4, description="Number of periods forecasted")

    # Story 6.3: Multi-variate forecasting fields
    model_type: str = Field(
        default="prophet_univariate",
        description="Model type: 'prophet_univariate' or 'prophet_multivariate'",
    )
    accuracy_metrics: dict[str, float] = Field(
        default_factory=dict,
        description="Accuracy metrics: {'rmse': X, 'mae': Y, 'mape': Z}",
    )
    regressors_used: list[str] = Field(
        default_factory=list,
        description="List of external regressors used in forecast",
    )
    improvement_vs_baseline: float | None = Field(
        default=None,
        description="Percentage improvement vs Epic 4 baseline RMSE",
    )

    # Story 6.4: Ensemble forecasting fields
    ensemble_models: list[str] = Field(
        default_factory=list,
        description="Models used in ensemble: ['prophet', 'linear', 'xgboost']",
    )
    individual_predictions: dict[str, list[float]] = Field(
        default_factory=dict,
        description="Per-model predictions: {'prophet': [1.2, 1.3], 'linear': [1.1, 1.4]}",
    )
    ensemble_weights: dict[str, float] = Field(
        default_factory=dict,
        description="Model weights: {'prophet': 0.4, 'linear': 0.3, 'xgboost': 0.3}",
    )

    # Story 7b-6: Model selection metadata
    model_source: Literal["cached", "default", "fallback"] = Field(
        default="default",
        description="Source of model selection: 'cached' (from model_selection table), 'default' (no cache), 'fallback' (error recovery)",
    )
    model_selection_reason: str | None = Field(
        default=None,
        description="Human-readable explanation of why this model was selected",
    )


# Story 4.3: Automated forecast updates models
class ForecastRefreshResult(BaseModel):
    """Result of automatic forecast refresh after document ingestion.

    Story 4.3 AC1/AC4: Returned from trigger_forecast_refresh() and included
    in MCP ingestion response to notify users of updated forecasts.

    Attributes:
        document_id: Identifier of the ingested document that triggered refresh
        metrics_refreshed: List of metrics successfully refreshed (e.g., ["revenue"])
        metrics_skipped: List of metrics skipped with reasons (e.g., ["expenses: insufficient data"])
        refresh_duration_ms: Time taken for forecast refresh in milliseconds
        success: Whether refresh completed successfully (partial success = True)
        error_message: Error details if refresh failed completely
    """

    document_id: str = Field(..., description="Document ID that triggered the refresh")
    metrics_refreshed: list[str] = Field(
        default_factory=list, description="Metrics successfully refreshed"
    )
    metrics_skipped: list[str] = Field(
        default_factory=list, description="Metrics skipped with reasons"
    )
    refresh_duration_ms: int = Field(..., description="Refresh duration in milliseconds")
    success: bool = Field(..., description="Whether refresh completed successfully")
    error_message: str | None = Field(default=None, description="Error message if failed")


# Story 4.4: Forecast Query Tool MCP models
class ForecastQueryRequest(BaseModel):
    """Request for financial forecast query via MCP.

    Story 4.4 AC1: MCP tool parameters for forecast queries.
    Story 5.0.1 Enhancement: Supports SQL-based extraction for any metric in database.
    Story 6.4 Enhancement: Supports ensemble forecasting with multiple models.
    Forecast debug fix (2026-01-28): Added target_year for year-based forecasting.
    Supports both structured parameters and natural language queries.

    Attributes:
        metric: Metric to forecast (e.g., revenue, turnover, ebitda, cash_flow, expenses, capex).
                Accepts any financial metric name - will search database via SQL and documents via hybrid search.
        periods_ahead: Number of periods to forecast (1-18, default 4). Ignored if target_year is set.
        target_year: Target year for forecast (e.g., 2026). Dynamically calculates periods_ahead
                     based on last historical data point to cover full year.
        query: Optional natural language query (e.g., "turnover forecast next quarter").
        model_type: Forecasting model type: 'prophet' (default), 'ensemble', or 'prophet_multivariate'.
    """

    metric: str | None = Field(
        default=None,
        description="Metric to forecast: revenue, turnover, cash_flow, expenses, ebitda, capex, or any financial metric name",
    )
    # Multi-geography support: Allows forecasting for specific regions
    # When None, defaults to config-based entity (GROUP for EBITDA, etc.)
    entity: str | None = Field(
        default=None,
        description=(
            "Entity/geography to forecast: 'GROUP' (consolidated, default for EBITDA), "
            "'Portugal', 'Brazil', 'Tunisia', 'Lebanon', 'Angola'. "
            "If not specified, uses config-based default for the metric."
        ),
    )
    periods_ahead: int = Field(
        default=4,
        ge=1,
        le=18,
        description="Number of periods to forecast (1-18). Ignored if target_year is set.",
    )
    # Forecast debug fix (2026-01-28): Add target_year for year-based forecasting
    target_year: int | None = Field(
        default=None,
        description=(
            "Target year for forecast (e.g., 2026). When set, periods_ahead is dynamically calculated "
            "to cover from last historical data point through December of target year. "
            "Takes precedence over periods_ahead when set."
        ),
    )
    query: str | None = Field(
        default=None,
        description="Optional natural language query (e.g., 'revenue forecast next quarter')",
    )
    model_type: str = Field(
        default="auto",
        description=(
            "Forecasting model selection: "
            "'auto' (intelligent selection based on metric and context), "
            "'prophet' (fast ~21s, recommended for most queries), "
            "'ensemble' (slower ~78s, Prophet+Linear+XGBoost+LightGBM, use with prefer_accuracy=True)"
        ),
    )
    # Story 6.11.6: Intelligent model selection parameter
    prefer_accuracy: bool = Field(
        default=False,
        description=(
            "When model_type='auto': Set True to prefer ensemble model for potentially higher accuracy "
            "(accepts ~3.7x slower execution: ~78s vs ~21s). Recommended for high-stakes financial forecasts."
        ),
    )
    # Story 6.11.1: Multi-variate forecasting parameters
    use_external_regressors: bool = Field(
        default=True,
        description="Enable multi-variate forecasting with external economic indicators (97% accuracy improvement)",
    )
    regressor_names: list[str] | None = Field(
        default=None,
        description="Specific regressors to use (auto-selected if None). Options: euribor_3m, ttf_gas, api2_coal, diesel, eurostat_electricity",
    )
    future_regressor_strategy: str = Field(
        default="constant",
        description="Strategy for future regressor values: 'constant' (last value), 'extrapolate' (trend)",
    )


class ForecastQueryResponse(BaseModel):
    """Response for financial forecast query via MCP.

    Story 4.4 AC2/AC3: Forecast results with confidence intervals and explanations.
    Forecast debug fix (2026-01-28): Added forecast date range fields for clarity.

    Attributes:
        metric_name: Name of forecasted metric.
        forecast: List of ForecastPoint predictions with confidence intervals.
        basis: Description of historical data used for forecast.
        confidence_reasoning: LLM-generated explanation of forecast confidence.
        methodology: Forecasting methodology description.
        accuracy_estimate: Expected forecast accuracy (±15% per NFR10).
        source_documents: Documents used for time-series data extraction.
        periods_ahead: Number of periods forecasted.
        forecast_start_date: First forecasted period (ISO date string).
        forecast_end_date: Last forecasted period (ISO date string).
        last_historical_date: Last actual data point date (ISO date string).
    """

    metric_name: str = Field(..., description="Name of forecasted metric")
    forecast: list[ForecastPoint] = Field(
        default_factory=list,
        description="Forecast predictions with confidence intervals",
    )
    basis: str = Field(
        ...,
        description="Description of historical data used for forecast",
    )
    confidence_reasoning: str = Field(
        default="",
        description="LLM-generated explanation of forecast confidence",
    )
    methodology: str = Field(
        default="Prophet + Mistral Large hybrid forecasting",
        description="Forecasting methodology description",
    )
    accuracy_estimate: str = Field(
        default="±15% (NFR10 target)",
        description="Expected forecast accuracy",
    )
    source_documents: list[str] = Field(
        default_factory=list,
        description="Documents used for time-series data extraction",
    )
    periods_ahead: int = Field(..., description="Number of periods forecasted")
    # Forecast debug fix (2026-01-28): Add forecast date range fields for user clarity
    forecast_start_date: str | None = Field(
        default=None,
        description="First forecasted period date (ISO 8601 format, e.g., '2025-12-01')",
    )
    forecast_end_date: str | None = Field(
        default=None,
        description="Last forecasted period date (ISO 8601 format, e.g., '2026-11-01')",
    )
    last_historical_date: str | None = Field(
        default=None,
        description="Last actual data point date before forecast (ISO 8601 format)",
    )
    # Story 6.11.1: Multi-variate forecasting response fields
    regressors_used: list[str] | None = Field(
        default=None,
        description="External regressors used in forecast (e.g., euribor_3m, ttf_gas)",
    )
    model_type: str = Field(
        default="prophet_univariate",
        description="Forecasting model type used: prophet_univariate, prophet_multivariate, ensemble",
    )
    # Story 6.11.6: Model selection explanation
    model_selection_reason: str | None = Field(
        default=None,
        description="Explanation of why this model was selected (when model_type='auto' was used)",
    )
    # Story 7b-6: Model selection source
    model_source: str = Field(
        default="default",
        description="Source of model selection: 'cached', 'default', or 'fallback'",
    )
    # Story 6.25: Accuracy metrics from Prophet cross-validation
    accuracy_metrics: dict[str, float] | None = Field(
        default=None,
        description="Model accuracy metrics from cross-validation: {'mape': X, 'rmse': Y, 'mae': Z}",
    )

    @classmethod
    def from_forecast_result(
        cls,
        result: "ForecastResult",
        source_documents: list[str] | None = None,
        regressors_used: list[str] | None = None,
        model_type: str = "prophet_univariate",
        model_selection_reason: str | None = None,
    ) -> "ForecastQueryResponse":
        """Create ForecastQueryResponse from ForecastResult.

        Story 4.4 AC2/AC3: Factory method for MCP response creation.
        Story 6.11.1: Added regressors_used and model_type parameters.
        Story 6.11.6: Added model_selection_reason for auto-selection transparency.
        Story 7b-6: Auto-populate model_source and model_selection_reason from ForecastResult.

        Args:
            result: ForecastResult from generate_forecast()
            source_documents: List of source document filenames
            regressors_used: List of external regressors used in forecast
            model_type: Forecasting model type used
            model_selection_reason: Explanation for model selection (when auto-selected)
                                   DEPRECATED: Use result.model_selection_reason instead

        Returns:
            ForecastQueryResponse with all fields populated
        """
        return cls(
            metric_name=result.metric_name,
            forecast=result.forecast,
            basis=result.basis,
            confidence_reasoning=result.confidence_reasoning,
            methodology="Prophet + Mistral Large hybrid forecasting",
            accuracy_estimate=result.accuracy_estimate,
            source_documents=source_documents or [],
            periods_ahead=result.periods_ahead,
            regressors_used=regressors_used,
            model_type=model_type,
            # Story 7b-6: Auto-populate from ForecastResult, fallback to parameter
            model_selection_reason=result.model_selection_reason or model_selection_reason,
            model_source=result.model_source,
            # Story 6.25: Include accuracy metrics from Prophet cross-validation
            accuracy_metrics=result.accuracy_metrics if result.accuracy_metrics else None,
        )


# Async forecast job models (moved to forecast_jobs.py for MCP timeout resolution)
# These are re-exported via __init__.py for backward compatibility
