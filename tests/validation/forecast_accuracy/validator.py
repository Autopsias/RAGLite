"""Forecast accuracy validator implementation.

Story 4.10 AC1/AC2: Backtesting framework for Prophet forecasts.
Uses 80% train / 20% test holdout methodology.
"""

from unittest.mock import AsyncMock, patch

import numpy as np
import pandas as pd

from raglite.forecasting.hybrid import MIN_DATA_POINTS, generate_forecast
from raglite.shared.models import TimeSeriesData, TimeSeriesPoint

from .models import ForecastValidationResult


class ForecastAccuracyValidator:
    """Validates forecast accuracy against NFR10 ±15% threshold.

    Story 4.10 AC1/AC2: Backtesting framework for Prophet forecasts.
    Uses 80% train / 20% test holdout methodology.

    Example:
        >>> validator = ForecastAccuracyValidator()
        >>> result = await validator.validate_forecasts(historical_data)
        >>> assert result.passed  # MAPE ≤ 15%
    """

    def __init__(self, threshold_pct: float = 15.0):
        """Initialize validator with MAPE threshold.

        Args:
            threshold_pct: Maximum acceptable MAPE (default 15.0 per NFR10)
        """
        self.threshold_pct = threshold_pct

    def calculate_mape(
        self,
        actuals: pd.Series | list[float],
        predictions: pd.Series | list[float],
    ) -> float:
        """Calculate Mean Absolute Percentage Error.

        Story 4.10 AC1: MAPE = mean(abs((actual - predicted) / actual) * 100)

        Args:
            actuals: Series of actual values
            predictions: Series of predicted values

        Returns:
            MAPE as percentage (e.g., 12.5 means 12.5% error)

        Raises:
            ValueError: If arrays have different lengths or all actuals are zero

        Example:
            >>> mape = validator.calculate_mape([100, 110, 120], [105, 115, 125])
            >>> assert abs(mape - 4.5) < 0.1  # ~4.5% error
        """
        actuals_arr = np.array(actuals)
        predictions_arr = np.array(predictions)

        if len(actuals_arr) != len(predictions_arr):
            raise ValueError(
                f"Arrays must have same length. Got {len(actuals_arr)} vs {len(predictions_arr)}"
            )

        if len(actuals_arr) == 0:
            raise ValueError("Cannot calculate MAPE on empty arrays")

        # Filter out zero values to avoid division by zero
        # Use SMAPE fallback for zero values
        non_zero_mask = actuals_arr != 0
        if not np.any(non_zero_mask):
            # All zeros - use SMAPE (Symmetric MAPE) as fallback
            return self._calculate_smape(actuals_arr, predictions_arr)

        # Calculate MAPE only for non-zero actuals
        filtered_actuals = actuals_arr[non_zero_mask]
        filtered_predictions = predictions_arr[non_zero_mask]

        percentage_errors = (
            np.abs((filtered_actuals - filtered_predictions) / filtered_actuals) * 100
        )

        return float(np.mean(percentage_errors))

    def _calculate_smape(
        self,
        actuals: np.ndarray,
        predictions: np.ndarray,
    ) -> float:
        """Calculate Symmetric Mean Absolute Percentage Error (fallback for zero values).

        SMAPE = mean(2 * |actual - predicted| / (|actual| + |predicted|)) * 100

        Args:
            actuals: Array of actual values
            predictions: Array of predicted values

        Returns:
            SMAPE as percentage
        """
        denominator = np.abs(actuals) + np.abs(predictions)
        # Avoid division by zero when both are zero
        mask = denominator != 0
        if not np.any(mask):
            return 0.0  # Both arrays are all zeros

        smape = np.mean(2 * np.abs(actuals[mask] - predictions[mask]) / denominator[mask]) * 100
        return float(smape)

    def get_per_period_errors(
        self,
        actuals: list[float],
        predictions: list[float],
    ) -> list[float]:
        """Calculate per-period absolute percentage errors.

        Args:
            actuals: List of actual values
            predictions: List of predicted values

        Returns:
            List of absolute percentage errors per period
        """
        errors = []
        for actual, predicted in zip(actuals, predictions, strict=False):
            if actual != 0:
                error = abs((actual - predicted) / actual) * 100
            else:
                # Use absolute error for zero actuals
                error = abs(predicted) * 100 if predicted != 0 else 0.0
            errors.append(error)
        return errors

    async def validate_forecasts(
        self,
        historical_data: pd.DataFrame,
        metric_name: str = "metric",
        train_ratio: float = 0.8,
    ) -> ForecastValidationResult:
        """Run backtesting validation on historical data.

        Story 4.10 AC1/AC2: Train on 80%, test on 20%, validate MAPE ≤15%.

        Args:
            historical_data: DataFrame with 'ds' (date) and 'y' (value) columns
            metric_name: Name of the metric being validated
            train_ratio: Proportion of data for training (default 0.8)

        Returns:
            ForecastValidationResult with MAPE per metric and pass/fail status

        Raises:
            ValueError: If insufficient data points (<MIN_DATA_POINTS)
        """
        if len(historical_data) < MIN_DATA_POINTS:
            raise ValueError(
                f"Insufficient data for validation. Need {MIN_DATA_POINTS}+, got {len(historical_data)}"
            )

        # Sort by date
        df = historical_data.sort_values("ds").reset_index(drop=True)

        # Split into train/test
        split_idx = int(len(df) * train_ratio)
        train_df = df.iloc[:split_idx]
        test_df = df.iloc[split_idx:]

        if len(test_df) == 0:
            raise ValueError("Test set is empty. Need more data or lower train_ratio")

        # Create TimeSeriesData for training
        train_points = [
            TimeSeriesPoint(date=row["ds"], value=row["y"]) for _, row in train_df.iterrows()
        ]
        train_data = TimeSeriesData(
            metric_name=metric_name,
            points=train_points,
            interval="quarterly",
            source_documents=["validation_test"],
        )

        # Generate forecasts for holdout period
        periods_ahead = len(test_df)

        # Mock LLM call for faster validation
        with patch("raglite.forecasting.hybrid.ensemble.get_mistral_client") as mock_client:
            mock_response = AsyncMock()
            mock_response.choices = [
                AsyncMock(message=AsyncMock(content='{"summary": "Test forecast"}'))
            ]
            mock_client.return_value.chat.complete.return_value = mock_response

            # Story 8 fix: Patch ensure_historical_data where it's used in ensemble.py
            with patch(
                "raglite.forecasting.hybrid.ensemble.ensure_historical_data",
                new_callable=AsyncMock,
            ) as mock_fetch:
                # Use AsyncMock for async function
                mock_fetch.return_value = train_data
                forecast_result = await generate_forecast(
                    metric=metric_name,
                    periods_ahead=periods_ahead,
                )

        # Extract predictions and actuals
        predictions = [p.value for p in forecast_result.forecast]
        actuals = test_df["y"].tolist()

        # Ensure we have matching lengths (Prophet may generate extra points)
        min_len = min(len(predictions), len(actuals))
        predictions = predictions[:min_len]
        actuals = actuals[:min_len]

        # Calculate MAPE
        mape = self.calculate_mape(actuals, predictions)
        per_period_errors = self.get_per_period_errors(actuals, predictions)

        return ForecastValidationResult(
            metric_name=metric_name,
            mape=mape,
            passed=mape <= self.threshold_pct,
            data_points_train=len(train_df),
            data_points_test=len(test_df),
            actuals=actuals,
            predictions=predictions,
            per_period_errors=per_period_errors,
        )
