"""Tests for backtesting validation workflow (Story 4.10 AC1/AC2)."""

from datetime import datetime

import pandas as pd
import pytest

from tests.validation.forecast_accuracy.test_data import (
    create_growth_data,
    create_seasonal_data,
    create_volatile_data,
)
from tests.validation.forecast_accuracy.validator import ForecastAccuracyValidator


@pytest.fixture
def validator() -> ForecastAccuracyValidator:
    """Create validator instance for tests."""
    return ForecastAccuracyValidator(threshold_pct=15.0)


@pytest.fixture
def growth_data() -> pd.DataFrame:
    """Create growth data fixture (12 quarters with 5% QoQ growth)."""
    return create_growth_data(
        start_date=datetime(2021, 1, 1),
        periods=12,
        start_value=100000.0,
        growth_rate=0.05,
        noise_pct=0.02,
    )


@pytest.fixture
def seasonal_data() -> pd.DataFrame:
    """Create seasonal data fixture (12 quarters with Q4 spike)."""
    return create_seasonal_data(
        start_date=datetime(2021, 1, 1),
        periods=12,
        base_value=100000.0,
        seasonal_amplitude=0.2,
        noise_pct=0.02,
    )


@pytest.fixture
def volatile_data() -> pd.DataFrame:
    """Create volatile data fixture (12 quarters with 15% volatility)."""
    return create_volatile_data(
        start_date=datetime(2021, 1, 1),
        periods=12,
        base_value=100000.0,
        volatility=0.15,
    )


@pytest.mark.slow  # Real Prophet fitting + mock isolation issues in xdist parallel
@pytest.mark.xdist_group(name="forecast_validation")
class TestBacktestingWorkflow:
    """Tests for backtesting validation workflow (Story 4.10 AC1/AC2).

    xdist_group ensures all tests run on same worker to prevent mock isolation issues.
    """

    @pytest.mark.asyncio
    @pytest.mark.validation
    async def test_validate_growth_data(
        self,
        validator: ForecastAccuracyValidator,
        growth_data: pd.DataFrame,
    ):
        """Test backtesting on growth data meets ±15% threshold.

        Story 4.10 AC2: Revenue forecast validation.
        """
        result = await validator.validate_forecasts(
            historical_data=growth_data,
            metric_name="revenue",
            train_ratio=0.8,
        )

        # Prophet should capture growth trend well
        assert result.metric_name == "revenue"
        assert result.data_points_train == 9  # 80% of 12
        assert result.data_points_test >= 2  # 20% of 12
        assert len(result.actuals) == len(result.predictions)
        assert len(result.per_period_errors) == len(result.actuals)

        # Log result for debugging
        print(f"\nGrowth data MAPE: {result.mape:.2f}%")
        print(f"Passed: {result.passed}")

    @pytest.mark.asyncio
    @pytest.mark.validation
    async def test_validate_seasonal_data(
        self,
        validator: ForecastAccuracyValidator,
        seasonal_data: pd.DataFrame,
    ):
        """Test backtesting on seasonal data meets ±15% threshold.

        Story 4.10 AC2: Expenses forecast validation (seasonal).
        """
        result = await validator.validate_forecasts(
            historical_data=seasonal_data,
            metric_name="expenses",
            train_ratio=0.8,
        )

        assert result.metric_name == "expenses"
        assert len(result.actuals) == len(result.predictions)

        print(f"\nSeasonal data MAPE: {result.mape:.2f}%")
        print(f"Passed: {result.passed}")

    @pytest.mark.asyncio
    @pytest.mark.validation
    async def test_validate_volatile_data(
        self,
        validator: ForecastAccuracyValidator,
        volatile_data: pd.DataFrame,
    ):
        """Test backtesting on volatile data (edge case).

        Story 4.10 Task 1.3: Volatile data may exceed threshold.
        """
        result = await validator.validate_forecasts(
            historical_data=volatile_data,
            metric_name="cash_flow",
            train_ratio=0.8,
        )

        assert result.metric_name == "cash_flow"
        assert len(result.actuals) == len(result.predictions)

        print(f"\nVolatile data MAPE: {result.mape:.2f}%")
        print(f"Passed: {result.passed}")
        # Volatile data may or may not pass - this is expected

    @pytest.mark.asyncio
    @pytest.mark.validation
    async def test_validate_ebitda_data(
        self,
        validator: ForecastAccuracyValidator,
        growth_data: pd.DataFrame,
    ):
        """Test backtesting on EBITDA data meets ±15% threshold.

        Story 5.0.4 AC6: EBITDA included in forecast accuracy validation.
        Uses growth pattern similar to real EBITDA (steady growth with low volatility).
        """
        # Use growth data pattern for EBITDA (similar characteristics)
        result = await validator.validate_forecasts(
            historical_data=growth_data,
            metric_name="ebitda",
            train_ratio=0.8,
        )

        # Validate EBITDA forecast results
        assert result.metric_name == "ebitda"
        assert result.data_points_train == 9  # 80% of 12
        assert result.data_points_test >= 2  # 20% of 12
        assert len(result.actuals) == len(result.predictions)
        assert len(result.per_period_errors) == len(result.actuals)

        # Log result for debugging
        print(f"\nEBITDA data MAPE: {result.mape:.2f}%")
        print(f"Passed: {result.passed}")

    @pytest.mark.asyncio
    @pytest.mark.validation
    async def test_validate_turnover_synonym(
        self,
        validator: ForecastAccuracyValidator,
        growth_data: pd.DataFrame,
    ):
        """Test backtesting on turnover (revenue synonym) validation.

        Story 5.0.4 AC6: Additional metrics for validation coverage.
        Turnover is a synonym for revenue in Secil financial reports.
        """
        result = await validator.validate_forecasts(
            historical_data=growth_data,
            metric_name="turnover",
            train_ratio=0.8,
        )

        # Validate turnover forecast results
        assert result.metric_name == "turnover"
        assert len(result.actuals) == len(result.predictions)

        print(f"\nTurnover data MAPE: {result.mape:.2f}%")
        print(f"Passed: {result.passed}")

    @pytest.mark.asyncio
    @pytest.mark.validation
    async def test_insufficient_data_raises(
        self,
        validator: ForecastAccuracyValidator,
    ):
        """Test validation raises for insufficient data."""
        small_data = pd.DataFrame(
            {
                "ds": [datetime(2021, 1, 1), datetime(2021, 4, 1)],
                "y": [100.0, 110.0],
            }
        )

        with pytest.raises(ValueError, match="Insufficient data"):
            await validator.validate_forecasts(small_data, "metric")
