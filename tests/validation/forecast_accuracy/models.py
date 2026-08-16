"""Data models for forecast accuracy validation.

Story 4.10 AC1: Structured validation result for MAPE comparison.
"""

from dataclasses import dataclass


@dataclass
class ForecastValidationResult:
    """Result of forecast accuracy validation.

    Story 4.10 AC1: Structured validation result for MAPE comparison.

    Attributes:
        metric_name: Name of the validated metric
        mape: Mean Absolute Percentage Error (percentage)
        passed: Whether MAPE meets ±15% threshold (NFR10)
        data_points_train: Number of training data points
        data_points_test: Number of test data points
        actuals: Actual values from holdout set
        predictions: Predicted values for holdout set
        per_period_errors: List of per-period absolute percentage errors
    """

    metric_name: str
    mape: float
    passed: bool
    data_points_train: int
    data_points_test: int
    actuals: list[float]
    predictions: list[float]
    per_period_errors: list[float]
